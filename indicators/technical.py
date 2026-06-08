"""
Technical indicator calculations.
All functions are pure — they operate on pandas Series / DataFrames
and return computed values without side effects.
"""

import numpy as np
import pandas as pd
from typing import Optional


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Args:
        series: Price series (typically close prices).
        period: EMA lookback period.

    Returns:
        EMA series aligned with input.
    """
    return series.ewm(span=period, adjust=False).mean()


def calculate_ema_slope(ema_series: pd.Series, lookback: int = 3) -> pd.Series:
    """
    Calculate the slope of an EMA over a lookback window.
    Positive slope = rising, negative = falling.

    Args:
        ema_series: EMA values.
        lookback: Number of bars to compute slope over.

    Returns:
        Series of slope values.
    """
    return ema_series.diff(lookback) / lookback


def is_ema_rising(ema_series: pd.Series, lookback: int = 3) -> bool:
    """
    Check if the EMA is consistently rising over the lookback window.

    Args:
        ema_series: EMA values.
        lookback: Number of bars to check.

    Returns:
        True if all recent changes are positive.
    """
    if len(ema_series) < lookback + 1:
        return False
    recent = ema_series.iloc[-lookback:]
    diffs = recent.diff().iloc[1:]
    return bool((diffs > 0).all())


def calculate_average_volume(volume_series: pd.Series, period: int = 20) -> float:
    """
    Calculate the average volume over a lookback period.

    Args:
        volume_series: Volume data.
        period: Averaging window.

    Returns:
        Average volume as float.
    """
    if len(volume_series) < period:
        return float(volume_series.mean()) if len(volume_series) > 0 else 0.0
    return float(volume_series.iloc[-period:].mean())


def calculate_candle_range_pct(
    open_price: float, high: float, low: float
) -> float:
    """
    Calculate the total range of a candle as a percentage of the open price.

    Args:
        open_price: Candle open.
        high: Candle high.
        low: Candle low.

    Returns:
        Range percentage.
    """
    if open_price <= 0:
        return 0.0
    return ((high - low) / open_price) * 100.0


def calculate_candle_body_high(open_price: float, close_price: float) -> float:
    """
    Get the body high of a candle (max of open, close).

    Args:
        open_price: Candle open.
        close_price: Candle close.

    Returns:
        Body high.
    """
    return max(open_price, close_price)


def calculate_candle_body_low(open_price: float, close_price: float) -> float:
    """
    Get the body low of a candle (min of open, close).

    Args:
        open_price: Candle open.
        close_price: Candle close.

    Returns:
        Body low.
    """
    return min(open_price, close_price)


def is_gap_up(current_open: float, prev_close: float) -> bool:
    """
    Check if the stock opened with a gap up.

    Args:
        current_open: Today's open price.
        prev_close: Previous day's close price.

    Returns:
        True if gap up.
    """
    return current_open > prev_close


def is_oversized_candle(
    candle_body: float,
    avg_range: float,
    multiplier: float = 2.0,
) -> bool:
    """
    Check if a candle is oversized compared to the average range.

    Args:
        candle_body: Absolute body size (abs(close - open)).
        avg_range: Average candle range.
        multiplier: Threshold multiplier.

    Returns:
        True if candle is oversized.
    """
    if avg_range <= 0:
        return False
    return candle_body > (multiplier * avg_range)


def calculate_rr_ratio(entry: float, stop_loss: float, target: float) -> float:
    """
    Calculate risk-reward ratio.

    Args:
        entry: Entry price.
        stop_loss: Stop loss price.
        target: Target price.

    Returns:
        Risk-reward ratio. Returns 0.0 if risk is zero.
    """
    risk = abs(entry - stop_loss)
    if risk <= 0:
        return 0.0
    reward = abs(target - entry)
    return round(reward / risk, 2)


def calculate_average_candle_range(df: pd.DataFrame, period: int = 20) -> float:
    """
    Calculate average absolute candle range (high - low) over a lookback period.

    Args:
        df: DataFrame with 'high' and 'low' columns.
        period: Lookback period.

    Returns:
        Average range as float.
    """
    if len(df) < 1:
        return 0.0
    ranges = (df["high"] - df["low"]).abs()
    if len(ranges) < period:
        return float(ranges.mean())
    return float(ranges.iloc[-period:].mean())


def calculate_average_body_size(df: pd.DataFrame, period: int = 20) -> float:
    """
    Calculate average absolute candle body size over a lookback period.

    Args:
        df: DataFrame with 'open' and 'close' columns.
        period: Lookback period.

    Returns:
        Average body size as float.
    """
    if len(df) < 1:
        return 0.0
    bodies = (df["close"] - df["open"]).abs()
    if len(bodies) < period:
        return float(bodies.mean())
    return float(bodies.iloc[-period:].mean())


def count_consecutive_green(df: pd.DataFrame) -> int:
    """
    Count consecutive green (close > open) candles from the most recent candle.

    Args:
        df: DataFrame with 'open' and 'close' columns.

    Returns:
        Number of consecutive green candles.
    """
    if len(df) < 1:
        return 0

    count = 0
    for i in range(len(df) - 1, -1, -1):
        if df.iloc[i]["close"] > df.iloc[i]["open"]:
            count += 1
        else:
            break
    return count


def has_abnormal_candle(df: pd.DataFrame, multiplier: float = 3.0, lookback: int = 20) -> bool:
    """
    Check if any candle in the lookback period has an abnormally large range.

    Args:
        df: DataFrame with 'high' and 'low' columns.
        multiplier: Abnormality threshold multiplier vs average range.
        lookback: Number of bars to check.

    Returns:
        True if an abnormal candle is found.
    """
    if len(df) < 2:
        return False
    avg_range = calculate_average_candle_range(df, lookback)
    if avg_range <= 0:
        return False
    recent = df.iloc[-lookback:] if len(df) >= lookback else df
    ranges = (recent["high"] - recent["low"]).abs()
    return bool((ranges > multiplier * avg_range).any())


def detect_impulse_move(df: pd.DataFrame, min_candles: int = 3) -> bool:
    """
    Detect a strong impulsive bullish move.
    Defined as at least min_candles consecutive green candles
    with expanding or strong bodies.

    Args:
        df: DataFrame with OHLC data.
        min_candles: Minimum consecutive green candles for impulse.

    Returns:
        True if impulsive move detected.
    """
    if len(df) < min_candles:
        return False

    green_count = 0
    for i in range(len(df) - 1, -1, -1):
        row = df.iloc[i]
        if row["close"] > row["open"]:
            green_count += 1
            if green_count >= min_candles:
                return True
        else:
            # Allow one red candle in the sequence if it's small
            body = abs(row["close"] - row["open"])
            avg_body = calculate_average_body_size(df.iloc[:i], 10)
            if body < avg_body * 0.5 and green_count > 0:
                continue
            break

    return green_count >= min_candles


def detect_pullback(
    df: pd.DataFrame,
    ema_fast: pd.Series,
    ema_slow: pd.Series,
) -> Optional[dict]:
    """
    Detect a healthy pullback after an impulsive move.
    A pullback is when price retraces toward the EMA zone but stays above EMA slow.

    Args:
        df: DataFrame with OHLC data.
        ema_fast: Fast EMA series (e.g., EMA 9).
        ema_slow: Slow EMA series (e.g., EMA 15).

    Returns:
        Dict with 'pullback_low', 'pullback_high', 'pullback_start_idx',
        'pullback_end_idx' if a valid pullback is found. None otherwise.
    """
    if len(df) < 5:
        return None

    pullback_start = None
    pullback_end = None
    pullback_high = 0.0
    pullback_low = float("inf")

    # Walk backward to find the pullback
    in_pullback = False
    for i in range(len(df) - 1, max(len(df) - 20, -1), -1):
        row = df.iloc[i]
        ema_s = ema_slow.iloc[i] if i < len(ema_slow) else 0

        if not in_pullback:
            # Look for the start of pullback (price coming down / consolidating)
            if row["close"] < row["open"] or row["low"] <= ema_fast.iloc[i]:
                in_pullback = True
                pullback_end = i
                pullback_high = row["high"]
                pullback_low = row["low"]
        else:
            # Track pullback boundaries
            pullback_high = max(pullback_high, row["high"])
            pullback_low = min(pullback_low, row["low"])

            # Check if pullback broke below EMA slow — invalid
            if row["low"] < ema_s * 0.998:  # Small tolerance
                return None

            # Check if we hit the impulse move (green candle before pullback)
            if row["close"] > row["open"] and i < pullback_end - 1:
                pullback_start = i + 1
                break

    if pullback_start is not None and pullback_end is not None:
        return {
            "pullback_low": pullback_low,
            "pullback_high": pullback_high,
            "pullback_start_idx": pullback_start,
            "pullback_end_idx": pullback_end,
        }

    return None


def calculate_distance_from_ema_pct(price: float, ema_value: float) -> float:
    """
    Calculate percentage distance of price from EMA.

    Args:
        price: Current price.
        ema_value: Current EMA value.

    Returns:
        Percentage distance (positive = above EMA).
    """
    if ema_value <= 0:
        return 0.0
    return ((price - ema_value) / ema_value) * 100.0
