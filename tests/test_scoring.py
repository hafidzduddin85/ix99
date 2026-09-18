import pytest
from app.scoring import (
    calculate_trend_score,
    classify_trend,
    check_entry_signal,
    score_ema,
    score_adx,
    score_momentum,
    score_volume,
    score_structure,
)


class TestScoreEMA:
    def test_full_bullish(self):
        assert score_ema(1100, 1050, 1000, 900) == 30.0

    def test_full_bearish(self):
        assert score_ema(900, 950, 1000, 1100) == 0.0

    def test_partial(self):
        assert score_ema(1100, 1050, 1000, None) == 20.0

    def test_all_none(self):
        assert score_ema(None, None, None, None) == 15.0


class TestScoreADX:
    def test_strong_bullish(self):
        assert score_adx(30, 25, 15) == 20.0

    def test_strong_bearish(self):
        assert score_adx(30, 15, 25) == 0.0

    def test_weak_trend(self):
        score = score_adx(10, 20, 15)
        assert score >= 0

    def test_none(self):
        assert score_adx(None, None, None) == 10.0


class TestScoreMomentum:
    def test_strong(self):
        assert score_momentum(65) == 15.0

    def test_neutral(self):
        assert score_momentum(50) == 10.0

    def test_weak(self):
        assert score_momentum(35) == 0.0

    def test_oversold(self):
        assert score_momentum(25) == -5.0

    def test_none(self):
        assert score_momentum(None) == 7.5


class TestScoreVolume:
    def test_high(self):
        assert score_volume(2.5) == 15.0

    def test_normal(self):
        assert score_volume(1.0) == 8.0

    def test_low(self):
        assert score_volume(0.3) == 0.0

    def test_none(self):
        assert score_volume(None) == 7.5


class TestScoreStructure:
    def test_full_bullish(self):
        assert score_structure(True, True, False, False) == 20.0

    def test_full_bearish(self):
        assert score_structure(False, False, True, True) == -20.0

    def test_mixed(self):
        score = score_structure(True, False, False, False)
        assert score == 10.0

    def test_all_none(self):
        assert score_structure(None, None, None, None) == 10.0


class TestClassifyTrend:
    def test_strong_uptrend(self):
        assert classify_trend(85)[0] == "STRONG UPTREND"

    def test_uptrend(self):
        assert classify_trend(70)[0] == "UPTREND"

    def test_sideways(self):
        assert classify_trend(55)[0] == "SIDEWAYS"

    def test_downtrend(self):
        assert classify_trend(35)[0] == "DOWNTREND"

    def test_strong_downtrend(self):
        assert classify_trend(10)[0] == "STRONG DOWNTREND"

    def test_boundaries(self):
        assert classify_trend(80)[0] == "STRONG UPTREND"
        assert classify_trend(79)[0] == "UPTREND"
        assert classify_trend(65)[0] == "UPTREND"
        assert classify_trend(64)[0] == "SIDEWAYS"
        assert classify_trend(45)[0] == "SIDEWAYS"
        assert classify_trend(44)[0] == "DOWNTREND"
        assert classify_trend(25)[0] == "DOWNTREND"
        assert classify_trend(24)[0] == "STRONG DOWNTREND"


class TestEntrySignal:
    def test_all_conditions_met(self):
        assert check_entry_signal(
            ema20=1100, ema50=1000, ema200=900,
            adx14=25, plus_di=30, minus_di=15,
            rsi14=55, volume_ratio=1.5,
            higher_high=True, higher_low=True
        ) is True

    def test_ema_not_aligned(self):
        assert check_entry_signal(
            ema20=900, ema50=1000, ema200=1100,
            adx14=25, plus_di=30, minus_di=15,
            rsi14=55, volume_ratio=1.5,
            higher_high=True, higher_low=True
        ) is False

    def test_adx_too_low(self):
        assert check_entry_signal(
            ema20=1100, ema50=1000, ema200=900,
            adx14=15, plus_di=30, minus_di=15,
            rsi14=55, volume_ratio=1.5,
            higher_high=True, higher_low=True
        ) is False

    def test_rsi_too_low(self):
        assert check_entry_signal(
            ema20=1100, ema50=1000, ema200=900,
            adx14=25, plus_di=30, minus_di=15,
            rsi14=45, volume_ratio=1.5,
            higher_high=True, higher_low=True
        ) is False

    def test_none_values(self):
        assert check_entry_signal(
            ema20=None, ema50=1000, ema200=900,
            adx14=25, plus_di=30, minus_di=15,
            rsi14=55, volume_ratio=1.5,
            higher_high=True, higher_low=True
        ) is False
