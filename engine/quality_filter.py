"""
Quality Filter.
Rejects any signal that doesn't meet A+ quality standards.
ALL conditions must pass — a single failure rejects the signal.
"""

import logging
from typing import Optional, Tuple

import pandas as pd

from strategies.base_strategy import Signal
from indicators.technical import (
    calculate_average_volume,
    calculate_average_candle_range,
    is_oversized_candle,
    count_consecutive_green,
    has_abnormal_candle,
    calculate_distance_from_ema_pct,
    calculate_ema,
)
from config.settings import settings

logger = logging.getLogger(__name__)


class QualityFilter:
    """
    A+ Quality Filter for trade signals.
    Rejects any stock if ANY of the following conditions fail:

    1. Entry candle is too large
    2. Volume is below average
    3. Liquidity is poor
    4. Spread is large
    5. Price is too extended from EMA 9
    6. Risk Reward below minimum threshold
    7. Momentum already exhausted
    8. Large abnormal candle present
    9. Any rule violation exists
    """

    def filter(
        self,
        signal: Signal,
        candles: pd.DataFrame,
        spread_pct: float = 0.0,
    ) -> Tuple[bool, str]:
        """
        Apply all quality filters to a signal.

        Args:
            signal: The trade signal to validate.
            candles: The candle DataFrame used to generate the signal.
            spread_pct: Current bid-ask spread as percentage (0 if unavailable).

        Returns:
            Tuple of (passed: bool, rejection_reason: str).
            If passed is True, rejection_reason is empty.
        """
        # ── Filter 1: Entry candle is too large ──
        avg_range = calculate_average_candle_range(candles, settings.VOLUME_AVG_PERIOD)
        if signal.candle_index < len(candles):
            entry_candle = candles.iloc[signal.candle_index]
            entry_body = abs(entry_candle["close"] - entry_candle["open"])
            if is_oversized_candle(
                entry_body, avg_range, settings.OVERSIZED_CANDLE_MULTIPLIER
            ):
                return False, "Entry candle is oversized"

        # ── Filter 2: Volume is below average ──
        avg_volume = calculate_average_volume(
            candles["volume"], settings.VOLUME_AVG_PERIOD
        )
        if avg_volume > 0 and signal.volume <= avg_volume:
            return False, f"Volume {signal.volume} below avg {avg_volume:.0f}"

        # ── Filter 3: Liquidity is poor ──
        liquidity = signal.entry_price * signal.volume
        min_liquidity = settings.MIN_LIQUIDITY_LAKHS * 100000
        if liquidity < min_liquidity:
            return (
                False,
                f"Liquidity {liquidity / 100000:.1f}L below min {settings.MIN_LIQUIDITY_LAKHS}L",
            )

        # ── Filter 4: Spread is large ──
        if spread_pct > 0 and spread_pct > settings.MAX_SPREAD_PCT:
            return False, f"Spread {spread_pct:.2f}% exceeds max {settings.MAX_SPREAD_PCT}%"

        # ── Filter 5: Price too extended from EMA 9 ──
        if abs(signal.distance_from_ema) > settings.MAX_EMA_DISTANCE_PCT:
            return (
                False,
                f"Distance from EMA 9: {signal.distance_from_ema:.2f}% "
                f"exceeds max {settings.MAX_EMA_DISTANCE_PCT}%",
            )

        # ── Filter 6: Risk Reward below minimum threshold ──
        if signal.setup_type == "1_pct_setup":
            min_rr = settings.MIN_RR_ONE_PCT
        else:
            min_rr = settings.MIN_RR_EMA_PULLBACK

        if signal.risk_reward < min_rr:
            return (
                False,
                f"RR {signal.risk_reward} below min {min_rr} for {signal.setup_type}",
            )

        # ── Filter 7: Momentum already exhausted ──
        consecutive_green = count_consecutive_green(candles.iloc[: signal.candle_index + 1])
        if consecutive_green > settings.MAX_CONSECUTIVE_GREEN:
            return (
                False,
                f"{consecutive_green} consecutive green candles — momentum exhausted",
            )

        # ── Filter 8: Large abnormal candle present ──
        lookback = min(len(candles), settings.VOLUME_AVG_PERIOD)
        check_candles = candles.iloc[max(0, signal.candle_index - lookback) : signal.candle_index + 1]
        if has_abnormal_candle(
            check_candles,
            multiplier=settings.ABNORMAL_CANDLE_MULTIPLIER,
            lookback=lookback,
        ):
            return False, "Abnormal large candle detected in recent history"

        # ── Filter 9: Check risk is positive ──
        risk = signal.entry_price - signal.stop_loss
        if risk <= 0:
            return False, "Invalid risk: entry <= stop_loss"

        logger.debug(f"Quality filter PASSED for {signal.symbol}")
        return True, ""
