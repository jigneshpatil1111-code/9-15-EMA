"""
Intraday Scanner — Live Trading Dashboard
==========================================
Professional real-time Streamlit dashboard.
Auto-refreshes every 30 seconds.
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st

# ── Page Config ──
st.set_page_config(
    page_title="Intraday Scanner Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.9rem;
        font-weight: 600;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }

    div[data-testid="stSidebarContent"] {
        background: linear-gradient(180deg, #0f1724 0%, #131d2f 100%);
    }

    h1, h2, h3 {
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .status-bullish {
        color: #00d26a;
        font-weight: 700;
        font-size: 1.5rem;
    }

    .status-neutral {
        color: #ffd700;
        font-weight: 700;
        font-size: 1.5rem;
    }

    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ──
with st.sidebar:
    st.markdown("## 📊 Intraday Scanner")
    st.markdown("---")
    st.markdown("**System Status**")

    # Auto-refresh toggle
    auto_refresh = st.checkbox("Auto-refresh (30s)", value=True, key="auto_refresh")
    if auto_refresh:
        st.markdown("🟢 Auto-refresh active")
    else:
        st.markdown("🔴 Auto-refresh paused")

    st.markdown("---")
    st.markdown("**Quick Stats**")

    try:
        from database.trade_repository import TradeRepository
        from datetime import date

        repo = TradeRepository()
        daily_pnl = repo.get_daily_pnl(date.today())
        st.metric("Today's P&L", f"₹{daily_pnl:,.2f}")
    except Exception:
        st.metric("Today's P&L", "₹0.00")

    st.markdown("---")
    st.markdown(
        "<p style='font-size: 0.75rem; color: #64748b;'>"
        "Built for Indian Stock Market<br>"
        "Nifty 500 Universe<br>"
        "LONG ONLY • INTRADAY"
        "</p>",
        unsafe_allow_html=True,
    )

# ── Main Content ──
st.title("📊 Intraday Trading Dashboard")
st.markdown("*Real-time Nifty 500 scanning • LONG ONLY momentum trading*")

# ── Dashboard Overview ──
try:
    from database.trade_repository import TradeRepository
    from datetime import date, timedelta

    repo = TradeRepository()

    # Today's stats
    today = date.today()
    stats = repo.get_performance_stats(today, today)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        pnl = stats.get("total_pnl", 0.0)
        st.metric(
            label="Today's P&L",
            value=f"₹{pnl:,.2f}",
            delta=f"₹{pnl:+,.2f}",
            delta_color="normal" if pnl >= 0 else "inverse",
        )

    with col2:
        st.metric(label="Total Trades", value=str(stats.get("total_trades", 0)))

    with col3:
        st.metric(label="Win Rate", value=f"{stats.get('win_rate', 0):.1f}%")

    with col4:
        st.metric(label="Profit Factor", value=f"{stats.get('profit_factor', 0):.2f}")

    with col5:
        st.metric(
            label="Max Drawdown",
            value=f"₹{stats.get('max_drawdown', 0):,.2f}",
        )

except Exception as e:
    st.info("📊 Dashboard will populate with live data when the scanner is running.")
    st.caption(f"Note: {e}")

# ── Auto-refresh ──
if auto_refresh:
    import time
    time.sleep(0.1)
    st.markdown(
        """
        <meta http-equiv="refresh" content="30">
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown(
    "👈 Navigate using the sidebar pages for detailed views: "
    "**Market Sentiment** • **Active Signals** • **Trade History** • "
    "**Performance** • **Analytics** • **Backtesting** • "
    "**Import Data** • **Reports**"
)
