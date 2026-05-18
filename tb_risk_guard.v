module tb_risk_guard;

reg [30:0] peak_equity;
reg [30:0] current_equity;
reg [31:0] current_position;
reg [30:0] order_qty;
reg order_side;
reg [30:0] max_position;
reg [6:0] max_drawdown_pct;
reg [30:0] trade_count;
reg [30:0] max_trades_per_sec;
wire safe;

initial begin
    $from_myhdl(
        peak_equity,
        current_equity,
        current_position,
        order_qty,
        order_side,
        max_position,
        max_drawdown_pct,
        trade_count,
        max_trades_per_sec
    );
    $to_myhdl(
        safe
    );
end

risk_guard dut(
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
);

endmodule
