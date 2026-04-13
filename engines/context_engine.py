import pandas as pd

def detect_htf_trend(data):
    """Deteksi tren berdasarkan High/Low 5 candle terakhir."""
    highs = data['high'].tail(5).values
    lows = data['low'].tail(5).values

    up = 0
    down = 0

    for i in range(1, len(highs)):
        if highs[i] > highs[i-1] and lows[i] > lows[i-1]:
            up += 1
        elif highs[i] < highs[i-1] and lows[i] < lows[i-1]:
            down += 1

    if up >= 2:
        return "BULLISH"
    if down >= 2:
        return "BEARISH"

    return None

def calculate_ma_context(data, period=200):
    """
    Menghitung posisi harga terhadap Exponential Moving Average.
    Berfungsi sebagai 'Filter Arus Besar'.
    """
    if len(data) < period:
        return "NEUTRAL"
    
    # Hitung EMA 200
    ema = data['close'].ewm(span=period, adjust=False).mean()
    current_ema = ema.iloc[-1]
    current_price = data['close'].iloc[-1]

    if current_price > current_ema:
        return "ABOVE_MA"
    elif current_price < current_ema:
        return "BELOW_MA"
    
    return "NEUTRAL"

def calculate_pd_zone(data):
    high = data['high'].max()
    low = data['low'].min()
    current = data.iloc[-1]['close']

    if high == low:
        return "MIDDLE"

    mid = (high + low) / 2

    # zone middle buffer
    if abs(current - mid) / mid < 0.05:
        return "MIDDLE"

    if current < mid:
        return "DISCOUNT"

    return "PREMIUM"

def detect_liquidity_target(data):
    highs = data['high']
    lows = data['low']

    recent_high = highs.tail(10).max()
    recent_low = lows.tail(10).min()
    current = data.iloc[-1]['close']

    if current < recent_high:
        return "BUY_SIDE"
    if current > recent_low:
        return "SELL_SIDE"

    return None

def build_context(htf_data, ltf_data):
    """
    Membangun narasi market dengan menggabungkan Struktur HTF, 
    Zona LTF, dan Filter Moving Average.
    """
    # 1. Deteksi Tren Dasar (Struktur High/Low)
    htf_trend = detect_htf_trend(htf_data)
    if htf_trend is None:
        return {"valid": False}

    # 2. Deteksi Lokasi (Premium/Discount)
    pd_zone = calculate_pd_zone(ltf_data)

    # 3. Deteksi Target Likuiditas
    liquidity_target = detect_liquidity_target(ltf_data)
    if liquidity_target is None:
        liquidity_target = "UNKNOWN"

    # 4. Deteksi Posisi terhadap MA 200 (Filter Arus)
    ma_position = calculate_ma_context(htf_data, period=200)

    # =========================
    # SCORING SYSTEM (The Brain)
    # =========================
    score = 0

    # A. Skor Struktur HTF (Dasar: 10)
    score += 10

    # B. Skor PD Zone (Valid: 5)
    score += 5

    # C. Skor Likuiditas (Valid: 10)
    score += 10

    # D. BONUS/PENALTI MOVING AVERAGE (Filter Pintar)
    # Jika Trend BULLISH dan harga di atas MA200 -> Sangat Bagus (+15)
    if htf_trend == "BULLISH" and ma_position == "ABOVE_MA":
        score += 15
    # Jika Trend BEARISH dan harga di bawah MA200 -> Sangat Bagus (+15)
    elif htf_trend == "BEARISH" and ma_position == "BELOW_MA":
        score += 15
    # Jika Trend berlawanan dengan MA -> Penalti (-10) agar bot lebih selektif
    elif ma_position != "NEUTRAL":
        score -= 10

    # Handle Middle Zone (Hati-hati di area abu-abu)
    if pd_zone == "MIDDLE":
        return {
            "valid": True,
            "htf_trend": htf_trend,
            "pd_zone": pd_zone,
            "liquidity_target": liquidity_target,
            "ma_position": ma_position,
            "context_score": score - 5 # Kurangi sedikit skor jika di tengah
        }

    return {
        "valid": True,
        "htf_trend": htf_trend,
        "pd_zone": pd_zone,
        "liquidity_target": liquidity_target,
        "ma_position": ma_position,
        "context_score": score
    }
