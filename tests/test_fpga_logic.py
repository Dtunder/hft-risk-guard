import pytest
from myhdl import *
from src.risk_fpga import risk_guard
from src.risk_barrier import HFTRiskGuard

def test_risk_logic_parity():
    # Signals for MyHDL simulation
    peak_equity = Signal(intbv(100000, min=0, max=2**31-1))
    current_equity = Signal(intbv(100000, min=0, max=2**31-1))
    current_position = Signal(intbv(0, min=-2**31, max=2**31-1))
    order_qty = Signal(intbv(0, min=0, max=2**31-1))
    order_side = Signal(bool(0))
    max_position = Signal(intbv(10, min=0, max=2**31-1))
    max_drawdown_pct = Signal(intbv(2, min=0, max=100))
    trade_count = Signal(intbv(0, min=0, max=2**31-1))
    max_trades_per_sec = Signal(intbv(20, min=0, max=2**31-1))
    safe_fpga = Signal(bool(1))

    # Instantiate the MyHDL block
    guard_inst = risk_guard(
        peak_equity,
        current_equity,
        current_position,
        order_qty,
        order_side,
        max_position,
        max_drawdown_pct,
        trade_count,
        max_trades_per_sec,
        safe_fpga
    )

    @instance
    def testbench():
        # Setup Python guard
        py_guard = HFTRiskGuard(max_position=10.0, max_drawdown=0.02, max_trades_per_sec=20)
        py_guard.peak_equity = 100000.0

        test_cases = [
            # current_equity, current_position, order_qty, order_side (1=BUY, 0=SELL), trade_count
            (100000.0, 0.0, 1.5, "BUY", 0),  # Safe normal order
            (100000.0, 0.0, 15.0, "BUY", 0), # Giant order (Violates Position size)
            (97000.0, 1.5, 0.5, "BUY", 0),   # Massive Drawdown
            (100000.0, 9.0, 2.0, "BUY", 0),  # Position exceeded by a little
            (100000.0, -9.0, 2.0, "SELL", 0), # Short position exceeded
            (100000.0, 0.0, 1.0, "BUY", 20), # Trade velocity exceeded
            (99000.0, 0.0, 5.0, "BUY", 10),  # Safe, small drawdown, ok position, ok velocity
        ]

        import time
        for ce, cp, oq, os, tc in test_cases:
            # Set Python guard state
            py_guard.current_equity = ce
            py_guard.current_position = cp

            # Since trade_count is dynamic based on timestamps in python, we'll manually spoof it
            # But the logic evaluates: len([t for t in timestamps if now - t < 1.0]) >= max_trades_per_sec
            # For testing parity, we can just inject timestamps
            now = time.time()
            py_guard.trade_timestamps = [now] * tc # just add enough timestamps so they don't get filtered out

            # Run Python logic
            safe_py, _, _ = py_guard.check_safety(os, oq)

            # Set FPGA inputs
            current_equity.next = int(ce)
            current_position.next = int(cp)
            order_qty.next = int(oq)
            order_side.next = 1 if os == "BUY" else 0
            trade_count.next = tc

            yield delay(10) # wait for combinatorial logic

            # Compare
            assert bool(safe_fpga) == safe_py, f"Mismatch: Python={safe_py}, FPGA={bool(safe_fpga)} for case {(ce, cp, oq, os, tc)}"

    sim = Simulation(guard_inst, testbench)
    sim.run()

if __name__ == '__main__':
    test_risk_logic_parity()
