from datetime import datetime, time, timedelta

try:
    from config import SYMBOLS, PAIR_SETTINGS, TIMEFRAME_HTF, TIMEFRAME_LTF, DEFAULT_SETTING
except ImportError:
    SYMBOLS = []
    PAIR_SETTINGS = {}
    TIMEFRAME_HTF = "H4"
    TIMEFRAME_LTF = "M15"
    DEFAULT_SETTING = {"vol_threshold": 0.0005, "tolerance_pts": 2}

# ==========================================================
# 🔰 RISK CONFIGURATION (CENT ACCOUNT SAFE)
# ==========================================================
RISK_PER_TRADE_CENTS = 15.0
RISK_PER_TRADE_PERCENT = 0.25
LOT_MIN = 0.01

# ==========================================================
# 🔰 PROTECTION SYSTEM
# ==========================================================
MAX_DAILY_LOSS_CENTS = 300.0
EQUITY_MIN_CENTS = 2500.0

# ==========================================================
# 🔒 MULTI POSITION LOCK (MANDATORY)
# ==========================================================
MAX_POSITIONS_PER_PAIR = 3

# ==========================================================
# 🔰 COOLDOWN CONTROL (OPTIMIZED FOR TRIAL BTC)
# ==========================================================
"""
Optimasi:
- BTC cepat → tapi tetap butuh jeda agar tidak overtrade
- 900 detik = 15 menit → ideal untuk M15 structure
"""
COOLDOWN_SECONDS = 900

# ==========================================================
# 🔰 TRADE LIMIT CONTROL
# ==========================================================
MAX_TRADES_PER_SESSION = 3
MAX_TRADES_PER_DAY = 5

MAX_SPREAD_POINTS = 2000

# ==========================================================
# 🔰 EXECUTION CONTROL
# ==========================================================
NEWS_API_ENABLED = False
MANUAL_NEWS_PAUSE = True
MANUAL_NEWS_FILE = "manual_news_pause.txt"

EXECUTE_TRADES = False  # SAFE MODE

# ==========================================================
# 🔒 SCORING SYSTEM LOCK
# ==========================================================
TRADE_SCORE_THRESHOLD = 8

ENABLE_LIQUIDITY_SWEEP = True
ENABLE_SESSION_VALIDATION = False

# ==========================================================
# 🔒 TRIAL MODE (BTC LOCK SYSTEM)
# ==========================================================
TRIAL_MODE = True
TRIAL_SYMBOL = "BTCUSDc"

TRIAL_MAX_TRADES = 3
TRIAL_EXECUTE_TRADES = True
TRIAL_BYPASS_SESSION = True
TRIAL_DISABLE_NEWS_PAUSE = True
TRIAL_FIXED_LOT_SIZE = 0.01
TRIAL_AUTO_SHUTDOWN = False

# ==========================================================
# 🔒 SYMBOL GATEWAY (SOURCE OF TRUTH)
# ==========================================================
"""
INI BAGIAN PALING KRUSIAL

RULE:
- Semua engine WAJIB pakai function ini
- DILARANG akses SYMBOLS langsung saat trading loop

BEHAVIOR:
- Trial Mode → hanya BTCUSDc
- Normal Mode → semua SYMBOLS
"""
def get_active_symbols():
    if TRIAL_MODE:
        return [TRIAL_SYMBOL]
    return SYMBOLS

# ==========================================================
# 🔰 SESSION WINDOWS
# ==========================================================
SESSION_WINDOWS = {
    "LONDON": (time(8, 0), time(17, 0)),
    "NEW_YORK": (time(13, 0), time(22, 0)),
    "SYDNEY": (time(22, 0), time(5, 0)),
}

# ==========================================================
# 🔰 TRAILING CONFIG
# ==========================================================
TRAILING_RULES = {
    "BTCUSDc": {
        "start_pips": 150,
        "trail_gap_pips": 80,
        "wider_gap_after_pips": 200,
        "wider_gap_pips": 120,
    },
    "FOREX_CRYPTO": {
        "tp1_cover_cents": 10,
        "post_tp1_gap_pips": 20,
    },
}

# ==========================================================
# 🔰 SESSION CHECK
# ==========================================================
def _is_time_in_range(current_time, start_time, end_time):
    if start_time <= end_time:
        return start_time <= current_time < end_time
    return current_time >= start_time or current_time < end_time


def is_session_allowed(now=None):
    now = now or datetime.utcnow()
    current_time = now.time()

    for window in SESSION_WINDOWS.values():
        if _is_time_in_range(current_time, *window):
            return True
    return False


# ==========================================================
# 🔰 NEWS BLOCK SYSTEM
# ==========================================================
def load_manual_news_blocks():
    blocks = []
    try:
        with open(MANUAL_NEWS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue

                parts = [p.strip() for p in raw.split(",")]
                if len(parts) < 2:
                    continue

                timestamp = parts[0]
                duration = int(parts[1])
                symbol = parts[2] if len(parts) >= 3 else None

                try:
                    block_start = datetime.fromisoformat(timestamp)
                except ValueError:
                    continue

                blocks.append({
                    "symbol": symbol,
                    "start": block_start,
                    "end": block_start + timedelta(minutes=duration),
                })
    except FileNotFoundError:
        pass

    return blocks


def is_manual_news_active(now=None, symbol=None):
    if not MANUAL_NEWS_PAUSE:
        return False

    now = now or datetime.utcnow()

    for block in load_manual_news_blocks():
        if symbol and block["symbol"] and block["symbol"] != symbol:
            continue

        if block["start"] <= now <= block["end"]:
            return True

    return False


# ==========================================================
# 🔰 TRIAL MODE FUNCTIONS (ISOLATED & SAFE)
# ==========================================================
def is_trial_mode_active():
    return TRIAL_MODE


def get_trial_config():
    """
    Menghasilkan override config saat trial aktif
    Tidak mengubah global → hanya override di engine
    """
    if not is_trial_mode_active():
        return {}

    return {
        "EXECUTE_TRADES": TRIAL_EXECUTE_TRADES,
        "MAX_TRADES_PER_SESSION": TRIAL_MAX_TRADES,
        "MAX_TRADES_PER_DAY": TRIAL_MAX_TRADES,
        "MANUAL_NEWS_PAUSE": not TRIAL_DISABLE_NEWS_PAUSE,
        "SYMBOLS": [TRIAL_SYMBOL],
        "TRIAL_FIXED_LOT_SIZE": TRIAL_FIXED_LOT_SIZE,
        "TRIAL_AUTO_SHUTDOWN": TRIAL_AUTO_SHUTDOWN,
    }


def is_session_allowed_trial(now=None):
    """
    Trial bisa bypass session (untuk testing fleksibel)
    """
    if is_trial_mode_active() and TRIAL_BYPASS_SESSION:
        return True
    return is_session_allowed(now)


def is_manual_news_active_trial(now=None, symbol=None):
    """
    Trial bisa ignore news pause
    """
    if is_trial_mode_active() and TRIAL_DISABLE_NEWS_PAUSE:
        return False
    return is_manual_news_active(now, symbol)
