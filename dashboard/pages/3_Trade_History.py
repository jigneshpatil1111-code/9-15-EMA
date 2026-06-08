"""Trade History & Journal page."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from datetime import date, timedelta
import pandas as pd

st.set_page_config(page_title="Trade History", page_icon="📜", layout="wide")
st.title("📜 Trade History & Journal")

try:
    from database.trade_repository import TradeRepository

    repo = TradeRepository()

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("From", value=date.today() - timedelta(days=30))
    with col2:
        end = st.date_input("To", value=date.today())

    # Filters
    col3, col4 = st.columns(2)
    with col3:
        setup_filter = st.selectbox("Setup Type", ["All", "1% Setup", "EMA Pullback"])
    with col4:
        status_filter = st.selectbox("Status", ["All", "closed", "active", "imported"])

    # Fetch trades
    trades_data = repo.get_all_trades_dataframe(start, end)

    if trades_data:
        df = pd.DataFrame(trades_data)

        # Apply filters
        if setup_filter == "1% Setup":
            df = df[df["setup_type"] == "1_pct_setup"]
        elif setup_filter == "EMA Pullback":
            df = df[df["setup_type"] == "ema_pullback"]

        if status_filter != "All":
            df = df[df["status"] == status_filter]

        # Display
        st.markdown(f"**{len(df)} trades found**")

        display_df = df[[
            "symbol", "date", "setup_type", "entry_price", "stop_loss",
            "exit_price", "pnl", "risk_reward", "rr_achieved",
            "signal_score", "status", "exit_reason",
        ]].copy()
        display_df.columns = [
            "Symbol", "Date", "Setup", "Entry", "SL",
            "Exit", "P&L", "RR", "RR Achieved",
            "Score", "Status", "Exit Reason",
        ]

        st.dataframe(display_df, use_container_width=True, height=500)

        # Summary stats
        st.markdown("---")
        st.subheader("📊 Period Summary")

        closed_df = df[df["status"] == "closed"]
        if not closed_df.empty:
            total_pnl = closed_df["pnl"].sum()
            wins = len(closed_df[closed_df["pnl"] > 0])
            losses = len(closed_df[closed_df["pnl"] < 0])
            total = len(closed_df)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total P&L", f"₹{total_pnl:,.2f}")
            with col2:
                st.metric("Win Rate", f"{wins/total*100:.1f}%" if total > 0 else "0%")
            with col3:
                st.metric("Trades", f"{total}")
            with col4:
                avg_rr = closed_df["rr_achieved"].mean() if total > 0 else 0
                st.metric("Avg RR", f"{avg_rr:.2f}")
    else:
        st.info("No trades found for the selected period.")

except Exception as e:
    st.info("Trade history will appear after trades are recorded.")
    st.caption(str(e))
