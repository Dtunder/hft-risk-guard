# cython: boundscheck=False, wraparound=False, nonecheck=False, cdivision=True, language_level=3

cdef extern from "<time.h>" nogil:
    struct timespec:
        long tv_sec
        long tv_nsec
    int clock_gettime(int clk_id, timespec *tp)
    int CLOCK_MONOTONIC

cdef inline long long current_ns() nogil:
    cdef timespec ts
    clock_gettime(CLOCK_MONOTONIC, &ts)
    return ts.tv_sec * 1000000000LL + ts.tv_nsec

cdef class FastRiskGuard:
    cdef public double max_position
    cdef public double max_drawdown
    cdef public int max_trades_per_sec
    cdef public double peak_equity
    cdef public double current_equity
    cdef public double current_position

    # Velocity tracking ring buffer for max speed
    cdef long long[1024] trade_timestamps
    cdef int trade_head
    cdef int trade_count

    def __init__(self, double max_position=10.0, double max_drawdown=0.02, int max_trades_per_sec=20):
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.max_trades_per_sec = max_trades_per_sec
        self.peak_equity = 100000.0
        self.current_equity = 100000.0
        self.current_position = 0.0
        self.trade_head = 0
        self.trade_count = 0
        for i in range(1024):
            self.trade_timestamps[i] = 0

    cpdef void update_portfolio(self, double current_equity, double current_position):
        self.current_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        self.current_position = current_position

    cpdef tuple check_safety(self, int is_buy, double order_qty):
        # Using integer for `is_buy` (1 for BUY, 0 for SELL)
        cdef long long start_time = current_ns()
        cdef long long now = start_time

        cdef double current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity

        cdef double potential_pos = self.current_position + (order_qty if is_buy else -order_qty)
        cdef double abs_pos = potential_pos if potential_pos > 0 else -potential_pos

        # Velocity logic
        # Clean up old timestamps (older than 1 second = 1,000,000,000 ns)
        cdef int active_trades = 0
        cdef int i
        cdef long long t
        for i in range(self.trade_count):
            t = self.trade_timestamps[(self.trade_head - 1 - i) & 1023]
            if now - t < 1000000000LL:
                active_trades += 1
            else:
                break

        # Purely bitwise operations for check
        cdef int draw_ok = current_drawdown <= self.max_drawdown
        cdef int pos_ok = abs_pos <= self.max_position
        cdef int rate_ok = active_trades < self.max_trades_per_sec

        # Bitwise AND to check safety
        cdef int is_safe = draw_ok & pos_ok & rate_ok

        cdef long long check_time_ns

        if is_safe:
            self.trade_timestamps[self.trade_head] = now
            self.trade_head = (self.trade_head + 1) & 1023
            if self.trade_count < 1024:
                self.trade_count += 1
            check_time_ns = current_ns() - start_time
            return True, "SAFE", check_time_ns
        else:
            check_time_ns = current_ns() - start_time
            if not draw_ok:
                return False, f"ABORT: Maximum drawdown limit exceeded! ({current_drawdown*100:.2f}%)", 0.0
            elif not pos_ok:
                return False, f"ABORT: Maximum position size exceeded! (Limit: {self.max_position} | Target: {abs_pos:.2f})", 0.0
            else:
                return False, f"ABORT: Order rate limit exceeded! ({active_trades} trades/sec)", 0.0
