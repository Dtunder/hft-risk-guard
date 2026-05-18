# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

import time

cdef class FastHFTRiskGuard:
    cdef public double max_position
    cdef public double max_drawdown
    cdef public int max_trades_per_sec
    cdef public double peak_equity
    cdef public double current_equity
    cdef public double current_position
    cdef list trade_timestamps

    def __init__(self, double max_position=10.0, double max_drawdown=0.02, int max_trades_per_sec=20):
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.max_trades_per_sec = max_trades_per_sec

        self.peak_equity = 100000.0  # $100k starting equity
        self.current_equity = 100000.0
        self.current_position = 0.0

        # Velocity tracking
        self.trade_timestamps = []

    cpdef void update_portfolio(self, double current_equity, double current_position):
        self.current_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        self.current_position = current_position

    cpdef tuple check_safety(self, str order_side, double order_qty):
        """
        Fast risk evaluation path in Cython.
        """
        cdef double start_time = time.perf_counter()
        cdef double now = time.time()
        cdef double current_drawdown
        cdef double potential_pos
        cdef double check_time_us

        # 1. Drawdown Check
        current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        if current_drawdown > self.max_drawdown:
            return False, f"ABORT: Maximum drawdown limit exceeded! ({current_drawdown*100:.2f}%)", 0.0

        # 2. Position Limit Check
        potential_pos = self.current_position + (order_qty if order_side.upper() == "BUY" else -order_qty)
        if abs(potential_pos) > self.max_position:
            return False, f"ABORT: Maximum position size exceeded! (Limit: {self.max_position} | Target: {abs(potential_pos):.2f})", 0.0

        # 3. Trade Velocity (Spam Protection)
        self.trade_timestamps = [t for t in self.trade_timestamps if now - t < 1.0]
        if len(self.trade_timestamps) >= self.max_trades_per_sec:
            return False, f"ABORT: Order rate limit exceeded! ({len(self.trade_timestamps)} trades/sec)", 0.0

        self.trade_timestamps.append(now)
        check_time_us = (time.perf_counter() - start_time) * 1_000_000.0

        return True, "SAFE", check_time_us
