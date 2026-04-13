import MetaTrader5 as mt5
import time
from core.logging_engine import log


# ==========================================================
# 🔧 CONNECTION ENGINE
# ==========================================================
def ensure_connection():
    if not mt5.initialize():
        log("🔄 MT5 INIT ulang...")
        for _ in range(3):
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
# 🔢 NORMALIZE PRICE
# ==========================================================
def normalize(price, digits):
    return round(price, digits)


# ==========================================================
# 🔥 HITUNG SL/TP BERDASARKAN PIPS
# ==========================================================
def calculate_sl_tp(symbol_info, price, sl_pips, tp_pips, is_buy):

    point = symbol_info.point
    digits = symbol_info.digits

    sl_dist = sl_pips * point
    tp_dist = tp_pips * point

    if is_buy:
        sl = price - sl_dist
        tp = price + tp_dist
    else:
        sl = price + sl_dist
        tp = price - tp_dist

    # 🔒 Anti negatif
    if sl <= 0:
        sl = price * 0.9
    if tp <= 0:
        tp = price * 1.1

    return normalize(sl, digits), normalize(tp, digits)


# ==========================================================
# 🔥 FIX STOP LEVEL BROKER
# ==========================================================
def fix_stop_level(symbol_info, price, sl, tp, is_buy):

    point = symbol_info.point
    digits = symbol_info.digits

    if symbol_info.trade_stops_level == 0:
        stop_level = 10 * point
    else:
        stop_level = symbol_info.trade_stops_level * point

    buffer = 5 * point
    min_dist = stop_level + buffer

    if is_buy:
        if (price - sl) < min_dist:
            sl = price - min_dist
        if (tp - price) < min_dist:
            tp = price + min_dist
    else:
        if (sl - price) < min_dist:
            sl = price + min_dist
        if (price - tp) < min_dist:
            tp = price - min_dist

    return normalize(sl, digits), normalize(tp, digits)


# ==========================================================
# 🔁 RETRY ENGINE
# ==========================================================
def send_order_with_retry(request, symbol, is_buy):

    for _ in range(5):

        result = mt5.order_send(request)

        if result is None:
            log(f"❌ order_send None ({symbol}) → retry")
            time.sleep(0.3)
            continue

        # ✅ SUCCESS
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"🔥 EXECUTED {symbol} @ {result.price}")
            return result

        # 🔁 REQUOTE
        elif result.retcode in [
            mt5.TRADE_RETCODE_REQUOTE,
            mt5.TRADE_RETCODE_PRICE_CHANGED
        ]:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                request["price"] = tick.ask if is_buy else tick.bid
            time.sleep(0.2)
            continue

        # ❌ NO MONEY
        elif result.retcode == mt5.TRADE_RETCODE_NO_MONEY:
            log("❌ SALDO TIDAK CUKUP")
            return result

        # ❌ INVALID STOPS
        elif result.retcode == mt5.TRADE_RETCODE_INVALID_STOPS:
            log("❌ INVALID STOPS (broker reject)")
            return result

        else:
            log(f"❌ ERROR {symbol}: {result.retcode}")
            return result

    log("❌ GAGAL EKSEKUSI")
    return None


# ==========================================================
# 🚀 EXECUTE TRADE (SNIPER ELIT MODE)
# ==========================================================
def execute_trade(symbol, order_type, lot, sl_pips, tp_pips, magic_number=123456):

    if not ensure_connection():
        return None

    symbol_info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)

    if not symbol_info or not tick:
        log(f"❌ Data invalid ({symbol})")
        return None

    is_buy = order_type == mt5.ORDER_TYPE_BUY
    price = tick.ask if is_buy else tick.bid

    price = normalize(price, symbol_info.digits)

    # ==================================================
    # 🔒 HARD LOCK LOT (MANDAT)
    # ==================================================
    lot = 0.01

    # ==================================================
    # 🔥 HITUNG SL TP
    # ==================================================
    sl, tp = calculate_sl_tp(symbol_info, price, sl_pips, tp_pips, is_buy)

    # ==================================================
    # 🔥 FIX STOP LEVEL
    # ==================================================
    sl, tp = fix_stop_level(symbol_info, price, sl, tp, is_buy)

    # ==================================================
    # 🔥 FINAL VALIDATION (ANTI ERROR)
    # ==================================================
    if sl <= 0 or tp <= 0:
        log(f"❌ SL/TP invalid {symbol}")
        return None

    # ==================================================
    # 🔍 DEBUG LOG (MANDATORY)
    # ==================================================
    log(f"DEBUG: Send Order {symbol} | Lot: {lot} | Price: {price} | SL: {sl} | TP: {tp}")

    # ==================================================
    # 📦 REQUEST
    # ==================================================
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 30,
        "magic": magic_number,
        "comment": "SNIPER ELIT MODE",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    return send_order_with_retry(request, symbol, is_buy)
