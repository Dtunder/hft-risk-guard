import time
from fast_risk import FastRiskGuard

def test_fast_safe_order():
    guard = FastRiskGuard()
    safe, msg, _ = guard.check_safety("BUY", 1.5)
    assert safe is True
    assert msg == "SAFE"

def test_fast_position_limit_exceeded():
    guard = FastRiskGuard(max_position=10.0)
    safe, msg, _ = guard.check_safety("BUY", 15.0)
    assert safe is False
    assert "position size exceeded" in msg

def test_fast_drawdown_limit_exceeded():
    guard = FastRiskGuard(max_drawdown=0.02)
    guard.update_portfolio(current_equity=97000.0, current_position=0.0)
    safe, msg, _ = guard.check_safety("BUY", 1.0)
    assert safe is False
    assert "drawdown limit exceeded" in msg

def test_fast_velocity_limit_exceeded():
    guard = FastRiskGuard(max_trades_per_sec=2)
    safe, _, _ = guard.check_safety("BUY", 1.0)
    assert safe is True
    safe, _, _ = guard.check_safety("SELL", 1.0)
    assert safe is True
    safe, msg, _ = guard.check_safety("BUY", 1.0)
    assert safe is False
    assert "rate limit exceeded" in msg

def test_fast_velocity_limit_reset():
    guard = FastRiskGuard(max_trades_per_sec=2)
    guard.check_safety("BUY", 1.0)
    guard.check_safety("SELL", 1.0)
    time.sleep(1.1)
    safe, _, _ = guard.check_safety("BUY", 1.0)
    assert safe is True
