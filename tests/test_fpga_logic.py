import pytest
from myhdl import Signal, intbv, delay, instance, Simulation
from src.fpga_logic import FPGARiskGuard

def test_fpga_parity_safe():
    current_equity = Signal(intbv(100000000)) # scaled by 1000
    peak_equity = Signal(intbv(100000000))
    max_drawdown_limit_scaled = Signal(intbv(2000000)) # 2% of 100k * 1000
    current_position = Signal(intbv(0))
    order_side = Signal(intbv(1))
    order_qty = Signal(intbv(1500)) # 1.5 * 1000
    max_position = Signal(intbv(10000)) # 10.0 * 1000

    drawdown_exceeded = Signal(intbv(0))
    position_exceeded = Signal(intbv(0))

    inst = FPGARiskGuard(
        current_equity,
        peak_equity,
        max_drawdown_limit_scaled,
        current_position,
        order_side,
        order_qty,
        max_position,
        drawdown_exceeded,
        position_exceeded
    )

    @instance
    def test():
        yield delay(10)
        assert drawdown_exceeded == 0
        assert position_exceeded == 0

    sim = Simulation(inst, test)
    sim.run()

def test_fpga_parity_position_exceeded():
    current_equity = Signal(intbv(100000000))
    peak_equity = Signal(intbv(100000000))
    max_drawdown_limit_scaled = Signal(intbv(2000000))
    current_position = Signal(intbv(0))
    order_side = Signal(intbv(1))
    order_qty = Signal(intbv(15000)) # 15.0 * 1000
    max_position = Signal(intbv(10000))

    drawdown_exceeded = Signal(intbv(0))
    position_exceeded = Signal(intbv(0))

    inst = FPGARiskGuard(
        current_equity,
        peak_equity,
        max_drawdown_limit_scaled,
        current_position,
        order_side,
        order_qty,
        max_position,
        drawdown_exceeded,
        position_exceeded
    )

    @instance
    def test():
        yield delay(10)
        assert drawdown_exceeded == 0
        assert position_exceeded == 1

    sim = Simulation(inst, test)
    sim.run()

def test_fpga_parity_drawdown_exceeded():
    current_equity = Signal(intbv(97000000))
    peak_equity = Signal(intbv(100000000))
    max_drawdown_limit_scaled = Signal(intbv(2000000))
    current_position = Signal(intbv(0))
    order_side = Signal(intbv(1))
    order_qty = Signal(intbv(1000))
    max_position = Signal(intbv(10000))

    drawdown_exceeded = Signal(intbv(0))
    position_exceeded = Signal(intbv(0))

    inst = FPGARiskGuard(
        current_equity,
        peak_equity,
        max_drawdown_limit_scaled,
        current_position,
        order_side,
        order_qty,
        max_position,
        drawdown_exceeded,
        position_exceeded
    )

    @instance
    def test():
        yield delay(10)
        assert drawdown_exceeded == 1
        assert position_exceeded == 0

    sim = Simulation(inst, test)
    sim.run()
