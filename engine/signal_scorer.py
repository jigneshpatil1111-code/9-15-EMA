"""
Signal Scoring and Priority System.
Ranks all signals and selects only the Top N highest-quality setups.
"""

import logging
from typing import List

from strategies.base_strategy import Signal
from config.settings import settings

logger = logging.getLogger(__name__)


class SignalScorer:
    """
    Scores trade signals from 0-100 based on weighted quality factors.

    Scoring Factors and Weights:
    - Volume strength (vs avg):      20%
    - EMA structure quality:         15%
    - Pullback quality:              15%
    - Breakout quality:              15%
    - Distance from EMA:             10%
    - Risk:Reward ratio:             15%
    - Momentum quality:              10%
    """

    WEIGHT_VOLUME = 20.0
    WEIGHT_EMA_STRUCTURE = 15.0
    WEIGHT_PULLBACK = 15.0
    WEIGHT_BREAKOUT = 15.0
    WEIGHT_EMA_DISTANCE = 10.0
    WEIGHT_RISK_REWARD = 15.0
    WEIGHT_MOMENTUM = 10.0

    def score(self, signal: Signal) -> float:
        """
        Calculate a composite quality score for a signal.

        Args:
            signal: The trade signal to score.

        Returns:
            Score from 0.0 to 100.0.
        """
        volume_score = self._score_volume(signal)
        ema_score = self._score_ema_structure(signal)
        pullback_score = self._score_pullback(signal)
        breakout_score = self._score_breakout(signal)
        ema_distance_score = self._score_ema_distance(signal)
        rr_score = self._score_risk_reward(signal)
        momentum_score = self._score_momentum(signal)

        # Store individual scores on the signal for transparency
        signal.volume_strength = volume_score
        signal.ema_quality = ema_score
        signal.pullback_quality = pullback_score
        signal.breakout_quality = breakout_score
        signal.momentum_quality = momentum_score

        total = (
            volume_score * (self.WEIGHT_VOLUME / 100.0)
            + ema_score * (self.WEIGHT_EMA_STRUCTURE / 100.0)
            + pullback_score * (self.WEIGHT_PULLBACK / 100.0)
            + breakout_score * (self.WEIGHT_BREAKOUT / 100.0)
            + ema_distance_score * (self.WEIGHT_EMA_DISTANCE / 100.0)
            + rr_score * (self.WEIGHT_RISK_REWARD / 100.0)
            + momentum_score * (self.WEIGHT_MOMENTUM / 100.0)
        )

        signal.signal_score = round(total, 1)

        logger.debug(
            f"Score for {signal.symbol}: {signal.signal_score} "
            f"[Vol:{volume_score:.0f} EMA:{ema_score:.0f} PB:{pullback_score:.0f} "
            f"BO:{breakout_score:.0f} Dist:{ema_distance_score:.0f} "
            f"RR:{rr_score:.0f} Mom:{momentum_score:.0f}]"
        )

        return signal.signal_score

    def rank_signals(self, signals: List[Signal], max_signals: int = 0) -> List[Signal]:
        """
        Score and rank all signals, returning only the top N.

        Args:
            signals: List of signals to rank.
            max_signals: Maximum signals to return (0 = use setting).

        Returns:
            List of top-ranked signals, sorted by score descending.
        """
        if not signals:
            return []

        max_n = max_signals or settings.MAX_SIGNALS_PER_SCAN

        # Score each signal
        for signal in signals:
            self.score(signal)

        # Sort by score descending
        ranked = sorted(signals, key=lambda s: s.signal_score, reverse=True)

        # Take top N
        top_signals = ranked[:max_n]

        logger.info(
            f"Ranked {len(signals)} signals → Top {len(top_signals)}: "
            + ", ".join(
                f"{s.symbol}({s.signal_score})" for s in top_signals
            )
        )

        return top_signals

    def _score_volume(self, signal: Signal) -> float:
        """
        Score volume strength.
        Higher volume relative to average = higher score.
        """
        if signal.avg_volume <= 0:
            return 50.0

        ratio = signal.volume / signal.avg_volume

        if ratio >= 3.0:
            return 100.0
        elif ratio >= 2.5:
            return 90.0
        elif ratio >= 2.0:
            return 80.0
        elif ratio >= 1.5:
            return 70.0
        elif ratio >= 1.2:
            return 60.0
        elif ratio >= 1.0:
            return 50.0
        else:
            return 30.0

    def _score_ema_structure(self, signal: Signal) -> float:
        """
        Score EMA structure quality.
        For EMA pullback: checks EMA 9 > EMA 15 spread.
        For 1% setup: checks proximity to EMA 9.
        """
        if signal.setup_type == "ema_pullback":
            if signal.ema9 <= 0 or signal.ema15 <= 0:
                return 50.0

            spread_pct = ((signal.ema9 - signal.ema15) / signal.ema15) * 100.0

            if spread_pct >= 0.5:
                return 90.0
            elif spread_pct >= 0.3:
                return 80.0
            elif spread_pct >= 0.15:
                return 70.0
            elif spread_pct > 0:
                return 60.0
            else:
                return 30.0
        else:
            # For 1% setup, score based on EMA 9 presence and alignment
            if signal.ema9 > 0 and signal.entry_price > signal.ema9:
                return 80.0
            elif signal.ema9 > 0:
                return 60.0
            return 50.0

    def _score_pullback(self, signal: Signal) -> float:
        """
        Score pullback quality.
        For EMA pullback: tighter pullback = higher score.
        For 1% setup: tighter first candle range = higher score.
        """
        if signal.setup_type == "ema_pullback":
            # Score based on how close the pullback stayed to EMA
            dist = abs(signal.distance_from_ema)
            if dist <= 0.3:
                return 95.0
            elif dist <= 0.5:
                return 85.0
            elif dist <= 0.8:
                return 75.0
            elif dist <= 1.0:
                return 65.0
            elif dist <= 1.5:
                return 55.0
            else:
                return 40.0
        else:
            # 1% setup: score based on first candle range
            if signal.entry_candle_range <= 0.3:
                return 95.0
            elif signal.entry_candle_range <= 0.5:
                return 85.0
            elif signal.entry_candle_range <= 0.7:
                return 75.0
            elif signal.entry_candle_range <= 1.0:
                return 60.0
            else:
                return 40.0

    def _score_breakout(self, signal: Signal) -> float:
        """
        Score breakout quality.
        Clean breakout with good volume and close near high = higher score.
        """
        # Score based on entry candle characteristics
        score = 60.0

        # Volume expansion bonus
        if signal.avg_volume > 0:
            vol_ratio = signal.volume / signal.avg_volume
            if vol_ratio >= 2.0:
                score += 20.0
            elif vol_ratio >= 1.5:
                score += 15.0
            elif vol_ratio >= 1.2:
                score += 10.0

        # Tight entry candle bonus
        if signal.entry_candle_range <= 0.5:
            score += 10.0
        elif signal.entry_candle_range <= 0.8:
            score += 5.0

        # Early breakout bonus (candle index)
        if signal.candle_index <= 3:
            score += 10.0
        elif signal.candle_index <= 5:
            score += 5.0

        return min(score, 100.0)

    def _score_ema_distance(self, signal: Signal) -> float:
        """
        Score distance from EMA 9.
        Closer to EMA = better entry = higher score.
        """
        dist = abs(signal.distance_from_ema)

        if dist <= 0.2:
            return 100.0
        elif dist <= 0.4:
            return 90.0
        elif dist <= 0.6:
            return 80.0
        elif dist <= 0.8:
            return 70.0
        elif dist <= 1.0:
            return 60.0
        elif dist <= 1.5:
            return 50.0
        else:
            return 30.0

    def _score_risk_reward(self, signal: Signal) -> float:
        """
        Score risk-reward ratio.
        Higher RR = higher score.
        """
        rr = signal.risk_reward

        if rr >= 4.0:
            return 100.0
        elif rr >= 3.5:
            return 90.0
        elif rr >= 3.0:
            return 80.0
        elif rr >= 2.5:
            return 70.0
        elif rr >= 2.0:
            return 60.0
        elif rr >= 1.5:
            return 40.0
        else:
            return 20.0

    def _score_momentum(self, signal: Signal) -> float:
        """
        Score momentum quality.
        Fresh momentum (early in the move) scores higher.
        """
        # Earlier candle index = fresher momentum
        idx = signal.candle_index

        if idx <= 3:
            return 90.0
        elif idx <= 5:
            return 80.0
        elif idx <= 8:
            return 70.0
        elif idx <= 12:
            return 60.0
        elif idx <= 20:
            return 50.0
        else:
            return 35.0
