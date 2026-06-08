"""Performance page — Daily, Weekly, Monthly, Yearly P&L with charts."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from datetime import date, timedelta
import pandas as pd

st.set_page_config(page_title="Performance", page_icon="📈", layout="wide")
st.title("📈 Performance Analytics")

try:
    from database.trade_repository import TradeRepository
    from reports.report_generator import ReportGenerator
    from dashboard.components.charts import (
        create_equity_curve,
        create_drawdown_chart,
        create_pnl_bar_chart,
        create_win_rate_pie,
    )
    from dashboard.components.metrics import render_performance_kpis

    repo = TradeRepository()
    gen = ReportGenerator(repo)
    today = date.today()

    # Period tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Daily", "📅 Weekly", "📅 Monthly", "📅 Yearly"])

    with tab1:
        st.subheader("Today's Performance")
        stats = repo.get_performance_stats(today, today)
        render_performance_kpis(stats)

    with tab2:
        st.subheader("This Week")
        start_week = today - timedelta(days=today.weekday())
        stats = repo.get_performance_stats(start_week, today)
        render_performance_kpis(stats)

    with tab3:
        st.subheader("This Month")
        start_month = today.replace(day=1)
        stats = repo.get_performance_stats(start_month, today)
        render_performance_kpis(stats)

    with tab4:
        st.subheader("This Year")
        start_year = today.replace(month=1, day=1)
        stats = repo.get_performance_stats(start_year, today)
        render_performance_kpis(stats)

    st.markdown("---")

    # Equity Curve and Drawdown
    st.subheader("📈 Equity Curve & Drawdown")

    period = st.selectbox(
        "Chart Period",
        ["Last 30 Days", "Last 90 Days", "Last 6 Months", "Last 1 Year", "All Time"],
    )

    period_map = {
        "Last 30 Days": 30,
        "Last 90 Days": 90,
        "Last 6 Months": 180,
        "Last 1 Year": 365,
        "All Time": 3650,
    }
    days_back = period_map[period]
    chart_start = today - timedelta(days=days_back)

    curve_data = repo.get_equity_curve(chart_start, today)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(create_equity_curve(curve_data), use_container_width=True)
    with col2:
        st.plotly_chart(create_drawdown_chart(curve_data), use_container_width=True)

    # Daily P&L bars
    st.plotly_chart(create_pnl_bar_chart(curve_data), use_container_width=True)

    # Win Rate
    stats_all = repo.get_performance_stats(chart_start, today)
    st.plotly_chart(
        create_win_rate_pie(
            stats_all.get("wins", 0),
            stats_all.get("losses", 0),
            stats_all.get("breakeven", 0),
        ),
        use_container_width=True,
    )

except Exception as e:
    st.info("Performance data will populate as trades are completed.")
    st.caption(str(e))
