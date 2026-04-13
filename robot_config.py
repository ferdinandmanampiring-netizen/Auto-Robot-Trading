# robot_config.py - v4.4 - FINAL COMMAND DECK
import MetaTrader5 as mt5

# ==========================================
# 1. SAKLAR UTAMA (MASTER SWITCH)
# ==========================================
TRIAL_MODE = False  # Set False untuk mengaktifkan SEMUA PAIR di hari Senin
TRADE_SCORE_THRESHOLD = 8

# ==========================================
# 2. SESSION MANAGER (ENABLE/DISABLE & CHARACTER)
# ==========================================
# WIB (UTC+7) Settings
SESSIONS = {
    "SYDNEY": {
        "active": True, 
        "start_time": "04:00", "end_time": "12:00",
        "risk_per_trade": 0.15,  # Lebih konservatif di subuh hari
        "threshold_score": 8,
        "trailing_gap": 100      # Gap lebih lebar untuk Sydney
    },
    "ASIA": {
        "active": False, # Kamu bisa matikan sesukamu
        "start_time": "07:00", "end_time": "15:00",
        "risk_per_trade": 0.15,
        "threshold_score": 9,    # Lebih ketat karena sideways
        "trailing_gap": 80
    },
    "LONDON": {
        "active": True,
        "start_time": "14:00", "end_time": "22:00",
        "risk_per_trade": 0.20,  # Agresif di London
        "threshold_score": 8,
        "trailing_gap": 70       # Ketat karena volatilitas tinggi
    },
    "NY": {
        "active": True,
        "start_time": "19:00", "end_time": "03:00",
        "risk_per_trade": 0.25,  # Maksimal Power
        "threshold_score": 8,
        "trailing_gap": 60
    }
}

# ==========================================
# 3. GLOBAL RISK & EXECUTION SETTINGS
# ==========================================
MAX_POSITIONS_PER_PAIR = 3
COOLDOWN_SECONDS = 900
NEWS_PAUSE_MINUTES = 30
DEFAULT_DEVIATION = 50  # Crypto-ready slippage

# ==========================================
# 4. SYMBOL & PAIR SETTINGS (Reference from config.py)
# ==========================================
ACTIVE_SYMBOLS = [
    "EURUSDc", "GBPUSDc", "USDJPYc", "BTCUSDc", 
    "XAUUSDc", "EURJPYc", "GBPJPYc"
]

def get_active_symbols():
    if TRIAL_MODE:
        return ["BTCUSDc"]
    return ACTIVE_SYMBOLS

# Fungsi Helper untuk cek sesi aktif (Akan dipanggil di main.py)
def is_session_active(current_time_str):
    # Logika pengecekan jam dan saklar 'active'
    pass
