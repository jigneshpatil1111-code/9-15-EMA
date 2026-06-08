"""
Export Manager.
Exports trade data and reports to Excel (.xlsx), CSV (.csv), and PDF (.pdf) formats.
"""

import logging
import os
import io
from datetime import date, datetime
from typing import List, Dict, Any, Optional

import pandas as pd

from database.trade_repository import TradeRepository
from config.settings import settings

logger = logging.getLogger(__name__)


class ExportManager:
    """
    Handles exporting trade data and reports to multiple formats.
    Supported: Excel (.xlsx), CSV (.csv), PDF (.pdf).
    """

    def __init__(self, trade_repo: TradeRepository = None):
        self._repo = trade_repo or TradeRepository()
        self._export_dir = os.path.join(settings.BASE_DIR, "data", "exports")
        os.makedirs(self._export_dir, exist_ok=True)

    def export_trades_to_excel(
        self, start_date: date, end_date: date, filename: str = ""
    ) -> str:
        """
        Export trades to Excel format.

        Args:
            start_date: Start date for trade data.
            end_date: End date for trade data.
            filename: Output filename (auto-generated if empty).

        Returns:
            Full path to the exported file.
        """
        if not filename:
            filename = f"trades_{start_date}_{end_date}.xlsx"

        filepath = os.path.join(self._export_dir, filename)
        trades_data = self._repo.get_all_trades_dataframe(start_date, end_date)
        df = pd.DataFrame(trades_data)

        if df.empty:
            logger.warning("No trades to export.")
            # Write empty DataFrame with headers
            df = pd.DataFrame(columns=[
                "id", "symbol", "date", "entry_time", "exit_time",
                "setup_type", "entry_price", "stop_loss", "target1", "target2",
                "exit_price", "pnl", "pnl_pct", "risk_reward", "rr_achieved",
                "signal_score", "volume", "status", "exit_reason", "notes",
            ])

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Trades", index=False)

            # Add performance summary sheet
            stats = self._repo.get_performance_stats(start_date, end_date)
            summary_data = {
                "Metric": [
                    "Total Trades", "Wins", "Losses", "Win Rate",
                    "Total P&L", "Profit Factor", "Max Drawdown",
                    "Average RR", "Largest Winner", "Largest Loser",
                ],
                "Value": [
                    stats.get("total_trades", 0),
                    stats.get("wins", 0),
                    stats.get("losses", 0),
                    f"{stats.get('win_rate', 0):.1f}%",
                    f"₹{stats.get('total_pnl', 0):.2f}",
                    f"{stats.get('profit_factor', 0):.2f}",
                    f"₹{stats.get('max_drawdown', 0):.2f}",
                    f"{stats.get('avg_rr', 0):.2f}",
                    f"₹{stats.get('largest_winner', 0):.2f}",
                    f"₹{stats.get('largest_loser', 0):.2f}",
                ],
            }
            pd.DataFrame(summary_data).to_excel(
                writer, sheet_name="Summary", index=False
            )

            # Add setup breakdown sheet
            setup_stats = self._repo.get_pnl_by_setup(start_date, end_date)
            setup_rows = []
            for setup, data in setup_stats.items():
                setup_rows.append({
                    "Setup": setup,
                    "Total": data["total"],
                    "Wins": data["wins"],
                    "Losses": data["losses"],
                    "Win Rate": f"{data['win_rate']:.1f}%",
                    "P&L": f"₹{data['total_pnl']:.2f}",
                })
            pd.DataFrame(setup_rows).to_excel(
                writer, sheet_name="By Setup", index=False
            )

        logger.info(f"Exported trades to Excel: {filepath}")
        return filepath

    def export_trades_to_csv(
        self, start_date: date, end_date: date, filename: str = ""
    ) -> str:
        """
        Export trades to CSV format.

        Args:
            start_date: Start date for trade data.
            end_date: End date for trade data.
            filename: Output filename (auto-generated if empty).

        Returns:
            Full path to the exported file.
        """
        if not filename:
            filename = f"trades_{start_date}_{end_date}.csv"

        filepath = os.path.join(self._export_dir, filename)
        trades_data = self._repo.get_all_trades_dataframe(start_date, end_date)
        df = pd.DataFrame(trades_data)
        df.to_csv(filepath, index=False)

        logger.info(f"Exported trades to CSV: {filepath}")
        return filepath

    def export_trades_to_pdf(
        self, start_date: date, end_date: date, filename: str = ""
    ) -> str:
        """
        Export trades and performance summary to PDF format.

        Args:
            start_date: Start date for trade data.
            end_date: End date for trade data.
            filename: Output filename (auto-generated if empty).

        Returns:
            Full path to the exported file.
        """
        if not filename:
            filename = f"report_{start_date}_{end_date}.pdf"

        filepath = os.path.join(self._export_dir, filename)

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                SimpleDocTemplate,
                Table,
                TableStyle,
                Paragraph,
                Spacer,
            )

            doc = SimpleDocTemplate(
                filepath,
                pagesize=landscape(A4),
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Title"],
                fontSize=18,
                spaceAfter=20,
            )
            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontSize=14,
                spaceAfter=10,
            )

            elements = []

            # Title
            elements.append(
                Paragraph(
                    f"Intraday Trading Report ({start_date} to {end_date})",
                    title_style,
                )
            )
            elements.append(Spacer(1, 12))

            # Performance Summary
            stats = self._repo.get_performance_stats(start_date, end_date)
            elements.append(Paragraph("Performance Summary", heading_style))

            summary_data = [
                ["Metric", "Value"],
                ["Total Trades", str(stats.get("total_trades", 0))],
                ["Wins", str(stats.get("wins", 0))],
                ["Losses", str(stats.get("losses", 0))],
                ["Win Rate", f"{stats.get('win_rate', 0):.1f}%"],
                ["Total P&L", f"₹{stats.get('total_pnl', 0):,.2f}"],
                ["Profit Factor", f"{stats.get('profit_factor', 0):.2f}"],
                ["Max Drawdown", f"₹{stats.get('max_drawdown', 0):,.2f}"],
                ["Average RR", f"{stats.get('avg_rr', 0):.2f}"],
            ]

            summary_table = Table(summary_data, colWidths=[200, 200])
            summary_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                    ]
                )
            )
            elements.append(summary_table)
            elements.append(Spacer(1, 20))

            # Trade Details
            trades_data = self._repo.get_all_trades_dataframe(start_date, end_date)
            if trades_data:
                elements.append(Paragraph("Trade Details", heading_style))
                headers = [
                    "Symbol", "Date", "Setup", "Entry", "SL",
                    "Exit", "P&L", "RR", "Status",
                ]
                table_data = [headers]
                for t in trades_data[:50]:  # Limit to 50 rows for PDF
                    table_data.append([
                        t["symbol"],
                        str(t["date"]),
                        t["setup_type"],
                        f"₹{t['entry_price']:.2f}",
                        f"₹{t['stop_loss']:.2f}",
                        f"₹{t.get('exit_price', 0):.2f}" if t.get("exit_price") else "—",
                        f"₹{t.get('pnl', 0):+.2f}",
                        f"{t.get('rr_achieved', 0):.2f}",
                        t["status"],
                    ])

                trade_table = Table(table_data, repeatRows=1)
                trade_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                        ]
                    )
                )
                elements.append(trade_table)

            doc.build(elements)
            logger.info(f"Exported report to PDF: {filepath}")

        except ImportError:
            logger.error("reportlab not installed. Cannot generate PDF.")
            raise

        return filepath

    def export_to_bytes(
        self,
        start_date: date,
        end_date: date,
        format: str = "xlsx",
    ) -> io.BytesIO:
        """
        Export trades to an in-memory buffer (for Streamlit downloads).

        Args:
            start_date: Start date.
            end_date: End date.
            format: 'xlsx', 'csv', or 'pdf'.

        Returns:
            BytesIO buffer with the exported data.
        """
        trades_data = self._repo.get_all_trades_dataframe(start_date, end_date)
        df = pd.DataFrame(trades_data)
        buffer = io.BytesIO()

        if format == "xlsx":
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Trades", index=False)
        elif format == "csv":
            csv_data = df.to_csv(index=False)
            buffer.write(csv_data.encode())
        elif format == "pdf":
            filepath = self.export_trades_to_pdf(start_date, end_date)
            with open(filepath, "rb") as f:
                buffer.write(f.read())

        buffer.seek(0)
        return buffer
