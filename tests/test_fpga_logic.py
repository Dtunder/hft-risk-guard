import pytest
from myhdl import Signal, intbv, Simulation, delay, instance
from src.fpga_risk import fpga_risk_guard


def test_fpga_safe_order():
    safe_out = Signal(intbv(0)[1:])
    order_side = Signal(intbv(0)[1:]) # 0 for BUY
    order_qty = Signal(intbv(15)[8:]) # Scaled by 10 (1.5)
    current_position = Signal(intbv(0, min=-1000, max=1000))
    max_position = Signal(intbv(100)[8:]) # Scaled by 10 (10.0)
    peak_equity = Signal(intbv(100000)[32:])
    current_equity = Signal(intbv(100000)[32:])
    max_drawdown_amount = Signal(intbv(2000)[32:]) # 2% of 100k
    trade_count = Signal(intbv(0)[8:])
    max_trades_per_sec = Signal(intbv(20)[8:])

    fpga_inst = fpga_risk_guard(
        safe_out, order_side, order_qty, current_position, max_position,
        peak_equity, current_equity, max_drawdown_amount, trade_count, max_trades_per_sec
    )

    @instance
    def test():
        yield delay(10)
        assert safe_out == 1 # Should be safe

    sim = Simulation(fpga_inst, test)
    sim.run()

def test_fpga_position_limit():
    safe_out = Signal(intbv(0)[1:])
    order_side = Signal(intbv(0)[1:]) # 0 for BUY
    order_qty = Signal(intbv(150)[8:]) # 15.0
    current_position = Signal(intbv(0, min=-1000, max=1000))
    max_position = Signal(intbv(100)[8:]) # 10.0
    peak_equity = Signal(intbv(100000)[32:])
    current_equity = Signal(intbv(100000)[32:])
    max_drawdown_amount = Signal(intbv(2000)[32:])
    trade_count = Signal(intbv(0)[8:])
    max_trades_per_sec = Signal(intbv(20)[8:])

    fpga_inst = fpga_risk_guard(
        safe_out, order_side, order_qty, current_position, max_position,
        peak_equity, current_equity, max_drawdown_amount, trade_count, max_trades_per_sec
    )

    @instance
    def test():
        yield delay(10)
        assert safe_out == 0 # Should fail due to position

    sim = Simulation(fpga_inst, test)
    sim.run()

def test_fpga_drawdown_limit():
    safe_out = Signal(intbv(0)[1:])
    order_side = Signal(intbv(0)[1:])
    order_qty = Signal(intbv(10)[8:])
    current_position = Signal(intbv(0, min=-1000, max=1000))
    max_position = Signal(intbv(100)[8:])
    peak_equity = Signal(intbv(100000)[32:])
    current_equity = Signal(intbv(97000)[32:]) # 3k drawdown > 2k
    max_drawdown_amount = Signal(intbv(2000)[32:])
    trade_count = Signal(intbv(0)[8:])
    max_trades_per_sec = Signal(intbv(20)[8:])

    fpga_inst = fpga_risk_guard(
        safe_out, order_side, order_qty, current_position, max_position,
        peak_equity, current_equity, max_drawdown_amount, trade_count, max_trades_per_sec
    )

    @instance
    def test():
        yield delay(10)
        assert safe_out == 0 # Should fail due to drawdown

    sim = Simulation(fpga_inst, test)
    sim.run()

def test_fpga_velocity_limit():
    safe_out = Signal(intbv(0)[1:])
    order_side = Signal(intbv(0)[1:])
    order_qty = Signal(intbv(10)[8:])
    current_position = Signal(intbv(0, min=-1000, max=1000))
    max_position = Signal(intbv(100)[8:])
    peak_equity = Signal(intbv(100000)[32:])
    current_equity = Signal(intbv(100000)[32:])
    max_drawdown_amount = Signal(intbv(2000)[32:])
    trade_count = Signal(intbv(25)[8:]) # 25 trades > 20
    max_trades_per_sec = Signal(intbv(20)[8:])

    fpga_inst = fpga_risk_guard(
        safe_out, order_side, order_qty, current_position, max_position,
        peak_equity, current_equity, max_drawdown_amount, trade_count, max_trades_per_sec
    )

    @instance
    def test():
        yield delay(10)
        assert safe_out == 0 # Should fail due to velocity

    sim = Simulation(fpga_inst, test)
    sim.run()
