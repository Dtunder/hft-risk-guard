import time
import datetime

class HFTRiskGuard:
    """
    Sub-10 microsecond safety filter for HFT execution.
    Instantly blocks orders that violate portfolio limits, drawdown rules, or velocity limits.
    """
    def __init__(self, max_position=10.0, max_drawdown=0.02, max_trades_per_sec=20, daily_loss_limit=0.05):
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.max_trades_per_sec = max_trades_per_sec
        self.daily_loss_limit = daily_loss_limit
        
        self.peak_equity = 100000.0  # $100k starting equity
        self.current_equity = 100000.0
        self.current_position = 0.0
        
        self.daily_start_equity = self.current_equity
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = ""
        self.last_reset_date = None

        # Velocity tracking
        self.trade_timestamps = []
        print("[RISK] Safety Guard Active. Drawdown limit: 2% | Max Position: 10 BTC")

    def reset_daily_tracking(self):
        self.daily_start_equity = self.current_equity
        self.last_reset_date = datetime.date.today().isoformat()
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = ""
        print("[RISK] Daily tracking reset.")

    def check_daily_reset(self):
        today = datetime.date.today().isoformat()
        if self.last_reset_date is None or self.last_reset_date != today:
            self.reset_daily_tracking()

    def update_portfolio(self, current_equity, current_position):
        self.current_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        self.current_position = current_position

    def check_safety(self, order_side, order_qty):
        """
        Fast risk evaluation path. Must execute in microseconds.
        """
        self.check_daily_reset()
        if self.circuit_breaker_active:
            return False, f"ABORT: Circuit breaker active — {self.circuit_breaker_reason}", 0.0

        start_time = time.perf_counter()
        now = time.time()
        
        # 1. Drawdown Check
        current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        if current_drawdown > self.max_drawdown:
            return False, f"ABORT: Maximum drawdown limit exceeded! ({current_drawdown*100:.2f}%)", 0.0
            
        # 1.5. Daily Loss Check
        daily_loss = (self.daily_start_equity - self.current_equity) / self.daily_start_equity
        if daily_loss > self.daily_loss_limit:
            self.circuit_breaker_active = True
            self.circuit_breaker_reason = f"Daily loss limit {self.daily_loss_limit*100:.1f}% breached"
            return False, f"ABORT: {self.circuit_breaker_reason}", 0.0

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

    # Scenario 6: Simulate daily loss
    guard.max_drawdown = 0.10  # Temporarily increase max drawdown to test daily loss limit
    guard.update_portfolio(current_equity=94000.0, current_position=1.5) # Drop to $94k (6% daily loss if start is $100k)
    safe, msg, latency = guard.check_safety("BUY", 1.0)
    print(f"[RISK] Check 6: {msg} | Latency: {latency:.2f} microseconds")
