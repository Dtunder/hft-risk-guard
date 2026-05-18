from myhdl import block, always, instances, intbv, delay, instance, Signal
from src.fpga_logic import FPGARiskGuard
from src.risk_barrier import HFTRiskGuard

def test_fpga_logic_parity():
    @block
    def testbench():
        clk = Signal(bool(0))
        rst = Signal(bool(0))
        order_side = Signal(intbv(0)[1:])
        order_qty = Signal(intbv(0)[32:])
        current_equity = Signal(intbv(100000)[32:])
        peak_equity = Signal(intbv(100000)[32:])
        current_position = Signal(intbv(0)[32:])
        max_position = Signal(intbv(10)[32:])
        max_drawdown_scaled = Signal(intbv(200)[32:]) # 200 = 2%
        is_safe = Signal(bool(0))
        reject_code = Signal(intbv(0)[2:])

        dut = FPGARiskGuard(
            clk, rst,
            order_side, order_qty,
            current_equity, peak_equity, current_position,
            max_position, max_drawdown_scaled,
            is_safe, reject_code
        )

        @always(delay(10))
        def clkgen():
            clk.next = not clk

        @instance
        def stimulus():
            python_guard = HFTRiskGuard(max_position=10.0, max_drawdown=0.02)

            # Reset
            rst.next = 1
            yield delay(20)
            rst.next = 0

            # Test 1: Safe Order
            order_side.next = 1 # BUY
            order_qty.next = 5
            yield clk.posedge
            yield delay(1)
            py_safe, _, _ = python_guard.check_safety("BUY", 5)
            assert bool(is_safe) == py_safe
            assert int(reject_code) == 0

            # Test 2: Position limit exceeded
            order_side.next = 1 # BUY
            order_qty.next = 15
            yield clk.posedge
            yield delay(1)
            py_safe, _, _ = python_guard.check_safety("BUY", 15)
            assert bool(is_safe) == py_safe
            assert int(reject_code) == 2

            # Test 3: Drawdown exceeded
            current_equity.next = 97000 # 3% drawdown
            python_guard.update_portfolio(current_equity=97000.0, current_position=0.0)
            order_qty.next = 1
            yield clk.posedge
            yield delay(1)
            py_safe, _, _ = python_guard.check_safety("BUY", 1)
            assert bool(is_safe) == py_safe
            assert int(reject_code) == 1

        return instances()

    tb = testbench()
    tb.config_sim(trace=False)
    tb.run_sim(100)
