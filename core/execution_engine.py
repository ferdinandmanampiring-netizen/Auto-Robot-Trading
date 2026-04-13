import MetaTrader5 as mt5
import time
from core.logging_engine import log


# ==========================================================
# 🔧 [HARDENING #1] CONNECTION ENGINE (STABLE LOOP)
# ==========================================================
def ensure_connection():
    """
    🔥 HARDENING:
    - Retry initialize
    - Auto reconnect
    - Stabil untuk koneksi fluktuatif
    """

    if not mt5.initialize():
        log("🔄 MT5 INIT ulang...")

        for i in range(3):
            time.sleep(2)
            if mt5.initialize():
                log("✅ MT5 reconnect sukses")
                break
        else:
            log(f"❌ MT5 INIT FAILED: {mt5.last_error()}")
            return False

    while True:
        terminal = mt5.terminal_info()
        if terminal and terminal.connected:
            return True

        log("📡 Menunggu koneksi broker...")
        time.sleep(3)


# ==========================================================
# 🔧 [HARDENING #2] FILLING MODE KHUSUS CRYPTO (EXNESS)
# ==========================================================
def get_filling_mode(symbol_info, symbol):
    """
    🔥 HARDENING:

    BTCUSDc (Exness):
    - Lebih stabil pakai ORDER_FILLING_IOC
    - Hindari FOK (sering gagal di crypto fast market)
    """

    if "BTC" in symbol.upper():
        return mt5.ORDER_FILLING_IOC

    # fallback normal
    if symbol_info.filling_mode == mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    elif symbol_info.filling_mode == mt5.ORDER_FILLING_RETURN:
        return mt5.ORDER_FILLING_RETURN
    else:
        return mt5.ORDER_FILLING_IOC


# ==========================================================
# 🔧 [HARDENING #3] VALIDASI STOPS (BROKER + BTC FALLBACK)
# ==========================================================
def validate_stops(symbol_info, price, sl, symbol):
    """
    🔥 HARDENING:

    - Gunakan trade_stops_level broker
    - Jika 0 → fallback khusus BTC
    """

    # 🔰 Ambil broker rule
    if symbol_info.trade_stops_level == 0:

        # 🔥 KHUSUS BTC (volatility tinggi)
        if "BTC" in symbol.upper():
            stops_level = 500 * symbol_info.point  # fallback BTC
            log("⚠️ Broker stops_level=0 → pakai fallback BTC")
        else:
            stops_level = 10 * symbol_info.point

    else:
        stops_level = symbol_info.trade_stops_level * symbol_info.point

    buffer = 5 * symbol_info.point
    min_distance = stops_level + buffer

    actual_distance = abs(price - sl)

    if actual_distance < min_distance:
        log(
            f"❌ SL TERLALU DEKAT!\n"
            f"Symbol        : {symbol}\n"
            f"Broker Min    : {stops_level}\n"
            f"Buffer        : {buffer}\n"
            f"Total Min     : {min_distance}\n"
            f"Actual        : {actual_distance}"
        )
        return False

    return True


# ==========================================================
# 🔧 [HARDENING #4] RETRY INTELLIGENCE (BTC FAST MARKET)
# ==========================================================
def send_order_with_retry(request, symbol, buy_signal):
    """
    🔥 HARDENING:

    - Adaptive retry delay
    - Aggressive requote handling
    - BTC fast reaction
    """

    max_retry = 5  # 🔥 dinaikkan (crypto fast market)

    for attempt in range(max_retry):

        result = mt5.order_send(request)

        if result is None:
            log(f"❌ order_send None ({symbol}) → retry")
            time.sleep(0.3)
            continue

        # ✅ SUCCESS
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"🔥 EXECUTED {symbol} @ {result.price}")
            return result

        # 🔁 REQUOTE / PRICE CHANGE (CRITICAL BTC)
        if result.retcode in [
            mt5.TRADE_RETCODE_REQUOTE,
            mt5.TRADE_RETCODE_PRICE_CHANGED
        ]:
            log(f"🔁 REQUOTE DETECTED ({symbol}) → update cepat")

            tick = mt5.symbol_info_tick(symbol)
            if tick:
                request["price"] = tick.ask if buy_signal else tick.bid

            time.sleep(0.2)  # 🔥 lebih cepat
            continue

        # ❌ INVALID STOPS
        elif result.retcode == mt5.TRADE_RETCODE_INVALID_STOPS:
            log("❌ INVALID STOPS (broker reject)")
            return result

        # ❌ NO MONEY
        elif result.retcode == mt5.TRADE_RETCODE_NO_MONEY:
            log("❌ SALDO TIDAK CUKUP")
            return result

        else:
            log(f"❌ ERROR {symbol}: {result.retcode} | {result.comment}")
            return result

    log("❌ GAGAL EKSEKUSI setelah retry")
    return None


# ==========================================================
# 🔥 EXECUTE TRADE
# ==========================================================
def execute_trade(symbol, order_type, lot, sl, tp, magic_number=123456):

    if not ensure_connection():
        return None

    symbol_info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)

    if not symbol_info or not tick:
        log(f"❌ Data invalid ({symbol})")
        return None

    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    # 🔧 VALIDASI STOPS
    if not validate_stops(symbol_info, price, sl, symbol):
        return None

    filling = get_filling_mode(symbol_info, symbol)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_type,
        "price": price,
        "sl": float(sl),
        "tp": float(tp),
        "deviation": 30,  # 🔥 diperbesar untuk BTC volatility
        "magic": magic_number,
        "comment": "Sniper BTC Engine",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    return send_order_with_retry(request, symbol, order_type == mt5.ORDER_TYPE_BUY)


# ==========================================================
# 🔥 HYBRID EXECUTION
# ==========================================================
def execute_trade_hybrid(
    symbol,
    buy_signal,
    sl,
    tp,
    lot,
    body_ratio=0.7,
    displacement_strong=False,
    zone_obj=None,
    magic_number=123456
):

    if not ensure_connection():
        return None

    symbol_info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)

    if not symbol_info or not tick:
        log(f"❌ Data invalid ({symbol})")
        return None

    order_type = mt5.ORDER_TYPE_BUY if buy_signal else mt5.ORDER_TYPE_SELL
    price = tick.ask if buy_signal else tick.bid

    if not validate_stops(symbol_info, price, sl, symbol):
        return None

    filling = get_filling_mode(symbol_info, symbol)

    momentum_strong = body_ratio > 0.8 or displacement_strong

    # 🚀 MARKET (BTC biasanya dominan)
    if momentum_strong:
        log(f"🚀 MARKET EXECUTION ({symbol})")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 30,
            "magic": magic_number,
            "comment": "BTC Market",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }

    else:
        log(f"❓ DEFAULT MARKET ({symbol})")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 30,
            "magic": magic_number,
            "comment": "BTC Default",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }

    return send_order_with_retry(request, symbol, buy_signal)


# ==========================================================
# 🔄 TRAILING STOP (NEXT PHASE)
# ==========================================================
def auto_trailing_stop(symbol, trail_pips, magic_number):

    if not ensure_connection():
        return

    pass
