import pytest
import pyximport; pyximport.install(setup_args={"script_args": ["--compiler=unix"]}, language_level=3)
from src.fast_risk import FastHFTRiskGuard
import time

def test_fast_risk_safe_order():
    guard = FastHFTRiskGuard(max_position=10.0, max_drawdown=0.02, max_trades_per_sec=20)
    safe, msg, latency = guard.check_safety("BUY", 1.5)
    assert safe is True
    assert msg == "SAFE"
    assert latency > 0

def test_fast_risk_position_limit():
    guard = FastHFTRiskGuard(max_position=10.0, max_drawdown=0.02, max_trades_per_sec=20)
    safe, msg, latency = guard.check_safety("BUY", 15.0)
    assert safe is False
    assert "position size exceeded" in msg

def test_fast_risk_drawdown_limit():
    guard = FastHFTRiskGuard(max_position=10.0, max_drawdown=0.02, max_trades_per_sec=20)
    guard.update_portfolio(current_equity=97000.0, current_position=1.5) # 3% drawdown
    safe, msg, latency = guard.check_safety("BUY", 0.5)
    assert safe is False
    assert "drawdown limit exceeded" in msg

def test_fast_risk_velocity_limit():
    guard = FastHFTRiskGuard(max_position=10.0, max_drawdown=0.02, max_trades_per_sec=3)
    # Trade 1
    safe, msg, lat = guard.check_safety("BUY", 1.0)
    assert safe is True
    # Trade 2
    safe, msg, lat = guard.check_safety("BUY", 1.0)
    assert safe is True
    # Trade 3
    safe, msg, lat = guard.check_safety("BUY", 1.0)
    assert safe is True
    # Trade 4 (fails)
    safe, msg, lat = guard.check_safety("BUY", 1.0)
    assert safe is False
    assert "rate limit exceeded" in msg
