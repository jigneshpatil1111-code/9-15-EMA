"""
Backtesting Historical Data Loader.
Fetches and caches historical 5-minute data from Dhan for backtesting.
"""

import logging
import os
from datetime import date, timedelta
from typing import List, Optional, Dict

import pandas as pd

from core.broker_base import BrokerBase, Instrument
from config.settings import settings

logger = logging.getLogger(__name__)


class BacktestDataLoader:
    """
    Loads and caches historical 5-minute candle data for backtesting.
    Uses Parquet format for fast local storage and retrieval.
    """

    def __init__(self, broker: BrokerBase, data_dir: str = ""):
        self._broker = broker
        self._data_dir = data_dir or os.path.join(
            settings.BASE_DIR, settings.DATA_DIR, "backtest"
        )
        os.makedirs(self._data_dir, exist_ok=True)

    def load_data(
        self,
        instrument: Instrument,
        start_date: date,
        end_date: date,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Load historical 5-minute data for a single instrument.

        Args:
            instrument: Instrument object with security_id.
            start_date: Start date.
            end_date: End date.
            use_cache: Whether to use cached data.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume, date.
        """
        cache_file = os.path.join(
            self._data_dir,
            f"{instrument.symbol}_{start_date}_{end_date}.parquet",
        )

        # Check cache
        if use_cache and os.path.exists(cache_file):
            try:
                df = pd.read_parquet(cache_file)
                logger.debug(f"Loaded cached data for {instrument.symbol}: {len(df)} candles")
                return df
            except Exception as e:
                logger.warning(f"Cache read failed for {instrument.symbol}: {e}")

        # Fetch from broker in chunks (Dhan limits data range per request)
        all_data = []
        chunk_start = start_date

        while chunk_start < end_date:
            chunk_end = min(chunk_start + timedelta(days=30), end_date)

            try:
                df = self._broker.get_historical_data(
                    security_id=instrument.security_id,
                    exchange_segment=instrument.exchange_segment,
                    instrument_type="EQUITY",
                    from_date=chunk_start.strftime("%Y-%m-%d"),
                    to_date=chunk_end.strftime("%Y-%m-%d"),
                    interval="5",
                )
                if not df.empty:
                    all_data.append(df)
            except Exception as e:
                logger.warning(
                    f"Data fetch error for {instrument.symbol} "
                    f"({chunk_start} to {chunk_end}): {e}"
                )

            chunk_start = chunk_end + timedelta(days=1)

        if not all_data:
            logger.warning(f"No data fetched for {instrument.symbol}")
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

        # Combine all chunks
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.sort_values("timestamp").reset_index(drop=True)
        combined = combined.drop_duplicates(subset=["timestamp"])

        # Add date column for day-by-day iteration
        combined["date"] = pd.to_datetime(combined["timestamp"]).dt.date

        # Cache to Parquet
        try:
            combined.to_parquet(cache_file, index=False)
            logger.debug(f"Cached {len(combined)} candles for {instrument.symbol}")
        except Exception as e:
            logger.warning(f"Cache write failed for {instrument.symbol}: {e}")

        return combined

    def load_bulk_data(
        self,
        instruments: List[Instrument],
        start_date: date,
        end_date: date,
        use_cache: bool = True,
        progress_callback=None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load historical data for multiple instruments.

        Args:
            instruments: List of instruments to load data for.
            start_date: Start date.
            end_date: End date.
            use_cache: Whether to use cached data.
            progress_callback: Optional callback(current, total) for progress tracking.

        Returns:
            Dict mapping symbol to DataFrame.
        """
        data = {}
        total = len(instruments)

        for i, inst in enumerate(instruments):
            try:
                df = self.load_data(inst, start_date, end_date, use_cache)
                if not df.empty:
                    data[inst.symbol] = df
            except Exception as e:
                logger.warning(f"Failed to load data for {inst.symbol}: {e}")

            if progress_callback:
                progress_callback(i + 1, total)

        logger.info(f"Loaded data for {len(data)}/{total} instruments")
        return data

    def get_daily_candles(
        self, data: pd.DataFrame, target_date: date
    ) -> pd.DataFrame:
        """
        Extract candles for a specific trading day.

        Args:
            data: Full historical DataFrame.
            target_date: The date to extract.

        Returns:
            DataFrame with candles for that day only.
        """
        if "date" not in data.columns:
            data["date"] = pd.to_datetime(data["timestamp"]).dt.date

        day_data = data[data["date"] == target_date].copy()
        return day_data.reset_index(drop=True)

    def get_previous_close(
        self, data: pd.DataFrame, target_date: date
    ) -> float:
        """
        Get the previous trading day's closing price.

        Args:
            data: Full historical DataFrame.
            target_date: Current date (will find the close from the day before).

        Returns:
            Previous close price, or 0.0 if not available.
        """
        if "date" not in data.columns:
            data["date"] = pd.to_datetime(data["timestamp"]).dt.date

        prev_days = data[data["date"] < target_date]
        if prev_days.empty:
            return 0.0

        last_day = prev_days["date"].max()
        last_candle = prev_days[prev_days["date"] == last_day].iloc[-1]
        return float(last_candle["close"])

    def get_trading_days(self, data: pd.DataFrame) -> List[date]:
        """Get a sorted list of unique trading days in the data."""
        if "date" not in data.columns:
            data["date"] = pd.to_datetime(data["timestamp"]).dt.date
        return sorted(data["date"].unique().tolist())

    def clear_cache(self):
        """Clear all cached backtest data."""
        import shutil
        if os.path.exists(self._data_dir):
            shutil.rmtree(self._data_dir)
            os.makedirs(self._data_dir, exist_ok=True)
            logger.info("Backtest data cache cleared.")
