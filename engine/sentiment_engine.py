"""
Market Sentiment Engine.
Scans all Nifty 500 stocks and counts positive vs negative stocks.
Scanning is ONLY allowed when market sentiment is BULLISH (>= 300 positive stocks).
"""

import logging
import threading
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class SentimentData:
    """Snapshot of market sentiment at a point in time."""
    timestamp: datetime
    positive_count: int
    negative_count: int
    unchanged_count: int
    total_scanned: int
    status: str  # 'BULLISH' or 'NEUTRAL'
    top_gainers: list
    top_losers: list


class SentimentEngine:
    """
    Market Sentiment Engine.
    Evaluates whether the broad market is bullish by counting
    how many of the Nifty 500 stocks are positive vs negative.

    Rule:
    - BULLISH: 300 or more stocks positive → scanning allowed
    - NEUTRAL: less than 300 positive → no signals generated
    """

    def __init__(self, market_feed=None, broker=None, instruments=None):
        """
        Args:
            market_feed: MarketFeedManager for real-time LTP.
            broker: BrokerBase instance for fallback quote fetching.
            instruments: List of Instrument objects (Nifty 500).
        """
        self._market_feed = market_feed
        self._broker = broker
        self._instruments = instruments or []
        self._lock = threading.Lock()
        self._latest_sentiment: Optional[SentimentData] = None
        self._threshold = settings.SENTIMENT_BULLISH_THRESHOLD

    def set_instruments(self, instruments):
        """Update the instrument list."""
        self._instruments = instruments

    def set_market_feed(self, market_feed):
        """Set the market feed reference."""
        self._market_feed = market_feed

    def evaluate(self) -> SentimentData:
        """
        Evaluate current market sentiment.
        Calculates the percentage change from previous close for each stock.
        Counts positive and negative stocks.

        Returns:
            SentimentData with current market sentiment status.
        """
        positive = 0
        negative = 0
        unchanged = 0
        scanned = 0
        changes = []

        for inst in self._instruments:
            try:
                ltp = 0.0
                prev_close = 0.0

                # Try market feed first (fastest)
                if self._market_feed:
                    ltp = self._market_feed.get_ltp(inst.security_id)
                    prev_close = self._market_feed.get_prev_close(inst.security_id)

                # Fallback to broker API
                if (ltp <= 0 or prev_close <= 0) and self._broker:
                    if ltp <= 0:
                        ltp = self._broker.get_ltp(inst.security_id, inst.exchange_segment)
                    if prev_close <= 0:
                        prev_close = self._broker.get_previous_close(
                            inst.security_id, inst.exchange_segment
                        )

                if ltp <= 0 or prev_close <= 0:
                    continue

                pct_change = ((ltp - prev_close) / prev_close) * 100.0
                scanned += 1

                if pct_change > 0:
                    positive += 1
                elif pct_change < 0:
                    negative += 1
                else:
                    unchanged += 1

                changes.append((inst.symbol, pct_change, ltp))

            except Exception as e:
                logger.debug(f"Sentiment scan error for {inst.symbol}: {e}")
                continue

        # Sort for top gainers/losers
        changes.sort(key=lambda x: x[1], reverse=True)
        top_gainers = [
            {"symbol": c[0], "change": round(c[1], 2), "ltp": c[2]}
            for c in changes[:10]
        ]
        top_losers = [
            {"symbol": c[0], "change": round(c[1], 2), "ltp": c[2]}
            for c in changes[-10:]
        ]

        # Determine status
        status = "BULLISH" if positive >= self._threshold else "NEUTRAL"

        sentiment = SentimentData(
            timestamp=datetime.now(),
            positive_count=positive,
            negative_count=negative,
            unchanged_count=unchanged,
            total_scanned=scanned,
            status=status,
            top_gainers=top_gainers,
            top_losers=top_losers,
        )

        with self._lock:
            self._latest_sentiment = sentiment

        logger.info(
            f"Sentiment: {status} | "
            f"Positive: {positive}/{scanned} | "
            f"Negative: {negative}/{scanned} | "
            f"Threshold: {self._threshold}"
        )

        return sentiment

    def is_bullish(self) -> bool:
        """
        Check if the market is currently bullish.
        Returns False if sentiment has not been evaluated yet.
        """
        with self._lock:
            if self._latest_sentiment is None:
                return False
            return self._latest_sentiment.status == "BULLISH"

    def get_sentiment_data(self) -> Optional[SentimentData]:
        """Get the latest sentiment evaluation data."""
        with self._lock:
            return self._latest_sentiment

    def get_positive_count(self) -> int:
        """Get the count of positive stocks from the latest evaluation."""
        with self._lock:
            if self._latest_sentiment is None:
                return 0
            return self._latest_sentiment.positive_count

    def get_negative_count(self) -> int:
        """Get the count of negative stocks from the latest evaluation."""
        with self._lock:
            if self._latest_sentiment is None:
                return 0
            return self._latest_sentiment.negative_count
