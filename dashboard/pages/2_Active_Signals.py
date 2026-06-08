"""Active Signals page."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from datetime import date, datetime
import pandas as pd

st.set_page_config(page_title="Active Signals", page_icon="🚀", layout="wide")
st.title("🚀 Active Signals & Open Trades")

try:
    from database.trade_repository import TradeRepository

    repo = TradeRepository()
    today = date.today()

    # Active trades
    st.subheader("📈 Open Trades")
    active = repo.get_active_trades()

    if active:
        active_data = [{
            "Symbol": t.symbol,
            "Setup": "1% Setup" if t.setup_type == "1_pct_setup" else "EMA Pullback",
            "Entry": f"₹{t.entry_price:.2f}",
            "Stop Loss": f"₹{t.stop_loss:.2f}",
            "Target 1": f"₹{t.target1:.2f}",
            "Target 2": f"₹{t.target2:.2f}" if t.target2 else "—",
            "RR": f"1:{t.risk_reward:.1f}",
            "Score": f"{t.signal_score:.0f}",
            "Entry Time": t.entry_time.strftime("%H:%M") if t.entry_time else "",
        } for t in active]
        st.dataframe(pd.DataFrame(active_data), use_container_width=True)
    else:
        st.info("No open trades currently.")

    st.markdown("---")

    # Today's signals (closed)
    st.subheader("📊 Today's Closed Trades")
    closed = repo.get_closed_trades_by_date(today)

    if closed:
        closed_data = [{
            "Symbol": t.symbol,
            "Setup": "1% Setup" if t.setup_type == "1_pct_setup" else "EMA Pullback",
            "Entry": f"₹{t.entry_price:.2f}",
            "Exit": f"₹{t.exit_price:.2f}" if t.exit_price else "—",
            "P&L": f"₹{t.pnl:+.2f}",
            "RR Achieved": f"{t.rr_achieved:.2f}",
            "Exit Reason": t.exit_reason or "—",
            "Score": f"{t.signal_score:.0f}",
        } for t in closed]

        df = pd.DataFrame(closed_data)
        st.dataframe(df, use_container_width=True)

        # Summary
        total_pnl = sum(t.pnl for t in closed)
        wins = len([t for t in closed if t.pnl > 0])
        losses = len([t for t in closed if t.pnl < 0])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total P&L", f"₹{total_pnl:+,.2f}")
        with col2:
            st.metric("Wins / Losses", f"{wins} / {losses}")
        with col3:
            wr = (wins / len(closed) * 100) if closed else 0
            st.metric("Win Rate", f"{wr:.1f}%")
    else:
        st.info("No closed trades today.")

except Exception as e:
    st.info("Trade data will appear when the scanner generates signals.")
    st.caption(str(e))
