from myhdl import *

@block
def risk_guard(
    peak_equity,
    current_equity,
    current_position,
    order_qty,
    order_side, # 1 for BUY, 0 for SELL
    max_position,
    max_drawdown_pct, # as integer percentage, e.g., 2 for 2%
    trade_count, # number of trades in the last second
    max_trades_per_sec,
    safe # output signal
):
    """
    FPGA-simulated hardware description layer for risk logic.
    """

    @always_comb
    def logic():
        # 1. Drawdown Check
        # (peak - current) * 100 > peak * max_drawdown_pct
        drawdown_exceeded = (peak_equity - current_equity) * 100 > peak_equity * max_drawdown_pct

        # 2. Position Limit Check
        # compute without intermediate assignments of different types
        position_exceeded = False
        if order_side == 1:
            if current_position + order_qty > max_position:
                position_exceeded = True
            elif current_position + order_qty < -max_position:
                position_exceeded = True
        else:
            if current_position - order_qty > max_position:
                position_exceeded = True
            elif current_position - order_qty < -max_position:
                position_exceeded = True

        # 3. Trade Velocity Check
        velocity_exceeded = trade_count >= max_trades_per_sec

        if drawdown_exceeded or position_exceeded or velocity_exceeded:
            safe.next = 0
        else:
            safe.next = 1

    return logic

def generate_verilog():
    peak_equity = Signal(intbv(100000, min=0, max=2**31-1))
    current_equity = Signal(intbv(100000, min=0, max=2**31-1))
    current_position = Signal(intbv(0, min=-2**31, max=2**31-1))
    order_qty = Signal(intbv(0, min=0, max=2**31-1))
    order_side = Signal(bool(0))
    max_position = Signal(intbv(10, min=0, max=2**31-1))
    max_drawdown_pct = Signal(intbv(2, min=0, max=100))
    trade_count = Signal(intbv(0, min=0, max=2**31-1))
    max_trades_per_sec = Signal(intbv(20, min=0, max=2**31-1))
    safe = Signal(bool(1))

    inst = risk_guard(
        peak_equity,
        current_equity,
        current_position,
        order_qty,
        order_side,
        max_position,
        max_drawdown_pct,
        trade_count,
        max_trades_per_sec,
        safe
    )

    inst.convert(hdl='Verilog')
    inst.convert(hdl='VHDL')

if __name__ == '__main__':
    generate_verilog()
