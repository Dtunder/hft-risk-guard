# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False

import time
from libc.math cimport fabs

cdef class FastHFTRiskGuard:
    cdef public double max_position
    cdef public double max_drawdown
    cdef public int max_trades_per_sec
    cdef public double peak_equity
    cdef public double current_equity
    cdef public double current_position
    cdef public list trade_timestamps

    def __init__(self, double max_position=10.0, double max_drawdown=0.02, int max_trades_per_sec=20):
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.max_trades_per_sec = max_trades_per_sec
        self.peak_equity = 100000.0
        self.current_equity = 100000.0
        self.current_position = 0.0
        self.trade_timestamps = []

    cpdef void update_portfolio(self, double current_equity, double current_position):
        self.current_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        self.current_position = current_position

    cpdef tuple check_safety(self, str order_side, double order_qty):
        cdef double start_time = time.perf_counter()
        cdef double now = time.time()
        cdef double current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        cdef double potential_pos = self.current_position + (order_qty if order_side.upper() == "BUY" else -order_qty)
        cdef double check_time_us
        cdef int i

        # 1. Drawdown Check
        if current_drawdown > self.max_drawdown:
            return False, f"ABORT: Maximum drawdown limit exceeded! ({current_drawdown*100:.2f}%)", 0.0

        # 2. Position Limit Check
        if fabs(potential_pos) > self.max_position:
            return False, f"ABORT: Maximum position size exceeded! (Limit: {self.max_position} | Target: {fabs(potential_pos):.2f})", 0.0

        # 3. Trade Velocity
        # In-place filtering to avoid list allocation overhead in hot path
        cdef list new_timestamps = []
        for t in self.trade_timestamps:
            if now - t < 1.0:
                new_timestamps.append(t)
        self.trade_timestamps = new_timestamps

        if len(self.trade_timestamps) >= self.max_trades_per_sec:
            return False, f"ABORT: Order rate limit exceeded! ({len(self.trade_timestamps)} trades/sec)", 0.0

        self.trade_timestamps.append(now)
        check_time_us = (time.perf_counter() - start_time) * 1_000_000.0

        return True, "SAFE", check_time_us
