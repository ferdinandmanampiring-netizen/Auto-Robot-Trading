# ==========================================================
# 🔥 RISK ENGINE - UNIT INTELLIGENCE (MANDAT 2 FINAL)
# ==========================================================
# Fokus:
# - Multi-position (max 3 posisi per symbol)
# - BTC safety buffer (anti invalid stops)
# - Exit intelligence stabil untuk banyak posisi
# ==========================================================

import MetaTrader5 as mt5


class RiskEngine:
    def __init__(
        self,
        symbol="BTCUSDc",
        risk_per_trade=15.0,
        max_daily_risk=500.0,
        min_equity_threshold=2500.0,
        max_spread_points=2000,
        max_positions_per_pair=3,  # 🔥 MANDAT: MAKSIMAL 3 POSISI
    ):
        self.symbol = symbol

        # 🔰 RISK SETTINGS
        self.max_risk_per_trade = risk_per_trade
        self.max_daily_risk = max_daily_risk
        self.min_equity_threshold = min_equity_threshold

        # 🔥 MANDAT: DIGUNAKAN DI can_trade()
        self.max_positions_per_pair = max_positions_per_pair

        # 🔰 MARKET FILTER
        self.max_spread_points = max_spread_points

        # 🔥 DETEKSI BTC MODE (VOLATILITY TINGGI)
        self.is_crypto = self.symbol in ["BTCUSDc", "ETHUSDc"]

        # 🔥 BEP BUFFER LEBIH BESAR UNTUK BTC
        self.bep_plus_points = 50 if self.is_crypto else 10

        # ======================================================
        # 🔥 STATE TRACKING (MULTI POSITION SAFE)
        # ======================================================
        """
        tp1_done adalah dictionary dengan key = ticket.

        Kenapa ini penting?
        - Kita handle hingga 3 posisi sekaligus
        - Setiap posisi punya ticket unik
        - Jadi state tidak akan bentrok

        Contoh:
        {
            12345: True,
            12346: True
        }

        👉 Artinya:
        - posisi 12345 sudah TP1
        - posisi 12346 sudah TP1
        """
        self.tp1_done = {}

    # ==========================================================
    # 🔥 CAN TRADE (MULTI POSITION SYNC)
    # ==========================================================
    def can_trade(self):
        """
        🔥 MANDAT:
        - Harus cek jumlah posisi aktif
        - Maksimal 3 posisi per symbol

        FLOW:
        1. Cek equity
        2. Cek daily risk
        3. Cek spread
        4. Cek jumlah posisi
        """

        account = mt5.account_info()
        if account is None:
            return False, "Account info failed"

        # EQUITY GUARD
        if account.equity < self.min_equity_threshold:
            return False, f"Equity too low: {account.equity}"

        # DAILY RISK GUARD
        if account.equity < (account.balance - self.max_daily_risk):
            return False, "Max daily risk reached"

        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            return False, "Symbol info failed"

        # 🔥 BTC: spread lebih fleksibel
        max_spread = self.max_spread_points * (2 if self.is_crypto else 1)

        if symbol_info.spread > max_spread:
            return False, f"Spread too high: {symbol_info.spread}"

        # ======================================================
        # 🔥 MULTI POSITION CHECK (MANDAT UTAMA)
        # ======================================================
        positions = mt5.positions_get(symbol=self.symbol)

        """
        LOGIKA:
        - Ambil semua posisi aktif untuk symbol ini
        - Jika jumlah >= 3 → STOP ENTRY

        Contoh:
        posisi = 3 → tidak boleh entry lagi
        posisi = 2 → masih boleh tambah 1
        """

        if positions and len(positions) >= self.max_positions_per_pair:
            return False, "Max positions reached (3)"

        return True, "Ready"

    # ==========================================================
    # 🔥 SAFE SL (BTC VOLATILITY SHIELD)
    # ==========================================================
    def get_safe_sl(self, entry, target_sl, is_buy):
        """
        🔥 MANDAT:
        - Pastikan SL tidak melanggar aturan broker
        - Khusus BTC → buffer diperbesar

        MASALAH:
        - BTC sangat volatile
        - SL terlalu dekat → INVALID STOPS

        SOLUSI:
        - Gunakan trade_stops_level dari broker
        - Tambahkan buffer ekstra untuk crypto
        """

        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            return target_sl

        # Jarak minimal dari broker
        stops_level = symbol_info.trade_stops_level * symbol_info.point

        # 🔥 BTC buffer lebih besar
        buffer_pips = 120 if self.is_crypto else 50
        buffer = buffer_pips * symbol_info.point

        min_dist = stops_level + buffer

        actual_dist = abs(entry - target_sl)

        if actual_dist < min_dist:
            return entry - min_dist if is_buy else entry + min_dist

        return target_sl

    # ==========================================================
    # 🔥 ATR (VOLATILITY)
    # ==========================================================
    def calculate_atr(self, period=14):

        rates = mt5.copy_rates_from_pos(
            self.symbol, mt5.TIMEFRAME_M5, 0, period + 1
        )

        if rates is None or len(rates) < period + 1:
            return None

        trs = []
        for i in range(1, len(rates)):
            high = rates[i]['high']
            low = rates[i]['low']
            prev_close = rates[i - 1]['close']

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)

        return sum(trs) / len(trs)

    # ==========================================================
    # 🔥 LOT CALCULATION
    # ==========================================================
    def calculate_lot(self, entry, sl):

        account = mt5.account_info()
        symbol_info = mt5.symbol_info(self.symbol)

        if account is None or symbol_info is None:
            return 0.0

        sl_distance = abs(entry - sl)
        if sl_distance == 0:
            return 0.0

        risk_amount = self.max_risk_per_trade

        point = symbol_info.point
        contract_size = symbol_info.trade_contract_size

        value_per_point = contract_size * point

        lot = risk_amount / (sl_distance * value_per_point)

        # normalisasi
        lot = max(symbol_info.volume_min, lot)
        lot = min(symbol_info.volume_max, lot)

        step = symbol_info.volume_step
        lot = round(lot / step) * step

        return float(lot)

    # ==========================================================
    # 🔰 MODIFY POSITION
    # ==========================================================
    def _modify_position(self, ticket, sl, tp):

        info = mt5.symbol_info(self.symbol)
        tick = mt5.symbol_info_tick(self.symbol)

        if info is None or tick is None:
            return

        current_price = tick.bid if tick.bid else tick.ask

        # 🔥 BTC: jarak minimal lebih besar
        min_distance = (120 if self.is_crypto else 50) * info.point

        if abs(current_price - sl) < min_distance:
            return

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl,
            "tp": tp
        }

        mt5.order_send(request)

    # ==========================================================
    # 🔰 CLOSE POSITION
    # ==========================================================
    def _close_position(self, ticket, volume):

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False

        pos = position[0]

        order_type = (
            mt5.ORDER_TYPE_SELL
            if pos.type == mt5.ORDER_TYPE_BUY
            else mt5.ORDER_TYPE_BUY
        )

        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return False

        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    # ==========================================================
    # 🔥 EXIT INTELLIGENCE (MULTI POSITION SAFE)
    # ==========================================================
    def manage_open_positions(self):
        """
        🔥 MANDAT:
        Harus bisa handle hingga 3 posisi TANPA konflik

        CARA KERJA:
        - Loop semua posisi
        - Setiap posisi diproses independen
        - State (tp1_done) berdasarkan ticket → tidak bentrok
        """

        positions = mt5.positions_get(symbol=self.symbol)
        if not positions:
            return

        info = mt5.symbol_info(self.symbol)
        point = info.point

        atr = self.calculate_atr()
        if atr is None:
            return

        multiplier = 2.0 if self.is_crypto else 1.2
        trailing_distance = atr * multiplier

        for pos in positions:

            ticket = pos.ticket
            entry = pos.price_open
            price = pos.price_current
            sl = pos.sl if pos.sl != 0 else entry
            tp = pos.tp
            volume = pos.volume

            # ================= BUY =================
            if pos.type == mt5.ORDER_TYPE_BUY:

                risk = abs(entry - sl)
                tp1 = entry + risk

                if tp > 0 and price >= tp:
                    self._close_position(ticket, volume)
                    continue

                if price >= tp1:

                    # 🔥 SETIAP POSISI DIHANDLE TERPISAH
                    if ticket not in self.tp1_done:
                        half = volume / 2
                        if half >= info.volume_min:
                            if self._close_position(ticket, half):
                                self.tp1_done[ticket] = True

                    raw_sl = max(
                        sl,
                        entry + (self.bep_plus_points * point),
                        price - trailing_distance
                    )

                    new_sl = self.get_safe_sl(entry, raw_sl, True)

                    if new_sl > sl:
                        self._modify_position(ticket, new_sl, tp)

                elif price > entry:

                    raw_sl = entry + (self.bep_plus_points * point)
                    new_sl = self.get_safe_sl(entry, raw_sl, True)

                    if (price - entry) >= atr and sl < entry:
                        self._modify_position(ticket, new_sl, tp)

            # ================= SELL =================
            elif pos.type == mt5.ORDER_TYPE_SELL:

                risk = abs(entry - sl)
                tp1 = entry - risk

                if tp > 0 and price <= tp:
                    self._close_position(ticket, volume)
                    continue

                if price <= tp1:

                    if ticket not in self.tp1_done:
                        half = volume / 2
                        if half >= info.volume_min:
                            if self._close_position(ticket, half):
                                self.tp1_done[ticket] = True

                    raw_sl = min(
                        sl,
                        entry - (self.bep_plus_points * point),
                        price + trailing_distance
                    )

                    new_sl = self.get_safe_sl(entry, raw_sl, False)

                    if new_sl < sl:
                        self._modify_position(ticket, new_sl, tp)

                elif price < entry:

                    raw_sl = entry - (self.bep_plus_points * point)
                    new_sl = self.get_safe_sl(entry, raw_sl, False)

                    if abs(entry - price) >= atr and sl > entry:
                        self._modify_position(ticket, new_sl, tp)

    # ==========================================================
    # 🔁 ALIAS (SYNC MAIN.PY)
    # ==========================================================
    def apply_tp1_tp2_logic(self):
        return self.manage_open_positions()
