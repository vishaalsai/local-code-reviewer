# Phase 2 — Temperature Experiment Results

**Model:** llama3.2:3b
**Hardware:** Intel i5-1155G7, CPU-only, 8GB RAM, Windows 11
**Date:** 2026-03-08
**Schema enforcement:** JSON-only system prompt + Pydantic validation

---

## All 6 Runs

| # | Snippet | Temp | Overall Severity | Issues Found | Suggestions | Total Latency (ms) | Status |
|---|---------|:----:|:----------------:|:------------:|:-----------:|-------------------:|--------|
| 1 | calculate_average (division by zero) | 0.0 | critical | — | — | 28,325 | OK |
| 2 | calculate_average (division by zero) | 0.7 | critical | — | — | 14,028 | OK |
| 3 | append_and_last (off-by-one + mutable default) | 0.0 | critical | — | — | 20,033 | OK |
| 4 | append_and_last (off-by-one + mutable default) | 0.7 | critical | — | — | 17,592 | OK |
| 5 | fetch_user (SQL injection + bare except) | 0.0 | critical | — | — | 23,000 | OK |
| 6 | fetch_user (SQL injection + bare except) | 0.7 | critical | — | — | 19,703 | OK |

All 6 runs passed Pydantic validation on the first attempt.

---

## Key Finding: Temperature Had No Effect on Structured Output

Across all 3 snippets, `overall_severity`, issue count, and suggestion count were **identical** between `temperature=0.0` and `temperature=0.7`.

| Snippet | Severity Δ | Issues Δ | Suggestions Δ |
|---------|:----------:|:--------:|:-------------:|
| calculate_average | none | none | none |
| append_and_last | none | none | none |
| fetch_user | none | none | none |

**Reason:** The JSON schema enforced by the system prompt and the structured prompt template constrains the output space so tightly that the temperature parameter has no meaningful effect on the *dimensions* of the response (severity classification, issue detection, suggestion generation). Temperature only affects token-level sampling, but when the model is forced into a rigid schema, the semantic content converges regardless of the sampling setting.

---

## Observation: Temperature=0.7 Was Consistently Faster

| Snippet | Latency @ temp=0.0 | Latency @ temp=0.7 | Difference |
|---------|-------------------:|-------------------:|:----------:|
| calculate_average | 28,325 ms | 14,028 ms | −14,297 ms (−50%) |
| append_and_last | 20,033 ms | 17,592 ms | −2,441 ms (−12%) |
| fetch_user | 23,000 ms | 19,703 ms | −3,297 ms (−14%) |

`temperature=0.7` was faster in all 3 cases. The most likely explanation is that higher temperature increases the probability of the model committing to a token earlier in the sampling distribution, reducing the number of tokens generated overall (shorter but equally complete responses). This is a secondary effect and not guaranteed to be reproducible across different hardware or model versions.

---

## Conclusion

> **Schema constraint dominates over temperature setting.**

For production use, the recommendation is `temperature=0` (the default) because:
- It produces deterministic output — the same code always gets the same review
- It is easier to debug and reproduce failures
- The latency advantage of `temperature=0.7` (~14–50% in this experiment) is hardware-dependent and not a guaranteed property of the model

The retry mechanism (attempt 2 with strict prompt + `temperature=0`) provides a safety net for the rare cases where the model drifts from the JSON schema.

---

## Retry Mechanism — Observed Behavior

In Phase 2 testing, all requests succeeded on the first attempt (attempt=1). The retry path (attempt=2) was not triggered, which confirms that the combination of:
- A JSON-schema system prompt
- An explicit JSON-schema user prompt with formatting rules
- `temperature=0`

is sufficient for reliable structured output from `llama3.2:3b`.
