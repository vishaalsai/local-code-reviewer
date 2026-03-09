# Phase 3 — Model Comparison Report

**Project:** Local Code Reviewer (AI Engineer Portfolio — Project 2)
**Date:** 2026-03-08
**Status:** Template — fill in actual numbers after running `python -m app.model_comparison`

---

## Hardware Context

| Property | Value |
|----------|-------|
| CPU | Intel Core i5-1155G7 (4 cores / 8 threads, 2.5 GHz base) |
| RAM | 8 GB DDR4 |
| GPU | None (CPU-only inference) |
| OS | Windows 11 Home |
| Inference backend | Ollama (local REST API) |
| Quantization | Default Ollama quantization per model |

All models run in the same process, sequentially, with no GPU acceleration. Results represent worst-case consumer hardware conditions.

---

## Models Under Test

| Model | Parameters | Specialty | Expected Size |
|-------|-----------|-----------|--------------|
| `llama3.2:3b` | 3B | General-purpose instruction following | ~2.0 GB |
| `phi3.5:latest` | 3.8B | Reasoning + coding (Microsoft) | ~2.2 GB |
| `qwen2.5-coder:3b` | 3B | Code-specialized (Alibaba) | ~1.9 GB |

---

## Benchmark Results

> Replace the placeholder values below with actual numbers from `results/model_comparison.json`

### Latency & Throughput

| Model | Avg tok/s | Avg TTFT (ms) | Avg Total Latency (ms) | Avg RAM Δ (MB) | Parse Failures |
|-------|----------:|--------------:|-----------------------:|---------------:|:--------------:|
| `llama3.2:3b` | — | — | — | — | — |
| `phi3.5:latest` | — | — | — | — | — |
| `qwen2.5-coder:3b` | — | — | — | — | — |

*Phase 1 baseline for `llama3.2:3b`: 7.0 tok/s · 12,701 ms TTFT · 77,507 ms total (Phase 1 used plain-text output; Phase 3 uses JSON schema, expect slightly higher latency)*

### Quality Evaluation

| Model | Avg Issues Found (buggy) | False Positives / 2 clean | FP Rate |
|-------|:------------------------:|:-------------------------:|:-------:|
| `llama3.2:3b` | — | — | — |
| `phi3.5:latest` | — | — | — |
| `qwen2.5-coder:3b` | — | — | — |

**False positive rate** = number of clean snippets (IDs 9, 10) where the model flagged at least one issue. Lower is better — a model that flags issues in correct code is noisy and untrustworthy.

### Per-Category Issue Detection

| Category | Description | `llama3.2:3b` | `phi3.5:latest` | `qwen2.5-coder:3b` |
|----------|-------------|:-------------:|:-------------:|:------------------:|
| `div` | Division / null safety (IDs 1–2) | — | — | — |
| `sec` | Security: SQL injection, hardcoded secrets (IDs 3–4) | — | — | — |
| `perf` | Performance: O(n²) loop, DB call in loop (IDs 5–6) | — | — | — |
| `anti` | Anti-patterns: mutable default, bare except (IDs 7–8) | — | — | — |
| `clean` | Correct code — should be 0 issues (IDs 9–10) | — | — | — |

---

## Trade-off Analysis

### Speed vs Quality Matrix

```
High Quality │  ??              ??
             │
             │
Low Quality  │  ??              ??
             └─────────────────────────
               Slow            Fast
```

*(Fill in model names after running the experiment)*

### Model Profiles

**`llama3.2:3b`**
- Baseline model, well-tested against this codebase (Phases 1 & 2)
- Known: 7.0 tok/s on this hardware, 100% schema compliance in Phase 2
- Trade-off: generalist model, not code-specialized

**`phi3.5:latest`**
- Microsoft's reasoning-focused small model
- Expected strength: logical reasoning about bugs and null safety
- Expected weakness: may over-explain, producing longer responses that inflate latency

**`qwen2.5-coder:3b`**
- Code-specialized model, trained on code-heavy corpus
- Expected strength: better at recognizing code-specific patterns (SQL injection, perf issues)
- Expected weakness: possibly over-sensitive — higher false positive rate on clean code

---

## Final Recommendation

> *To be filled after running the experiment. Template below:*

**Recommended model for production: `___________`**

**Justification:**
- Speed: ___________
- Quality (avg issues on buggy snippets): ___________
- False positive rate: ___________
- Schema compliance: ___________

**Runner-up for quality-first use cases:** `___________`

**Suggested configuration:**
```bash
OLLAMA_MODEL=___________
```

---

## Observations & Insights

*(To be filled after experiment)*

1. **Schema compliance** — did all models return valid JSON on the first attempt, or did any require retries?
2. **Security detection** — which model best caught the SQL injection (ID 3) and hardcoded secret (ID 4)?
3. **Performance detection** — which model identified the O(n²) loop (ID 5) and N+1 query (ID 6)?
4. **False positives** — did any model flag the correct parameterized query (ID 10) as insecure?

---

## Bonus: GGUF Quantization Comparison (Placeholder)

This section will compare different quantization levels of the winning model once GGUF files are available:

| Quantization | Size | Avg tok/s | Quality Impact |
|-------------|------|----------:|---------------|
| Q8_0 (8-bit) | — | — | Baseline |
| Q4_K_M (4-bit) | — | — | — |
| Q2_K (2-bit) | — | — | — |

*Goal: find the smallest quantization that maintains detection quality, maximizing speed on CPU-only hardware.*
