# 🛡️ HFT Risk Guard
*Ultra-Low Overhead Safety Gateway & Margin Monitor*

> [!NOTE]
> This module functions as a strict risk filter (the "Guardian" layer) to prevent catastrophic liquidation events. It sits on the hot execution path, blocking any trade packet that violates configured margin or risk thresholds in $<10$ microseconds.

## 🛡️ Risk Parameters
- **Drawdown Limit:** Rejects orders if peak-to-trough equity drop exceeds $2\%$.
- **Max Position Size:** Limits order sizes to prevent over-leveraging.
- **Velocity Limit:** Rejects trade packets if trade velocity (orders per second) spikes past threshold levels, protecting against algorithmic loops.

---

## ⚡ Execution Instructions
To test the risk management module:
```bash
python src/risk_barrier.py
```
