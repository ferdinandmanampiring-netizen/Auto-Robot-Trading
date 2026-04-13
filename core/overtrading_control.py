import MetaTrader5 as mt5
from datetime import datetime, time

class SmartQuota:
    def __init__(self, daily_limit=500):
        self.daily_limit = daily_limit

    def get_daily_pnl(self):
        """Menghitung total profit/loss hari ini dalam Cent."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        history = mt5.history_deals_get(today, datetime.now())
        
        if history is None or len(history) == 0:
            return 0.0
            
        total_pnl = sum(deal.profit + deal.commission + deal.swap for deal in history)
        return total_pnl

    def is_allowed_to_trade(self):
        current_pnl = self.get_daily_pnl()
        
        # Logika Smart Quota:
        # Jika rugi sudah mencapai daily_limit (misal -500), STOP.
        if current_pnl <= -self.daily_limit:
            print(f"🛑 [SMART QUOTA] Limit tercapai ({current_pnl}). Robot istirahat.")
            return False
            
        print(f"✅ [SMART QUOTA] Current PnL: {current_pnl} Cents. Sisa jatah aman.")
        return True
