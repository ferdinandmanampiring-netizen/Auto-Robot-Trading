# config.py

# Daftar target operasi
SYMBOLS = [
    "EURUSDc", "GBPUSDc", "USDJPYc", "BTCUSDc", 
    "AUDUSDc", "USDCHFc", "USDCADc", "NZDUSDc", 
    "EURJPYc", "GBPJPYc", "EURGBPc", "XAUUSDc", "XAGUSDc"
]

# Timeframe Settings
TIMEFRAME_HTF = "H4"  # Sensor Tren Utama
TIMEFRAME_LTF = "M15" # Area Eksekusi
COOLDOWN_SECONDS = 900 # 15 Menit (Mode Agresif)

RISK_PER_TRADE = 0.25
MIN_SCORE = 40

# --- KACAMATA SNIPER (Dinamis berdasarkan Karakter Pair) ---
# Format: "Pair": (Threshold_Volatilitas, Tolerance_Points)
PAIR_SETTINGS = {
    "EURUSDc": {"vol_threshold": 0.05, "tolerance_pts": 10},
    "GBPUSDc": {"vol_threshold": 0.07, "tolerance_pts": 12},
    "USDJPYc": {"vol_threshold": 0.06, "tolerance_pts": 10},
    "BTCUSDc": {"vol_threshold": 0.30, "tolerance_pts": 50},
    "AUDUSDc": {"vol_threshold": 0.05, "tolerance_pts": 10},
    "USDCHFc": {"vol_threshold": 0.04, "tolerance_pts": 10},
    "USDCADc": {"vol_threshold": 0.05, "tolerance_pts": 10}, # Baru
    "NZDUSDc": {"vol_threshold": 0.04, "tolerance_pts": 10}, # Baru
    "EURJPYc": {"vol_threshold": 0.08, "tolerance_pts": 15}, # Baru
    "GBPJPYc": {"vol_threshold": 0.12, "tolerance_pts": 20}, # Baru
    "EURGBPc": {"vol_threshold": 0.03, "tolerance_pts": 8},   # Baru

    # VIP METAL PROTOCOL
    "XAUUSDc": {"vol_threshold": 0.20, "tolerance_pts": 35}, # Buffer 35 pts
    "XAGUSDc": {"vol_threshold": 0.25, "tolerance_pts": 45}  # Buffer 45 pts
}

DEFAULT_SETTING = {"vol_threshold": 0.0005, "tolerance_pts": 2}
