import pytest
import pyximport; pyximport.install(setup_args={"script_args": ["--compiler=unix"]}, language_level=3)
from src.risk_barrier import HFTRiskGuard
from src.fast_risk import FastHFTRiskGuard
import time

def test_risk_barrier_initialization():
    python_guard = HFTRiskGuard()
    cython_guard = FastHFTRiskGuard()

    assert python_guard.max_position == 10.0
    # can't easily assert cython variables as they are cdef'd, but we can test behavior.

def test_safe_order_parity():
    python_guard = HFTRiskGuard()
    cython_guard = FastHFTRiskGuard()

    p_safe, p_msg, _ = python_guard.check_safety("BUY", 1.5)
    c_safe, c_msg, _ = cython_guard.check_safety("BUY", 1.5)

    assert p_safe is True
    assert c_safe is True
    assert p_msg == c_msg

def test_position_limit_parity():
    python_guard = HFTRiskGuard()
    cython_guard = FastHFTRiskGuard()

    p_safe, p_msg, _ = python_guard.check_safety("BUY", 15.0)
    c_safe, c_msg, _ = cython_guard.check_safety("BUY", 15.0)

    assert p_safe is False
    assert c_safe is False
    assert "Maximum position size exceeded" in p_msg
    assert "Maximum position size exceeded" in c_msg

def test_drawdown_parity():
    python_guard = HFTRiskGuard()
    cython_guard = FastHFTRiskGuard()

    python_guard.update_portfolio(current_equity=97000.0, current_position=0.0)
    cython_guard.update_portfolio(current_equity=97000.0, current_position=0.0)

    p_safe, p_msg, _ = python_guard.check_safety("BUY", 1.0)
    c_safe, c_msg, _ = cython_guard.check_safety("BUY", 1.0)

    assert p_safe is False
    assert c_safe is False
    assert "drawdown limit exceeded" in p_msg
    assert "drawdown limit exceeded" in c_msg

def test_velocity_parity():
    python_guard = HFTRiskGuard(max_trades_per_sec=2)
    cython_guard = FastHFTRiskGuard(max_trades_per_sec=2)

    # 1st trade
    python_guard.check_safety("BUY", 1.0)
    cython_guard.check_safety("BUY", 1.0)
    # 2nd trade
    python_guard.check_safety("BUY", 1.0)
    cython_guard.check_safety("BUY", 1.0)

    # 3rd trade (should fail)
    p_safe, p_msg, _ = python_guard.check_safety("BUY", 1.0)
    c_safe, c_msg, _ = cython_guard.check_safety("BUY", 1.0)

    assert p_safe is False
    assert c_safe is False
    assert "Order rate limit exceeded" in p_msg
    assert "Order rate limit exceeded" in c_msg
