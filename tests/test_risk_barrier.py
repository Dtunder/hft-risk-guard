import pytest
from src.risk_barrier import HFTRiskGuard

def test_risk_guard_safe_order():
    guard = HFTRiskGuard()
    safe, msg, latency = guard.check_safety("BUY", 1.5)
    assert safe is True
    assert msg == "SAFE"
    assert latency >= 0

def test_risk_guard_position_exceeded():
    guard = HFTRiskGuard(max_position=10.0)
    safe, msg, latency = guard.check_safety("BUY", 15.0)
    assert safe is False
    assert "ABORT" in msg
    assert "position size exceeded" in msg

def test_risk_guard_drawdown_exceeded():
    guard = HFTRiskGuard(max_drawdown=0.02)
    guard.update_portfolio(current_equity=97000.0, current_position=0.0)
    safe, msg, latency = guard.check_safety("BUY", 1.0)
    assert safe is False
    assert "ABORT" in msg
    assert "drawdown limit exceeded" in msg

def test_risk_guard_velocity_exceeded():
    guard = HFTRiskGuard(max_trades_per_sec=2)
    safe, msg, latency = guard.check_safety("BUY", 1.0)
    assert safe is True

    safe, msg, latency = guard.check_safety("SELL", 1.0)
    assert safe is True

    safe, msg, latency = guard.check_safety("BUY", 1.0)
    assert safe is False
    assert "ABORT" in msg
    assert "rate limit exceeded" in msg
