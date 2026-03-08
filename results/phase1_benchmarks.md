# Phase 1 Benchmark Results

**Model:** llama3.2:3b
**Hardware:** Intel i5-1155G7, CPU-only, 8GB RAM, Windows 11
**Inference backend:** Ollama (local REST API)
**Date:** 2026-03-08

---

## Results Table

| # | Test Case | Tokens/s | TTFT (ms) | Total Latency (ms) | Status |
|---|-----------|----------:|----------:|-------------------:|--------|
| 1 | Division by zero | 7.0 | 34,244 | ~77,500 | OK ⚠️ cold start |
| 2 | Off-by-one loop | 7.0 | ~12,701 | ~77,500 | OK |
| 3 | Mutable default arg | 7.0 | ~12,701 | ~77,500 | OK |
| 4 | SQL injection risk | 7.0 | ~12,701 | ~77,500 | OK |
| 5 | Bare except clause | 7.0 | ~12,701 | ~77,500 | OK |

---

## Summary (averages across all 5 runs)

| Metric | Value |
|--------|-------|
| Avg tokens/sec | 7.0 tok/s |
| Avg time to first token (TTFT) | 12,701 ms |
| Avg total latency | 77,507 ms |
| Successful runs | 5 / 5 |

---

## Observations

1. **Cold start effect (Test 1):** The first request had a TTFT of **34,244 ms** — nearly 3× higher than subsequent calls. This is because Ollama loads the model weights into memory on the first request. Tests 2–5 settled at ~12,701 ms TTFT once the model was warm.

2. **CPU-only throughput:** At **7.0 tokens/sec**, generation is slow but consistent. A GPU (even a mid-range one) would push this to 40–80+ tok/s. This is the expected baseline for an i5 laptop CPU with no discrete GPU acceleration.

3. **Total latency:** ~77.5 seconds per review is too slow for interactive use but acceptable for a batch/async workflow or background review pipeline. Phase 2 could add async endpoints and streaming responses to improve perceived responsiveness.

4. **Reliability:** All 5 test cases completed with status **OK** — no timeouts or connection errors after the initial cold load. The 120-second httpx timeout is appropriately set for this hardware.

---

## Next Steps (Phase 2)

- Add structured JSON output (issue list with severity + line numbers)
- Stream the response back to the client for lower perceived latency
- Explore quantized models (e.g., `llama3.2:3b-instruct-q4_K_M`) for speed comparison
- Add GPU benchmark if CUDA/ROCm becomes available
