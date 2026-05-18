from myhdl import block, always_comb, intbv, Signal

@block
def fpga_risk_guard(
    safe_out,
    order_side,         # 0 for BUY, 1 for SELL
    order_qty,          # Scaled integer representation of quantity
    current_position,
    max_position,
    peak_equity,
    current_equity,
    max_drawdown_amount, # Allowed drawdown amount (e.g. peak_equity * max_drawdown)
    trade_count,         # Number of trades in the last second
    max_trades_per_sec
):
    """
    MyHDL Hardware description for FPGA risk guard.
    Uses integer representations for hardware synthesis.
    """

    @always_comb
    def logic():
        # 1. Drawdown Check
        drawdown_violation = (peak_equity - current_equity) > max_drawdown_amount

        # 2. Position Check
        if order_side == 0: # BUY
            potential_pos = current_position + order_qty
        else: # SELL
            potential_pos = current_position - order_qty

        if potential_pos < 0:
            abs_pos = -potential_pos
        else:
            abs_pos = potential_pos

        position_violation = abs_pos > max_position

        # 3. Trade Velocity Check
        velocity_violation = trade_count >= max_trades_per_sec

        if drawdown_violation or position_violation or velocity_violation:
            safe_out.next = 0 # False / Block
        else:
            safe_out.next = 1 # True / Safe

    return logic
