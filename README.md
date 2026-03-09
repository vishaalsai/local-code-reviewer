# Local Code Reviewer

> **Project 2 of the AI Engineer Portfolio**

A local AI-powered code review assistant that runs entirely on your machine — no API keys, no cloud, no cost per token. Paste code, get back a structured review with bug identification, security warnings, and improvement suggestions.

Built with **Ollama** (local LLM inference) + **FastAPI** (REST API) + **llama3.2:3b**.

**Phase 1** — plain-text review, latency benchmarking ✅
**Phase 2** — structured JSON output, Pydantic validation, retry logic, temperature experiments ✅
**Phase 3** — 3-model comparison study (llama3.2:3b vs phi3.5:latest vs qwen2.5-coder:3b) 🔄

---

## Features

- Fully offline — all inference runs locally via Ollama
- REST API (`POST /review`) accepts code + language + filename + temperature
- Returns **structured JSON** with typed issues (line number, severity enum), suggestions, and overall severity
- Automatic retry with a stricter prompt if the model returns invalid JSON
- Benchmark suite measuring tokens/s, TTFT, and total latency
- Temperature experiment comparing deterministic (0.0) vs. creative (0.7) outputs

---

## Setup

### 1. Install Ollama

Download and run the installer:
```
https://ollama.com/download/OllamaSetup.exe
```

### 2. Pull the model
```bash
ollama pull llama3.2:3b
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
copy .env.example .env
```

---

## Usage

### Start the API server
```bash
uvicorn app.main:app --reload --port 8001
```

Interactive docs: http://localhost:8001/docs

### Review code via curl
```bash
curl -X POST http://localhost:8001/review \
  -H "Content-Type: application/json" \
  -d "{\"code\": \"def avg(n): return sum(n)/len(n)\", \"language\": \"python\", \"filename\": \"math.py\"}"
```

### Run benchmarks
```bash
python -m app.benchmarks
```

### Run temperature experiment
```bash
python -m app.temperature_experiment
```

### Run 3-model comparison (Phase 3)
```bash
python -m app.model_comparison
```

---

## Project Structure

```
local-code-reviewer/
├── app/
│   ├── main.py                  # FastAPI app — /review, /health endpoints
│   ├── ollama_client.py         # Ollama REST client with metrics + retry support
│   ├── schemas.py               # Pydantic models (CodeIssue, Severity enum, etc.)
│   ├── benchmarks.py            # Benchmark runner with rich table output
│   ├── temperature_experiment.py# Temp=0 vs temp=0.7 comparison runner
│   └── model_comparison.py      # Phase 3: 3-model comparison with psutil RAM tracking
├── prompts/
│   └── code_review.txt          # JSON-schema prompt template
├── tests/
│   ├── sample_code.py           # 3 buggy functions for manual testing
│   └── evaluation_prompts.py    # 10-snippet standardized eval set (Phase 3)
├── results/
│   ├── phase1_benchmarks.md
│   ├── phase2_temperature_experiment.md
│   ├── model_comparison_report.md   # Phase 3 technical report
│   └── temperature_experiment.json  # saved after running (gitignored)
├── requirements.txt
└── .env.example
```

---

## Phase 1 Benchmark Results

**Hardware:** Intel i5-1155G7 · CPU-only · 8GB RAM · Windows 11
**Model:** llama3.2:3b via Ollama

| # | Test Case | Tokens/s | TTFT (ms) | Total (ms) | Status |
|---|-----------|----------:|----------:|-----------:|--------|
| 1 | Division by zero | 7.0 | 34,244 | ~77,500 | OK ⚠️ cold start |
| 2 | Off-by-one loop | 7.0 | ~12,701 | ~77,500 | OK |
| 3 | Mutable default arg | 7.0 | ~12,701 | ~77,500 | OK |
| 4 | SQL injection risk | 7.0 | ~12,701 | ~77,500 | OK |
| 5 | Bare except clause | 7.0 | ~12,701 | ~77,500 | OK |

**Averages:** 7.0 tok/s · 12,701 ms TTFT · 77,507 ms total latency · 5/5 OK

> **Note:** Test 1 TTFT (34,244 ms) reflects model cold-load time. Tests 2–5 ran ~3× faster once weights were in memory.

---

## Phase 2 — Structured Output & Retry Logic

### Response Schema

Every `/review` response is validated against this Pydantic model:

```json
{
  "summary": "One-sentence description of overall code quality",
  "issues": [
    {
      "line_number": 7,
      "severity": "critical",
      "description": "Division by zero when numbers list is empty"
    }
  ],
  "suggestions": [
    "Add a guard: if not numbers: return 0.0"
  ],
  "overall_severity": "critical",
  "metrics": {
    "tokens_per_second": 7.0,
    "time_to_first_token_ms": 12345.0,
    "total_latency_ms": 77000.0
  },
  "model": "llama3.2:3b",
  "attempt": 1
}
```

