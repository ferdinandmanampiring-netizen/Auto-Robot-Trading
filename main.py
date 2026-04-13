import MetaTrader5 as mt5
import time as t
from datetime import datetime
import pandas as pd

from core.logging_engine import log
from core.risk_engine import RiskEngine
import core.execution_engine as exec_engine
import engines.context_engine as ctx


TRADE_SCORE_THRESHOLD = 20


# ==========================================================
# 📊 DATA
# ==========================================================
def get_data(symbol, timeframe, bars=300):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None:
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df


# ==========================================================
# 🔥 ATR
# ==========================================================
def calculate_atr(df, period=14):
    df['tr'] = df['high'] - df['low']
    return df['tr'].rolling(period).mean().iloc[-1]


# ==========================================================
# 🔥 SWING SL (MANDAT)
# ==========================================================
def get_swing_sl(df, is_buy, atr):
    buffer = atr * 0.5

    if is_buy:
        swing_low = df['low'].tail(5).min()
        return swing_low - buffer
    else:
        swing_high = df['high'].tail(5).max()
        return swing_high + buffer


# ==========================================================
# 🔥 RR
# ==========================================================
def calculate_tp(entry, sl):
    risk = abs(entry - sl)
    return entry + (risk * 2) if entry < sl else entry - (risk * 2)


# ==========================================================
# 🚀 MAIN
# ==========================================================
def main():

    log("🚀 SNIPER ELIT MODE v6.0 FINAL")

    if not mt5.initialize():
        log("❌ MT5 Failed")
        return

    risk_engine = RiskEngine()

    symbols = [
        "EURUSDc","GBPUSDc","USDJPYc","BTCUSDc",
        "AUDUSDc","USDCHFc","NZDUSDc","EURGBPc","XAGUSDc"
    ]

    while True:
        try:

            # 🔥 EXIT MANAGEMENT (WAJIB SELALU JALAN)
            risk_engine.manage_open_positions()

            for symbol in symbols:

                # =========================
                # 🛡️ RISK FILTER
                # =========================
                allowed, reason = risk_engine.can_trade(symbol)

                # =========================
                # 📊 DATA
                # =========================
                htf = get_data(symbol, mt5.TIMEFRAME_H1)
                ltf = get_data(symbol, mt5.TIMEFRAME_M5)

                if htf is None or ltf is None:
                    log(f"[SCAN] {symbol} | Score: 0/20 | Result: Data Error")
                    continue

                context = ctx.build_context(htf, ltf)

                if not context.get("valid"):
                    log(f"[SCAN] {symbol} | Score: 0/20 | Result: Context Invalid")
                    continue

                score = context["context_score"]
                pd_zone = context.get("pd_zone")
                trend = context.get("htf_trend")

                # =========================
                # 🔥 PD FILTER
                # =========================
                if trend == "BULLISH" and pd_zone != "DISCOUNT":
                    log(f"[SCAN] {symbol} | Score: {score}/20 | Result: Not Discount")
                    continue

                if trend == "BEARISH" and pd_zone != "PREMIUM":
                    log(f"[SCAN] {symbol} | Score: {score}/20 | Result: Not Premium")
                    continue

                # =========================
                # 🔥 SCORE FILTER
                # =========================
                if score < TRADE_SCORE_THRESHOLD:
                    log(f"[SCAN] {symbol} | Score: {score}/20 | Result: Below Threshold")
                    continue

                # =========================
                # 🔥 RISK CHECK
                # =========================
                if not allowed:
                    log(f"[SCAN] {symbol} | Score: {score}/20 | Result: {reason}")
                    continue

                # =========================
                # 🔥 ENTRY LOGIC
                # =========================
                price = ltf.iloc[-1]['close']
                atr = calculate_atr(ltf)

                if atr is None:
                    continue

                is_buy = trend == "BULLISH"

                sl = get_swing_sl(ltf, is_buy, atr)
                tp = calculate_tp(price, sl)

                # =========================
                # 🚀 EXECUTE
                # =========================
                log(f"[ENTRY] {symbol} | Score: {score} | EXECUTE")

                exec_engine.execute_trade(
                    symbol,
                    mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
                    0.01,
                    100,  # tetap dipakai engine internal
                    200
                )

            t.sleep(60)

        except Exception as e:
            log(f"❌ ERROR: {e}")
            t.sleep(5)


if __name__ == "__main__":
    main()
