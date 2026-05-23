import math
import statistics

class PortfolioHeatMonitor:
    def __init__(self, max_heat=0.8, window=20):
        self.max_heat = max_heat
        self.window = window
        self.returns = []

    def update(self, returns: list[float]):
        """Speichert letzte `window` Werte"""
        if self.window > 0:
            self.returns = returns[-self.window:]
        else:
            self.returns = []
        return self

    def get_heat(self) -> float:
        """
        Pearson-Korrelation der Returns zu sich selbst (0.0–1.0, normiert)
        Formel: heat = abs(mean(returns)) / (stdev(returns) + 1e-9), geclippt auf [0,1]
        """
        if len(self.returns) < 2:
            return 0.0

        mean_val = statistics.mean(self.returns)
        stdev_val = statistics.stdev(self.returns)

        heat = abs(mean_val) / (stdev_val + 1e-9)
        return max(0.0, min(1.0, heat))

    def is_safe_to_add(self, new_return: float) -> bool:
        """True wenn get_heat() < max_heat"""
        return self.get_heat() < self.max_heat
