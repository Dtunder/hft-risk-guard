import pytest
from myhdl import block, always, instances, intbv, delay, instance

@block
def fpga_risk_check(clk, rst, order_qty, current_pos, max_pos, reject_out):
    """
    Simplified FPGA parity check for position limit.
    Takes integer scaled values.
    """
    @always(clk.posedge)
    def logic():
        if rst:
            reject_out.next = 0
        else:
            if abs(current_pos + order_qty) > max_pos:
                reject_out.next = 1
            else:
                reject_out.next = 0
    return logic

def test_fpga_logic_parity():
    from myhdl import Signal, Simulation, StopSimulation

    clk = Signal(bool(0))
    rst = Signal(bool(0))
    # Using scaled integers for MyHDL (e.g., 10.0 -> 100)
    order_qty = Signal(intbv(0, min=-1000, max=1000))
    current_pos = Signal(intbv(0, min=-1000, max=1000))
    max_pos = Signal(intbv(100, min=0, max=1000)) # e.g. max pos 10.0 -> 100
    reject_out = Signal(bool(0))

    dut = fpga_risk_check(clk, rst, order_qty, current_pos, max_pos, reject_out)

    @always(delay(10))
    def clkgen():
        clk.next = not clk

    @instance
    def stimulus():
        rst.next = 1
        yield clk.posedge
        rst.next = 0
        yield clk.posedge

        # Safe order
        current_pos.next = 0
        order_qty.next = 15 # 1.5 -> 15
        yield clk.posedge
        assert reject_out == 0

        # Giant order
        current_pos.next = 0
        order_qty.next = 150 # 15.0 -> 150
        yield clk.posedge
        yield clk.posedge # allow register update
        assert reject_out == 1

        raise StopSimulation

    sim = Simulation(dut, clkgen, stimulus)
    sim.run()

if __name__ == "__main__":
    test_fpga_logic_parity()
