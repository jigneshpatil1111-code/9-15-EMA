"""
Strategy 1: 1% Setup
====================
Timeframe: 5 Minute

Rules (implemented EXACTLY as specified):
1. Stock opens gap-up.
2. First candle total range must be below 1%.
3. First candle can be green or red.
4. Second candle must not break first candle low.
5. Third or fourth candle must close above first candle body high.
6. Entry candle must not be oversized.
7. Entry candle must remain close to EMA 9.
8. Volume must be above average volume.
9. Liquidity must be sufficient.

Entry: Close of breakout candle.
Stop Loss: Low of entry candle.
Target 1: 1:3 Risk Reward.
Target 2: 1:4 Risk Reward.
Management: If trade does not move within next 4-5 candles, exit at breakeven.
"""

import logging
from typing import Optional

import pandas as pd

from strategies.base_strategy import BaseStrategy, Signal
from indicators.technical import (
    calculate_ema,
    calculate_candle_range_pct,
    calculate_candle_body_high,
    calculate_candle_body_low,
    is_gap_up,
    is_oversized_candle,
    calculate_average_volume,
    calculate_average_candle_range,
    calculate_rr_ratio,
    calculate_distance_from_ema_pct,
)
from config.settings import settings

logger = logging.getLogger(__name__)


class OnePercentSetup(BaseStrategy):
    """
    1% Setup Strategy.
    Detects gap-up stocks with a tight first candle (range < 1%)
    and a breakout above the first candle body high on the 3rd or 4th candle.
    """

    @property
    def name(self) -> str:
        return "1% Setup"

    @property
    def setup_type(self) -> str:
        return "1_pct_setup"

    def scan(
        self,
        symbol: str,
        security_id: str,
        candles: pd.DataFrame,
        prev_close: float,
    ) -> Optional[Signal]:
        """
        Scan for 1% Setup on 5-minute intraday candles.

        The scan checks candles sequentially:
        - Candle 0 (index 0): First candle (9:15-9:20)
        - Candle 1 (index 1): Second candle
        - Candle 2 (index 2): Third candle
        - Candle 3 (index 3): Fourth candle

        Returns a Signal if all rules pass on candle 2 or candle 3.
        """
        if not self._validate_candles(candles):
            return None

        # Need at least 3 candles (first + second + breakout on third)
        if len(candles) < 3:
            return None

        if prev_close <= 0:
            return None

        # ── Rule 1: Stock opens gap-up ──
        first_candle = candles.iloc[0]
        if not is_gap_up(first_candle["open"], prev_close):
            return None

        # ── Rule 2: First candle total range must be below 1% ──
        first_range_pct = calculate_candle_range_pct(
            first_candle["open"], first_candle["high"], first_candle["low"]
        )
        if first_range_pct >= settings.ONE_PCT_MAX_RANGE:
            return None

        # ── Rule 3: First candle can be green or red — no filter needed ──

        # ── Compute first candle reference values ──
        first_body_high = calculate_candle_body_high(
            first_candle["open"], first_candle["close"]
        )
        first_candle_low = first_candle["low"]

        # ── Rule 4: Second candle must not break first candle low ──
        second_candle = candles.iloc[1]
        if second_candle["low"] < first_candle_low:
            return None

        # ── Pre-compute EMA 9 and volume averages ──
        ema9 = calculate_ema(candles["close"], settings.EMA_FAST_PERIOD)
        avg_volume = calculate_average_volume(
            candles["volume"], settings.VOLUME_AVG_PERIOD
        )
        avg_range = calculate_average_candle_range(candles, settings.VOLUME_AVG_PERIOD)

        # ── Rule 5: Third or fourth candle must close above first candle body high ──
        breakout_candle = None
        breakout_idx = None

        # Check third candle (index 2)
        if len(candles) >= 3:
            third_candle = candles.iloc[2]
            if third_candle["close"] > first_body_high:
                breakout_candle = third_candle
                breakout_idx = 2

        # If third didn't break out, check fourth (index 3)
        if breakout_candle is None and len(candles) >= 4:
            fourth_candle = candles.iloc[3]
            if fourth_candle["close"] > first_body_high:
                # Also verify third candle didn't break first candle low
                if candles.iloc[2]["low"] >= first_candle_low:
                    breakout_candle = fourth_candle
                    breakout_idx = 3

        if breakout_candle is None:
            return None

        # ── Rule 6: Entry candle must not be oversized ──
        entry_body = abs(breakout_candle["close"] - breakout_candle["open"])
        if is_oversized_candle(
            entry_body, avg_range, settings.OVERSIZED_CANDLE_MULTIPLIER
        ):
            return None

        # ── Rule 7: Entry candle must remain close to EMA 9 ──
        ema9_at_entry = ema9.iloc[breakout_idx] if breakout_idx < len(ema9) else 0
        if ema9_at_entry > 0:
            distance_pct = calculate_distance_from_ema_pct(
                breakout_candle["close"], ema9_at_entry
            )
            if abs(distance_pct) > settings.MAX_EMA_DISTANCE_PCT:
                return None
        else:
            distance_pct = 0.0

        # ── Rule 8: Volume must be above average volume ──
        if avg_volume > 0 and breakout_candle["volume"] <= avg_volume:
            return None

        # ── Rule 9: Liquidity must be sufficient ──
        liquidity = breakout_candle["close"] * breakout_candle["volume"]
        min_liquidity = settings.MIN_LIQUIDITY_LAKHS * 100000  # Convert lakhs to absolute
        if liquidity < min_liquidity:
            return None

        # ── Calculate Entry, Stop Loss, Targets ──
        entry_price = breakout_candle["close"]
        stop_loss = breakout_candle["low"]
        risk = entry_price - stop_loss

        if risk <= 0:
            return None

        target1 = entry_price + (risk * settings.ONE_PCT_RR_TARGET1)
        target2 = entry_price + (risk * settings.ONE_PCT_RR_TARGET2)
        rr = calculate_rr_ratio(entry_price, stop_loss, target1)

        # ── Build Signal ──
        signal = Signal(
            symbol=symbol,
            security_id=security_id,
            setup_type=self.setup_type,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            target1=round(target1, 2),
            target2=round(target2, 2),
            risk_reward=rr,
            volume=int(breakout_candle["volume"]),
            candle_index=breakout_idx,
            ema9=round(ema9_at_entry, 2),
            avg_volume=round(avg_volume, 0),
            distance_from_ema=round(distance_pct, 2),
            entry_candle_range=round(
                calculate_candle_range_pct(
                    breakout_candle["open"],
                    breakout_candle["high"],
                    breakout_candle["low"],
                ),
                2,
            ),
            timestamp=pd.Timestamp(breakout_candle["timestamp"]),
            notes=f"Gap-up: {round(((first_candle['open'] - prev_close) / prev_close) * 100, 2)}%, "
            f"1st range: {round(first_range_pct, 2)}%, "
            f"Breakout on candle {breakout_idx + 1}",
        )

        logger.info(
            f"[1% Setup] Signal: {symbol} @ {entry_price}, "
            f"SL: {stop_loss}, T1: {target1}, T2: {target2}, RR: {rr}"
        )
        return signal
