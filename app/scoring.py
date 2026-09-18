from dataclasses import dataclass


@dataclass
class ScoreComponents:
    ema_signal: float
    adx_signal: float
    momentum_signal: float
    volume_signal: float
    structure_signal: float

    @property
    def total(self) -> float:
        return (
            self.ema_signal
            + self.adx_signal
            + self.momentum_signal
            + self.volume_signal
            + self.structure_signal
        )


def score_ema(close, ema20, ema50, ema200) -> float:
    """Max 30 points."""
    if any(v is None for v in [close, ema20, ema50, ema200]):
        # fallback jika ema200 belum tersedia
        if any(v is None for v in [close, ema20, ema50]):
            return 15.0
        score = 0.0
        if close > ema20:
            score += 10
        if ema20 > ema50:
            score += 10
        return score

    score = 0.0
    if close > ema20:
        score += 10
    if ema20 > ema50:
        score += 10
    if ema50 > ema200:
        score += 10
    return score


def score_adx(adx14, plus_di, minus_di) -> float:
    """Max 20 points."""
    if any(v is None for v in [adx14, plus_di, minus_di]):
        return 10.0

    score = 0.0
    if adx14 >= 25:
        score += 10
    elif adx14 >= 20:
        score += 7
    elif adx14 >= 15:
        score += 4

    if plus_di > minus_di:
        score += 10
    elif plus_di < minus_di:
        score -= 10

    return max(-20.0, min(20.0, score))


def score_momentum(rsi14) -> float:
    """Max 15 points."""
    if rsi14 is None:
        return 7.5

    if rsi14 >= 60:
        return 15.0
    elif rsi14 >= 50:
        return 10.0
    elif rsi14 >= 40:
        return 5.0
    elif rsi14 >= 30:
        return 0.0
    else:
        return -5.0


def score_volume(volume_ratio) -> float:
    """Max 15 points."""
    if volume_ratio is None:
        return 7.5

    if volume_ratio >= 2.0:
        return 15.0
    elif volume_ratio >= 1.5:
        return 12.0
    elif volume_ratio >= 1.0:
        return 8.0
    elif volume_ratio >= 0.5:
        return 4.0
    else:
        return 0.0


def score_structure(higher_high, higher_low, lower_high, lower_low) -> float:
    """Max 20 points."""
    if all(v is None for v in [higher_high, higher_low, lower_high, lower_low]):
        return 10.0

    score = 0.0
    if higher_high:
        score += 10
    if higher_low:
        score += 10
    if lower_high:
        score -= 10
    if lower_low:
        score -= 10

    return max(-20.0, min(20.0, score))


def calculate_trend_score(
    close, ema20, ema50, ema200,
    adx14, plus_di, minus_di,
    rsi14, volume_ratio,
    higher_high, higher_low, lower_high, lower_low
) -> ScoreComponents:
    ema = score_ema(close, ema20, ema50, ema200)
    adx = score_adx(adx14, plus_di, minus_di)
    momentum = score_momentum(rsi14)
    volume = score_volume(volume_ratio)
    structure = score_structure(higher_high, higher_low, lower_high, lower_low)

    return ScoreComponents(
        ema_signal=ema,
        adx_signal=adx,
        momentum_signal=momentum,
        volume_signal=volume,
        structure_signal=structure,
    )


def classify_trend(score: float) -> tuple[str, str]:
    """Returns (trend_direction, trend_strength)."""
    if score >= 80:
        return "STRONG UPTREND", "STRONG"
    elif score >= 65:
        return "UPTREND", "MODERATE"
    elif score >= 45:
        return "SIDEWAYS", "WEAK"
    elif score >= 25:
        return "DOWNTREND", "MODERATE"
    else:
        return "STRONG DOWNTREND", "STRONG"


def check_entry_signal(
    ema20, ema50, ema200,
    adx14, plus_di, minus_di,
    rsi14, volume_ratio,
    higher_high, higher_low
) -> bool:
    if any(v is None for v in [ema20, ema50, ema200, adx14, plus_di, minus_di, rsi14, volume_ratio]):
        return False
    return (
        ema20 > ema50
        and ema50 > ema200
        and adx14 >= 20
        and plus_di > minus_di
        and rsi14 >= 50
        and volume_ratio >= 1.0
        and higher_high is True
        and higher_low is True
    )
