# ==========================================================
# 🛡️ ART RISK ENGINE - PROTOKOL KO-EKSISTENSI (v6.1)
# ==========================================================
# Identitas: ART-Agent | Magic: 888001
# Fokus: Isolasi Manajemen & Proteksi Shared Equity
# ==========================================================

import MetaTrader5 as mt5

class RiskEngine:
    def __init__(
        self,
        symbol="BTCUSDc",
        magic_number=888001,  # 🆔 Magic Number ART
        risk_per_trade=15.0,
        max_daily_risk=500.0,
        min_equity_threshold=2500.0,
        max_spread_points=2000,
        max_positions_total=5, # 🛡️ Limit Global ART
    ):
        self.symbol = symbol
        self.magic_number = magic_number
        self.comment = "ART-Agent"
        
        # 🔰 RISK SETTINGS
        self.max_risk_per_trade = risk_per_trade
        self.max_daily_risk = max_daily_risk
        self.min_equity_threshold = min_equity_threshold
        self.max_positions_total = max_positions_total
        self.max_spread_points = max_spread_points

        # 🔰 STATE MANAGEMENT
        self.tp1_done = {}
        self.bep_plus_points = 50  # BE+ dikit untuk cover biaya
        self.is_metal = self.symbol in ["XAUUSDc", "XAGUSDc"]

    def can_trade(self):
        """Mengecek kelayakan trade berdasarkan Protokol Shared Equity."""
        account = mt5.account_info()
        if account is None:
            return False

        # 1. Cek Shared Equity (Batas aman akun)
        if account.equity < self.min_equity_threshold:
            print(f"[{self.comment}] ⚠️ Equity rendah, tunda eksekusi.")
            return False

        # 2. Cek Margin Level (Shared Awareness)
        if account.margin_level < 500.0:
            print(f"[{self.comment}] ⚠️ Margin Level kritis ({account.margin_level}%), tunda eksekusi.")
            return False

        # 3. Cek Jumlah Posisi Khusus ART (Magic Number Filter)
        positions = mt5.positions_get(group=f"*{self.symbol}*")
        art_positions = [p for p in positions if p.magic == self.magic_number]
        
        if len(art_positions) >= 1: # One Pair, One Trade Rule
            return False

        return True

    def manage_open_positions(self, current_atr=None):
        """Manajemen posisi dengan ISOLASI KETAT (Hanya urus Magic 888001)."""
        positions = mt5.positions_get()
        if not positions:
            return

        for pos in positions:
            # 🛡️ FILTER ISOLASI: Abaikan jika bukan milik ART
            if pos.magic != self.magic_number:
                continue

            ticket = pos.ticket
            symbol = pos.symbol
            volume = pos.volume
            entry = pos.price_open
            sl = pos.sl
            tp = pos.tp
            price = mt5.symbol_info_tick(symbol).ask if pos.type == mt5.POSITION_TYPE_SELL else mt5.symbol_info_tick(symbol).bid
            point = mt5.symbol_info(symbol).point
            
            # Setup Jarak Trailing & BE
            atr = current_atr if current_atr else 100 * point
            # Metal Multiplier untuk XAU/XAG agar tidak gampang terjilat
            multiplier = 3.0 if symbol in ["XAUUSDc", "XAGUSDc"] else 1.5
            trailing_distance = atr * multiplier

            # 🟢 LOGIKA BUY
            if pos.type == mt5.POSITION_TYPE_BUY:
                risk = abs(entry - sl)
                # TP1 Nearest: RR 1:1
                tp1 = entry + risk

                # Pemicu Break Even (BE)
                if price >= tp1:
                    # Anti-Spam Lot 0.01: Tidak ada partial close
                    raw_sl = max(sl, entry + (self.bep_plus_points * point), price - trailing_distance)
                    
                    if raw_sl > sl:
                        self._modify_sl(ticket, raw_sl, tp)

            # 🔴 LOGIKA SELL
            elif pos.type == mt5.POSITION_TYPE_SELL:
                risk = abs(entry - sl)
                tp1 = entry - risk

                if price <= tp1:
                    raw_sl = min(sl, entry - (self.bep_plus_points * point), price + trailing_distance)
                    
                    if raw_sl < sl or sl == 0:
                        self._modify_sl(ticket, raw_sl, tp)

    def _modify_sl(self, ticket, new_sl, tp):
        """Kirim instruksi modifikasi ke MT5."""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": tp,
        }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[{self.comment}] ✅ SL Modified for #{ticket}")
        return result
