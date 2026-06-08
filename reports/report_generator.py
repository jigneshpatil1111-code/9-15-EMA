"""
Report Generator.
Generates daily, weekly, monthly, and yearly performance reports
using data from the trade repository.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional

from database.trade_repository import TradeRepository
from telegram_bot.formatters import (
    format_daily_report,
    format_weekly_report,
    format_monthly_report,
    format_yearly_report,
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates performance reports at different time intervals.

    Report Schedule:
    - Daily: at 15:30 IST
    - Weekly: every Friday after market close
    - Monthly: last trading day of month
    - Yearly: last trading day of year
    """

    def __init__(self, trade_repo: TradeRepository = None):
        self._repo = trade_repo or TradeRepository()

    def generate_daily_report(self, report_date: date = None) -> Dict[str, Any]:
        """
        Generate a daily performance report.

        Args:
            report_date: Date for the report (default: today).

        Returns:
            Dict with report data and formatted message.
        """
        if report_date is None:
            report_date = date.today()

        stats = self._repo.get_performance_stats(report_date, report_date)
        formatted = format_daily_report(
            stats, report_date.strftime("%Y-%m-%d")
        )

        # Save daily performance to database
        try:
            best = stats.get("best_trade", {})
            worst = stats.get("worst_trade", {})
            self._repo.save_daily_performance(report_date, {
                "total_trades": stats["total_trades"],
                "wins": stats["wins"],
                "losses": stats["losses"],
                "breakeven": stats["breakeven"],
                "win_rate": stats["win_rate"],
                "total_pnl": stats["total_pnl"],
                "gross_profit": stats["gross_profit"],
                "gross_loss": stats["gross_loss"],
                "profit_factor": stats["profit_factor"],
                "best_trade_pnl": best.get("pnl", 0.0) if best else 0.0,
                "best_trade_symbol": best.get("symbol", "") if best else "",
                "worst_trade_pnl": worst.get("pnl", 0.0) if worst else 0.0,
                "worst_trade_symbol": worst.get("symbol", "") if worst else "",
                "avg_rr": stats["avg_rr"],
                "max_drawdown": stats["max_drawdown"],
            })
        except Exception as e:
            logger.error(f"Failed to save daily performance: {e}")

        logger.info(f"Daily report generated for {report_date}")
        return {
            "type": "daily",
            "date": report_date,
            "stats": stats,
            "message": formatted,
        }

    def generate_weekly_report(self, reference_date: date = None) -> Dict[str, Any]:
        """
        Generate a weekly performance report.

        Args:
            reference_date: Any date within the week (default: today).

        Returns:
            Dict with report data and formatted message.
        """
        if reference_date is None:
            reference_date = date.today()

        start_of_week = reference_date - timedelta(days=reference_date.weekday())
        end_of_week = start_of_week + timedelta(days=4)  # Friday

        stats = self._repo.get_performance_stats(start_of_week, end_of_week)
        week_str = f"{start_of_week.strftime('%d %b')} - {end_of_week.strftime('%d %b %Y')}"
        formatted = format_weekly_report(stats, week_str)

        logger.info(f"Weekly report generated for {week_str}")
        return {
            "type": "weekly",
            "start_date": start_of_week,
            "end_date": end_of_week,
            "stats": stats,
            "message": formatted,
        }

    def generate_monthly_report(
        self, year: int = None, month: int = None
    ) -> Dict[str, Any]:
        """
        Generate a monthly performance report.

        Args:
            year: Report year (default: current year).
            month: Report month (default: current month).

        Returns:
            Dict with report data and formatted message.
        """
        if year is None:
            year = date.today().year
        if month is None:
            month = date.today().month

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        stats = self._repo.get_performance_stats(start_date, end_date)
        top_stocks = self._repo.get_top_performers(start_date, end_date, limit=5)
        worst_stocks = self._repo.get_worst_performers(start_date, end_date, limit=5)

        month_str = start_date.strftime("%B %Y")
        formatted = format_monthly_report(
            stats, month_str, top_stocks, worst_stocks
        )

        logger.info(f"Monthly report generated for {month_str}")
        return {
            "type": "monthly",
            "year": year,
            "month": month,
            "stats": stats,
            "top_performers": top_stocks,
            "worst_performers": worst_stocks,
            "message": formatted,
        }

    def generate_yearly_report(self, year: int = None) -> Dict[str, Any]:
        """
        Generate a yearly performance report.

        Args:
            year: Report year (default: current year).

        Returns:
            Dict with report data and formatted message.
        """
        if year is None:
            year = date.today().year

        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        stats = self._repo.get_performance_stats(start_date, end_date)
        formatted = format_yearly_report(stats, year)

        logger.info(f"Yearly report generated for {year}")
        return {
            "type": "yearly",
            "year": year,
            "stats": stats,
            "message": formatted,
        }

    def get_pnl_by_setup(
        self, start_date: date, end_date: date
    ) -> Dict[str, Dict]:
        """Get P&L breakdown by setup type."""
        return self._repo.get_pnl_by_setup(start_date, end_date)

    def get_equity_curve(
        self, start_date: date, end_date: date
    ) -> list:
        """Get equity curve data for charting."""
        return self._repo.get_equity_curve(start_date, end_date)
