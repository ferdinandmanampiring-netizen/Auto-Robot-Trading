import pandas as pd
import numpy as np

class ZoneEngine:
    """
    Mesin utama Sniper Powerful Ferdy untuk mendeteksi area Supply & Demand.
    Fokus: Unmitigated FVG dan Order Blocks dengan Displacement.
    """
    def __init__(self, fvg_min_size=0.5):
        # fvg_min_size bisa disesuaikan untuk BTCUSDc agar tidak mendeteksi gap terlalu kecil
        self.fvg_min_size = fvg_min_size 

    def detect_fvg(self, data):
        """
        Mencari Fair Value Gap yang belum tertutup (Unmitigated).
        """
        fvg_zones = []
        length = len(data)

        for i in range(2, length):
            prev = data.iloc[i-2]
            curr = data.iloc[i]
            
            # 1. Bullish FVG (Gap antara High candle 1 dan Low candle 3)
            if prev['high'] < curr['low']:
                zone_high = curr['low']
                zone_low = prev['high']
                
                # Cek apakah zona ini sudah dimitigasi (disentuh) oleh candle-candle setelahnya
                is_mitigated = False
                if i + 1 < length:
                    # Jika ada Low candle setelahnya yang masuk ke zona, maka Mitigated
                    subsequent_lows = data['low'].iloc[i+1:]
                    if any(subsequent_lows < zone_high):
                        is_mitigated = True
                
                if not is_mitigated:
                    fvg_zones.append({
                        "type": "FVG_BULLISH",
                        "low": zone_low,
                        "high": zone_high,
                        "index": i,
                        "fresh": True
                    })

            # 2. Bearish FVG (Gap antara Low candle 1 dan High candle 3)
            elif prev['low'] > curr['high']:
                zone_high = prev['low']
                zone_low = curr['high']
                
                is_mitigated = False
                if i + 1 < length:
                    subsequent_highs = data['high'].iloc[i+1:]
                    if any(subsequent_highs > zone_low):
                        is_mitigated = True
                
                if not is_mitigated:
                    fvg_zones.append({
                        "type": "FVG_BEARISH",
                        "low": zone_low,
                        "high": zone_high,
                        "index": i,
                        "fresh": True
                    })
        return fvg_zones

    def detect_order_block(self, data, lookback=20):
        """
        Mencari Order Block (OB) yang menyebabkan Displacement/Breakout.
        """
        ob_zones = []
        length = len(data)
        
        # Cari dari candle terbaru ke belakang
        for i in range(length - 3, length - lookback, -1):
            if i < 1: break
            
            candle = data.iloc[i]
            # Candle setelah OB harus menunjukkan ledakan harga (Displacement)
            next_candles = data.iloc[i+1 : i+4] 
            
            # Bullish OB: Candle Bearish terakhir sebelum kenaikan kuat
            if candle['close'] < candle['open']:
                # Konfirmasi Displacement: Harga nembus High OB dengan cepat
                if next_candles['high'].max() > candle['high']:
                    # Cek Mitigation
                    is_mitigated = any(data['low'].iloc[i+3:] < candle['low']) if i+3 < length else False
                    if not is_mitigated:
                        ob_zones.append({
                            "type": "OB_BULLISH",
                            "low": candle['low'],
                            "high": candle['high'],
                            "index": i
                        })

            # Bearish OB: Candle Bullish terakhir sebelum penurunan kuat
            elif candle['close'] > candle['open']:
                if next_candles['low'].min() < candle['low']:
                    is_mitigated = any(data['high'].iloc[i+3:] > candle['high']) if i+3 < length else False
                    if not is_mitigated:
                        ob_zones.append({
                            "type": "OB_BEARISH",
                            "low": candle['low'],
                            "high": candle['high'],
                            "index": i
                        })
        return ob_zones

def analyze_zone(data):
    """
    Fungsi Integrasi: Memilih zona terbaik (Confluence) untuk dikirim ke Risk Engine.
    """
    engine = ZoneEngine()
    
    fvg = engine.detect_fvg(data)
    ob = engine.detect_order_block(data)
    
    result = {
        "valid": False,
        "type": None,
        "entry_low": None,
        "entry_high": None,
        "source": None,
        "confidence": 0
    }

    # PRIORITAS 1: OB + FVG Confluence (Area paling kuat)
    # Jika ada FVG yang letaknya berdekatan atau di dalam OB
    if ob and fvg:
        last_ob = ob[0]
        last_fvg = fvg[-1]
        
        # Jika tipe searah (Sama-sama Bullish atau Bearish)
        if last_ob['type'].split('_')[1] == last_fvg['type'].split('_')[1]:
            result.update({
                "valid": True,
                "type": last_ob['type'],
                "entry_low": last_ob['low'],
                "entry_high": last_ob['high'],
                "source": "OB_WITH_FVG",
                "confidence": 0.95
            })
            return result

    # PRIORITAS 2: Unmitigated FVG saja
    if fvg:
        last_fvg = fvg[-1]
        result.update({
            "valid": True,
            "type": last_fvg["type"],
            "entry_low": last_fvg["low"],
            "entry_high": last_fvg["high"],
            "source": "FVG_ONLY",
            "confidence": 0.85
        })
        return result

    # PRIORITAS 3: Order Block saja
    if ob:
        last_ob = ob[0]
        result.update({
            "valid": True,
            "type": last_ob["type"],
            "entry_low": last_ob["low"],
            "entry_high": last_ob["high"],
            "source": "OB_ONLY",
            "confidence": 0.75
        })
        return result

    return result
