import pytest
from src.risk_barrier import HFTRiskGuard
import time

def test_ddl_ladder_limits():
    guard = HFTRiskGuard(max_position=10.0) # Override max_position to test DDL

    # < €10
    guard.update_portfolio(current_equity=5.0, current_position=0)
    lev, max_qty = guard.get_ddl_limits(guard.current_equity)
    assert lev == 100
    assert max_qty == 0.01

    # < €100
    guard.update_portfolio(current_equity=50.0, current_position=0)
    lev, max_qty = guard.get_ddl_limits(guard.current_equity)
    assert lev == 50
    assert max_qty == 0.05

    # < €1k
    guard.update_portfolio(current_equity=500.0, current_position=0)
    lev, max_qty = guard.get_ddl_limits(guard.current_equity)
    assert lev == 25
    assert max_qty == 0.20

    # < €10k
    guard.update_portfolio(current_equity=5000.0, current_position=0)
    lev, max_qty = guard.get_ddl_limits(guard.current_equity)
    assert lev == 10
    assert max_qty == 1.0

    # > €20k
    guard.update_portfolio(current_equity=25000.0, current_position=0)
    lev, max_qty = guard.get_ddl_limits(guard.current_equity)
    assert lev == 3
    assert max_qty == 5.0

def test_trailing_stop():
    guard = HFTRiskGuard()
    # Assume price is 100
    guard.update_tick(100.0)

    # Enter long position
    guard.update_portfolio(current_equity=100000.0, current_position=1.0)

    # Initially stop should be at 100 * (1 - 0.0035) = 99.65
    assert abs(guard.stop_price - 99.65) < 1e-6

    # Price moves up to 200
    guard.update_tick(200.0)
    assert abs(guard.stop_price - 199.3) < 1e-6

    # Price moves down to 199.5 - trailing stop is not triggered yet, but new stop shouldn't move down
    guard.update_tick(199.5)
    assert abs(guard.stop_price - 199.3) < 1e-6

    # Safe to buy more
    safe, reason, _ = guard.check_safety("BUY", 0.5)
    assert safe == True

    # Price drops below stop (199.2)
    guard.update_tick(199.2)

    # Now it should be triggered, preventing any new BUY orders
    safe, reason, _ = guard.check_safety("BUY", 0.5)
    assert safe == False
    assert "Trailing Stop Loss triggered" in reason

    # Should still allow SELL (to close position)
    safe, reason, _ = guard.check_safety("SELL", 1.0)
    assert safe == True

def test_daily_drawdown_limit():
    guard = HFTRiskGuard(max_drawdown=0.03)
    guard.update_portfolio(current_equity=100000.0, current_position=0)
    guard.daily_start_equity = 100000.0

    # 2% drawdown - safe
    guard.update_portfolio(current_equity=98000.0, current_position=0)
    safe, reason, _ = guard.check_safety("BUY", 0.1)
    assert safe == True

    # 4% drawdown - unsafe, circuit breaker triggers
    guard.update_portfolio(current_equity=96000.0, current_position=0)
    safe, reason, _ = guard.check_safety("BUY", 0.1)
    assert safe == False
    assert "Daily loss limit 3.0% breached" in reason
    assert guard.circuit_breaker_active == True

    # Circuit breaker should remain active even if equity goes up
    guard.update_portfolio(current_equity=100000.0, current_position=0)
    safe, reason, _ = guard.check_safety("BUY", 0.1)
    assert safe == False
    assert "Circuit breaker active" in reason

def test_method_chaining():
    guard = HFTRiskGuard()
    res = guard.update_tick(100.0).update_portfolio(current_equity=100000.0, current_position=1.0)
    assert isinstance(res, HFTRiskGuard)
