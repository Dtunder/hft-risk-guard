import math
import random

class PortfolioHeatMonitor:
    def __init__(self, max_heat: float = 0.8, lookback: int = 20):
        self.max_heat = max_heat
        self.lookback = lookback
        self.prices = {}

    def update_prices(self, symbol: str, price: float):
        if symbol not in self.prices:
            self.prices[symbol] = []
        self.prices[symbol].append(price)
        if len(self.prices[symbol]) > self.lookback + 1:
            self.prices[symbol] = self.prices[symbol][-(self.lookback + 1):]

    def _get_returns(self, symbol: str) -> list[float]:
        p = self.prices.get(symbol, [])
        if len(p) < 2:
            return []
        return [(p[i] / p[i-1]) - 1.0 for i in range(1, len(p))]

    def get_correlation(self, sym_a: str, sym_b: str) -> float:
        ret_a = self._get_returns(sym_a)
        ret_b = self._get_returns(sym_b)

        n = min(len(ret_a), len(ret_b))
        if n < 2:
            return 0.0

        ret_a = ret_a[-n:]
        ret_b = ret_b[-n:]

        mean_a = sum(ret_a) / n
        mean_b = sum(ret_b) / n

        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(ret_a, ret_b))
        var_a = sum((a - mean_a) ** 2 for a in ret_a)
        var_b = sum((b - mean_b) ** 2 for b in ret_b)

        if var_a == 0.0 or var_b == 0.0:
            return 0.0

        return cov / math.sqrt(var_a * var_b)

    def get_portfolio_heat(self, positions: dict) -> float:
        symbols = list(positions.keys())
        if len(symbols) < 2:
            return 0.0

        total_corr = 0.0
        weight_sum = 0.0

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                sym_a = symbols[i]
                sym_b = symbols[j]
                w_a = positions[sym_a]
                w_b = positions[sym_b]
                corr = self.get_correlation(sym_a, sym_b)
                pair_weight = w_a * w_b

                total_corr += corr * pair_weight
                weight_sum += pair_weight

        if weight_sum == 0.0:
            return 0.0

        return total_corr / weight_sum

    def is_safe_to_add(self, symbol: str, positions: dict) -> tuple:
        new_positions = dict(positions)
        if symbol not in new_positions:
            avg_weight = sum(positions.values()) / len(positions) if positions else 1.0
            new_positions[symbol] = avg_weight

        heat = self.get_portfolio_heat(new_positions)
        return heat <= self.max_heat, heat

if __name__ == "__main__":
    monitor = PortfolioHeatMonitor(max_heat=0.8, lookback=20)

    btc = 60000.0
    eth = 3000.0
    sol = 100.0

    # 30 Ticks simulieren
    for _ in range(30):
        # Mache BTC und ETH sehr stark korreliert, SOL weniger
        market = random.uniform(-0.01, 0.01)
        btc *= 1 + market + random.uniform(-0.002, 0.002)
        eth *= 1 + market + random.uniform(-0.003, 0.003)
        sol *= 1 + market * 0.2 + random.uniform(-0.015, 0.015)

        monitor.update_prices("BTC", btc)
        monitor.update_prices("ETH", eth)
        monitor.update_prices("SOL", sol)

    print(f"Korrelation BTC-ETH: {monitor.get_correlation('BTC', 'ETH'):.3f}")
    print(f"Korrelation BTC-SOL: {monitor.get_correlation('BTC', 'SOL'):.3f}")
    print(f"Korrelation ETH-SOL: {monitor.get_correlation('ETH', 'SOL'):.3f}")

    positions = {"BTC": 0.5, "ETH": 0.5}
    heat = monitor.get_portfolio_heat(positions)
    print(f"Portfolio Heat (BTC + ETH): {heat:.3f}")

    safe, new_heat = monitor.is_safe_to_add("SOL", positions)
    print(f"Safe to add SOL? {safe} (Heat: {new_heat:.3f})")
