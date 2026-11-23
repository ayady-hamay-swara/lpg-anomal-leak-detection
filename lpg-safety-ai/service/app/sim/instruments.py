import random

def analog_ma(value: float, low: float, high: float) -> float:
    ma = 4.0 + 16.0 * (value - low) / (high - low)
    return max(0.0, min(22.0, ma))

def loop_quality(ma: float) -> str:
    if ma < 3.6 or ma > 21.0:
        return "bad"
    if ma < 3.8 or ma > 20.5:
        return "suspect"
    return "good"

def noisy(value: float, sigma: float, rng: random.Random) -> float:
    return value + rng.gauss(0.0, sigma)
