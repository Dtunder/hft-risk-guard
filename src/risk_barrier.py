import time
import datetime

class HFTRiskGuard:
    """
    Sub-10 microsecond safety filter for HFT execution.
    Instantly blocks orders that violate portfolio limits, drawdown rules, or velocity limits.
    """
    def __init__(self, max_position=2.0, max_drawdown=0.03, max_trades_per_sec=10):
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.max_trades_per_sec = max_trades_per_sec
        self.daily_loss_limit = max_drawdown
        
        self.peak_equity = 100000.0  # $100k starting equity
        self.current_equity = 100000.0
        self.current_position = 0.0
        
        self.daily_start_equity = self.current_equity
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = ""
        self.last_reset_date = datetime.date.today().isoformat()

        # Velocity tracking
        self.trade_timestamps = []

        self.stop_price = None
        self.trailing_stop_pct = 0.0035 # 0.35%
        self.last_price = None

    def reset_daily_tracking(self):
        self.daily_start_equity = self.current_equity
        self.last_reset_date = datetime.date.today().isoformat()
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = ""
        return self

    def check_daily_reset(self):
        today = datetime.date.today().isoformat()
        if self.last_reset_date is None or self.last_reset_date != today:
            self.reset_daily_tracking()
        return self

    def update_portfolio(self, current_equity, current_position):
        self.current_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if current_position == 0.0:
            self.stop_price = None
        elif self.current_position == 0.0 and current_position != 0.0 and self.last_price is not None:
            if current_position > 0:
                self.stop_price = self.last_price * (1.0 - self.trailing_stop_pct)
            else:
                self.stop_price = self.last_price * (1.0 + self.trailing_stop_pct)

        self.current_position = current_position
        return self

    def update_tick(self, price: float):
        """Updates trailing stop loss every tick."""
        self.last_price = price
        if self.current_position > 0:
            # Trailing stop for long position
            new_stop = price * (1.0 - self.trailing_stop_pct)
            if self.stop_price is None or new_stop > self.stop_price:
                self.stop_price = new_stop
        elif self.current_position < 0:
            # Trailing stop for short position
            new_stop = price * (1.0 + self.trailing_stop_pct)
            if self.stop_price is None or new_stop < self.stop_price:
                self.stop_price = new_stop
        return self

    def get_ddl_limits(self, capital: float) -> tuple[int, float]:
        """
        50-cents-to-50k Dynamic De-leveraging (DDL) Ladder:
        < €10 -> 100x max 0.01 BTC, < €100 -> 50x max 0.05 BTC, < €1k -> 25x max 0.20 BTC, < €10k -> 10x max 1.0 BTC, > €20k -> 3x max 5.0 BTC.
        """
        if capital < 10:
            return 100, 0.01
        elif capital < 100:
            return 50, 0.05
        elif capital < 1000:
            return 25, 0.20
        elif capital < 10000:
            return 10, 1.0
        elif capital <= 20000:
            return 10, 1.0
        else:
            return 3, 5.0

    def check_safety(self, signal: str, qty: float) -> tuple[bool, str, float]:
        """
        Fast risk evaluation path. Must execute in microseconds.
        """
        self.check_daily_reset()
        if self.circuit_breaker_active:
            return False, f"ABORT: Circuit breaker active — {self.circuit_breaker_reason}", 0.0

        start_time = time.perf_counter()
        now = time.time()
        
        # 1. Daily Drawdown Check (3% max daily drawdown hard kill-switch)
        if self.daily_start_equity > 0:
            current_drawdown = (self.daily_start_equity - self.current_equity) / self.daily_start_equity
            if current_drawdown > self.max_drawdown:
                self.circuit_breaker_active = True
                self.circuit_breaker_reason = f"Daily loss limit {self.max_drawdown*100:.1f}% breached"
                latency_us = (time.perf_counter() - start_time) * 1_000_000.0
                return False, f"ABORT: {self.circuit_breaker_reason}", latency_us

        # 2. Trailing Stop Loss Check
        if self.current_position > 0 and self.last_price is not None and self.stop_price is not None:
            if self.last_price <= self.stop_price:
                if signal.upper() != "SELL":
                    latency_us = (time.perf_counter() - start_time) * 1_000_000.0
                    return False, "ABORT: Trailing Stop Loss triggered", latency_us
        elif self.current_position < 0 and self.last_price is not None and self.stop_price is not None:
            if self.last_price >= self.stop_price:
                if signal.upper() != "BUY":
                    latency_us = (time.perf_counter() - start_time) * 1_000_000.0
                    return False, "ABORT: Trailing Stop Loss triggered", latency_us

        # 3. Position Limit & DDL Check
        max_lev, max_qty = self.get_ddl_limits(self.current_equity)
        eff_max_qty = min(self.max_position, max_qty)

        potential_pos = self.current_position + (qty if signal.upper() == "BUY" else -qty)

        if abs(potential_pos) > eff_max_qty:
            latency_us = (time.perf_counter() - start_time) * 1_000_000.0
            return False, f"ABORT: Maximum position size exceeded! (Limit: {eff_max_qty} | Target: {abs(potential_pos):.2f})", latency_us
            
        if abs(potential_pos) > abs(self.current_position) and self.last_price is not None and self.current_equity > 0:
            potential_lev = (abs(potential_pos) * self.last_price) / self.current_equity
            if potential_lev > max_lev:
                latency_us = (time.perf_counter() - start_time) * 1_000_000.0
                return False, f"ABORT: Maximum leverage exceeded! (Limit: {max_lev}x | Target: {potential_lev:.2f}x)", latency_us

        # 4. Trade Velocity (Spam Protection)
        self.trade_timestamps = [t for t in self.trade_timestamps if now - t < 1.0]
        if len(self.trade_timestamps) >= self.max_trades_per_sec:
            latency_us = (time.perf_counter() - start_time) * 1_000_000.0
            return False, f"ABORT: Order rate limit exceeded! ({len(self.trade_timestamps)} trades/sec)", latency_us
            
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
