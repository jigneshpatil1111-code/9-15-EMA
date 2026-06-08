"""
Instrument manager.
Loads Nifty 500 constituents and maps them to Dhan security IDs
using the Dhan security master CSV.
"""

import logging
import os
import time
from typing import List, Dict, Optional
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

from core.broker_base import Instrument
from config.settings import settings

logger = logging.getLogger(__name__)

# Dhan security master download URL
DHAN_SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

# NSE Nifty 500 index constituents URL
NIFTY500_URL = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"

# Local fallback: if NSE API fails, use cached file
NIFTY500_CACHE_FILE = "nifty500_symbols.csv"


class InstrumentManager:
    """
    Manages Nifty 500 instrument loading and Dhan security_id mapping.
    Downloads Dhan security master CSV and cross-references with Nifty 500 symbols.
    """

    def __init__(self, data_dir: str = ""):
        self._data_dir = data_dir or os.path.join(settings.BASE_DIR, settings.DATA_DIR)
        os.makedirs(self._data_dir, exist_ok=True)

        self._scrip_master: Optional[pd.DataFrame] = None
        self._nifty500_symbols: List[str] = []
        self._instruments: List[Instrument] = []
        self._symbol_to_instrument: Dict[str, Instrument] = {}
        self._secid_to_instrument: Dict[str, Instrument] = {}

    def load(self) -> List[Instrument]:
        """
        Load Nifty 500 instruments with Dhan security IDs.

        Steps:
        1. Download/load Dhan security master CSV.
        2. Load Nifty 500 symbol list.
        3. Cross-reference to build instrument list.

        Returns:
            List of Instrument objects with security IDs.
        """
        logger.info("Loading instrument data...")

        self._load_scrip_master()
        self._load_nifty500_symbols()
        self._build_instrument_list()

        logger.info(f"Loaded {len(self._instruments)} Nifty 500 instruments with security IDs.")
        return self._instruments

    def _load_scrip_master(self):
        """Download and parse the Dhan security master CSV."""
        cache_path = os.path.join(self._data_dir, "api-scrip-master.csv")
        today_str = date.today().strftime("%Y-%m-%d")
        marker_path = os.path.join(self._data_dir, f".scrip_master_{today_str}")

        # Use cached file if downloaded today
        if os.path.exists(cache_path) and os.path.exists(marker_path):
            logger.info("Using cached Dhan security master (downloaded today).")
        else:
            logger.info("Downloading Dhan security master CSV...")
            try:
                response = requests.get(DHAN_SCRIP_MASTER_URL, timeout=60)
                response.raise_for_status()
                with open(cache_path, "wb") as f:
                    f.write(response.content)
                # Write date marker
                with open(marker_path, "w") as f:
                    f.write(today_str)
                logger.info("Dhan security master downloaded successfully.")
            except Exception as e:
                logger.error(f"Failed to download security master: {e}")
                if not os.path.exists(cache_path):
                    raise RuntimeError(
                        "Cannot load Dhan security master. "
                        "Check your internet connection."
                    )
                logger.warning("Using stale cached security master.")

        try:
            self._scrip_master = pd.read_csv(cache_path, low_memory=False)
            logger.info(f"Security master loaded: {len(self._scrip_master)} records.")
        except Exception as e:
            raise RuntimeError(f"Failed to parse security master CSV: {e}")

    def _load_nifty500_symbols(self):
        """Load Nifty 500 constituent symbols."""
        cache_path = os.path.join(self._data_dir, NIFTY500_CACHE_FILE)

        # Try NSE API first
        symbols = self._fetch_nifty500_from_nse()

        if not symbols:
            # Try loading from cache
            if os.path.exists(cache_path):
                logger.info("Loading Nifty 500 symbols from cache.")
                try:
                    df = pd.read_csv(cache_path)
                    symbols = df["symbol"].tolist()
                except Exception as e:
                    logger.error(f"Failed to load cached Nifty 500 list: {e}")

        if not symbols:
            # Final fallback: extract top 500 NSE equities from scrip master
            logger.warning("Falling back to top NSE equities from scrip master.")
            symbols = self._extract_nse_equities_from_master()

        self._nifty500_symbols = symbols

        # Cache the symbols
        try:
            pd.DataFrame({"symbol": symbols}).to_csv(cache_path, index=False)
        except Exception as e:
            logger.warning(f"Failed to cache Nifty 500 symbols: {e}")

        logger.info(f"Loaded {len(self._nifty500_symbols)} Nifty 500 symbols.")

    def _fetch_nifty500_from_nse(self) -> List[str]:
        """Fetch Nifty 500 constituents from NSE India API."""
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "application/json",
                "Referer": "https://www.nseindia.com/",
            }
            session = requests.Session()
            # First hit the main page to get cookies
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            time.sleep(1)
            # Then hit the API
            response = session.get(NIFTY500_URL, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            stocks = data.get("data", [])
            symbols = [
                s["symbol"]
                for s in stocks
                if s.get("symbol") and s["symbol"] != "NIFTY 500"
            ]
            logger.info(f"Fetched {len(symbols)} symbols from NSE API.")
            return symbols
        except Exception as e:
            logger.warning(f"NSE API fetch failed (will use cache): {e}")
            return []

    def _extract_nse_equities_from_master(self) -> List[str]:
        """Extract NSE equity symbols from the Dhan security master as fallback."""
        if self._scrip_master is None:
            return []
        try:
            nse_eq = self._scrip_master[
                (self._scrip_master["SEM_EXM_EXCH_ID"] == "NSE")
                & (self._scrip_master["SEM_SEGMENT"] == "E")
                & (self._scrip_master["SEM_INSTRUMENT_NAME"] == "EQUITY")
            ]
            symbols = nse_eq["SEM_TRADING_SYMBOL"].dropna().unique().tolist()
            # Return all NSE equities (may be more than 500 but covers the universe)
            return symbols[:500]
        except Exception as e:
            logger.error(f"Failed to extract equities from master: {e}")
            return []

    def _build_instrument_list(self):
        """Cross-reference Nifty 500 symbols with Dhan security master."""
        if self._scrip_master is None or not self._nifty500_symbols:
            logger.error("Cannot build instrument list: missing data.")
            return

        # Filter scrip master for NSE equity
        nse_eq = self._scrip_master[
            (self._scrip_master["SEM_EXM_EXCH_ID"] == "NSE")
            & (self._scrip_master["SEM_SEGMENT"] == "E")
        ].copy()

        # Build a lookup by trading symbol
        symbol_lookup = {}
        for _, row in nse_eq.iterrows():
            sym = str(row.get("SEM_TRADING_SYMBOL", "")).strip().upper()
            if sym:
                symbol_lookup[sym] = row

        instruments = []
        matched = 0
        unmatched = []

        for symbol in self._nifty500_symbols:
            sym_upper = symbol.strip().upper()
            row = symbol_lookup.get(sym_upper)

            if row is not None:
                inst = Instrument(
                    symbol=sym_upper,
                    security_id=str(int(row["SEM_SMST_SECURITY_ID"])),
                    exchange_segment="NSE_EQ",
                    isin=str(row.get("SEM_ISIN", "")),
                    name=str(row.get("SEM_CUSTOM_SYMBOL", sym_upper)),
                    lot_size=int(row.get("SEM_LOT_UNITS", 1)),
                    tick_size=float(row.get("SEM_TICK_SIZE", 0.05)),
                )
                instruments.append(inst)
                matched += 1
            else:
                unmatched.append(sym_upper)

        self._instruments = instruments
        self._symbol_to_instrument = {inst.symbol: inst for inst in instruments}
        self._secid_to_instrument = {inst.security_id: inst for inst in instruments}

        if unmatched:
            logger.warning(
                f"{len(unmatched)} symbols not found in Dhan master: "
                f"{unmatched[:10]}{'...' if len(unmatched) > 10 else ''}"
            )
        logger.info(f"Matched {matched}/{len(self._nifty500_symbols)} Nifty 500 symbols.")

    def get_instruments(self) -> List[Instrument]:
        """Get the full list of loaded instruments."""
        return self._instruments

    def get_instrument_by_symbol(self, symbol: str) -> Optional[Instrument]:
        """Look up an instrument by its trading symbol."""
        return self._symbol_to_instrument.get(symbol.upper())

    def get_instrument_by_security_id(self, security_id: str) -> Optional[Instrument]:
        """Look up an instrument by its Dhan security ID."""
        return self._secid_to_instrument.get(str(security_id))

    def get_websocket_subscription_list(self) -> List[Dict]:
        """
        Get the list of instruments formatted for WebSocket subscription.
        Returns list of dicts: [{"exchange_segment": "NSE_EQ", "security_id": "1333"}, ...]
        """
        return [
            {
                "exchange_segment": inst.exchange_segment,
                "security_id": inst.security_id,
            }
            for inst in self._instruments
        ]
