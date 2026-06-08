"""Backtesting page."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from datetime import date
import pandas as pd

st.set_page_config(page_title="Backtesting", page_icon="🧪", layout="wide")
st.title("🧪 Backtesting Engine")

st.markdown("*Run historical backtests on your strategies against Nifty 500 data*")

try:
    from core.broker_factory import get_broker
    from core.instrument_manager import InstrumentManager
    from backtesting.backtest_data import BacktestDataLoader
    from backtesting.backtest_engine import BacktestEngine
    from dashboard.components.charts import (
        create_equity_curve,
        create_pnl_bar_chart,
        create_win_rate_pie,
        create_setup_comparison,
    )

    # Configuration
    st.subheader("⚙️ Backtest Configuration")

    col1, col2, col3 = st.columns(3)
    with col1:
        period = st.selectbox("Period", ["6 Months", "1 Year", "2 Years"])
    with col2:
        initial_capital = st.number_input("Initial Capital (₹)", value=100000, step=10000)
    with col3:
        max_signals = st.number_input("Max Signals/Day", value=5, min_value=1, max_value=20)

    period_map = {"6 Months": 6, "1 Year": 12, "2 Years": 24}

    # Run backtest
    if st.button("🚀 Run Backtest", type="primary"):
        with st.spinner("Initializing broker..."):
            broker = get_broker()
            im = InstrumentManager()
            instruments = im.load()

        loader = BacktestDataLoader(broker)
        engine = BacktestEngine(loader)

        progress_bar = st.progress(0, text="Running backtest...")

        def update_progress(current, total):
            progress_bar.progress(current / total, text=f"Day {current}/{total}")

        with st.spinner("Running backtest..."):
            results = engine.run_backtest(
                instruments=instruments[:50],  # Limit for speed
                period_months=period_map[period],
                initial_capital=initial_capital,
                max_signals_per_day=max_signals,
                progress_callback=update_progress,
            )

        progress_bar.empty()

        if results.get("status") == "success":
            st.success(f"✅ Backtest complete! Period: {results['period']}")

            metrics = results["metrics"]

            # KPIs
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Trades", str(metrics["total_trades"]))
            with col2:
                st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
            with col3:
                st.metric("Total Return", f"{metrics['total_return_pct']:.2f}%")
            with col4:
                st.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
            with col5:
                st.metric("Max Drawdown", f"{metrics['max_drawdown_pct']:.2f}%")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Final Capital", f"₹{results['final_capital']:,.2f}")
            with col2:
                st.metric("Total P&L", f"₹{metrics['total_pnl']:,.2f}")
            with col3:
                st.metric("Avg RR", f"{metrics['avg_rr']:.2f}")
            with col4:
                st.metric("Avg P&L/Trade", f"₹{metrics['avg_pnl_per_trade']:.2f}")

            st.markdown("---")

            # Charts
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(
                    create_equity_curve(results["daily_pnl"]),
                    use_container_width=True,
                )
            with col2:
                st.plotly_chart(
                    create_win_rate_pie(
                        metrics["wins"], metrics["losses"], metrics["breakeven"]
                    ),
                    use_container_width=True,
                )

            st.plotly_chart(
                create_pnl_bar_chart(results["daily_pnl"]),
                use_container_width=True,
            )

            # Setup breakdown
            if metrics.get("by_setup"):
                st.plotly_chart(
                    create_setup_comparison(metrics["by_setup"]),
                    use_container_width=True,
                )

            # Trade list
            st.subheader("📋 All Backtest Trades")
            trade_df = pd.DataFrame(results["trades"])
            if not trade_df.empty:
                st.dataframe(trade_df, use_container_width=True, height=400)

            # Monthly returns
            if metrics.get("monthly_returns"):
                st.subheader("📊 Monthly Returns")
                monthly_df = pd.DataFrame(
                    list(metrics["monthly_returns"].items()),
                    columns=["Month", "P&L"],
                )
                st.dataframe(monthly_df, use_container_width=True)

        else:
            st.error(f"Backtest failed: {results.get('message', 'Unknown error')}")

except Exception as e:
    st.warning("Configure your Dhan API credentials to run backtests.")
    st.caption(str(e))
