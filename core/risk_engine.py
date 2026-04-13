import MetaTrader5 as mt5


class RiskEngine:

    def __init__(self, max_positions_total=5):
        self.max_positions_total = max_positions_total

    # ==========================================================
    # 🔥 CAN TRADE
    # ==========================================================
    def can_trade(self, symbol):

        all_positions = mt5.positions_get()

        if all_positions and len(all_positions) >= self.max_positions_total:
            return False, "Max global positions"

        pair_positions = mt5.positions_get(symbol=symbol)

        if pair_positions:
            return False, "Pair already active"

        return True, "OK"

    # ==========================================================
    # 🔥 EXIT MANAGEMENT (MANDAT FINAL)
    # ==========================================================
    def manage_open_positions(self):

        positions = mt5.positions_get()
        if not positions:
            return

        for pos in positions:

            symbol = pos.symbol
            ticket = pos.ticket
            entry = pos.price_open
            price = pos.price_current
            sl = pos.sl

            symbol_info = mt5.symbol_info(symbol)
            point = symbol_info.point

            risk = abs(entry - sl)

            # ==================================================
            # 🔥 BREAK EVEN
            # ==================================================
            if pos.type == mt5.ORDER_TYPE_BUY:
                if price >= entry + (risk * 0.5):
                    new_sl = entry + (10 * point)

                    if new_sl > sl:
                        self.modify_sl(ticket, new_sl)

            else:
                if price <= entry - (risk * 0.5):
                    new_sl = entry - (10 * point)

                    if new_sl < sl:
                        self.modify_sl(ticket, new_sl)

            # ==================================================
            # 🔥 TRAILING (AGGRESSIVE BTC)
            # ==================================================
            trail = 100 * point if "BTC" in symbol else 30 * point

            if pos.type == mt5.ORDER_TYPE_BUY:
                new_sl = price - trail
                if new_sl > sl:
                    self.modify_sl(ticket, new_sl)

            else:
                new_sl = price + trail
                if new_sl < sl:
                    self.modify_sl(ticket, new_sl)

    # ==========================================================
    # 🔧 MODIFY SL
    # ==========================================================
    def modify_sl(self, ticket, sl):

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl,
        }

        mt5.order_send(request)
