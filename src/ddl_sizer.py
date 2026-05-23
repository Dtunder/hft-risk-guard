DDL_STAGES = [
    {"min_capital": 0,      "max_capital": 250,    "risk_pct": 0.020, "max_leverage": 1.0},
    {"min_capital": 250,    "max_capital": 1000,   "risk_pct": 0.020, "max_leverage": 1.5},
    {"min_capital": 1000,   "max_capital": 5000,   "risk_pct": 0.015, "max_leverage": 2.0},
    {"min_capital": 5000,   "max_capital": 15000,  "risk_pct": 0.010, "max_leverage": 3.0},
    {"min_capital": 15000,  "max_capital": 999999, "risk_pct": 0.005, "max_leverage": 3.0},
]

class DDLPositionSizer:
    def __init__(self, target_capital=50000.0):
        self.target_capital = target_capital

    def get_stage(self, capital: float) -> dict:
        for stage in DDL_STAGES:
            if stage["min_capital"] <= capital < stage["max_capital"]:
                return stage
        return DDL_STAGES[-1]

    def get_position_size(self, capital: float, price: float, stop_loss_pct: float = 0.01, signal_confidence: float = 1.0) -> dict:
        stage = self.get_stage(capital)
        risk_amount = capital * stage["risk_pct"] * signal_confidence
        position_value = risk_amount / stop_loss_pct
        qty = position_value / price
        leverage = stage["max_leverage"]
        effective_qty = qty * leverage

        return {
            "qty": round(qty, 6),
            "effective_qty": round(effective_qty, 6),
            "leverage": leverage,
            "risk_amount": round(risk_amount, 4),
            "stage": stage,
            "progress_pct": round(capital / self.target_capital * 100, 2)
        }

    def get_progress_report(self, capital: float) -> str:
        stage = self.get_stage(capital)
        stage_num = DDL_STAGES.index(stage) + 1
        progress_pct = round(capital / self.target_capital * 100, 2)
        next_threshold = stage["max_capital"] if stage != DDL_STAGES[-1] else "None (Max Stage)"

        return (f"Capital: ${capital} (Stage {stage_num})\n"
                f"Progress toward ${self.target_capital} goal: {progress_pct}%\n"
                f"Next stage threshold: ${next_threshold}")

if __name__ == "__main__":
    sizer = DDLPositionSizer()
    capitals = [50, 300, 1500, 8000, 20000]
    price = 58000
    stop_loss_pct = 0.01

    for cap in capitals:
        print(f"--- Testing Capital: ${cap} ---")
        print(sizer.get_progress_report(cap))
        pos_size = sizer.get_position_size(cap, price, stop_loss_pct=stop_loss_pct)
        print("Position Size Details:")
        for k, v in pos_size.items():
            print(f"  {k}: {v}")
        print()
