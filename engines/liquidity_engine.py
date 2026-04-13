import numpy as np
import pandas as pd

class LiquidityMaster:
    """
    Project Sniper - Window 3: Signal Refinement (The Eyes)
    Update: IDM Sweep Precision, Zone Mapping, & Candle Trigger.
    """
    def __init__(self, sensitivity=0.0015):
        self.sensitivity = sensitivity 

    def is_valid_pullback(self, data, i, direction="BULLISH"):
        """
        Pullback valid jika candle saat ini menyapu High/Low candle sebelumnya.
        """
        if i < 1: return False
        curr = data.iloc[i]
        prev = data.iloc[i-1]
        
        if direction == "BULLISH":
            return curr['low'] < prev['low']
        else: # BEARISH
            return curr['high'] > prev['high']

    def check_zone_freshness(self, data, zone_high, zone_low, start_idx):
        """
        ZONE MAPPING: Memastikan OB atau FVG belum tersentuh (Unmitigated).
        """
        future_data = data.iloc[start_idx + 1:]
        if future_data.empty: return True
        
        # Cek apakah ada harga yang masuk ke area zona setelah zona terbentuk
        mitigation = future_data[(future_data['low'] <= zone_high) & (future_data['high'] >= zone_low)]
        return len(mitigation) == 0

    def detect_candle_trigger(self, data):
        """
        CANDLE TRIGGER: Filter tajam untuk Doji dan Engulfing.
        Menghindari entry di area kosong (no momentum).
        """
        last = data.iloc[-1]
        prev = data.iloc[-2]
        body_size = abs(last['close'] - last['open'])
        prev_body_size = abs(prev['close'] - prev['open'])
        total_range = last['high'] - last['low']

        # 1. Engulfing Precision (Harus menutup di luar range candle sebelumnya)
        is_bullish_engulfing = last['close'] > prev['high'] and last['close'] > last['open']
        is_bearish_engulfing = last['close'] < prev['low'] and last['close'] < last['open']

        # 2. Doji Filter (Wick panjang di zona, bukan di tengah trend)
        is_doji = body_size <= (total_range * 0.2)
        
        return {
            "is_engulfing": is_bullish_engulfing or is_bearish_engulfing,
            "is_doji": is_doji,
            "trigger_valid": (is_bullish_engulfing or is_bearish_engulfing) and not is_doji
        }

    def detect_idm_and_swings(self, data, trend="BULLISH"):
        """
        IDM SWEEP PRECISION: Mencari level Inducement dan validasi Sweep.
        """
        idm_level = None
        major_swings = {"high": [], "low": []}
        highest_high = -float('inf')
        lowest_low = float('inf')
        
        for i in range(1, len(data)):
            row = data.iloc[i]
            
            if trend == "BULLISH":
                if row['high'] > highest_high:
                    highest_high = row['high']
                    if self.is_valid_pullback(data, i, "BULLISH"):
                        idm_level = data.iloc[i-1]['low']
                
                # Syarat Entry: LOW harus melintasi IDM (Sweep)
                if idm_level and row['low'] < idm_level:
                    major_swings["high"].append(highest_high)
                    idm_level = None 
            
            else: # BEARISH
                if row['low'] < lowest_low:
                    lowest_low = row['low']
                    if self.is_valid_pullback(data, i, "BEARISH"):
                        idm_level = data.iloc[i-1]['high']
                
                if idm_level and row['high'] > idm_level:
                    major_swings["low"].append(lowest_low)
                    idm_level = None

        return idm_level, major_swings

# --- UTILITY FUNCTIONS ---

def detect_sweep(data, level, direction="above"):
    """
    Sweep Valid: Wick menembus level, tapi Close tetap di dalam (Liquidity Grab).
    """
    last = data.iloc[-1]
    if direction == "above":
        # Wick ke atas tapi close di bawah level
        is_swept = last['high'] > level and last['close'] <= level
    else:
        # Wick ke bawah tapi close di atas level
        is_swept = last['low'] < level and last['close'] >= level
        
    return is_swept

def analyze_liquidity(data, trend_bias="BULLISH"):
    master = LiquidityMaster(sensitivity=0.0015)
    current_idm, swings = master.detect_idm_and_swings(data, trend_bias)
    trigger = master.detect_candle_trigger(data)
    
    result = {
        "liquidity_detected": False,
        "action": "WAIT",
        "level": current_idm,
        "trigger_confirmed": trigger['trigger_valid'],
        "confidence": 0
    }

    # LOGIKA FILTER SNIPER (The Eyes)
    # 1. Cek apakah IDM sudah tersapu
    if current_idm is None:
        # 2. Cek apakah ada konfirmasi Candle Trigger (Engulfing)
        if trigger['trigger_valid']:
            result.update({
                "liquidity_detected": True,
                "action": "EXECUTE",
                "type": "IDM_SWEPT_CONFIRMED",
                "confidence": 0.95
            })
        else:
            result.update({
                "liquidity_detected": True,
                "action": "WATCH_CANDLE",
                "type": "IDM_SWEPT_WAIT_TRIGGER",
                "confidence": 0.7
            })
    
    return result
