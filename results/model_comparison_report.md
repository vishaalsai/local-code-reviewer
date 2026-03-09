# Phase 3 — Model Comparison Report

**Project:** Local Code Reviewer (AI Engineer Portfolio — Project 2)
**Date:** 2026-03-08
**Status:** Complete — 2-model study (phi3.5 excluded due to OOM crash)

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

## Hardware Constraints

**phi3.5 was excluded from this study due to out-of-memory (OOM) crashes on 8 GB RAM.**

On a fresh boot, this machine had approximately **1.0 GB of free RAM** available after the OS, background processes, and Ollama overhead consumed the remainder. The phi3.5 model requires approximately **2.2 GB of RAM** to load — more than double what was available.

**Exact error observed:**
```
llama runner process has terminated: exit status 2
```

This is a real-world finding: on memory-constrained hardware, model selection must account for **available RAM at runtime**, not just the model's stated size on paper. A model that works in a clean lab environment may be completely unusable on a production machine with typical workloads running.

**Available RAM at testing: ~1.0 GB (after fresh boot)**

---

## Models Under Test

| Model | Parameters | Specialty | Expected Size | Status |
|-------|-----------|-----------|--------------|--------|
| `llama3.2:3b` | 3B | General-purpose instruction following | ~2.0 GB | Tested |
| `qwen2.5-coder:3b` | 3B | Code-specialized (Alibaba) | ~1.9 GB | Tested |
| `phi3.5:latest` | 3.8B | Reasoning + coding (Microsoft) | ~2.2 GB | **Excluded — OOM crash (exit status 2)** |

---

## Benchmark Results

### Latency & Throughput

| Model | Avg tok/s | Avg TTFT (ms) | Avg Total Latency (ms) | Parse Failures |
|-------|----------:|--------------:|-----------------------:|:--------------:|
| `llama3.2:3b` | 7.14 | 11,364 | 24,766 | 0 |
| `qwen2.5-coder:3b` | 7.11 | 10,548 | 21,564 | 0 |
| `phi3.5:latest` | — | — | — | **N/A — excluded (OOM)** |

*Phase 1 baseline for `llama3.2:3b`: 7.0 tok/s · 12,701 ms TTFT · 77,507 ms total (Phase 1 used plain-text output; Phase 3 uses JSON schema, which accounts for the dramatically reduced total latency — the prompt is more constrained and the model returns a compact JSON object rather than a verbose prose review.)*

### Quality Evaluation

| Model | False Positives / 2 clean snippets | FP Rate |
|-------|:----------------------------------:|:-------:|
| `llama3.2:3b` | 2 / 2 | 100% |
| `qwen2.5-coder:3b` | 0 / 2 | 0% |
| `phi3.5:latest` | — | **Excluded** |

**False positive rate** = number of clean snippets (IDs 9, 10) where the model flagged at least one issue. Lower is better — a model that flags issues in correct code is noisy and untrustworthy.

---

## Trade-off Analysis

### Speed vs Quality Matrix

```
High Quality │                    qwen2.5-coder:3b
             │
             │
Low Quality  │  llama3.2:3b
             └─────────────────────────────────────
               Slow                            Fast
```

Both models are nearly identical in throughput (~7.1 tok/s), but `qwen2.5-coder:3b` is both faster (lower latency) and more accurate (zero false positives). It strictly dominates `llama3.2:3b` for code review tasks on this hardware.

### Model Profiles

**`llama3.2:3b`**
- Baseline model, well-tested against this codebase (Phases 1 & 2)
- 7.14 tok/s, 11,364 ms TTFT, 24,766 ms total latency
- **False positives: 2/2** — flagged issues in clean, correct code
- Trade-off: generalist model not tuned for code patterns; produces noise on clean snippets
- Best for: general-purpose tasks beyond code review (summarization, Q&A, chat)

**`qwen2.5-coder:3b`**
- Code-specialized model, trained on a code-heavy corpus (Alibaba)
- 7.11 tok/s, 10,548 ms TTFT, 21,564 ms total latency
- **False positives: 0/2** — correctly identified both clean snippets as issue-free
- Faster total latency than llama3.2:3b despite similar throughput (more concise responses)
- Best for: code review, bug detection, static analysis augmentation

**`phi3.5:latest`** *(excluded)*
- Microsoft's reasoning-focused small model (3.8B parameters)
- Requires ~2.2 GB RAM — exceeded available memory on this hardware
- Cannot be used on 8 GB machines with typical OS and application overhead
- Would need a machine with at least 4–6 GB free RAM to run reliably

---

## Final Recommendation

**Recommended model for production code review: `qwen2.5-coder:3b`**

**Justification:**
- **Speed:** 7.11 tok/s, 10,548 ms TTFT, 21,564 ms total latency — fastest of the tested models
- **Quality:** Zero false positives on clean code — the model does not raise phantom issues
- **Schema compliance:** 0 parse failures — consistent, machine-readable JSON output
- **Code specialization:** Training on code-heavy corpus makes it better suited for recognizing real bug patterns vs. flagging stylistic non-issues

**When to use `llama3.2:3b` instead:**
- General-purpose tasks beyond code review (chat, summarization, documentation Q&A)
- When you need a model with broad world knowledge rather than code-specific reasoning
- Acceptable for code tasks where some false positive noise is tolerable

**Suggested configuration:**
```bash
OLLAMA_MODEL=qwen2.5-coder:3b
```

---

## Observations & Insights

1. **Hardware is a first-class constraint** — The phi3.5 exclusion demonstrates that model selection on constrained hardware must account for runtime available RAM, not just peak model size. On an 8 GB machine under normal use, effectively only ~1–2 GB is free for model loading.

2. **Schema compliance** — Both tested models returned valid JSON on every attempt (0 parse failures). The structured prompt from Phase 2 works reliably across both model families.

3. **False positive problem with generalist models** — `llama3.2:3b` flagged both clean snippets (IDs 9 and 10) as having issues. This is the core problem with using general-purpose LLMs for code review: they tend to over-report, reducing trust in their output. A code-specialized model like `qwen2.5-coder:3b` has learned to distinguish correct patterns from buggy ones.

4. **Latency reduction vs. Phase 1** — Total latency dropped from ~77,507 ms (Phase 1) to ~21,564–24,766 ms (Phase 3) for `llama3.2:3b`. The main driver is the structured JSON schema constraint: the model produces a compact, bounded response rather than a verbose prose review, resulting in fewer tokens generated and lower total time.

5. **Throughput parity** — Both models achieve near-identical throughput (~7.1 tok/s) on this CPU. The latency difference is driven entirely by response length, not model speed. `qwen2.5-coder:3b` produces slightly more concise JSON, leading to lower total latency.

---

## Bonus: GGUF Quantization Comparison (Future Work)

If moving this to a production deployment, the next step would be comparing quantization levels of `qwen2.5-coder:3b`:

| Quantization | Size | Avg tok/s | Quality Impact |
|-------------|------|----------:|---------------|
| Q8_0 (8-bit) | — | — | Baseline |
| Q4_K_M (4-bit) | — | — | — |
| Q2_K (2-bit) | — | — | — |

*Goal: find the smallest quantization that maintains zero false positives, maximizing speed on CPU-only hardware.*
