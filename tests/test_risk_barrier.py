import pytest
from src.risk_barrier import HFTRiskGuard

def test_dynamic_position_sizing_kelly_criterion():
    guard = HFTRiskGuard(max_position=10.0)

    # Base check
    assert guard.max_position == 10.0

    # Favorable Kelly (Win Prob=0.6, W/L Ratio=1.0) => Kelly f = 0.6 - (0.4/1.0) = 0.2
    guard.update_market_conditions(win_prob=0.6, win_loss_ratio=1.0, current_volatility=0.2, target_volatility=0.2)
    assert round(guard.max_position, 2) == 2.0  # 10.0 * 0.2 * 1.0

def test_dynamic_position_sizing_volatility_spike():
    guard = HFTRiskGuard(max_position=10.0)

    # Kelly f = 0.6 - (0.4/1.0) = 0.2
    # Volatility Spike (Current=0.4, Target=0.2) => Vol Scalar = 0.2 / 0.4 = 0.5
    # Max Pos = 10.0 * 0.2 * 0.5 = 1.0
    guard.update_market_conditions(win_prob=0.6, win_loss_ratio=1.0, current_volatility=0.4, target_volatility=0.2)
    assert round(guard.max_position, 2) == 1.0

def test_dynamic_position_sizing_low_volatility_cap():
    guard = HFTRiskGuard(max_position=10.0)

    # Kelly f = 1.0 - (0.0/1.0) = 1.0
    # Volatility drop (Current=0.1, Target=0.2) => Vol Scalar = 2.0
    # Max Pos should be capped at base_max_position = 10.0
    guard.update_market_conditions(win_prob=1.0, win_loss_ratio=1.0, current_volatility=0.1, target_volatility=0.2)
    assert guard.max_position == 10.0

def test_dynamic_position_sizing_negative_edge():
    guard = HFTRiskGuard(max_position=10.0)

    # Negative Kelly (Win Prob=0.4, W/L Ratio=1.0) => Kelly f = 0.4 - (0.6/1.0) = -0.2 => 0.0
    guard.update_market_conditions(win_prob=0.4, win_loss_ratio=1.0, current_volatility=0.2, target_volatility=0.2)
    assert guard.max_position == 0.0

def test_dynamic_position_sizing_check_safety_abort():
    guard = HFTRiskGuard(max_position=10.0)

    # Volatility spike drops max_position to 1.0
    guard.update_market_conditions(win_prob=0.6, win_loss_ratio=1.0, current_volatility=0.4, target_volatility=0.2)

    # Order of 1.5 should now fail
    safe, msg, _ = guard.check_safety("BUY", 1.5)
    assert safe is False
    assert "ABORT: Maximum position size exceeded" in msg
    assert "Limit: 1.00" in msg

def test_dynamic_position_sizing_check_safety_pass():
    guard = HFTRiskGuard(max_position=10.0)

    # Volatility spike drops max_position to 1.0
    guard.update_market_conditions(win_prob=0.6, win_loss_ratio=1.0, current_volatility=0.4, target_volatility=0.2)

    # Order of 0.5 should pass
    safe, msg, _ = guard.check_safety("BUY", 0.5)
    assert safe is True
    assert msg == "SAFE"
