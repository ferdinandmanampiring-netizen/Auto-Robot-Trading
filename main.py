# === SNIPER POWERFUL FERDY v4.5 (VERBOSE SCORING + CONTROLLED SCAN) ===

# ==========================================================
# 🔥 IMPORT
# ==========================================================
import time as t  # 🔥 Anti bentrok dengan datetime.time
import MetaTrader5 as mt5
import os
import json
from datetime import datetime

from engines.liquidity_engine import analyze_liquidity
from engines.zone_engine import analyze_zone
from engines.context_engine import build_context
from core.risk_engine import RiskEngine
from core.execution_engine import execute_trade_hybrid, ensure_connection
from core.logging_engine import log
from utils.helpers import get_market_data
from robot_config import *


# ==========================================================
# 🔰 COOLDOWN STORAGE (PERSISTENT)
# ==========================================================
COOLDOWN_FILE = "cooldown_state.json"


def load_cooldown_state(symbols):
    """
    🔥 TUJUAN:
    Menyimpan cooldown walaupun bot restart
    """
    if os.path.exists(COOLDOWN_FILE):
        try:
            with open(COOLDOWN_FILE, "r") as f:
                data = json.load(f)
                return {s: data.get(s, 0) for s in symbols}
        except Exception as e:
            log(f"⚠️ COOLDOWN LOAD ERROR: {e}")
    return {s: 0 for s in symbols}


def save_cooldown_state(state):
    """
    🔥 TUJUAN:
    Anti file corrupt dengan atomic write
    """
    temp_file = COOLDOWN_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(state, f)
    os.replace(temp_file, COOLDOWN_FILE)


# ==========================================================
# 🔥 ACTIVE SYMBOL CONTROLLER (TRIAL MODE SYNC)
# ==========================================================
def get_active_symbols():
    """
    ==========================================================
    🔥 TUJUAN:
    - Sinkronisasi TRIAL_MODE dengan symbol loop
    - Jika trial aktif → hanya 1 symbol
    - Jika tidak → semua symbol aktif
    ==========================================================
    """

    if TRIAL_MODE:
        log(f"🎯 TRIAL MODE AKTIF → HANYA {TRIAL_SYMBOL}")
        return [TRIAL_SYMBOL]

    return SYMBOLS


# ==========================================================
# 🔥 UNIVERSAL LOT HANDLER
# ==========================================================
def get_lot_size(risk_engine, entry, sl):

    if hasattr(risk_engine, "calculate_lot"):
        return risk_engine.calculate_lot(entry, sl)

    elif hasattr(risk_engine, "calculate_position_size"):
        return risk_engine.calculate_position_size(entry, sl)

    elif hasattr(risk_engine, "get_lot_size"):
        return risk_engine.get_lot_size(entry, sl)

    else:
        log("❌ LOT FUNCTION NOT FOUND")
        return None


# ==========================================================
# 🔥 STOP LEVEL PROTECTION (BROKER AWARE)
# ==========================================================
def adjust_to_stops_level(symbol, entry, target_sl, is_buy):

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return target_sl

    stops_level_points = symbol_info.trade_stops_level
    min_dist = (stops_level_points + 50) * symbol_info.point

    if abs(entry - target_sl) < min_dist:
        new_sl = entry - min_dist if is_buy else entry + min_dist
        log(f"⚠️ SL Adjusted for {symbol}")
        return new_sl

    return target_sl


