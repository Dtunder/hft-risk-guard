import pytest
import time
from src.risk_barrier import HFTRiskGuard

def test_dynamic_position_sizing_normal():
    guard = HFTRiskGuard(max_position=10.0)

    # Normal condition: win rate 60%, win_loss_ratio 1.5
    # Kelly fraction = 0.6 - (0.4 / 1.5) = 0.6 - 0.266 = 0.333
    # Volatility normal: 0.2, target 0.2 -> vol_scalar = 1.0
    # Expected max pos = 10 * 0.333 * 1.0 = 3.333
    guard.update_dynamic_limits(win_rate=0.6, win_loss_ratio=1.5, current_volatility=0.2, target_volatility=0.2)

    assert guard.max_position > 3.0 and guard.max_position < 3.5

    # Should allow 2.0 order
    safe, msg, _ = guard.check_safety("BUY", 2.0)
    assert safe is True

    # Should reject 4.0 order
    safe, msg, _ = guard.check_safety("BUY", 4.0)
    assert safe is False
    assert "Maximum position size exceeded" in msg

def test_dynamic_position_sizing_volatility_spike():
    guard = HFTRiskGuard(max_position=10.0)

    # Normal win stats, but extreme volatility!
    # current_volatility = 0.8 (4x normal)
    # Vol scalar = 0.2 / 0.8 = 0.25
    # Kelly fraction = 0.333
    # Expected max pos = 10 * 0.333 * 0.25 = 0.833
    guard.update_dynamic_limits(win_rate=0.6, win_loss_ratio=1.5, current_volatility=0.8, target_volatility=0.2)

    assert guard.max_position > 0.8 and guard.max_position < 0.9

    # Should reject 2.0 order now!
    safe, msg, _ = guard.check_safety("BUY", 2.0)
    assert safe is False
    assert "Maximum position size exceeded" in msg

    # Should allow 0.5 order
    safe, msg, _ = guard.check_safety("BUY", 0.5)
    assert safe is True

def test_negative_kelly():
    guard = HFTRiskGuard(max_position=10.0)

    # Terrible strategy, negative expected value
    # win_rate 0.3, win_loss_ratio 1.0
    # Kelly fraction = 0.3 - (0.7 / 1.0) = -0.4 -> bounded to 0.0
    guard.update_dynamic_limits(win_rate=0.3, win_loss_ratio=1.0, current_volatility=0.2, target_volatility=0.2)

    assert guard.max_position == 0.0

    # Should reject any order
    safe, msg, _ = guard.check_safety("BUY", 0.1)
    assert safe is False
