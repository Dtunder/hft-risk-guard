import time
import sys
import os

# Ensure the compiled module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fast_risk import FastRiskGuard

def test_latency():
    guard = FastRiskGuard(max_position=10.0, max_drawdown=0.02, max_trades_per_sec=20)

    # Warmup
    for _ in range(100):
        guard.check_safety(1, 1.0)

    # Benchmark
    iterations = 100000
    total_latency_ns = 0

    start = time.perf_counter_ns()
    for _ in range(iterations):
        guard.check_safety(1, 1.0)
    end = time.perf_counter_ns()

    avg_latency_ns = (end - start) / iterations

    print(f"Average Latency: {avg_latency_ns:.2f} ns")

    # Assert execution is under 500 nanoseconds
    assert avg_latency_ns < 500, f"Latency {avg_latency_ns:.2f} ns exceeds 500 ns threshold!"

    # Write proof to logs
    os.makedirs('logs', exist_ok=True)
    with open('logs/nanosecond_proof.txt', 'w') as f:
        f.write(f"Average Latency: {avg_latency_ns:.2f} ns\n")
        f.write("Successfully executed under 500 nanoseconds threshold using purely bitwise operations in Cython.")

if __name__ == "__main__":
    test_latency()
