"""
Main Scanner Orchestrator.
Runs the full scanning pipeline on a 5-minute schedule:
1. Check market sentiment
2. Iterate all Nifty 500 instruments
3. Run both strategies
4. Apply quality filters
5. Score and rank signals
6. Send top 5 to Telegram
7. Log to database
"""

import logging
import time
from datetime import datetime, date
from typing import List, Optional

import pytz
import pandas as pd

from strategies.base_strategy import Signal
from strategies.one_percent_setup import OnePercentSetup
from strategies.ema_pullback_setup import EMAPullbackSetup
from engine.sentiment_engine import SentimentEngine
from engine.quality_filter import QualityFilter
from engine.signal_scorer import SignalScorer
from engine.trade_manager import TradeManager
from core.broker_base import BrokerBase
from core.market_feed import MarketFeedManager
from core.instrument_manager import InstrumentManager
from config.settings import settings

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class Scanner:
    """
    Main scanner that orchestrates the entire scanning pipeline.
    Runs on a 5-minute aligned schedule during market hours.
    """

    def __init__(
        self,
        broker: BrokerBase,
        market_feed: MarketFeedManager,
        instrument_manager: InstrumentManager,
        sentiment_engine: SentimentEngine,
        trade_manager: TradeManager,
        telegram_notifier=None,
        trade_repository=None,
    ):
        self._broker = broker
        self._market_feed = market_feed
        self._instrument_manager = instrument_manager
        self._sentiment_engine = sentiment_engine
        self._trade_manager = trade_manager
        self._telegram = telegram_notifier
        self._trade_repo = trade_repository

        # Strategies
        self._strategies = [
            OnePercentSetup(),
            EMAPullbackSetup(),
        ]

        # Quality filter and scorer
        self._quality_filter = QualityFilter()
        self._signal_scorer = SignalScorer()

        # State
        self._running = False
        self._scan_count = 0
        self._last_scan_time: Optional[datetime] = None
        self._already_signaled: set = set()  # Avoid duplicate signals per day

    def run_scan_cycle(self):
        """
        Execute one complete scan cycle.
        Called on each 5-minute interval during trading hours.
        """
        self._scan_count += 1
        scan_start = datetime.now(IST)

        logger.info(
            f"{'='*60}\n"
            f"SCAN CYCLE #{self._scan_count} started at {scan_start.strftime('%H:%M:%S')}\n"
            f"{'='*60}"
        )

        # ── Step 0: Check if signal time is allowed ──
        if not self._trade_manager.is_signal_time_allowed():
            logger.info("Outside signal window (09:15 - 14:30). Skipping scan.")

            # Check if force close is needed
            if self._trade_manager.should_force_close():
                self._handle_force_close()

            self._last_scan_time = scan_start
            return

        # ── Step 1: Evaluate market sentiment ──
        try:
            sentiment = self._sentiment_engine.evaluate()
        except Exception as e:
            logger.error(f"Sentiment evaluation failed: {e}")
            return

        if not self._sentiment_engine.is_bullish():
            logger.info(
                f"Market NOT BULLISH ({sentiment.positive_count} positive / "
                f"{sentiment.total_scanned} total). Skipping scan."
            )
            self._last_scan_time = scan_start
            return

        logger.info(
            f"Market BULLISH: {sentiment.positive_count} positive / "
            f"{sentiment.total_scanned} total. Scanning..."
        )

        # ── Step 2: Scan all instruments ──
        instruments = self._instrument_manager.get_instruments()
        raw_signals: List[Signal] = []
        scanned = 0
        errors = 0

        for inst in instruments:
            # Skip if we already have a signal for this stock today
            if inst.symbol in self._already_signaled:
                continue

            # Skip if there's already an open trade
            if self._trade_manager.has_open_trade(inst.symbol):
                continue

            try:
                # Fetch intraday candles
                candles = self._broker.get_intraday_data(
                    security_id=inst.security_id,
                    exchange_segment=inst.exchange_segment,
                    instrument_type="EQUITY",
                )

                if candles.empty or len(candles) < 3:
                    continue

                # Get previous close
                prev_close = self._market_feed.get_prev_close(inst.security_id)
                if prev_close <= 0:
                    prev_close = self._broker.get_previous_close(
                        inst.security_id, inst.exchange_segment
                    )
                if prev_close <= 0:
                    continue

                scanned += 1

                # ── Step 3: Run both strategies ──
                for strategy in self._strategies:
                    try:
                        signal = strategy.scan(
                            symbol=inst.symbol,
                            security_id=inst.security_id,
                            candles=candles,
                            prev_close=prev_close,
                        )
                        if signal:
                            raw_signals.append(signal)
                    except Exception as e:
                        logger.debug(
                            f"Strategy {strategy.name} error for {inst.symbol}: {e}"
                        )

            except Exception as e:
                errors += 1
                logger.debug(f"Scan error for {inst.symbol}: {e}")
                continue

        logger.info(
            f"Scanned {scanned} stocks | {len(raw_signals)} raw signals | "
            f"{errors} errors"
        )

        if not raw_signals:
            self._last_scan_time = scan_start
            return

        # ── Step 4: Apply quality filters ──
        filtered_signals: List[Signal] = []
        for signal in raw_signals:
            try:
                # Get candle data for quality check
                candles = self._broker.get_intraday_data(
                    security_id=signal.security_id,
                    exchange_segment="NSE_EQ",
                    instrument_type="EQUITY",
                )

                passed, reason = self._quality_filter.filter(signal, candles)
                if passed:
                    filtered_signals.append(signal)
                else:
                    logger.debug(f"Quality rejected {signal.symbol}: {reason}")
            except Exception as e:
                logger.debug(f"Quality filter error for {signal.symbol}: {e}")

        logger.info(
            f"Quality filter: {len(filtered_signals)}/{len(raw_signals)} passed"
        )

        if not filtered_signals:
            self._last_scan_time = scan_start
            return

        # ── Step 5: Score and rank signals ──
        top_signals = self._signal_scorer.rank_signals(filtered_signals)

        logger.info(
            f"Top {len(top_signals)} signals: "
            + ", ".join(f"{s.symbol}({s.signal_score})" for s in top_signals)
        )

        # ── Step 6: Send to Telegram and add to trade tracking ──
        for signal in top_signals:
            self._already_signaled.add(signal.symbol)
            self._trade_manager.add_trade(signal)

            # Send Telegram alert
            if self._telegram:
                try:
                    self._telegram.send_trade_alert(signal)
                except Exception as e:
                    logger.error(f"Telegram send error for {signal.symbol}: {e}")

        # ── Step 7: Update trade monitoring ──
        self._update_open_trades()

        self._last_scan_time = scan_start
        scan_duration = (datetime.now(IST) - scan_start).total_seconds()
        logger.info(f"Scan cycle #{self._scan_count} completed in {scan_duration:.1f}s")

    def _update_open_trades(self):
        """Update all open trades with current LTP data."""
        open_trades = self._trade_manager.get_open_trades()
        if not open_trades:
            return

        ltp_map = {}
        for trade in open_trades:
            ltp = self._market_feed.get_ltp(trade.security_id)
            if ltp <= 0:
                ltp = self._broker.get_ltp(trade.security_id)
            if ltp > 0:
                ltp_map[trade.symbol] = ltp

        self._trade_manager.update_trades(ltp_map, candles_elapsed=1)

        # Send exit alerts for newly closed trades
        if self._telegram:
            for trade in self._trade_manager.get_closed_trades():
                if trade.exit_time and (
                    datetime.now(IST) - trade.exit_time.replace(tzinfo=IST)
                ).total_seconds() < 60:
                    try:
                        self._telegram.send_exit_alert(trade)
                    except Exception as e:
                        logger.error(f"Telegram exit alert error: {e}")

    def _handle_force_close(self):
        """Handle forced end-of-day close for all open trades."""
        open_trades = self._trade_manager.get_open_trades()
        if not open_trades:
            return

        logger.info(
            f"FORCE CLOSE: Closing {len(open_trades)} open trades "
            f"(15:15-15:25 IST window)"
        )

        ltp_map = {}
        for trade in open_trades:
            ltp = self._market_feed.get_ltp(trade.security_id)
            if ltp <= 0:
                ltp = self._broker.get_ltp(trade.security_id)
            if ltp > 0:
                ltp_map[trade.symbol] = ltp

        self._trade_manager.force_close_all(ltp_map)

        # Send exit alerts
        if self._telegram:
            for trade in self._trade_manager.get_closed_trades():
                if trade.exit_reason == "forced_eod_close":
                    try:
                        self._telegram.send_exit_alert(trade)
                    except Exception as e:
                        logger.error(f"Telegram force-close alert error: {e}")

    def reset_daily(self):
        """Reset daily state for a new trading day."""
        self._already_signaled.clear()
        self._scan_count = 0
        logger.info("Scanner daily state reset.")

    def get_scan_stats(self) -> dict:
        """Get current scanner statistics."""
        return {
            "scan_count": self._scan_count,
            "last_scan_time": self._last_scan_time,
            "signals_today": len(self._already_signaled),
            "sentiment_bullish": self._sentiment_engine.is_bullish(),
            "positive_count": self._sentiment_engine.get_positive_count(),
            "negative_count": self._sentiment_engine.get_negative_count(),
            "open_trades": len(self._trade_manager.get_open_trades()),
            "closed_trades": len(self._trade_manager.get_closed_trades()),
        }
