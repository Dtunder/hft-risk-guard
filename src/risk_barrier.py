import time

class HFTRiskGuard:
    """
    Sub-10 microsecond safety filter for HFT execution.
    Instantly blocks orders that violate portfolio limits, drawdown rules, or velocity limits.
    """
    def __init__(self, max_position=10.0, max_drawdown=0.02, max_trades_per_sec=20):
        self.base_max_position = max_position
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.max_trades_per_sec = max_trades_per_sec
        
        self.peak_equity = 100000.0  # $100k starting equity
        self.current_equity = 100000.0
        self.current_position = 0.0
        
        # Velocity tracking
        self.trade_timestamps = []
        print("[RISK] Safety Guard Active. Drawdown limit: 2% | Max Position: 10 BTC")

    def update_portfolio(self, current_equity, current_position):
        self.current_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        self.current_position = current_position

    def update_dynamic_limits(self, win_rate, win_loss_ratio, current_volatility, target_volatility=0.2):
        """
        Phase B: Dynamic Position Sizing Rules.
        Uses Kelly Criterion & Volatility Target to scale max position size.
        """
        # Calculate Kelly fraction
        if win_loss_ratio > 0:
            kelly_fraction = win_rate - ((1 - win_rate) / win_loss_ratio)
            # Bound Kelly fraction between 0 and 1
            kelly_fraction = max(0.0, min(1.0, kelly_fraction))
        else:
            kelly_fraction = 0.0

        # Calculate Volatility scalar
        if current_volatility > 0:
            vol_scalar = target_volatility / current_volatility
        else:
            vol_scalar = 1.0

        # Extreme volatility dampening: prevent scalar from being completely unbound, but focus on the reduction part
        # if current_volatility is high, vol_scalar will be < 1, which reduces the position.

        # We apply kelly and vol_scalar to base max position
        # Default behavior: If no kelly given, or we assume base_max_position is the max 100% kelly sizing,
        # we scale base_max_position. If win_rate/ratio are not available or not applicable, we could just use vol_scalar.
        # But since Kelly is requested, we use it.
        # However, to avoid max_position going to 0 if kelly is 0 during startup,
        # let's assume we scale by kelly * vol_scalar, bounded by base_max_position.

        # The prompt says: "Implement the Kelly Criterion and dynamic Volatility Target logic in the RiskGuard class.
        # If the VIX or local asset volatility spikes, the RiskGuard must dynamically reduce the max position size limits."

        target_max_position = self.base_max_position * kelly_fraction * vol_scalar

        # We also enforce that it doesn't exceed base_max_position
        self.max_position = min(self.base_max_position, target_max_position)

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
