"""Import Data page — Upload Dhan P&L, tradebook, and contract note files."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from datetime import date
import pandas as pd

st.set_page_config(page_title="Import Data", page_icon="📥", layout="wide")
st.title("📥 Import Dhan Reports")

st.markdown(
    """
    Upload your Dhan P&L reports, tradebooks, contract notes, or broker statements.
    Supported formats: **Excel (.xlsx)** and **CSV (.csv)**.
    """
)

try:
    from importer.dhan_importer import DhanImporter

    importer = DhanImporter()

    # Upload section
    st.subheader("📂 Upload File")

    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["xlsx", "csv"],
            help="Upload Dhan P&L report, tradebook, or contract note",
        )
    with col2:
        report_type = st.selectbox(
            "Report Type",
            ["auto", "tradebook", "pnl", "contract_note"],
            help="Auto-detect or manually specify the report type",
        )

    if uploaded_file is not None:
        st.markdown(f"**File:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")

        # Preview
        try:
            if uploaded_file.name.endswith(".xlsx"):
                preview_df = pd.read_excel(uploaded_file, engine="openpyxl", nrows=10)
            else:
                preview_df = pd.read_csv(uploaded_file, nrows=10)

            st.markdown("**Preview (first 10 rows):**")
            st.dataframe(preview_df, use_container_width=True)

            # Reset file position
            uploaded_file.seek(0)
        except Exception as e:
            st.warning(f"Could not preview file: {e}")

        # Import button
        if st.button("📥 Import Data", type="primary"):
            with st.spinner("Importing..."):
                file_content = uploaded_file.read()
                result = importer.import_uploaded_file(
                    file_content=file_content,
                    filename=uploaded_file.name,
                    report_type=report_type,
                )

            if result.get("status") == "success":
                st.success(
                    f"✅ Import successful!\n\n"
                    f"**Records imported:** {result.get('records', 0)}\n\n"
                    f"**Date range:** {result.get('date_range', 'N/A')}"
                )
                if result.get("total_pnl"):
                    st.metric("Total P&L Imported", f"₹{result['total_pnl']:,.2f}")
            elif result.get("status") == "warning":
                st.warning(result.get("message", "Import completed with warnings."))
            else:
                st.error(result.get("message", "Import failed."))

    st.markdown("---")

    # Import history
    st.subheader("📋 Import History")

    from database.connection import get_session
    from database.models import ImportedReport
    from sqlalchemy import desc

    session = get_session()
    try:
        reports = session.query(ImportedReport).order_by(desc(ImportedReport.import_date)).limit(20).all()

        if reports:
            report_data = [{
                "Filename": r.filename,
                "Source": r.source,
                "Records": r.record_count,
                "P&L": f"₹{r.total_pnl:,.2f}" if r.total_pnl else "—",
                "Date Range": f"{r.date_range_start} to {r.date_range_end}" if r.date_range_start else "—",
                "Imported": r.import_date.strftime("%Y-%m-%d %H:%M") if r.import_date else "—",
                "Status": r.status,
            } for r in reports]
            st.dataframe(pd.DataFrame(report_data), use_container_width=True)
        else:
            st.info("No imports yet.")
    finally:
        session.close()

except Exception as e:
    st.info("Import module ready. Upload a file to get started.")
    st.caption(str(e))
