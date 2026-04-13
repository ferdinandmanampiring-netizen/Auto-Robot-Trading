import pandas as pd
import numpy as np

class MarketStructure:
    def __init__(self, window=3):
        self.window = window
        self.pending_reversal = None 

    def _detect_fractals(self, df):
        """Mendeteksi Swing High & Swing Low berdasarkan Fractal Logic."""
        df['is_sh'] = df['high'] == df['high'].rolling(window=2*self.window+1, center=True).max()
        df['is_sl'] = df['low'] == df['low'].rolling(window=2*self.window+1, center=True).min()
        return df

    def process_structure(self, df):
        df = self._detect_fractals(df.copy())
        
        # Inisialisasi Kolom
        df['structure'] = None      
        df['trend'] = "Neutral"     
        df['near_swing'] = np.nan   # Data untuk SL
        df['far_swing'] = np.nan    # Data untuk TP2
        df['signal'] = None         

        last_sh = df['high'].iloc[0]
        last_sl = df['low'].iloc[0]
        current_trend = "Neutral"
        
        for i in range(self.window, len(df)):
            curr = df.iloc[i]
            idx = df.index[i]
            
            # Update Swing Points (Fractal Terkonfirmasi)
            if df['is_sh'].iloc[i - self.window]:
                last_sh = df['high'].iloc[i - self.window]
            if df['is_sl'].iloc[i - self.window]:
                last_sl = df['low'].iloc[i - self.window]

            # 1. DETEKSI LIQUIDITY SWEEP (Umpan)
            is_sweep_high = (curr['high'] > last_sh) and (curr['close'] <= last_sh)
            is_sweep_low = (curr['low'] < last_sl) and (curr['close'] >= last_sl)

            if is_sweep_high:
                self.pending_reversal = "BEARISH_CHOCH_WAIT"
            elif is_sweep_low:
                self.pending_reversal = "BULLISH_CHOCH_WAIT"

            # 2. DETEKSI CHOCH / BOS (Konfirmasi - Body Close)
            # Bullish Break
            if curr['close'] > last_sh:
                if current_trend == "Bearish":
                    df.at[idx, 'structure'] = "CHOCH"
                    current_trend = "Bullish"
                    if self.pending_reversal == "BULLISH_CHOCH_WAIT":
                        df.at[idx, 'signal'] = "STRONG_BUY"
                        self.pending_reversal = None
                else:
                    df.at[idx, 'structure'] = "BOS"
                    current_trend = "Bullish"
                last_sh = curr['high'] 

            # Bearish Break
            elif curr['close'] < last_sl:
                if current_trend == "Bullish":
                    df.at[idx, 'structure'] = "CHOCH"
                    current_trend = "Bearish"
                    if self.pending_reversal == "BEARISH_CHOCH_WAIT":
                        df.at[idx, 'signal'] = "STRONG_SELL"
                        self.pending_reversal = None
                else:
                    df.at[idx, 'structure'] = "BOS"
                    current_trend = "Bearish"
                last_sl = curr['low']

            # Simpan navigasi harian
            df.at[idx, 'trend'] = current_trend
            df.at[idx, 'near_swing'] = last_sl if current_trend == "Bullish" else last_sh
            df.at[idx, 'far_swing'] = last_sh if current_trend == "Bullish" else last_sl

        return df
