from myhdl import block, always_comb, Signal, intbv

@block
def FPGARiskGuard(
    current_equity,
    peak_equity,
    max_drawdown_limit_scaled,
    current_position,
    order_side, # 1 for BUY, 0 for SELL
    order_qty,
    max_position,
    drawdown_exceeded,
    position_exceeded
):
    """
    Hardware implementation of the HFT Risk Guard.
    All inputs should be integer scaled values (e.g., multiplied by 1000).
    """

    @always_comb
    def logic():
        # Drawdown check: (peak_equity - current_equity) > limit
        if (peak_equity - current_equity) > max_drawdown_limit_scaled:
            drawdown_exceeded.next = 1
        else:
            drawdown_exceeded.next = 0

        # Position check
        # order_side: 1=BUY, 0=SELL
        if order_side == 1:
            potential_pos = current_position + order_qty
        else:
            potential_pos = current_position - order_qty

        # Check absolute position
        if potential_pos > max_position or potential_pos < -max_position:
            position_exceeded.next = 1
        else:
            position_exceeded.next = 0

    return logic
