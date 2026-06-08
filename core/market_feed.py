"""
WebSocket live market feed manager.
Connects to Dhan MarketFeed WebSocket for real-time tick data.
Maintains an in-memory tick store keyed by security_id.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """In-memory tick data for a single instrument."""
    security_id: str
    ltp: float = 0.0
    prev_close: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: int = 0
    last_update: Optional[datetime] = None


class MarketFeedManager:
    """
    Manages WebSocket connection to Dhan MarketFeed for real-time LTP data.
    Supports subscribing up to 5000 instruments per connection.
    """

    def __init__(self):
        self._feed = None
        self._tick_store: Dict[str, TickData] = {}
        self._lock = threading.Lock()
        self._connected = False
        self._feed_thread: Optional[threading.Thread] = None
        self._on_tick_callback: Optional[Callable] = None
        self._subscribed_instruments: List[Dict] = []

    def connect(self, instruments: List[Dict]) -> bool:
        """
        Connect to Dhan MarketFeed WebSocket and subscribe to instruments.

        Args:
            instruments: List of dicts with 'exchange_segment' and 'security_id'.
                         Example: [{"exchange_segment": "NSE_EQ", "security_id": "1333"}]

        Returns:
            True if connection started successfully.
        """
        try:
            from dhanhq import MarketFeed

            self._subscribed_instruments = instruments

            # Initialize tick store
            with self._lock:
                for inst in instruments:
                    sid = str(inst["security_id"])
                    if sid not in self._tick_store:
                        self._tick_store[sid] = TickData(security_id=sid)

            # Build subscription list in batches of 100
            instrument_list = [
                (inst["exchange_segment"], str(inst["security_id"]))
                for inst in instruments
            ]

            self._feed = MarketFeed(
                client_id=settings.DHAN_CLIENT_ID,
                access_token=settings.DHAN_ACCESS_TOKEN,
                instrument_list=instrument_list[:100],
                feed_type="ticker",
            )

            self._feed.on_connect = self._handle_connect
            self._feed.on_message = self._handle_message
            self._feed.on_close = self._handle_close
            self._feed.on_error = self._handle_error

            # Start in background thread
            self._feed_thread = threading.Thread(
                target=self._run_feed,
                daemon=True,
                name="MarketFeedThread",
            )
            self._feed_thread.start()

            logger.info(
                f"MarketFeed connection started for {len(instruments)} instruments."
            )
            return True

        except ImportError:
            logger.error("dhanhq package not installed. Run: pip install dhanhq")
            return False
        except Exception as e:
            logger.error(f"Failed to start MarketFeed: {e}")
            return False

    def _run_feed(self):
        """Run the WebSocket feed in the background thread."""
        try:
            self._feed.connect()
        except Exception as e:
            logger.error(f"MarketFeed connection error: {e}")
            self._connected = False
            # Auto-reconnect after delay
            time.sleep(5)
            self._attempt_reconnect()

    def _attempt_reconnect(self):
        """Attempt to reconnect to the market feed."""
        max_retries = 10
        retry_delay = 5

        for attempt in range(1, max_retries + 1):
            logger.info(f"Reconnect attempt {attempt}/{max_retries}...")
            try:
                if self.connect(self._subscribed_instruments):
                    logger.info("Reconnected successfully.")
                    return
            except Exception as e:
                logger.error(f"Reconnect attempt {attempt} failed: {e}")

            time.sleep(retry_delay * attempt)

        logger.error("Max reconnect attempts reached. MarketFeed offline.")

    def _handle_connect(self, message):
        """Called when WebSocket connection is established."""
        self._connected = True
        logger.info(f"MarketFeed connected: {message}")

        # Subscribe remaining instruments in batches of 100
        remaining = self._subscribed_instruments[100:]
        batch_size = 100
        for i in range(0, len(remaining), batch_size):
            batch = remaining[i : i + batch_size]
            try:
                sub_list = [
                    (inst["exchange_segment"], str(inst["security_id"]))
                    for inst in batch
                ]
                self._feed.subscribe(sub_list)
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Subscription batch error: {e}")

    def _handle_message(self, message):
        """
        Called for each incoming tick from the WebSocket.
        Updates the in-memory tick store.
        """
        try:
            if not isinstance(message, dict):
                return

            security_id = str(message.get("security_id", ""))
            if not security_id:
                return

            with self._lock:
                tick = self._tick_store.get(security_id)
                if tick is None:
                    tick = TickData(security_id=security_id)
                    self._tick_store[security_id] = tick

                tick.ltp = float(message.get("ltp", tick.ltp))
                tick.prev_close = float(message.get("prev_close", tick.prev_close))
                tick.open = float(message.get("open", tick.open))
                tick.high = float(message.get("high", tick.high))
                tick.low = float(message.get("low", tick.low))
                tick.volume = int(message.get("volume", tick.volume))
                tick.last_update = datetime.now()

            # Fire external callback if set
            if self._on_tick_callback:
                self._on_tick_callback(security_id, tick)

        except Exception as e:
            logger.error(f"Error processing tick message: {e}")

    def _handle_close(self, message):
        """Called when WebSocket connection closes."""
        self._connected = False
        logger.warning(f"MarketFeed connection closed: {message}")

    def _handle_error(self, error):
        """Called on WebSocket error."""
        logger.error(f"MarketFeed error: {error}")

    def set_on_tick(self, callback: Callable):
        """Set an external callback for each tick update."""
        self._on_tick_callback = callback

    def get_ltp(self, security_id: str) -> float:
        """Get the last traded price from the in-memory store."""
        with self._lock:
            tick = self._tick_store.get(str(security_id))
            return tick.ltp if tick else 0.0

    def get_prev_close(self, security_id: str) -> float:
        """Get the previous close from the in-memory store."""
        with self._lock:
            tick = self._tick_store.get(str(security_id))
            return tick.prev_close if tick else 0.0

    def get_tick(self, security_id: str) -> Optional[TickData]:
        """Get full tick data from the in-memory store."""
        with self._lock:
            return self._tick_store.get(str(security_id))

    def get_all_ticks(self) -> Dict[str, TickData]:
        """Get a snapshot of all ticks."""
        with self._lock:
            return dict(self._tick_store)

    def is_connected(self) -> bool:
        """Check if the WebSocket is connected."""
        return self._connected

    def disconnect(self):
        """Disconnect the WebSocket feed."""
        try:
            if self._feed:
                self._feed.disconnect()
            self._connected = False
            logger.info("MarketFeed disconnected.")
        except Exception as e:
            logger.error(f"Error disconnecting MarketFeed: {e}")

    def update_prev_close(self, security_id: str, prev_close: float):
        """Manually set the previous close for an instrument (used at startup)."""
        with self._lock:
            tick = self._tick_store.get(str(security_id))
            if tick:
                tick.prev_close = prev_close
            else:
                self._tick_store[str(security_id)] = TickData(
                    security_id=str(security_id),
                    prev_close=prev_close,
                )
