# vision_library.py

def get_candle_anatomy(open_p, high_p, low_p, close_p):
    """
    Membedah anatomi satu candle secara mendetail.
    Menghindari crash dengan proteksi division by zero.
    """
    # 1. Kalkulasi Dasar
    total_range = high_p - low_p
    body = abs(open_p - close_p)
    
    # Proteksi Range 0 (Candle Tunggal Tanpa Pergerakan)
    if total_range == 0:
        return {
            "range": 0, "body": 0, "upper_shadow": 0, "lower_shadow": 0,
            "body_pct": 0, "upper_pct": 0, "lower_pct": 0, "type": "NONE"
        }

    upper_shadow = high_p - max(open_p, close_p)
    lower_shadow = min(open_p, close_p) - low_p
    
    # 2. Persentase untuk Identifikasi Pola
    body_pct = (body / total_range) * 100
    upper_pct = (upper_shadow / total_range) * 100
    lower_pct = (lower_shadow / total_range) * 100
    
    candle_type = "BULLISH" if close_p > open_p else "BEARISH" if close_p < open_p else "DOJI"

    return {
        "range": total_range,
        "body": body,
        "upper_shadow": upper_shadow,
        "lower_shadow": lower_shadow,
        "body_pct": body_pct,
        "upper_pct": upper_pct,
        "lower_pct": lower_pct,
        "type": candle_type
    }

def identify_single_pattern(anatomy):
    """
    Identifikasi pola single candle berdasarkan data dari get_candle_anatomy.
    """
    res = anatomy
    if res["range"] == 0: return "INACTIVE"

    # Logika Pola
    # Marubozu: Body mendominasi > 90%
    if res["body_pct"] > 90:
        return "MARUBOZU"
    
    # Doji: Body sangat kecil < 10%
    if res["body_pct"] < 10:
        return "DOJI"
    
    # Hammer / Pin Bar (Lower Shadow panjang)
    if res["lower_pct"] > 60 and res["body_pct"] < 35:
        return "HAMMER/PIN_BAR_BULL"
    
    # Shooting Star / Pin Bar (Upper Shadow panjang)
    if res["upper_pct"] > 60 and res["body_pct"] < 35:
        return "SHOOTING_STAR/PIN_BAR_BEAR"

    return "STANDARD"
