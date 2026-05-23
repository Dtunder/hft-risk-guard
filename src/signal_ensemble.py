import collections
import random
import requests

class OBISignal:
    def __init__(self, obi_threshold=0.75, momentum_window=3):
        self.obi_threshold = obi_threshold
        self.momentum_window = momentum_window
        self.history = collections.deque(maxlen=momentum_window)

    def check_signals(self, bid_depth, ask_depth):
        bid_vol = sum(vol for _, vol in bid_depth)
        ask_vol = sum(vol for _, vol in ask_depth)

        if bid_vol + ask_vol == 0:
            return "HOLD", 0.0

        obi = (bid_vol - ask_vol) / (bid_vol + ask_vol)
        self.history.append(obi)

        if len(self.history) < self.momentum_window:
            return "HOLD", obi

        is_sustained_buy = all(x > self.obi_threshold for x in self.history)
        is_sustained_sell = all(x < -self.obi_threshold for x in self.history)

        if is_sustained_buy:
            return "LONG", obi
        elif is_sustained_sell:
            return "SHORT", obi
        elif abs(obi) > self.obi_threshold:
            return "HOLD (Fake OBI Spike)", obi

        return "HOLD", obi

class VWAPSignal:
    def __init__(self, window=100, buy_dev=-0.003, sell_dev=0.003):
        self.window = window
        self.buy_dev = buy_dev
        self.sell_dev = sell_dev
        self.trades = collections.deque(maxlen=window)
        self.total_vol = 0.0
        self.total_pv = 0.0

    def add_trade(self, price, volume):
        if len(self.trades) == self.window:
            old_p, old_v = self.trades.popleft()
            self.total_vol -= old_v
            self.total_pv -= old_p * old_v

        self.trades.append((price, volume))
        self.total_vol += volume
        self.total_pv += price * volume

    def get_signal(self, current_price):
        if self.total_vol == 0:
            return "NEUTRAL", 0.0

        vwap = self.total_pv / self.total_vol
        dev = (current_price - vwap) / vwap

        if dev < self.buy_dev:
            return "BUY", dev
        elif dev > self.sell_dev:
            return "SELL", dev

        return "NEUTRAL", dev

class FundingSignal:
    def __init__(self, long_threshold=-0.0005, short_threshold=0.0010):
        self.long_threshold = long_threshold
        self.short_threshold = short_threshold
        self.session = requests.Session()

    def get_signal(self, symbol="BTCUSDT"):
        try:
            url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
            response = self.session.get(url, timeout=2)
            response.raise_for_status()
            data = response.json()
            rate = float(data['lastFundingRate'])

            if rate < self.long_threshold:
                return "LONG", rate
            elif rate > self.short_threshold:
                return "SHORT", rate

            return "NEUTRAL", rate
        except Exception:
            return "NEUTRAL", 0.0

class SignalEnsemble:
    def __init__(self, symbol="BTCUSDT", obi_threshold=0.75, vwap_window=100, required_votes=2):
        self.symbol = symbol
        self.required_votes = required_votes
        self.obi = OBISignal(obi_threshold)
        self.vwap = VWAPSignal(window=vwap_window)
        self.funding = FundingSignal()
        self.signal_history = collections.deque(maxlen=50)

    def update_vwap(self, price: float, volume: float):
        self.vwap.add_trade(price, volume)

    def get_signal(self, bid_depth: list, ask_depth: list, current_price: float) -> dict:
        obi_signal, obi_val = self.obi.check_signals(bid_depth, ask_depth)
        vwap_signal, vwap_dev = self.vwap.get_signal(current_price)
        fund_signal, fund_rate = self.funding.get_signal(self.symbol)

        # Normalize signals
        obi_norm = "NEUTRAL"
        if obi_signal == "LONG": obi_norm = "BUY"
        elif obi_signal == "SHORT": obi_norm = "SELL"

        vwap_norm = "NEUTRAL"
        if vwap_signal == "BUY": vwap_norm = "BUY"
        elif vwap_signal == "SELL": vwap_norm = "SELL"

        fund_norm = "NEUTRAL"
        if fund_signal == "LONG": fund_norm = "BUY"
        elif fund_signal == "SHORT": fund_norm = "SELL"

        votes = [obi_norm, vwap_norm, fund_norm]
        buy_votes = sum(1 for v in votes if v == "BUY")
        sell_votes = sum(1 for v in votes if v == "SELL")
        neutral_votes = sum(1 for v in votes if v == "NEUTRAL")

        if buy_votes >= self.required_votes:
            final = "BUY"
            confidence = buy_votes / 3
        elif sell_votes >= self.required_votes:
            final = "SELL"
            confidence = sell_votes / 3
        else:
            final = "HOLD"
            confidence = 0.0

        self.signal_history.append(final)

        return {
            "signal": final,
            "confidence": round(confidence, 4),
            "votes": {"buy": buy_votes, "sell": sell_votes, "neutral": neutral_votes},
            "components": {
                "obi": obi_signal, "obi_val": obi_val,
                "vwap": vwap_signal, "vwap_dev": vwap_dev,
                "funding": fund_signal, "funding_rate": fund_rate
            }
        }

if __name__ == "__main__":
    ensemble = SignalEnsemble("BTCUSDT")
    base_price = 58000.0

    print(f"Testing SignalEnsemble for {ensemble.symbol}")
    print("-" * 60)

    for i in range(10):
        # Generate fake data
        current_price = base_price + random.uniform(-100, 100)
        volume = random.uniform(0.1, 2.0)

        # Fake order book with varying imbalance
        bid_vol = random.uniform(5.0, 50.0)
        ask_vol = random.uniform(5.0, 50.0)

        # Force some momentum to test OBI
        if i >= 3 and i < 6:
            bid_vol = 100.0
            ask_vol = 5.0
            current_price -= random.uniform(100, 300) # Force VWAP deviation down (buy signal)

        bid_depth = [(current_price - j, bid_vol / 5) for j in range(1, 6)]
        ask_depth = [(current_price + j, ask_vol / 5) for j in range(1, 6)]

        ensemble.update_vwap(current_price, volume)
        result = ensemble.get_signal(bid_depth, ask_depth, current_price)

        print(f"Tick {i+1} | Price: {current_price:.2f}")
        print(f"Result: {result}")
        print("-" * 60)
