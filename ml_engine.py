import numpy as np

# ── Z-score anomaly detection ──────────────────────────────────────────────────
# Flags a data point as anomalous if it's > threshold standard deviations
# from the rolling mean of recent prices.

ZSCORE_THRESHOLD = 2.0   # flag if |z| > 2.0

def compute_zscore(prices: list[float]) -> float:
    """Returns the z-score of the latest price vs the recent window."""
    if len(prices) < 5:
        return 0.0
    arr = np.array(prices, dtype=float)
    mean = np.mean(arr[:-1])   # mean of all but latest
    std  = np.std(arr[:-1])
    if std < 1e-6:
        return 0.0
    return float((arr[-1] - mean) / std)

def is_anomaly(zscore: float) -> bool:
    return abs(zscore) > ZSCORE_THRESHOLD

# ── EMA trend + buy/sell signal ───────────────────────────────────────────────
# Uses two Exponential Moving Averages:
#   fast EMA (span=5)  — reacts quickly to recent moves
#   slow EMA (span=20) — smoother baseline
# Signal: fast > slow → BUY, fast < slow → SELL, else HOLD

def ema(prices: list[float], span: int) -> float:
    """Returns the last EMA value."""
    if not prices:
        return 0.0
    arr = np.array(prices, dtype=float)
    k = 2.0 / (span + 1)
    e = arr[0]
    for p in arr[1:]:
        e = p * k + e * (1 - k)
    return float(e)

def compute_signal(prices: list[float], pcts: list[float]) -> tuple[str, str, float]:
    """
    Returns (signal, reason, zscore).
    signal: 'BUY' | 'SELL' | 'HOLD'
    """
    zscore = compute_zscore(prices)
    anomaly = is_anomaly(zscore)

    if len(prices) < 6:
        return "HOLD", "Insufficient data", zscore

    fast = ema(prices, span=5)
    slow = ema(prices, span=20)
    latest_pct = pcts[0] if pcts else 0.0   # most recent % from open

    if fast > slow and latest_pct > 0.3:
        signal = "BUY"
        reason = f"EMA crossover ↑  (fast={fast:.1f} > slow={slow:.1f})"
    elif fast < slow and latest_pct < -0.3:
        signal = "SELL"
        reason = f"EMA crossover ↓  (fast={fast:.1f} < slow={slow:.1f})"
    else:
        signal = "HOLD"
        reason = f"No clear trend  (fast={fast:.1f}, slow={slow:.1f})"

    if anomaly:
        direction = "spike" if zscore > 0 else "drop"
        reason += f"  |  ⚠ Z={zscore:.2f} price {direction}"

    return signal, reason, zscore