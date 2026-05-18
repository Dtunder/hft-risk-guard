import pytest
from src.risk_barrier import HFTRiskGuard

def test_dynamic_limits_normal_volatility():
    guard = HFTRiskGuard(max_position=10.0)
    # Win prob = 0.55, Win/Loss ratio = 2.0
    # Kelly = 0.55 - (0.45 / 2.0) = 0.55 - 0.225 = 0.325
    # Normal volatility (0.02) vs target (0.02) = 1.0 multiplier
    guard.update_dynamic_limits(win_prob=0.55, win_loss_ratio=2.0, current_volatility=0.02, target_volatility=0.02)
    assert pytest.approx(guard.max_position) == 3.25

def test_dynamic_limits_high_volatility():
    guard = HFTRiskGuard(max_position=10.0)
    # Win prob = 0.55, Win/Loss ratio = 2.0 => Kelly = 0.325
    # High volatility (0.04) vs target (0.02) = 0.5 multiplier
    guard.update_dynamic_limits(win_prob=0.55, win_loss_ratio=2.0, current_volatility=0.04, target_volatility=0.02)
    assert pytest.approx(guard.max_position) == 1.625

def test_dynamic_limits_low_volatility():
    guard = HFTRiskGuard(max_position=10.0)
    # Win prob = 0.55, Win/Loss ratio = 2.0 => Kelly = 0.325
    # Low volatility (0.01) vs target (0.02) = 2.0 scalar, but capped at 1.0
    guard.update_dynamic_limits(win_prob=0.55, win_loss_ratio=2.0, current_volatility=0.01, target_volatility=0.02)
    assert pytest.approx(guard.max_position) == 3.25

def test_dynamic_limits_negative_kelly():
    guard = HFTRiskGuard(max_position=10.0)
    # Win prob = 0.4, Win/Loss ratio = 1.0 => Kelly = 0.4 - 0.6 = -0.2 (capped at 0)
    guard.update_dynamic_limits(win_prob=0.4, win_loss_ratio=1.0, current_volatility=0.02, target_volatility=0.02)
    assert pytest.approx(guard.max_position) == 0.0

def test_dynamic_limits_max_kelly():
    guard = HFTRiskGuard(max_position=10.0)
    # Win prob = 1.0, Win/Loss ratio = 2.0 => Kelly = 1.0 - 0.0 = 1.0
    guard.update_dynamic_limits(win_prob=1.0, win_loss_ratio=2.0, current_volatility=0.02, target_volatility=0.02)
    assert pytest.approx(guard.max_position) == 10.0

def test_check_safety_shrinks_on_volatility():
    guard = HFTRiskGuard(max_position=10.0)
    # Initially 10.0 max pos
    safe, _, _ = guard.check_safety("BUY", 5.0)
    assert safe == True

    # High volatility, max position shrinks to 1.625
    guard.update_dynamic_limits(win_prob=0.55, win_loss_ratio=2.0, current_volatility=0.04, target_volatility=0.02)
    safe, msg, _ = guard.check_safety("BUY", 5.0)
    assert safe == False
    assert "ABORT: Maximum position size exceeded" in msg
