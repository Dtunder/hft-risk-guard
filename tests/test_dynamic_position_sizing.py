import pytest
from src.risk_barrier import HFTRiskGuard

def test_dynamic_position_sizing_kelly():
    guard = HFTRiskGuard(base_max_position=10.0, target_volatility=20.0)

    # Baseline condition, Kelly should scale down position size if unfavorable
    # win_prob=0.5, win_loss_ratio=1.0 -> kelly_fraction = 0.5 - 0.5/1.0 = 0.0
    guard.update_market_conditions(win_prob=0.5, win_loss_ratio=1.0, current_volatility=20.0)
    assert guard.max_position == 0.0

    # win_prob=0.6, win_loss_ratio=1.0 -> kelly_fraction = 0.6 - 0.4/1.0 = 0.2
    # volatility scalar = 20/20 = 1.0
    # Expected max pos = 10.0 * 0.2 * 1.0 = 2.0
    guard.update_market_conditions(win_prob=0.6, win_loss_ratio=1.0, current_volatility=20.0)
    assert pytest.approx(guard.max_position) == 2.0

    # Better win probability -> larger position
    # win_prob=0.8, win_loss_ratio=2.0 -> kelly_fraction = 0.8 - 0.2/2.0 = 0.7
    guard.update_market_conditions(win_prob=0.8, win_loss_ratio=2.0, current_volatility=20.0)
    assert pytest.approx(guard.max_position) == 7.0

def test_dynamic_position_sizing_volatility_spike():
    guard = HFTRiskGuard(base_max_position=10.0, target_volatility=20.0)

    # High volatility reduces max position
    # win_prob=0.8, win_loss_ratio=2.0 -> kelly_fraction = 0.7
    # current_vol=40.0 -> vol_scalar = 20.0 / 40.0 = 0.5
    # Expected max pos = 10.0 * 0.7 * 0.5 = 3.5
    guard.update_market_conditions(win_prob=0.8, win_loss_ratio=2.0, current_volatility=40.0)
    assert pytest.approx(guard.max_position) == 3.5

    # Extremely high volatility
    # current_vol=100.0 -> vol_scalar = 20.0 / 100.0 = 0.2
    # Expected max pos = 10.0 * 0.7 * 0.2 = 1.4
    guard.update_market_conditions(win_prob=0.8, win_loss_ratio=2.0, current_volatility=100.0)
    assert pytest.approx(guard.max_position) == 1.4

def test_dynamic_position_sizing_low_volatility():
    guard = HFTRiskGuard(base_max_position=10.0, target_volatility=20.0)

    # Low volatility doesn't increase above base position (vol_scalar capped at 1.0)
    # win_prob=1.0, win_loss_ratio=1.0 -> kelly_fraction = 1.0
    # current_vol=10.0 -> max(20.0, 10.0) is 20.0 -> vol_scalar = 20.0/20.0 = 1.0
    # Expected max pos = 10.0 * 1.0 * 1.0 = 10.0
    guard.update_market_conditions(win_prob=1.0, win_loss_ratio=1.0, current_volatility=10.0)
    assert pytest.approx(guard.max_position) == 10.0

def test_dynamic_position_sizing_negative_edge():
    guard = HFTRiskGuard(base_max_position=10.0, target_volatility=20.0)

    # Negative expected value -> Kelly should be 0
    # win_prob=0.4, win_loss_ratio=1.0 -> kelly_fraction = 0.4 - 0.6 = -0.2 -> 0.0
    guard.update_market_conditions(win_prob=0.4, win_loss_ratio=1.0, current_volatility=20.0)
    assert guard.max_position == 0.0

def test_dynamic_position_sizing_safety_check_rejection():
    guard = HFTRiskGuard(base_max_position=10.0, target_volatility=20.0)

    # Set to strict constraints
    # win_prob=0.6, win_loss_ratio=1.0 -> kelly=0.2
    # current_vol=40.0 -> vol_scalar=0.5
    # max_pos = 1.0
    guard.update_market_conditions(win_prob=0.6, win_loss_ratio=1.0, current_volatility=40.0)
    assert pytest.approx(guard.max_position) == 1.0

    # Try to buy 1.5, should be blocked
    safe, msg, latency = guard.check_safety("BUY", 1.5)
    assert not safe
    assert "ABORT: Maximum position size exceeded" in msg

    # Try to buy 0.5, should be safe
    safe, msg, latency = guard.check_safety("BUY", 0.5)
    assert safe
    assert msg == "SAFE"
