"""Reports page — Generate and download reports."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from datetime import date, timedelta
import pandas as pd

st.set_page_config(page_title="Reports", page_icon="📄", layout="wide")
st.title("📄 Reports & Downloads")

try:
    from reports.report_generator import ReportGenerator
    from reports.export import ExportManager
    from database.trade_repository import TradeRepository

    repo = TradeRepository()
    gen = ReportGenerator(repo)
    export = ExportManager(repo)
    today = date.today()

    # Quick Reports
    st.subheader("📊 Generate Reports")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📅 Daily Report", use_container_width=True):
            report = gen.generate_daily_report()
            st.markdown("### Daily Report")
            st.text(report["message"])

    with col2:
        if st.button("📅 Weekly Report", use_container_width=True):
            report = gen.generate_weekly_report()
            st.markdown("### Weekly Report")
            st.text(report["message"])

    with col3:
        if st.button("📅 Monthly Report", use_container_width=True):
            report = gen.generate_monthly_report()
            st.markdown("### Monthly Report")
            st.text(report["message"])

    with col4:
        if st.button("📅 Yearly Report", use_container_width=True):
            report = gen.generate_yearly_report()
            st.markdown("### Yearly Report")
            st.text(report["message"])

    st.markdown("---")

    # Downloads
    st.subheader("📥 Download Reports")

    col1, col2 = st.columns(2)
    with col1:
        dl_start = st.date_input("From Date", value=today - timedelta(days=30), key="dl_start")
    with col2:
        dl_end = st.date_input("To Date", value=today, key="dl_end")

    st.markdown("**Choose format:**")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 Download Excel (.xlsx)", use_container_width=True):
            try:
                buffer = export.export_to_bytes(dl_start, dl_end, format="xlsx")
                st.download_button(
                    label="💾 Save Excel File",
                    data=buffer,
                    file_name=f"trades_{dl_start}_{dl_end}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception as e:
                st.error(str(e))

    with col2:
        if st.button("📊 Download CSV (.csv)", use_container_width=True):
            try:
                buffer = export.export_to_bytes(dl_start, dl_end, format="csv")
                st.download_button(
                    label="💾 Save CSV File",
                    data=buffer,
                    file_name=f"trades_{dl_start}_{dl_end}.csv",
                    mime="text/csv",
                )
            except Exception as e:
                st.error(str(e))

    with col3:
        if st.button("📊 Download PDF (.pdf)", use_container_width=True):
            try:
                buffer = export.export_to_bytes(dl_start, dl_end, format="pdf")
                st.download_button(
                    label="💾 Save PDF File",
                    data=buffer,
                    file_name=f"report_{dl_start}_{dl_end}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(str(e))

    st.markdown("---")

    # Available downloads
    st.subheader("📁 Available Downloads")
    st.markdown(
        """
        | Report | Description |
        |--------|-------------|
        | Daily Report | Today's complete trading summary |
        | Weekly Report | This week's performance analysis |
        | Monthly Report | This month's detailed performance |
        | Yearly Report | Annual performance review |
        | Trade Journal | Complete trade history with notes |
        | P&L History | Historical profit & loss data |
        | Performance Analytics | Detailed performance metrics |
        """
    )

except Exception as e:
    st.info("Reports will be available after trades are recorded.")
    st.caption(str(e))
