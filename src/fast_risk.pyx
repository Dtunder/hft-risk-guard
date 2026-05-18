# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

import time
from libc.time cimport time_t
from posix.time cimport clock_gettime, timespec, CLOCK_MONOTONIC
from libc.stdlib cimport malloc, free

cdef class FastHFTRiskGuard:
    cdef double max_position
    cdef double max_drawdown
    cdef int max_trades_per_sec

    cdef double peak_equity
    cdef double current_equity
    cdef double current_position

    cdef double* trade_timestamps
    cdef int trade_timestamps_head
    cdef int trade_timestamps_tail
    cdef int trade_timestamps_count
    cdef int trade_timestamps_capacity

    def __init__(self, double max_position=10.0, double max_drawdown=0.02, int max_trades_per_sec=20):
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.max_trades_per_sec = max_trades_per_sec

        self.peak_equity = 100000.0
        self.current_equity = 100000.0
        self.current_position = 0.0

        # Ring buffer for trade timestamps
        self.trade_timestamps_capacity = max_trades_per_sec + 1
        self.trade_timestamps = <double*>malloc(self.trade_timestamps_capacity * sizeof(double))
        self.trade_timestamps_head = 0
        self.trade_timestamps_tail = 0
        self.trade_timestamps_count = 0

    def __dealloc__(self):
        if self.trade_timestamps is not NULL:
            free(self.trade_timestamps)

    cpdef void update_portfolio(self, double current_equity, double current_position):
        self.current_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        self.current_position = current_position

    cpdef tuple check_safety(self, str order_side, double order_qty):
        cdef timespec ts_start
        cdef timespec ts_end
        clock_gettime(CLOCK_MONOTONIC, &ts_start)

        cdef double now = time.time()
        cdef double current_drawdown
        cdef double potential_pos

        # 1. Drawdown Check
        current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        if current_drawdown > self.max_drawdown:
            return False, f"ABORT: Maximum drawdown limit exceeded! ({current_drawdown*100:.2f}%)", 0.0

        # 2. Position Limit Check
        potential_pos = self.current_position + (order_qty if order_side.upper() == "BUY" else -order_qty)
        if (potential_pos if potential_pos > 0 else -potential_pos) > self.max_position:
            return False, f"ABORT: Maximum position size exceeded! (Limit: {self.max_position} | Target: {(potential_pos if potential_pos > 0 else -potential_pos):.2f})", 0.0

        # 3. Trade Velocity (Spam Protection)
        # Evict old timestamps
        while self.trade_timestamps_count > 0:
            if now - self.trade_timestamps[self.trade_timestamps_tail] >= 1.0:
                self.trade_timestamps_tail = (self.trade_timestamps_tail + 1) % self.trade_timestamps_capacity
                self.trade_timestamps_count -= 1
            else:
                break

        if self.trade_timestamps_count >= self.max_trades_per_sec:
            return False, f"ABORT: Order rate limit exceeded! ({self.trade_timestamps_count} trades/sec)", 0.0

        # Add new timestamp
        self.trade_timestamps[self.trade_timestamps_head] = now
        self.trade_timestamps_head = (self.trade_timestamps_head + 1) % self.trade_timestamps_capacity
        self.trade_timestamps_count += 1

        clock_gettime(CLOCK_MONOTONIC, &ts_end)

        cdef double check_time_us = (ts_end.tv_sec - ts_start.tv_sec) * 1000000.0 + (ts_end.tv_nsec - ts_start.tv_nsec) / 1000.0

        return True, "SAFE", check_time_us
