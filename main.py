"""
Intraday Stock Scanner — Main Entry Point
==========================================
Runs the automated scanning system with:
- Dhan API connection
- Nifty 500 instrument loading
- WebSocket live market feed
- Market sentiment evaluation
- Strategy scanning on 5-minute intervals
- Quality filtering and signal scoring
- Telegram alerts for top 5 signals
- Trade tracking and P&L management
- Automatic report scheduling
"""

import os
import sys
import json
import time
import signal
import logging
from datetime import datetime, date, time as dt_time
from pathlib import Path

import pytz

# ── Setup paths ──
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ── Load .env ──
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

from config.settings import settings

# ── Setup logging ──
os.makedirs(os.path.dirname(settings.LOG_FILE) if os.path.dirname(settings.LOG_FILE) else "logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.LOG_FILE, mode="a"),
    ],
)
logger = logging.getLogger("main")

IST = pytz.timezone("Asia/Kolkata")


def main():
    """Main entry point for the intraday scanner."""

    logger.info("=" * 70)
    logger.info("  INTRADAY STOCK SCANNER — STARTING")
    logger.info("  LONG ONLY • NIFTY 500 • INTRADAY")
    logger.info("=" * 70)

    # ── Step 1: Initialize Database ──
    logger.info("Step 1: Initializing database...")
    try:
        from database.connection import init_database, check_connection

        if not check_connection():
            logger.error(
                "Database connection failed. "
                "Ensure PostgreSQL is running and DATABASE_URL is correct."
            )
            logger.info("Continuing without database — trades will not be persisted.")

        init_database()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}. Continuing without DB.")

    # ── Step 2: Initialize Broker ──
    logger.info("Step 2: Initializing broker...")
    try:
        from core.broker_factory import get_broker

        broker = get_broker()
        logger.info(f"Broker '{settings.BROKER}' initialized.")
    except Exception as e:
        logger.error(f"Broker initialization failed: {e}")
        logger.error("Cannot continue without broker connection. Exiting.")
        sys.exit(1)

    # ── Step 3: Load Instruments ──
    logger.info("Step 3: Loading Nifty 500 instruments...")
    try:
        from core.instrument_manager import InstrumentManager

        instrument_manager = InstrumentManager()
        instruments = instrument_manager.load()
        logger.info(f"Loaded {len(instruments)} instruments.")
    except Exception as e:
        logger.error(f"Instrument loading failed: {e}")
        sys.exit(1)

    # ── Step 4: Start Market Feed ──
    logger.info("Step 4: Starting WebSocket market feed...")
    from core.market_feed import MarketFeedManager

    market_feed = MarketFeedManager()
    sub_list = instrument_manager.get_websocket_subscription_list()

    try:
        market_feed.connect(sub_list)
        logger.info("WebSocket market feed started.")
        # Wait for connection to establish
        time.sleep(3)
    except Exception as e:
        logger.warning(f"WebSocket feed failed: {e}. Using REST API fallback.")

    # Pre-load previous close prices
    logger.info("Loading previous close prices...")
    loaded_closes = 0
    for inst in instruments[:50]:  # Load first batch quickly
        try:
            prev_close = broker.get_previous_close(inst.security_id, inst.exchange_segment)
            if prev_close > 0:
                market_feed.update_prev_close(inst.security_id, prev_close)
                loaded_closes += 1
        except Exception:
            pass
    logger.info(f"Loaded {loaded_closes} previous close prices.")

    # ── Step 5: Initialize Engine Components ──
    logger.info("Step 5: Initializing engine components...")

    from engine.sentiment_engine import SentimentEngine
    from engine.scanner import Scanner
    from engine.trade_manager import TradeManager
    from database.trade_repository import TradeRepository
    from telegram_bot.notifier import TelegramNotifier
    from reports.report_generator import ReportGenerator
    from reports.report_scheduler import ReportScheduler

    sentiment_engine = SentimentEngine(
        market_feed=market_feed,
        broker=broker,
        instruments=instruments,
    )

    trade_manager = TradeManager()
    trade_repo = TradeRepository()
    trade_manager.set_trade_repository(trade_repo)

    telegram = TelegramNotifier()

    scanner = Scanner(
        broker=broker,
        market_feed=market_feed,
        instrument_manager=instrument_manager,
        sentiment_engine=sentiment_engine,
        trade_manager=trade_manager,
        telegram_notifier=telegram,
        trade_repository=trade_repo,
    )

    # ── Step 6: Start Report Scheduler ──
    logger.info("Step 6: Starting report scheduler...")
    report_gen = ReportGenerator(trade_repo)
    report_scheduler = ReportScheduler(report_gen, telegram)
    report_scheduler.start()

    # ── Step 7: Test Telegram ──
    logger.info("Step 7: Testing Telegram connection...")
    try:
        telegram.test_connection()
        logger.info("Telegram connection verified.")
    except Exception as e:
        logger.warning(f"Telegram test failed: {e}. Alerts may not be delivered.")

    # ── Step 8: Main Loop ──
    logger.info("=" * 70)
    logger.info("  SCANNER READY — ENTERING MAIN LOOP")
    logger.info(f"  Market Open: {settings.MARKET_OPEN}")
    logger.info(f"  Signal Cutoff: {settings.SIGNAL_CUTOFF}")
    logger.info(f"  Force Exit: {settings.FORCE_EXIT_START} - {settings.FORCE_EXIT_END}")
    logger.info(f"  Scan Interval: {settings.SCAN_INTERVAL_SECONDS}s")
    logger.info("=" * 70)

    # Graceful shutdown handler
    running = True

    def shutdown_handler(signum, frame):
        nonlocal running
        logger.info("Shutdown signal received. Stopping scanner...")
        running = False

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    last_date = None

    while running:
        try:
            now = datetime.now(IST)
            current_time = now.time()
            current_date = now.date()

            # Daily reset
            if current_date != last_date:
                scanner.reset_daily()
                last_date = current_date
                logger.info(f"New trading day: {current_date}")

            # Check if market is in trading hours
            h_open, m_open = settings.get_market_open_parts()
            h_close = 15
            m_close = 30

            market_start = dt_time(h_open, m_open)
            market_end = dt_time(h_close, m_close)

            # Weekend check
            if now.weekday() >= 5:
                logger.debug("Weekend. Sleeping 60s...")
                time.sleep(60)
                continue

            # Outside market hours
            if current_time < market_start or current_time > market_end:
                logger.debug("Outside market hours. Sleeping 30s...")
                time.sleep(30)
                continue

            # ── Run scan cycle ──
            scanner.run_scan_cycle()

            # ── Save sentiment state for dashboard ──
            try:
                sentiment = sentiment_engine.get_sentiment_data()
                if sentiment:
                    state_file = os.path.join(project_root, "data", "sentiment_state.json")
                    state = {
                        "positive_count": sentiment.positive_count,
                        "negative_count": sentiment.negative_count,
                        "total_scanned": sentiment.total_scanned,
                        "status": sentiment.status,
                        "timestamp": sentiment.timestamp.isoformat(),
                    }
                    with open(state_file, "w") as f:
                        json.dump(state, f)

                    # Log sentiment to database
                    trade_repo.save_sentiment_log(sentiment)
            except Exception as e:
                logger.debug(f"Sentiment state save error: {e}")

            # ── Wait for next scan interval ──
            elapsed = (datetime.now(IST) - now).total_seconds()
            sleep_time = max(0, settings.SCAN_INTERVAL_SECONDS - elapsed)
            logger.info(f"Next scan in {sleep_time:.0f}s")

            # Sleep in small chunks for responsive shutdown
            for _ in range(int(sleep_time / 5)):
                if not running:
                    break
                time.sleep(5)
            remaining = sleep_time % 5
            if remaining > 0 and running:
                time.sleep(remaining)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt. Shutting down...")
            running = False
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
            time.sleep(30)

    # ── Cleanup ──
    logger.info("Shutting down...")

    # Force close any open trades
    try:
        open_trades = trade_manager.get_open_trades()
        if open_trades:
            logger.info(f"Force-closing {len(open_trades)} open trades...")
            ltp_map = {}
            for trade in open_trades:
                ltp = market_feed.get_ltp(trade.security_id)
                if ltp > 0:
                    ltp_map[trade.symbol] = ltp
            trade_manager.force_close_all(ltp_map)
    except Exception as e:
        logger.error(f"Force close error: {e}")

    # Stop components
    try:
        report_scheduler.stop()
    except Exception:
        pass
    try:
        market_feed.disconnect()
    except Exception:
        pass

    # Final daily report
    try:
        report = report_gen.generate_daily_report()
        if report["stats"]["total_trades"] > 0:
            telegram.send_report(report["message"])
    except Exception:
        pass

    logger.info("Scanner shutdown complete.")


if __name__ == "__main__":
    main()
