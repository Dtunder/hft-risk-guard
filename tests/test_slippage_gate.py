import pytest
from unittest.mock import patch
from src.slippage_gate import AdaptiveSlippageGate

def test_initial_state():
    gate = AdaptiveSlippageGate(base_slippage=0.001)
    assert gate.slippage_limit() == 0.001

def test_method_chaining():
    gate = AdaptiveSlippageGate()
    ret = gate.update(order_book_depth=5.0, volatility=0.1)
    assert ret is gate
    assert gate.order_book_depth == 5.0
    assert gate.volatility == 0.1

def test_high_volatility():
    gate = AdaptiveSlippageGate(base_slippage=0.001, max_slippage=0.05)

    # Low depth, high volatility
    gate.update(order_book_depth=0.1, volatility=0.5)

    # calculation: 0.001 + 0.01 * (0.5 / 0.1) = 0.001 + 0.05 = 0.051
    # capped at max_slippage 0.05
    assert gate.slippage_limit() == 0.05

    # Moderate depth, moderate volatility
    gate.update(order_book_depth=2.0, volatility=0.1)
    # calculation: 0.001 + 0.01 * (0.1 / 2.0) = 0.001 + 0.0005 = 0.0015
    assert gate.slippage_limit() == 0.0015

@patch("src.slippage_gate.time.monotonic")
def test_token_bucket_rate_limit(mock_monotonic):
    # Start at time 0.0
    mock_monotonic.return_value = 0.0
    gate = AdaptiveSlippageGate(bucket_capacity=3.0, refill_rate=1.0)

    # Consumes 3 tokens initially
    assert gate.check_rate_limit() is True
    assert gate.check_rate_limit() is True
    assert gate.check_rate_limit() is True

    # Bucket should be empty now (assuming negligible time passed)
    assert gate.check_rate_limit() is False

    # Wait for 1 token to refill (1.0 second elapsed)
    mock_monotonic.return_value = 1.0

    # Should be able to consume 1 token
    assert gate.check_rate_limit() is True

    # Bucket should be empty again
    assert gate.check_rate_limit() is False

def test_depth_clamping():
    gate = AdaptiveSlippageGate()
    # Zero or negative depth clamped to 0.0001
    gate.update(order_book_depth=0)
    assert gate.order_book_depth == 0.0001
    gate.update(order_book_depth=-5)
    assert gate.order_book_depth == 0.0001

def test_volatility_clamping():
    gate = AdaptiveSlippageGate()
    # Negative volatility clamped to 0
    gate.update(volatility=-0.5)
    assert gate.volatility == 0.0
