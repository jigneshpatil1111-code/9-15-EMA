"""
Strategy 2: 9 EMA / 15 EMA Pullback Setup
==========================================
Timeframe: 5 Minute

Trend Conditions (ALL must be true):
- EMA 9 > EMA 15
- EMA 9 rising
- EMA 15 rising
- Strong upward slope
- Price above EMA 15

Momentum Conditions:
- Strong impulsive bullish move
- Healthy pullback
- Pullback remains above EMA 15
- Pullback high identified
- Breakout candle closes above pullback high
- Volume expansion present
- Entry candle should not be oversized
- Entry should not be too far from EMA 9

Entry: Close of breakout candle.
Stop Loss: Low of entry candle.
Target: 1:2.5 to 1:3 Risk Reward.
"""

import logging
from typing import Optional

import pandas as pd

from strategies.base_strategy import BaseStrategy, Signal
from indicators.technical import (
    calculate_ema,
    calculate_ema_slope,
    is_ema_rising,
    calculate_average_volume,
    calculate_average_candle_range,
    calculate_rr_ratio,
    calculate_distance_from_ema_pct,
    is_oversized_candle,
    detect_impulse_move,
    detect_pullback,
)
from config.settings import settings

logger = logging.getLogger(__name__)


class EMAPullbackSetup(BaseStrategy):
    """
    9 EMA / 15 EMA Pullback Strategy.
    Detects pullback entries in a strong EMA uptrend with volume expansion.
    """

    @property
    def name(self) -> str:
        return "9/15 EMA Pullback"

    @property
    def setup_type(self) -> str:
        return "ema_pullback"

    def scan(
        self,
        symbol: str,
        security_id: str,
        candles: pd.DataFrame,
        prev_close: float,
    ) -> Optional[Signal]:
        """
        Scan for 9/15 EMA Pullback Setup on 5-minute intraday candles.

        Requires sufficient candle history to compute EMA 15 and
        detect impulse-pullback-breakout pattern.
        """
        if not self._validate_candles(candles):
            return None

        # Need enough candles for EMA computation
        if len(candles) < settings.EMA_SLOW_PERIOD + 5:
            return None

        # ── Compute EMAs ──
        ema9 = calculate_ema(candles["close"], settings.EMA_FAST_PERIOD)
        ema15 = calculate_ema(candles["close"], settings.EMA_SLOW_PERIOD)

        # ── Trend Condition 1: EMA 9 > EMA 15 ──
        latest_ema9 = ema9.iloc[-1]
        latest_ema15 = ema15.iloc[-1]
        if latest_ema9 <= latest_ema15:
            return None

        # ── Trend Condition 2: EMA 9 rising ──
        if not is_ema_rising(ema9, lookback=3):
            return None

        # ── Trend Condition 3: EMA 15 rising ──
        if not is_ema_rising(ema15, lookback=3):
            return None

        # ── Trend Condition 4: Strong upward slope ──
        ema9_slope = calculate_ema_slope(ema9, lookback=3)
        latest_slope = ema9_slope.iloc[-1] if len(ema9_slope) > 0 else 0
        # Slope must be meaningfully positive (at least 0.05% of price per bar)
        min_slope = candles["close"].iloc[-1] * 0.0005
        if latest_slope < min_slope:
            return None

        # ── Trend Condition 5: Price above EMA 15 ──
        latest_close = candles.iloc[-1]["close"]
        if latest_close <= latest_ema15:
            return None

        # ── Momentum Condition 1: Strong impulsive bullish move ──
        # Look for impulse move in the candles before the current position
        # We check a window before the most recent candles
        lookback_window = min(len(candles) - 3, 15)
        impulse_data = candles.iloc[: len(candles) - 3] if len(candles) > 6 else candles
        if not detect_impulse_move(impulse_data, min_candles=3):
            return None

        # ── Momentum Condition 2-4: Healthy pullback above EMA 15 ──
        pullback = detect_pullback(candles, ema9, ema15)
        if pullback is None:
            return None

        pullback_high = pullback["pullback_high"]
        pullback_end = pullback["pullback_end_idx"]

        # ── Momentum Condition 5: Breakout candle closes above pullback high ──
        # Check the most recent candle (or the one after pullback end)
        breakout_candle = None
        breakout_idx = None

        for i in range(pullback_end + 1, len(candles)):
            candle = candles.iloc[i]
            if candle["close"] > pullback_high:
                breakout_candle = candle
                breakout_idx = i
                break

        if breakout_candle is None:
            return None

        # ── Momentum Condition 6: Volume expansion ──
        avg_volume = calculate_average_volume(
            candles["volume"], settings.VOLUME_AVG_PERIOD
        )
        if avg_volume > 0 and breakout_candle["volume"] <= avg_volume:
            return None

        # ── Momentum Condition 7: Entry candle not oversized ──
        avg_range = calculate_average_candle_range(candles, settings.VOLUME_AVG_PERIOD)
        entry_body = abs(breakout_candle["close"] - breakout_candle["open"])
        if is_oversized_candle(
            entry_body, avg_range, settings.OVERSIZED_CANDLE_MULTIPLIER
        ):
            return None

        # ── Momentum Condition 8: Entry not too far from EMA 9 ──
        ema9_at_entry = ema9.iloc[breakout_idx] if breakout_idx < len(ema9) else 0
        if ema9_at_entry > 0:
            distance_pct = calculate_distance_from_ema_pct(
                breakout_candle["close"], ema9_at_entry
            )
            if abs(distance_pct) > settings.MAX_EMA_DISTANCE_PCT:
                return None
        else:
            distance_pct = 0.0

        # ── Liquidity Check ──
        liquidity = breakout_candle["close"] * breakout_candle["volume"]
        min_liquidity = settings.MIN_LIQUIDITY_LAKHS * 100000
        if liquidity < min_liquidity:
            return None

        # ── Calculate Entry, Stop Loss, Target ──
        entry_price = breakout_candle["close"]
        stop_loss = breakout_candle["low"]
        risk = entry_price - stop_loss

        if risk <= 0:
            return None

        # Target: 1:2.75 RR (average of 2.5 and 3.0)
        target1 = entry_price + (risk * settings.EMA_PULLBACK_RR_TARGET)
        target2 = entry_price + (risk * settings.EMA_PULLBACK_RR_MAX)
        rr = calculate_rr_ratio(entry_price, stop_loss, target1)

        if rr < settings.MIN_RR_EMA_PULLBACK:
            return None

        # ── Build Signal ──
        ema15_at_entry = ema15.iloc[breakout_idx] if breakout_idx < len(ema15) else 0

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
            ema15=round(ema15_at_entry, 2),
            avg_volume=round(avg_volume, 0),
            distance_from_ema=round(distance_pct, 2),
            entry_candle_range=round(
                ((breakout_candle["high"] - breakout_candle["low"]) / breakout_candle["open"]) * 100,
                2,
            ),
            timestamp=pd.Timestamp(breakout_candle["timestamp"]),
            notes=f"EMA9: {round(ema9_at_entry, 2)}, "
            f"EMA15: {round(ema15_at_entry, 2)}, "
            f"Pullback high: {round(pullback_high, 2)}, "
            f"Slope: {round(latest_slope, 4)}",
        )

        logger.info(
            f"[EMA Pullback] Signal: {symbol} @ {entry_price}, "
            f"SL: {stop_loss}, T1: {target1}, T2: {target2}, RR: {rr}"
        )
        return signal
