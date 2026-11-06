"""Risk manager � position sizing + daily loss."""
from __future__ import annotations
from datetime import datetime
import config


class RiskManager:
    def __init__(self, equity: float):
        self.equity_start_day = equity
        self.equity = equity
        self.day = datetime.utcnow().date()
        self.daily_limit_alerted = False

    def _reset_daily(self):
        today = datetime.utcnow().date()
        if today != self.day:
            self.day = today
            self.equity_start_day = self.equity
            self.daily_limit_alerted = False

    def daily_loss_exceeded(self) -> bool:
        self._reset_daily()
        if self.equity_start_day <= 0:
            return False
        loss = (self.equity_start_day - self.equity) / self.equity_start_day
        return loss >= config.MAX_DAILY_LOSS

    def should_alert_daily_limit(self) -> bool:
        if not self.daily_loss_exceeded() or self.daily_limit_alerted:
            return False
        self.daily_limit_alerted = True
        return True

    def position_size(self, entry_price: float, atr: float) -> float:
        if entry_price <= 0 or atr <= 0:
            return 0.0
        risk_amount = self.equity * config.RISK_PER_TRADE
        sl_distance = atr * config.ATR_SL_MULT
        qty_by_risk = risk_amount / sl_distance if sl_distance > 0 else 0.0
        max_margin = self.equity * config.MAX_POSITION_PCT
        max_notional = max_margin * config.LEVERAGE
        qty_by_margin = max_notional / entry_price
        return min(qty_by_risk, qty_by_margin)

    def sl_tp(self, entry_price: float, atr: float, side: str = "LONG"):
        if side == "LONG":
            sl = entry_price - atr * config.ATR_SL_MULT
            tp = entry_price + atr * config.ATR_TP_MULT
        else:
            sl = entry_price + atr * config.ATR_SL_MULT
            tp = entry_price - atr * config.ATR_TP_MULT
        return sl, tp

    def update_equity(self, eq: float):
        self.equity = eq


if __name__ == "__main__":
    rm = RiskManager(equity=5000)
    qty = rm.position_size(entry_price=78000, atr=500)
    print(f"? position_size: qty={qty:.6f}")
    assert 0.03 < qty < 0.05

    sl, tp = rm.sl_tp(78000, 500, "LONG")
    assert sl == 78000 - 750
    assert tp == 78000 + 1500
    print(f"? SL={sl}, TP={tp}")

    rm.update_equity(5000)
    assert not rm.daily_loss_exceeded()
    rm.update_equity(5000 * 0.96)
    assert rm.daily_loss_exceeded()
    print(f"? Daily loss OK")

    assert rm.should_alert_daily_limit() is True
    assert rm.should_alert_daily_limit() is False
    print(f"? Alert-once OK")

    print("\n?? Semua test risk PASS")
