import time

class HFTRiskGuard:
    """
    Sub-10 microsecond safety filter for HFT execution.
    Instantly blocks orders that violate portfolio limits, drawdown rules, or velocity limits.
    """
    def __init__(self, max_position=10.0, max_drawdown=0.02, max_trades_per_sec=20, base_vix=20.0, base_volatility=0.05):
        self.base_max_position = max_position
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.max_trades_per_sec = max_trades_per_sec
        
        self.peak_equity = 100000.0  # $100k starting equity
        self.current_equity = 100000.0
        self.current_position = 0.0
        
        # Volatility tracking
        self.base_vix = base_vix
        self.base_volatility = base_volatility
        self.current_vix = base_vix
        self.current_volatility = base_volatility
        self.current_kelly_fraction = 1.0

        # Velocity tracking
        self.trade_timestamps = []
        print(f"[RISK] Safety Guard Active. Drawdown limit: {self.max_drawdown*100}% | Base Max Position: {self.base_max_position} BTC")

    def update_portfolio(self, current_equity, current_position):
        self.current_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        self.current_position = current_position

    def update_volatility(self, current_vix, current_volatility):
        """
        Update the current VIX and asset volatility to dynamically adjust risk limits.
        """
        self.current_vix = current_vix
        self.current_volatility = current_volatility
        self._recalculate_limits()

    def update_dynamic_limits(self, win_prob, win_loss_ratio):
        """
        Dynamically adjusts position size limits based on the Kelly Criterion.
        win_prob: Expected probability of a winning trade (0 to 1).
        win_loss_ratio: Ratio of average win to average loss.
        """
        if win_loss_ratio > 0:
            kelly_fraction = win_prob - ((1 - win_prob) / win_loss_ratio)
        else:
            kelly_fraction = 0

        # Ensure kelly fraction is non-negative and doesn't exceed 1.0 (Full Kelly is risky, often use Half Kelly)
        self.current_kelly_fraction = max(0.0, min(1.0, kelly_fraction))
        self._recalculate_limits()
        return self.max_position

    def _recalculate_limits(self):
        """
        Recalculates the max position based on volatility limits and Kelly criterion.
        If volatility spikes, we reduce the max position size.
        """
        # Volatility penalty: if VIX or local vol increases, max pos decreases
        vix_ratio = self.current_vix / self.base_vix
        vol_ratio = self.current_volatility / self.base_volatility

        # Use the worst case volatility spike (max of the two ratios)
        vol_penalty = max(1.0, max(vix_ratio, vol_ratio))

        vol_adjusted_limit = self.base_max_position / vol_penalty

        self.max_position = vol_adjusted_limit * self.current_kelly_fraction
        return self.max_position

    def check_safety(self, order_side, order_qty):
        """
        Fast risk evaluation path. Must execute in microseconds.
        """
        start_time = time.perf_counter()
        now = time.time()
        
        # 1. Drawdown Check
        current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        if current_drawdown > self.max_drawdown:
            return False, f"ABORT: Maximum drawdown limit exceeded! ({current_drawdown*100:.2f}%)", 0.0
            
        # 2. Position Limit Check
        potential_pos = self.current_position + (order_qty if order_side.upper() == "BUY" else -order_qty)
        if abs(potential_pos) > self.max_position:
            return False, f"ABORT: Maximum position size exceeded! (Limit: {self.max_position} | Target: {abs(potential_pos):.2f})", 0.0
            
        # 3. Trade Velocity (Spam Protection)
        self.trade_timestamps = [t for t in self.trade_timestamps if now - t < 1.0]
        if len(self.trade_timestamps) >= self.max_trades_per_sec:
            return False, f"ABORT: Order rate limit exceeded! ({len(self.trade_timestamps)} trades/sec)", 0.0
            
        self.trade_timestamps.append(now)
        check_time_us = (time.perf_counter() - start_time) * 1_000_000.0
        
        return True, "SAFE", check_time_us

if __name__ == "__main__":
    guard = HFTRiskGuard()
    
    # Scenario 1: Safe normal order
    safe, msg, latency = guard.check_safety("BUY", 1.5)
    print(f"[RISK] Check 1: {msg} | Latency: {latency:.2f} microseconds")
    
    # Scenario 2: Giant order (Violates Position size)
    safe, msg, latency = guard.check_safety("BUY", 15.0)
    print(f"[RISK] Check 2: {msg} | Latency: {latency:.2f} microseconds")
    
    # Scenario 3: Massive Drawdown
    guard.update_portfolio(current_equity=97000.0, current_position=1.5)  # Drop to $97k (3% drawdown)
    safe, msg, latency = guard.check_safety("BUY", 0.5)
    print(f"[RISK] Check 3: {msg} | Latency: {latency:.2f} microseconds")