# ==========================================================
# 🔰 MAIN ENGINE
# ==========================================================
def main():

    log("🚀 SYSTEM START")

    if not ensure_connection():
        log("❌ INITIAL CONNECTION FAILED")
        return

    symbols_to_trade = get_active_symbols()
    last_trade_times = load_cooldown_state(symbols_to_trade)
    last_manage_time = {}

    while True:
        try:

            # ==================================================
            # 🔥 SAFE RECONNECT
            # ==================================================
            term = mt5.terminal_info()
            if term is None or not term.connected:
                if not ensure_connection():
                    log("❌ RECONNECT FAILED")
                    t.sleep(5)
                    continue

            # ==================================================
            # 🔁 LOOP PER SYMBOL
            # ==================================================
            for SYMBOL in symbols_to_trade:

                symbol_info = mt5.symbol_info(SYMBOL)
                if symbol_info is None:
                    continue

                risk_engine = RiskEngine(symbol=SYMBOL)

                # ==================================================
                # 🔥 EXIT MANAGEMENT (TETAP DI ENGINE)
                # ==================================================
                if EXECUTE_TRADES:
                    positions = mt5.positions_get(symbol=SYMBOL)

                    if positions:
                        now = t.time()

                        if now - last_manage_time.get(SYMBOL, 0) > 30:

                            if hasattr(risk_engine, "manage_open_positions"):
                                risk_engine.manage_open_positions()

                            elif hasattr(risk_engine, "apply_tp1_tp2_logic"):
                                risk_engine.apply_tp1_tp2_logic()

                            last_manage_time[SYMBOL] = now

                # ==================================================
                # 🔰 ENTRY GATE
                # ==================================================
                can_trade, reason = risk_engine.can_trade()
                if not can_trade:
                    continue

                # ==================================================
                # 🔰 MARKET DATA
                # ==================================================
                data_ltf = get_market_data(SYMBOL, TIMEFRAME_LTF, 100)
                data_htf = get_market_data(SYMBOL, TIMEFRAME_HTF, 100)

                if data_ltf is None or data_htf is None:
                    continue

                if len(data_ltf) < 2:
                    continue

                # ==================================================
                # 🔥 SCORING SYSTEM (VERBOSE)
                # ==================================================
                total_score = 0

                # --- CONTEXT (2 poin)
                context = build_context(data_htf, data_ltf)
                htf_bias = context.get("htf_trend", "UNCLEAR")

                context_score = 2 if htf_bias != "UNCLEAR" else 0
                total_score += context_score

                # --- LIQUIDITY (3 poin)
                liquidity = analyze_liquidity(data_ltf)
                liquidity_score = 3 if liquidity.get("liquidity_detected", False) else 0
                total_score += liquidity_score

                # --- ZONE (3 poin)
                zone = analyze_zone(data_ltf)
                zone_score = 3 if zone and zone.get("zone_valid", False) else 0
                total_score += zone_score

                # ==================================================
                # 🔥 VERBOSE LOGGING (TRANSPARANSI)
                # ==================================================
                log(f"📊 {SYMBOL} | Score: {total_score}/8 "
                    f"(Context: {context_score}, Liquidity: {liquidity_score}, Zone: {zone_score})")

                # ==================================================
                # 🔥 STRICT FILTER
                # ==================================================
                if total_score < TRADE_SCORE_THRESHOLD:
                    log(f"❌ {SYMBOL} REJECTED (Score below threshold)")
                    continue
                else:
                    log(f"✅ {SYMBOL} PASSED SCORING")

                # ==================================================
                # 🔰 VALIDASI LANJUT
                # ==================================================
                last_c = data_ltf.iloc[-2]

                range_candle = last_c.high - last_c.low
                body_ratio = abs(last_c.close - last_c.open) / range_candle if range_candle > 0 else 0

                if body_ratio < 0.7:
                    continue

                if t.time() - last_trade_times.get(SYMBOL, 0) < COOLDOWN_SECONDS:
                    continue

                tick = mt5.symbol_info_tick(SYMBOL)
                if not tick or tick.ask == 0 or tick.bid == 0:
                    continue

                # ==================================================
                # 🔰 ENTRY LOGIC
                # ==================================================
                buy_signal = (htf_bias == "BULLISH")
                entry = tick.ask if buy_signal else tick.bid

                if buy_signal:
                    raw_sl = entry - (150 * symbol_info.point)
                    tp = entry + (200 * symbol_info.point)
                else:
                    raw_sl = entry + (150 * symbol_info.point)
                    tp = entry - (200 * symbol_info.point)

                sl = adjust_to_stops_level(SYMBOL, entry, raw_sl, buy_signal)

                # ==================================================
                # 🔰 LOT SIZE
                # ==================================================
                lot = get_lot_size(risk_engine, entry, sl)

                if not lot or lot < LOT_MIN:
                    continue

                # ==================================================
                # 🔥 EXECUTION
                # ==================================================
                result = execute_trade_hybrid(
                    symbol=SYMBOL,
                    buy_signal=buy_signal,
                    sl=sl,
                    tp=tp,
                    lot=lot
                )

                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    last_trade_times[SYMBOL] = t.time()
                    save_cooldown_state(last_trade_times)

                    log(f"🔥 TRADE EXECUTED: {SYMBOL} | Lot {lot} | Score {total_score}")

            # ==================================================
            # 🔥 THROTTLING SCAN (MANDATORY UPDATE)
            # ==================================================
            """
            ======================================================
            🔥 PERUBAHAN PENTING:
            - Sebelumnya: scan tiap 10 detik
            - Sekarang: scan tiap 60 detik

            TUJUAN:
            - Lebih stabil
            - Tidak over-scan
            - Lebih profesional untuk live trading
            ======================================================
            """
            t.sleep(60)

        except Exception as e:
            log(f"⚠️ ERROR: {e}")
            t.sleep(5)


# ==========================================================
# 🔰 ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    main()
