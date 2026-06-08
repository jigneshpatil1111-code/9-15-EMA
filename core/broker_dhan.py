"""
Dhan API broker implementation.
Concrete implementation of BrokerBase using the dhanhq Python SDK.
"""

import logging
import time
from typing import Dict, Optional
from datetime import date, datetime, timedelta

import pandas as pd

from core.broker_base import BrokerBase, Quote
from config.settings import settings

logger = logging.getLogger(__name__)


class DhanBroker(BrokerBase):
    """
    Dhan API broker adapter.
    Wraps the dhanhq SDK to provide a unified interface.
    """

    def __init__(self):
        self._client = None
        self._initialized = False
        self._rate_limit_delay = 0.35  # ~3 requests/sec to stay within limits

    def initialize(self) -> bool:
        """Initialize the Dhan API client with credentials from settings."""
        try:
            from dhanhq import dhanhq, DhanContext

            context = DhanContext(settings.DHAN_CLIENT_ID, settings.DHAN_ACCESS_TOKEN)
            self._client = dhanhq(context)
            self._initialized = True
            logger.info("Dhan API client initialized successfully.")
            return True
        except ImportError:
            logger.error("dhanhq package not installed. Run: pip install dhanhq")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Dhan API client: {e}")
            return False

    def _ensure_initialized(self):
        """Raise if broker not initialized."""
        if not self._initialized or self._client is None:
            raise RuntimeError("Dhan broker not initialized. Call initialize() first.")

    def _throttle(self):
        """Rate-limit API calls to stay within Dhan limits."""
        time.sleep(self._rate_limit_delay)

    def get_ltp(self, security_id: str, exchange_segment: str = "NSE_EQ") -> float:
        """Get Last Traded Price from Dhan API."""
        self._ensure_initialized()
        self._throttle()
        try:
            response = self._client.quote_data(
                {exchange_segment: [security_id]}
            )
            if response and response.get("status") == "success":
                data = response.get("data", {})
                return float(data.get("ltp", 0.0))
            logger.warning(f"LTP fetch failed for {security_id}: {response}")
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching LTP for {security_id}: {e}")
            return 0.0

    def get_ohlc(self, security_id: str, exchange_segment: str = "NSE_EQ") -> Dict[str, float]:
        """Get current day OHLC data from Dhan API."""
        self._ensure_initialized()
        self._throttle()
        try:
            response = self._client.quote_data(
                {exchange_segment: [security_id]}
            )
            if response and response.get("status") == "success":
                data = response.get("data", {})
                return {
                    "open": float(data.get("open", 0.0)),
                    "high": float(data.get("high", 0.0)),
                    "low": float(data.get("low", 0.0)),
                    "close": float(data.get("ltp", 0.0)),
                }
            logger.warning(f"OHLC fetch failed for {security_id}: {response}")
            return {"open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0}
        except Exception as e:
            logger.error(f"Error fetching OHLC for {security_id}: {e}")
            return {"open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0}

    def get_quote(self, security_id: str, exchange_segment: str = "NSE_EQ") -> Quote:
        """Get full market quote from Dhan API."""
        self._ensure_initialized()
        self._throttle()
        try:
            response = self._client.quote_data(
                {exchange_segment: [security_id]}
            )
            if response and response.get("status") == "success":
                data = response.get("data", {})
                return Quote(
                    security_id=security_id,
                    symbol=data.get("symbol", ""),
                    ltp=float(data.get("ltp", 0.0)),
                    open=float(data.get("open", 0.0)),
                    high=float(data.get("high", 0.0)),
                    low=float(data.get("low", 0.0)),
                    close=float(data.get("ltp", 0.0)),
                    prev_close=float(data.get("prev_close", 0.0)),
                    volume=int(data.get("volume", 0)),
                    bid=float(data.get("bid", 0.0)),
                    ask=float(data.get("ask", 0.0)),
                    timestamp=datetime.now(),
                )
            return Quote(security_id=security_id, symbol="")
        except Exception as e:
            logger.error(f"Error fetching quote for {security_id}: {e}")
            return Quote(security_id=security_id, symbol="")

    def get_historical_data(
        self,
        security_id: str,
        exchange_segment: str = "NSE_EQ",
        instrument_type: str = "EQUITY",
        from_date: str = "",
        to_date: str = "",
        interval: str = "5",
    ) -> pd.DataFrame:
        """
        Get historical OHLCV candle data from Dhan API.
        Returns a DataFrame with columns: timestamp, open, high, low, close, volume.
        """
        self._ensure_initialized()
        self._throttle()

        if not from_date:
            from_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not to_date:
            to_date = date.today().strftime("%Y-%m-%d")

        try:
            response = self._client.historical_minute_data(
                security_id=security_id,
                exchange_segment=exchange_segment,
                instrument_type=instrument_type,
                from_date=from_date,
                to_date=to_date,
            )
            return self._parse_candle_response(response)
        except Exception as e:
            logger.error(f"Error fetching historical data for {security_id}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    def get_intraday_data(
        self,
        security_id: str,
        exchange_segment: str = "NSE_EQ",
        instrument_type: str = "EQUITY",
    ) -> pd.DataFrame:
        """
        Get today's intraday 5-minute candle data from Dhan API.
        Returns a DataFrame with columns: timestamp, open, high, low, close, volume.
        """
        self._ensure_initialized()
        self._throttle()
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            response = self._client.intraday_minute_data(
                security_id=security_id,
                exchange_segment=exchange_segment,
                instrument_type=instrument_type,
                from_date=today_str,
                to_date=today_str,
            )
            return self._parse_candle_response(response)
        except Exception as e:
            logger.error(f"Error fetching intraday data for {security_id}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    def get_previous_close(self, security_id: str, exchange_segment: str = "NSE_EQ") -> float:
        """Get previous trading day's closing price."""
        self._ensure_initialized()
        self._throttle()
        try:
            response = self._client.quote_data(
                {exchange_segment: [security_id]}
            )
            if response and response.get("status") == "success":
                data = response.get("data", {})
                return float(data.get("prev_close", 0.0))
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching previous close for {security_id}: {e}")
            return 0.0

    def get_market_status(self) -> str:
        """
        Determine market status based on current IST time.
        Dhan does not provide a direct market status endpoint,
        so we derive it from the clock.
        """
        import pytz

        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        current_time = now.time()

        from datetime import time as dt_time

        pre_open_start = dt_time(9, 0)
        market_open = dt_time(9, 15)
        market_close = dt_time(15, 30)

        if now.weekday() >= 5:
            return "closed"
        if pre_open_start <= current_time < market_open:
            return "pre_open"
        elif market_open <= current_time <= market_close:
            return "open"
        else:
            return "closed"

    def _parse_candle_response(self, response: dict) -> pd.DataFrame:
        """
        Parse Dhan candle API response into a standardized DataFrame.
        Dhan returns candle data as:
        {
            "status": "success",
            "data": {
                "open": [...], "high": [...], "low": [...],
                "close": [...], "volume": [...], "timestamp": [...]
            }
        }
        """
        empty = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        if not response or response.get("status") != "success":
            logger.warning(f"Candle data response unsuccessful: {response}")
            return empty

        data = response.get("data", {})
        if not data:
            return empty

        timestamps = data.get("start_Time", data.get("timestamp", []))
        opens = data.get("open", [])
        highs = data.get("high", [])
        lows = data.get("low", [])
        closes = data.get("close", [])
        volumes = data.get("volume", [])

        if not timestamps or not opens:
            return empty

        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(timestamps),
                "open": [float(x) for x in opens],
                "high": [float(x) for x in highs],
                "low": [float(x) for x in lows],
                "close": [float(x) for x in closes],
                "volume": [int(x) for x in volumes],
            }
        )
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
