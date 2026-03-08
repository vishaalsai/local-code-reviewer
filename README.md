# Local Code Reviewer

> **Project 2 of the AI Engineer Portfolio**

A local AI-powered code review assistant that runs entirely on your machine — no API keys, no cloud, no cost per token. Paste code, get back a structured review with bug identification, security warnings, and improvement suggestions.

Built with **Ollama** (local LLM inference) + **FastAPI** (REST API) + **llama3.2:3b**.

---

## Features

- Fully offline — all inference runs locally via Ollama
- REST API (`POST /review`) accepts code + language + filename
- Returns plain-text review with CRITICAL / WARNING / INFO severity labels
- Benchmark suite with `rich` table output measuring tokens/s, TTFT, and total latency
- Phase 2 (coming): structured JSON output, streaming responses

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

---

## Project Structure

```
local-code-reviewer/
├── app/
│   ├── main.py            # FastAPI app — /review, /health endpoints
│   ├── ollama_client.py   # Ollama REST client with TTFT + tok/s metrics
│   ├── schemas.py         # Pydantic request/response models
│   └── benchmarks.py      # Benchmark runner with rich table output
├── prompts/
│   └── code_review.txt    # Prompt template (language, filename, code)
├── tests/
│   └── sample_code.py     # 3 buggy functions for manual testing
├── results/
│   └── phase1_benchmarks.md
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

## Metrics Explained

| Metric | Description |
|--------|-------------|
| `tokens_per_second` | Generation speed reported by Ollama (`eval_count / eval_duration`) |
| `time_to_first_token_ms` | Wall-clock time until the first streamed token arrives |
| `total_latency_ms` | Wall-clock time for the complete response |
