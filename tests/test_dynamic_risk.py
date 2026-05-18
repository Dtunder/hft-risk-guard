import pytest
from src.risk_barrier import HFTRiskGuard

def test_dynamic_limits_volatility_spike():
    guard = HFTRiskGuard(max_position=10.0, base_vix=20.0, base_volatility=0.05)

    # Assert initial base limits
    assert guard.max_position == 10.0

    # Update volatility (VIX spikes to 40 - 2x)
    guard.update_volatility(current_vix=40.0, current_volatility=0.05)

    # Expected max position should halve due to 2x VIX penalty
    assert guard.max_position == 5.0

    # Update volatility (Local asset volatility spikes to 0.15 - 3x)
    guard.update_volatility(current_vix=20.0, current_volatility=0.15)

    # Expected max position should be a third due to 3x Volatility penalty
    assert pytest.approx(guard.max_position) == 10.0 / 3.0

def test_dynamic_limits_kelly_criterion():
    guard = HFTRiskGuard(max_position=10.0)

    # 50% win rate, 2.0 win/loss ratio
    # Kelly = 0.5 - ((1 - 0.5) / 2.0) = 0.5 - 0.25 = 0.25
    # Max position = base_max (10.0) * kelly (0.25) = 2.5
    guard.update_dynamic_limits(win_prob=0.5, win_loss_ratio=2.0)
    assert guard.max_position == 2.5

    # 30% win rate, 1.0 win/loss ratio
    # Kelly = 0.3 - ((1 - 0.3) / 1.0) = 0.3 - 0.7 = -0.4 -> cap at 0
    guard.update_dynamic_limits(win_prob=0.3, win_loss_ratio=1.0)
    assert guard.max_position == 0.0

def test_dynamic_limits_combined_vol_and_kelly():
    guard = HFTRiskGuard(max_position=20.0, base_vix=20.0)

    # VIX spikes to 40 (2x). Base limit of 20 -> 10.
    guard.update_volatility(current_vix=40.0, current_volatility=0.05)
    assert guard.max_position == 10.0

    # Apply Kelly Criterion: 60% win rate, 1.0 win/loss ratio
    # Kelly = 0.6 - ((1 - 0.6) / 1.0) = 0.6 - 0.4 = 0.2
    # Final max pos = 10.0 * 0.2 = 2.0
    guard.update_dynamic_limits(win_prob=0.6, win_loss_ratio=1.0)
    assert pytest.approx(guard.max_position) == 2.0

def test_dynamic_limits_safety_check_abort():
    guard = HFTRiskGuard(max_position=10.0)

    # Reduce max position drastically via Kelly
    guard.update_dynamic_limits(win_prob=0.5, win_loss_ratio=1.0) # Kelly = 0

    safe, msg, latency = guard.check_safety("BUY", 1.0)
    assert not safe
    assert "Maximum position size exceeded" in msg