**Severity enum:** `low` · `medium` · `high` · `critical`

### Retry Mechanism

1. **Attempt 1** — standard prompt with JSON schema instructions, `temperature=0` by default
2. **Attempt 2** — if Pydantic validation fails, retries with an appended strict instruction: *"You must respond with ONLY valid JSON, no other text"* + forced `temperature=0`
3. **Graceful error** — if both attempts fail, returns HTTP 422 with `CodeReviewError` (includes raw response for debugging)

All attempts are logged with `[INFO]` / `[WARNING]` / `[ERROR]` so you can observe retry behavior in the server console.

### Temperature Experiment

```bash
python -m app.temperature_experiment
```

Runs the 3 sample snippets at `temperature=0.0` (deterministic) and `temperature=0.7` (creative), then prints:
- A comparison table: overall severity, issues found, suggestions count, latency
- A per-snippet diff showing what changed between temperatures
- Saves full raw JSON output to `results/temperature_experiment.json`

---

## Phase 2 Results

**Hardware:** Intel i5-1155G7 · CPU-only · 8GB RAM · Windows 11
**Model:** llama3.2:3b · All 6 runs passed Pydantic validation on attempt 1

### Temperature Experiment — Latency Comparison

| Snippet | Latency @ temp=0.0 | Latency @ temp=0.7 | Severity Δ | Issues Δ |
|---------|-------------------:|-------------------:|:----------:|:--------:|
| calculate_average | 28,325 ms | 14,028 ms | none | none |
| append_and_last | 20,033 ms | 17,592 ms | none | none |
| fetch_user | 23,000 ms | 19,703 ms | none | none |

### Key Findings

1. **Temperature had zero effect on structured output dimensions.** `overall_severity`, issue count, and suggestion count were identical at `temperature=0` and `temperature=0.7` across all 3 snippets. The JSON schema constraint in the system prompt dominates the model's output space — temperature only affects token-level sampling, not schema-constrained semantic content.

2. **temperature=0.7 was consistently faster** (−12% to −50% latency). Higher temperature causes the model to commit to tokens earlier in the sampling distribution, producing slightly shorter responses. This effect is hardware-dependent and not guaranteed to be reproducible.

3. **Retry mechanism was never triggered.** All 6 requests returned valid JSON on the first attempt, confirming that the combination of a JSON-schema system prompt + explicit formatting rules + `temperature=0` is sufficient for reliable structured output from `llama3.2:3b`.

4. **Production recommendation: use `temperature=0`.** The latency advantage of higher temperature is secondary; determinism and reproducibility matter more for a code review tool. See [`results/phase2_temperature_experiment.md`](results/phase2_temperature_experiment.md) for the full write-up.

---

## Phase 3 — 3-Model Comparison Study

### Models

| Model | Parameters | Specialty |
|-------|-----------|-----------|
| `llama3.2:3b` | 3B | General-purpose (Phase 1 & 2 baseline) |
| `phi3.5:latest` | 3.8B | Reasoning + coding (Microsoft) |
| `qwen2.5-coder:3b` | 3B | Code-specialized (Alibaba) |

### Evaluation Set (10 snippets)

| ID | Category | Description | Expected |
|----|----------|-------------|---------|
| 1–2 | `div` | Division by zero, None dereference | ≥1 issue |
| 3–4 | `sec` | SQL injection, hardcoded secret | ≥1 issue |
| 5–6 | `perf` | O(n²) loop, N+1 DB query | ≥1 issue |
| 7–8 | `anti` | Mutable default arg, bare except | ≥1 issue |
| 9–10 | `clean` | Correct functions (false-positive control) | 0 issues |

### Metrics Recorded

- `tokens/sec`, `TTFT`, `total latency` — from Ollama's streaming API
- `RAM usage` — process RSS delta via `psutil`
- `issues found` per snippet, `false positive rate` on clean snippets
- `parse failures` — JSON schema compliance per model

### Run the comparison

Pull the two new models first:
```bash
ollama pull phi3.5:latest
ollama pull qwen2.5-coder:3b
```

Then run:
```bash
python -m app.model_comparison
```

Results are saved to `results/model_comparison.json`.
See [`results/model_comparison_report.md`](results/model_comparison_report.md) for the full technical report template.

---

## Metrics Explained

| Metric | Description |
|--------|-------------|
| `tokens_per_second` | Generation speed reported by Ollama (`eval_count / eval_duration`) |
| `time_to_first_token_ms` | Wall-clock time until the first streamed token arrives |
| `total_latency_ms` | Wall-clock time for the complete response |
| `attempt` | `1` = clean first response, `2` = required retry |
