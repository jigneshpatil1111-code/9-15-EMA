"""Analytics page — Deep analysis of trading performance."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from datetime import date, timedelta
import pandas as pd

st.set_page_config(page_title="Analytics", page_icon="🔬", layout="wide")
st.title("🔬 Trading Analytics")

try:
    from database.trade_repository import TradeRepository
    from dashboard.components.charts import create_setup_comparison, create_monthly_heatmap

    repo = TradeRepository()
    today = date.today()

    # Period selector
    period = st.selectbox(
        "Analysis Period",
        ["Last 30 Days", "Last 90 Days", "Last 6 Months", "This Year", "All Time"],
    )
    period_map = {"Last 30 Days": 30, "Last 90 Days": 90, "Last 6 Months": 180, "This Year": 365, "All Time": 3650}
    start = today - timedelta(days=period_map[period])

    stats = repo.get_performance_stats(start, today)

    # Setup comparison
    st.subheader("📊 Setup Comparison")
    setup_stats = repo.get_pnl_by_setup(start, today)
    if setup_stats:
        st.plotly_chart(create_setup_comparison(setup_stats), use_container_width=True)

        col1, col2 = st.columns(2)
        for setup, data in setup_stats.items():
            name = "1% Setup" if setup == "1_pct_setup" else "EMA Pullback"
            col = col1 if setup == "1_pct_setup" else col2
            with col:
                st.markdown(f"**{name}**")
                st.metric("Trades", str(data["total"]))
                st.metric("Win Rate", f"{data['win_rate']:.1f}%")
                st.metric("P&L", f"₹{data['total_pnl']:,.2f}")

    st.markdown("---")

    # Top and worst performers
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 Best Performing Stocks")
        top = repo.get_top_performers(start, today, limit=10)
        if top:
            st.dataframe(pd.DataFrame(top), use_container_width=True)
        else:
            st.info("No data yet.")

    with col2:
        st.subheader("📉 Worst Performing Stocks")
        worst = repo.get_worst_performers(start, today, limit=10)
        if worst:
            st.dataframe(pd.DataFrame(worst), use_container_width=True)
        else:
            st.info("No data yet.")

    st.markdown("---")

    # Win Rate by Setup
    st.subheader("📊 Detailed Statistics")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Holding Time", f"{stats.get('avg_holding_time', 0):.0f} min")
    with col2:
        st.metric("Profit Factor", f"{stats.get('profit_factor', 0):.2f}")
    with col3:
        st.metric("Avg RR Achieved", f"{stats.get('avg_rr', 0):.2f}")
    with col4:
        st.metric("Max Drawdown", f"₹{stats.get('max_drawdown', 0):,.2f}")

    # Monthly growth
    st.markdown("---")
    st.subheader("📊 Monthly Growth")
    equity_data = repo.get_equity_curve(start, today)
    if equity_data:
        df = pd.DataFrame(equity_data)
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.to_period("M").astype(str)
        monthly = df.groupby("month")["daily_pnl"].sum().to_dict()
        st.plotly_chart(create_monthly_heatmap(monthly), use_container_width=True)

except Exception as e:
    st.info("Analytics will populate as trades are recorded.")
    st.caption(str(e))
