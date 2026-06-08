"""
Abstract broker interface.
All broker implementations must inherit from BrokerBase.
This allows swapping Dhan for Kite/Upstox without changing application code.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd


@dataclass
class Quote:
    """Market quote data for a single instrument."""
    security_id: str
    symbol: str
    ltp: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    prev_close: float = 0.0
    volume: int = 0
    bid: float = 0.0
    ask: float = 0.0
    timestamp: Optional[datetime] = None


@dataclass
class Instrument:
    """Represents a tradeable instrument."""
    symbol: str
    security_id: str
    exchange_segment: str
    isin: str = ""
    name: str = ""
    lot_size: int = 1
    tick_size: float = 0.05


class BrokerBase(ABC):
    """
    Abstract base class for all broker integrations.
    Defines the contract that every broker adapter must implement.
    """

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the broker connection.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def get_ltp(self, security_id: str, exchange_segment: str = "NSE_EQ") -> float:
        """
        Get the Last Traded Price for a given instrument.

        Args:
            security_id: Broker-specific security identifier.
            exchange_segment: Exchange segment (e.g., 'NSE_EQ').

        Returns:
            Last traded price as float.
        """
        pass

    @abstractmethod
    def get_ohlc(self, security_id: str, exchange_segment: str = "NSE_EQ") -> Dict[str, float]:
        """
        Get current day OHLC data.

        Args:
            security_id: Broker-specific security identifier.
            exchange_segment: Exchange segment.

        Returns:
            Dict with keys: open, high, low, close.
        """
        pass

    @abstractmethod
    def get_quote(self, security_id: str, exchange_segment: str = "NSE_EQ") -> Quote:
        """
        Get full market quote for a given instrument.

        Args:
            security_id: Broker-specific security identifier.
            exchange_segment: Exchange segment.

        Returns:
            Quote object with all market data fields.
        """
        pass

    @abstractmethod
    def get_historical_data(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
        from_date: str,
        to_date: str,
        interval: str = "5",
    ) -> pd.DataFrame:
        """
        Get historical OHLCV candle data.

        Args:
            security_id: Broker-specific security identifier.
            exchange_segment: Exchange segment.
            instrument_type: Instrument type (e.g., 'EQUITY').
            from_date: Start date string (YYYY-MM-DD).
            to_date: End date string (YYYY-MM-DD).
            interval: Candle interval in minutes (default '5').

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume.
        """
        pass

    @abstractmethod
    def get_intraday_data(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
    ) -> pd.DataFrame:
        """
        Get today's intraday candle data (5-minute candles).

        Args:
            security_id: Broker-specific security identifier.
            exchange_segment: Exchange segment.
            instrument_type: Instrument type.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume.
        """
        pass

    @abstractmethod
    def get_previous_close(self, security_id: str, exchange_segment: str = "NSE_EQ") -> float:
        """
        Get previous trading day's closing price.

        Args:
            security_id: Broker-specific security identifier.
            exchange_segment: Exchange segment.

        Returns:
            Previous close price as float.
        """
        pass

    @abstractmethod
    def get_market_status(self) -> str:
        """
        Check if market is currently open.

        Returns:
            'open', 'closed', or 'pre_open'.
        """
        pass
