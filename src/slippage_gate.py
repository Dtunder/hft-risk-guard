import time

class AdaptiveSlippageGate:
    """
    Dynamically adjusts allowable slippage based on real-time order book depth
    and recent volatility. Implements a Token-Bucket rate throttler.
    """
    def __init__(self, base_slippage=0.001, max_slippage=0.05, bucket_capacity=10.0, refill_rate=5.0):
        # Slippage parameters
        self.base_slippage = base_slippage
        self.max_slippage = max_slippage

        # State
        self.order_book_depth = 1.0  # normalized depth, higher is deeper/more liquid
        self.volatility = 0.0        # normalized volatility

        # Token-Bucket parameters
        self.bucket_capacity = float(bucket_capacity)
        self.refill_rate = float(refill_rate)

        # Token-Bucket state
        self.tokens = float(bucket_capacity)
        self.last_refill_time = time.monotonic()

    def update(self, order_book_depth=None, volatility=None):
        """
        Updates the internal state. Returns self to support method chaining.
        """
        if order_book_depth is not None:
            # Avoid divide by zero by clamping depth to a small positive value
            self.order_book_depth = max(0.0001, float(order_book_depth))
        if volatility is not None:
            self.volatility = max(0.0, float(volatility))
        return self

    def slippage_limit(self):
        """
        Calculates the dynamic slippage limit based on current state.
        Higher volatility -> higher allowable slippage.
        Higher depth -> lower allowable slippage (market can absorb without moving much).
        """
        # Dynamic component: volatility / depth
        # Scale factor arbitrary for logic implementation, e.g. 0.01
        dynamic_factor = 0.01 * (self.volatility / self.order_book_depth)

        calculated_slippage = self.base_slippage + dynamic_factor
        return min(calculated_slippage, self.max_slippage)

    def _refill_tokens(self):
        """
        Refills the token bucket based on elapsed time.
        """
        now = time.monotonic()
        elapsed = now - self.last_refill_time
        new_tokens = elapsed * self.refill_rate

        self.tokens = min(self.bucket_capacity, self.tokens + new_tokens)
        self.last_refill_time = now

    def check_rate_limit(self, tokens_needed=1.0):
        """
        Consumes tokens if available.
        Returns True if the action is allowed, False if throttled.
        """
        self._refill_tokens()
        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            return True
        return False
