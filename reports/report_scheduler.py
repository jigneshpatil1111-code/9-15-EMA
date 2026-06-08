"""
Report Scheduler.
APScheduler-based cron jobs for automatic report generation and Telegram delivery.
"""

import logging
from datetime import date, datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from reports.report_generator import ReportGenerator
from telegram_bot.notifier import TelegramNotifier
from config.settings import settings

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class ReportScheduler:
    """
    Schedules automatic report generation and Telegram delivery.

    Schedule:
    - Daily Report: at 15:30 IST every weekday
    - Weekly Report: every Friday at 15:45 IST
    - Monthly Report: last trading day of month at 16:00 IST
    - Yearly Report: December 31 at 16:00 IST
    """

    def __init__(
        self,
        report_generator: ReportGenerator = None,
        telegram_notifier: TelegramNotifier = None,
    ):
        self._generator = report_generator or ReportGenerator()
        self._telegram = telegram_notifier or TelegramNotifier()
        self._scheduler = BackgroundScheduler(timezone=IST)

    def start(self):
        """Start the report scheduler with all cron jobs."""
        report_h, report_m = settings.get_report_time_parts()

        # Daily report: weekdays at 15:30 IST
        self._scheduler.add_job(
            self._run_daily_report,
            CronTrigger(
                day_of_week="mon-fri",
                hour=report_h,
                minute=report_m,
                timezone=IST,
            ),
            id="daily_report",
            name="Daily Performance Report",
            replace_existing=True,
        )

        # Weekly report: every Friday at 15:45 IST
        self._scheduler.add_job(
            self._run_weekly_report,
            CronTrigger(
                day_of_week="fri",
                hour=15,
                minute=45,
                timezone=IST,
            ),
            id="weekly_report",
            name="Weekly Performance Report",
            replace_existing=True,
        )

        # Monthly report: last weekday of every month at 16:00 IST
        # Using day='last' with day_of_week constraint
        self._scheduler.add_job(
            self._run_monthly_report,
            CronTrigger(
                day="last",
                hour=16,
                minute=0,
                timezone=IST,
            ),
            id="monthly_report",
            name="Monthly Performance Report",
            replace_existing=True,
        )

        # Yearly report: December 31 at 16:00 IST
        self._scheduler.add_job(
            self._run_yearly_report,
            CronTrigger(
                month=12,
                day=31,
                hour=16,
                minute=0,
                timezone=IST,
            ),
            id="yearly_report",
            name="Yearly Performance Report",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("Report scheduler started with all cron jobs.")

    def stop(self):
        """Stop the report scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Report scheduler stopped.")

    def _run_daily_report(self):
        """Generate and send daily report."""
        try:
            logger.info("Generating daily report...")
            report = self._generator.generate_daily_report()
            if report["stats"]["total_trades"] > 0:
                self._telegram.send_report(report["message"])
                logger.info("Daily report sent to Telegram.")
            else:
                logger.info("No trades today. Skipping daily report.")
        except Exception as e:
            logger.error(f"Daily report generation failed: {e}")

    def _run_weekly_report(self):
        """Generate and send weekly report."""
        try:
            logger.info("Generating weekly report...")
            report = self._generator.generate_weekly_report()
            if report["stats"]["total_trades"] > 0:
                self._telegram.send_report(report["message"])
                logger.info("Weekly report sent to Telegram.")
            else:
                logger.info("No trades this week. Skipping weekly report.")
        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")

    def _run_monthly_report(self):
        """Generate and send monthly report."""
        try:
            logger.info("Generating monthly report...")
            report = self._generator.generate_monthly_report()
            if report["stats"]["total_trades"] > 0:
                self._telegram.send_report(report["message"])
                logger.info("Monthly report sent to Telegram.")
            else:
                logger.info("No trades this month. Skipping monthly report.")
        except Exception as e:
            logger.error(f"Monthly report generation failed: {e}")

    def _run_yearly_report(self):
        """Generate and send yearly report."""
        try:
            logger.info("Generating yearly report...")
            report = self._generator.generate_yearly_report()
            if report["stats"]["total_trades"] > 0:
                self._telegram.send_report(report["message"])
                logger.info("Yearly report sent to Telegram.")
        except Exception as e:
            logger.error(f"Yearly report generation failed: {e}")

    def trigger_report(self, report_type: str) -> dict:
        """
        Manually trigger a specific report.

        Args:
            report_type: 'daily', 'weekly', 'monthly', or 'yearly'.

        Returns:
            Report data dict.
        """
        generators = {
            "daily": self._generator.generate_daily_report,
            "weekly": self._generator.generate_weekly_report,
            "monthly": self._generator.generate_monthly_report,
            "yearly": self._generator.generate_yearly_report,
        }

        gen_func = generators.get(report_type)
        if gen_func is None:
            raise ValueError(f"Invalid report type: {report_type}")

        report = gen_func()
        self._telegram.send_report(report["message"])
        return report
