"""
Dhan P&L Import Module.
Imports Dhan P&L reports, tradebooks, contract notes, and broker statements.
Supports Excel (.xlsx) and CSV (.csv) formats.
"""

import logging
import os
from datetime import date, datetime
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd

from database.connection import get_session
from database.models import Trade, ImportedReport
from database.trade_repository import TradeRepository
from config.settings import settings

logger = logging.getLogger(__name__)


class DhanImporter:
    """
    Imports trading data from Dhan broker exports.

    Supported imports:
    - Dhan P&L Reports
    - Tradebook Reports
    - Contract Notes
    - Broker Statements

    Formats: Excel (.xlsx), CSV (.csv)
    """

    # Known Dhan column mappings for different report types
    TRADEBOOK_COLUMNS = {
        "trading_symbol": ["Trading Symbol", "Symbol", "TRADING_SYMBOL", "trading_symbol"],
        "trade_date": ["Trade Date", "Date", "TRADE_DATE", "trade_date", "Order Date"],
        "trade_time": ["Trade Time", "Time", "TRADE_TIME", "trade_time", "Order Time"],
        "trade_type": ["Trade Type", "Type", "TRADE_TYPE", "trade_type", "Buy/Sell"],
        "quantity": ["Quantity", "Qty", "QUANTITY", "quantity", "Trade Qty"],
        "price": ["Price", "Trade Price", "PRICE", "price", "Avg Price"],
        "order_id": ["Order ID", "ORDER_ID", "order_id", "Order No"],
        "exchange": ["Exchange", "EXCHANGE", "exchange"],
    }

    PNL_COLUMNS = {
        "symbol": ["Symbol", "Trading Symbol", "SYMBOL", "Instrument"],
        "buy_avg": ["Buy Avg", "Buy Average", "BUY_AVG", "Avg Buy Price"],
        "sell_avg": ["Sell Avg", "Sell Average", "SELL_AVG", "Avg Sell Price"],
        "buy_qty": ["Buy Qty", "Buy Quantity", "BUY_QTY"],
        "sell_qty": ["Sell Qty", "Sell Quantity", "SELL_QTY"],
        "realized_pnl": ["Realized P&L", "P&L", "PNL", "Net P&L", "Profit/Loss"],
        "trade_date": ["Date", "Trade Date", "TRADE_DATE"],
    }

    def __init__(self, trade_repo: TradeRepository = None):
        self._repo = trade_repo or TradeRepository()

    def import_file(
        self, filepath: str, report_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Import a Dhan report file.

        Args:
            filepath: Path to the file (.xlsx or .csv).
            report_type: Type of report - 'tradebook', 'pnl', 'contract_note',
                        or 'auto' (auto-detect).

        Returns:
            Dict with import results.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()
        filename = os.path.basename(filepath)

        # Read the file
        try:
            if ext == ".xlsx":
                df = pd.read_excel(filepath, engine="openpyxl")
            elif ext == ".csv":
                df = pd.read_csv(filepath)
            else:
                raise ValueError(f"Unsupported file format: {ext}. Use .xlsx or .csv")
        except Exception as e:
            raise ValueError(f"Failed to read file: {e}")

        if df.empty:
            return {
                "status": "error",
                "message": "File is empty.",
                "records": 0,
            }

        # Auto-detect report type
        if report_type == "auto":
            report_type = self._detect_report_type(df)

        # Process based on type
        if report_type == "tradebook":
            result = self._import_tradebook(df, filename)
        elif report_type == "pnl":
            result = self._import_pnl_report(df, filename)
        else:
            result = self._import_generic(df, filename, report_type)

        return result

    def import_uploaded_file(
        self, file_content: bytes, filename: str, report_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Import from uploaded file content (for Streamlit uploads).

        Args:
            file_content: Raw bytes of the file.
            filename: Original filename.
            report_type: Report type or 'auto'.

        Returns:
            Dict with import results.
        """
        ext = os.path.splitext(filename)[1].lower()

        try:
            import io
            if ext == ".xlsx":
                df = pd.read_excel(io.BytesIO(file_content), engine="openpyxl")
            elif ext == ".csv":
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                raise ValueError(f"Unsupported format: {ext}")
        except Exception as e:
            raise ValueError(f"Failed to read uploaded file: {e}")

        if df.empty:
            return {"status": "error", "message": "File is empty.", "records": 0}

        if report_type == "auto":
            report_type = self._detect_report_type(df)

        if report_type == "tradebook":
            return self._import_tradebook(df, filename)
        elif report_type == "pnl":
            return self._import_pnl_report(df, filename)
        else:
            return self._import_generic(df, filename, report_type)

    def _detect_report_type(self, df: pd.DataFrame) -> str:
        """Auto-detect the report type from column names."""
        cols = set(c.lower().strip() for c in df.columns)

        tradebook_markers = {"trade date", "trading symbol", "trade type", "quantity", "price"}
        pnl_markers = {"buy avg", "sell avg", "realized p&l"}
        alt_pnl_markers = {"avg buy price", "avg sell price", "net p&l"}

        if len(tradebook_markers.intersection(cols)) >= 3:
            return "tradebook"
        elif len(pnl_markers.intersection(cols)) >= 2:
            return "pnl"
        elif len(alt_pnl_markers.intersection(cols)) >= 2:
            return "pnl"
        else:
            return "generic"

    def _find_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Find the first matching column name from a list of candidates."""
        for col in candidates:
            if col in df.columns:
                return col
            # Case-insensitive match
            for df_col in df.columns:
                if df_col.lower().strip() == col.lower().strip():
                    return df_col
        return None

    def _import_tradebook(
        self, df: pd.DataFrame, filename: str
    ) -> Dict[str, Any]:
        """Import a Dhan tradebook report."""
        inserted = 0
        skipped = 0
        errors = 0

        # Find column mappings
        symbol_col = self._find_column(df, self.TRADEBOOK_COLUMNS["trading_symbol"])
        date_col = self._find_column(df, self.TRADEBOOK_COLUMNS["trade_date"])
        price_col = self._find_column(df, self.TRADEBOOK_COLUMNS["price"])
        qty_col = self._find_column(df, self.TRADEBOOK_COLUMNS["quantity"])
        type_col = self._find_column(df, self.TRADEBOOK_COLUMNS["trade_type"])

        if not all([symbol_col, date_col, price_col]):
            return {
                "status": "error",
                "message": "Missing required columns in tradebook.",
                "records": 0,
            }

        session = get_session()
        total_pnl = 0.0
        date_min = None
        date_max = None

        try:
            # Group trades by symbol and date to create paired entries
            for _, row in df.iterrows():
                try:
                    symbol = str(row[symbol_col]).strip().upper()
                    trade_date = pd.to_datetime(row[date_col]).date()
                    price = float(row[price_col])
                    qty = int(row[qty_col]) if qty_col else 1
                    trade_type = str(row[type_col]).upper() if type_col else "BUY"

                    if date_min is None or trade_date < date_min:
                        date_min = trade_date
                    if date_max is None or trade_date > date_max:
                        date_max = trade_date

                    # Only import BUY trades (this is a long-only system)
                    if "BUY" in trade_type:
                        trade = Trade(
                            symbol=symbol,
                            security_id="imported",
                            trade_date=trade_date,
                            entry_time=datetime.combine(trade_date, datetime.min.time()),
                            setup_type="imported",
                            entry_price=price,
                            stop_loss=0.0,
                            target1=0.0,
                            target2=0.0,
                            quantity=qty,
                            status="imported",
                            notes=f"Imported from {filename}",
                        )
                        session.add(trade)
                        inserted += 1

                except Exception as e:
                    errors += 1
                    logger.debug(f"Row import error: {e}")

            session.commit()

            # Record the import
            self._repo.insert_imported_report(
                filename=filename,
                source="dhan_tradebook",
                record_count=inserted,
                total_pnl=total_pnl,
                date_start=date_min or date.today(),
                date_end=date_max or date.today(),
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Tradebook import failed: {e}")
            return {"status": "error", "message": str(e), "records": 0}
        finally:
            session.close()

        logger.info(
            f"Tradebook import: {inserted} inserted, {skipped} skipped, {errors} errors"
        )
        return {
            "status": "success",
            "records": inserted,
            "skipped": skipped,
            "errors": errors,
            "date_range": f"{date_min} to {date_max}",
        }

    def _import_pnl_report(
        self, df: pd.DataFrame, filename: str
    ) -> Dict[str, Any]:
        """Import a Dhan P&L report."""
        inserted = 0
        errors = 0
        total_pnl = 0.0

        symbol_col = self._find_column(df, self.PNL_COLUMNS["symbol"])
        date_col = self._find_column(df, self.PNL_COLUMNS["trade_date"])
        buy_col = self._find_column(df, self.PNL_COLUMNS["buy_avg"])
        sell_col = self._find_column(df, self.PNL_COLUMNS["sell_avg"])
        pnl_col = self._find_column(df, self.PNL_COLUMNS["realized_pnl"])
        buy_qty_col = self._find_column(df, self.PNL_COLUMNS["buy_qty"])

        if not symbol_col:
            return {
                "status": "error",
                "message": "Missing symbol column in P&L report.",
                "records": 0,
            }

        session = get_session()
        date_min = None
        date_max = None

        try:
            for _, row in df.iterrows():
                try:
                    symbol = str(row[symbol_col]).strip().upper()
                    trade_date = (
                        pd.to_datetime(row[date_col]).date()
                        if date_col and pd.notna(row.get(date_col))
                        else date.today()
                    )
                    entry_price = float(row[buy_col]) if buy_col and pd.notna(row.get(buy_col)) else 0.0
                    exit_price = float(row[sell_col]) if sell_col and pd.notna(row.get(sell_col)) else 0.0
                    pnl = float(row[pnl_col]) if pnl_col and pd.notna(row.get(pnl_col)) else 0.0
                    qty = int(row[buy_qty_col]) if buy_qty_col and pd.notna(row.get(buy_qty_col)) else 1

                    if date_min is None or trade_date < date_min:
                        date_min = trade_date
                    if date_max is None or trade_date > date_max:
                        date_max = trade_date

                    total_pnl += pnl

                    trade = Trade(
                        symbol=symbol,
                        security_id="imported",
                        trade_date=trade_date,
                        entry_time=datetime.combine(trade_date, datetime.min.time()),
                        exit_time=datetime.combine(trade_date, datetime.min.time()),
                        setup_type="imported",
                        entry_price=entry_price,
                        exit_price=exit_price,
                        stop_loss=0.0,
                        target1=0.0,
                        target2=0.0,
                        quantity=qty,
                        pnl=pnl,
                        pnl_pct=(pnl / entry_price * 100) if entry_price > 0 else 0.0,
                        status="imported",
                        exit_reason="imported",
                        notes=f"Imported from {filename}",
                    )
                    session.add(trade)
                    inserted += 1

                except Exception as e:
                    errors += 1
                    logger.debug(f"P&L row import error: {e}")

            session.commit()

            self._repo.insert_imported_report(
                filename=filename,
                source="dhan_pnl",
                record_count=inserted,
                total_pnl=total_pnl,
                date_start=date_min or date.today(),
                date_end=date_max or date.today(),
            )

        except Exception as e:
            session.rollback()
            logger.error(f"P&L import failed: {e}")
            return {"status": "error", "message": str(e), "records": 0}
        finally:
            session.close()

        logger.info(f"P&L import: {inserted} records, total P&L: {total_pnl:.2f}")
        return {
            "status": "success",
            "records": inserted,
            "errors": errors,
            "total_pnl": round(total_pnl, 2),
            "date_range": f"{date_min} to {date_max}",
        }

    def _import_generic(
        self, df: pd.DataFrame, filename: str, source: str
    ) -> Dict[str, Any]:
        """Import a generic report by best-effort column mapping."""
        logger.info(
            f"Generic import for {filename}. "
            f"Columns: {list(df.columns)}"
        )

        # Try to find any recognizable columns
        symbol_candidates = ["Symbol", "Trading Symbol", "Stock", "Instrument", "Scrip"]
        symbol_col = self._find_column(df, symbol_candidates)

        if not symbol_col:
            return {
                "status": "warning",
                "message": "Could not identify symbol column. File imported as raw data.",
                "records": len(df),
                "columns": list(df.columns),
            }

        # Record the import even if we can't parse individual trades
        self._repo.insert_imported_report(
            filename=filename,
            source=source,
            record_count=len(df),
            total_pnl=0.0,
            date_start=date.today(),
            date_end=date.today(),
        )

        return {
            "status": "success",
            "records": len(df),
            "message": "File imported as raw data.",
        }
