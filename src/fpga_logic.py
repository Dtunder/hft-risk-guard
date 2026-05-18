from myhdl import block, always, instances, intbv, delay

@block
def FPGARiskGuard(
    clk, rst,
    order_side, order_qty,
    current_equity, peak_equity, current_position,
    max_position, max_drawdown_scaled,
    is_safe, reject_code
):
    """
    FPGA-level Risk Guard logic.
    All inputs should be integer/fixed-point types for hardware synthesis.

    Ports:
    clk: Clock signal
    rst: Reset signal
    order_side: 1 for BUY, 0 for SELL
    order_qty: Order quantity
    current_equity: Current portfolio equity
    peak_equity: Peak portfolio equity
    current_position: Current portfolio position
    max_position: Maximum allowed position size
    max_drawdown_scaled: Maximum drawdown allowed (scaled for integer math)
    is_safe: Output, 1 if safe, 0 if rejected
    reject_code: Output, 1 for drawdown, 2 for position limit, 0 for safe
    """

    @always(clk.posedge)
    def logic():
        if rst:
            is_safe.next = 1
            reject_code.next = 0
        else:
            # Drawdown logic
            # Drawdown = (peak - current) / peak > max_drawdown
            # scaled to: (peak - current) * SCALE > max_drawdown_scaled * peak
            # For simplicity, assuming inputs are pre-scaled or handled as integers appropriately.
            # Example using a simple fixed scale. Let's assume max_drawdown_scaled is out of 10000 (e.g., 200 = 2%).
            # peak_equity - current_equity > (peak_equity * max_drawdown_scaled) / 10000

            drawdown_amt = peak_equity - current_equity
            max_drawdown_amt = (peak_equity * max_drawdown_scaled) // 10000

            if drawdown_amt > max_drawdown_amt:
                is_safe.next = 0
                reject_code.next = 1
            else:
                # Position Limit Check
                potential_pos = current_position + order_qty if order_side == 1 else current_position - order_qty
                abs_pos = potential_pos if potential_pos >= 0 else -potential_pos

                if abs_pos > max_position:
                    is_safe.next = 0
                    reject_code.next = 2
                else:
                    is_safe.next = 1
                    reject_code.next = 0

    return logic
