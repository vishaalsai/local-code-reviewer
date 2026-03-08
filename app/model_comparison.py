"""
Phase 3 — 3-model comparison study.

Runs all 10 evaluation prompts against each of:
  - llama3.2:3b
  - phi3.5:mini
  - qwen2.5-coder:3b

Records per run: tokens/sec, TTFT, total latency, RAM usage,
issues found, false positive flag on clean snippets.

Usage:
    python -m app.model_comparison
"""

import sys
import os
import json
import time
from datetime import datetime
from dataclasses import dataclass, field, asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psutil
import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich import box

from app.ollama_client import (
    OLLAMA_BASE_URL,
    SYSTEM_PROMPT,
    build_prompt,
    extract_json,
)
from tests.evaluation_prompts import EVALUATION_PROMPTS

console = Console()

MODELS = ["llama3.2:3b", "phi3.5:mini", "qwen2.5-coder:3b"]
CLEAN_IDS = {p["id"] for p in EVALUATION_PROMPTS if p["is_clean"]}
TOTAL_RUNS = len(MODELS) * len(EVALUATION_PROMPTS)


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class RunResult:
    model: str
    snippet_id: int
    category: str
    label: str
    is_clean: bool
    ok: bool
    issue_count: int
    overall_severity: str
    tokens_per_second: float
    time_to_first_token_ms: float
    total_latency_ms: float
    ram_used_mb: float
    false_positive: bool          # True if clean snippet got issues flagged
    parse_error: str = ""
    raw_response: str = ""


@dataclass
class ModelSummary:
    model: str
    avg_tokens_per_second: float
    avg_ttft_ms: float
    avg_latency_ms: float
    avg_ram_mb: float
    avg_issues_on_buggy: float
    false_positive_count: int
    false_positive_rate: float    # out of 2 clean snippets
    parse_failures: int
    total_runs: int


# ── Ollama call (model-switchable) ───────────────────────────────────────────

def _call_model(model: str, prompt: str) -> tuple[str, float, float, float]:
    """
    Returns (raw_text, tokens_per_second, ttft_ms, total_latency_ms).
    Raises on connection or HTTP error.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": True,
        "options": {"temperature": 0.0},
    }

    chunks: list[str] = []
    ttft_ms = 0.0
    first = False
    start = time.perf_counter()
    eval_count = 0
    eval_duration_ns = 0

    with httpx.Client(timeout=300.0) as client:
        with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if not first and chunk.get("response"):
                    ttft_ms = (time.perf_counter() - start) * 1000
                    first = True
                if chunk.get("response"):
                    chunks.append(chunk["response"])
                if chunk.get("done"):
                    eval_count = chunk.get("eval_count", 0)
                    eval_duration_ns = chunk.get("eval_duration", 0)
                    break

    total_ms = (time.perf_counter() - start) * 1000
    tps = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0.0
    return "".join(chunks), round(tps, 2), round(ttft_ms, 2), round(total_ms, 2)


def _ram_mb() -> float:
    proc = psutil.Process(os.getpid())
    return round(proc.memory_info().rss / 1024 / 1024, 1)


# ── Core runner ───────────────────────────────────────────────────────────────

def run_single(model: str, snippet: dict) -> RunResult:
    prompt = build_prompt(
        code=snippet["code"],
        language=snippet["language"],
        filename=None,
        strict=False,
    )

    ram_before = _ram_mb()

    try:
        raw, tps, ttft, latency = _call_model(model, prompt)
    except Exception as e:
        return RunResult(
            model=model,
            snippet_id=snippet["id"],
            category=snippet["category"],
            label=snippet["label"],
            is_clean=snippet["is_clean"],
            ok=False,
            issue_count=0,
            overall_severity="unknown",
            tokens_per_second=0.0,
            time_to_first_token_ms=0.0,
            total_latency_ms=0.0,
            ram_used_mb=_ram_mb() - ram_before,
            false_positive=False,
            parse_error=str(e),
            raw_response="",
        )

    ram_used = round(_ram_mb() - ram_before, 1)

    try:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        issue_count = len(data.get("issues", []))
        overall_severity = data.get("overall_severity", "unknown")
        false_positive = snippet["is_clean"] and issue_count > 0
        return RunResult(
            model=model,
            snippet_id=snippet["id"],
            category=snippet["category"],
            label=snippet["label"],
            is_clean=snippet["is_clean"],
            ok=True,
            issue_count=issue_count,
            overall_severity=overall_severity,
            tokens_per_second=tps,
            time_to_first_token_ms=ttft,
            total_latency_ms=latency,
            ram_used_mb=ram_used,
            false_positive=false_positive,
            raw_response=raw,
        )
    except Exception as e:
        return RunResult(
            model=model,
            snippet_id=snippet["id"],
            category=snippet["category"],
            label=snippet["label"],
            is_clean=snippet["is_clean"],
            ok=False,
            issue_count=0,
            overall_severity="unknown",
            tokens_per_second=tps,
            time_to_first_token_ms=ttft,
            total_latency_ms=latency,
            ram_used_mb=ram_used,
            false_positive=False,
            parse_error=str(e),
            raw_response=raw,
        )


def _summarise(model: str, runs: list[RunResult]) -> ModelSummary:
    ok = [r for r in runs if r.ok]
    buggy_ok = [r for r in ok if not r.is_clean]
    clean_ok = [r for r in ok if r.is_clean]

    def avg(vals):
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    fp_count = sum(1 for r in clean_ok if r.false_positive)

    return ModelSummary(
        model=model,
        avg_tokens_per_second=avg([r.tokens_per_second for r in ok]),
        avg_ttft_ms=avg([r.time_to_first_token_ms for r in ok]),
        avg_latency_ms=avg([r.total_latency_ms for r in ok]),
        avg_ram_mb=avg([r.ram_used_mb for r in ok]),
        avg_issues_on_buggy=avg([r.issue_count for r in buggy_ok]),
        false_positive_count=fp_count,
        false_positive_rate=round(fp_count / max(len(clean_ok), 1), 2),
        parse_failures=sum(1 for r in runs if not r.ok),
        total_runs=len(runs),
    )


# ── Rich output ───────────────────────────────────────────────────────────────

def _print_per_model_table(all_runs: dict[str, list[RunResult]]):
    table = Table(
        title="Per-Snippet Results (all models)",
        box=box.SIMPLE_HEAVY,
        show_lines=True,
    )
    table.add_column("ID", width=3, justify="right", style="dim")
    table.add_column("Category", width=6)
    table.add_column("Label", min_width=30, style="cyan")
    for model in MODELS:
        short = model.split(":")[0]
        table.add_column(f"{short}\nissues", justify="center", width=8)
        table.add_column(f"{short}\nms", justify="right", width=9)

    for snippet in EVALUATION_PROMPTS:
        sid = snippet["id"]
        row = [str(sid), snippet["category"], snippet["label"]]
        for model in MODELS:
            run = next((r for r in all_runs[model] if r.snippet_id == sid), None)
            if run is None:
                row += ["—", "—"]
            elif not run.ok:
                row += ["[red]ERR[/red]", "—"]
            else:
                fp_marker = " ⚠" if run.false_positive else ""
                sev_colors = {
                    "low": "green", "medium": "yellow",
                    "high": "orange3", "critical": "red", "unknown": "dim",
                }
                c = sev_colors.get(run.overall_severity, "white")
                row += [
                    f"[{c}]{run.issue_count}{fp_marker}[/{c}]",
                    f"{run.total_latency_ms:.0f}",
                ]
        table.add_row(*row)

    console.print(table)


def _print_summary_table(summaries: list[ModelSummary]):
    table = Table(
        title="Model Comparison Summary",
        box=box.HEAVY_EDGE,
        show_lines=True,
    )
    table.add_column("Model", style="bold cyan", min_width=20)
    table.add_column("Avg tok/s", justify="right", style="green")
    table.add_column("Avg TTFT (ms)", justify="right", style="yellow")
    table.add_column("Avg Latency (ms)", justify="right", style="magenta")
    table.add_column("Avg RAM Δ (MB)", justify="right")
    table.add_column("Avg Issues\n(buggy)", justify="right", style="red")
    table.add_column("False Positives\n/ 2 clean", justify="center")
    table.add_column("Parse\nFails", justify="center")

    for s in summaries:
        fp_display = f"{s.false_positive_count}/2"
        fp_color = "green" if s.false_positive_count == 0 else "red"
        pf_color = "green" if s.parse_failures == 0 else "red"
        table.add_row(
            s.model,
            str(s.avg_tokens_per_second),
            f"{s.avg_ttft_ms:.0f}",
            f"{s.avg_latency_ms:.0f}",
            f"{s.avg_ram_mb:.1f}",
            f"{s.avg_issues_on_buggy:.1f}",
            f"[{fp_color}]{fp_display}[/{fp_color}]",
            f"[{pf_color}]{s.parse_failures}[/{pf_color}]",
        )

    console.print(table)


# ── Main entry point ──────────────────────────────────────────────────────────

def run_comparison():
    console.print("\n[bold cyan]Phase 3 — Model Comparison Study[/bold cyan]")
    console.print(
        f"Models: [bold]{', '.join(MODELS)}[/bold]  ·  "
        f"Snippets: [bold]{len(EVALUATION_PROMPTS)}[/bold]  ·  "
        f"Total runs: [bold]{TOTAL_RUNS}[/bold]\n"
    )

    all_runs: dict[str, list[RunResult]] = {m: [] for m in MODELS}
    run_num = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
        transient=True,
    ) as progress:
        overall = progress.add_task("[cyan]Overall progress", total=TOTAL_RUNS)

        for model in MODELS:
            console.print(f"\n[bold yellow]▶ Running model: {model}[/bold yellow]")
            for snippet in EVALUATION_PROMPTS:
                run_num += 1
                desc = f"[white]{model}[/white] · [{snippet['category']}] {snippet['label'][:40]}"
                progress.update(overall, description=desc)

                result = run_single(model, snippet)
                all_runs[model].append(result)
                progress.advance(overall)

    # Print tables
    console.print()
    _print_per_model_table(all_runs)
    console.print()
    summaries = [_summarise(m, all_runs[m]) for m in MODELS]
    _print_summary_table(summaries)

    # Save JSON
    output = {
        "experiment_date": datetime.now().isoformat(),
        "hardware": "Intel i5-1155G7, CPU-only, 8GB RAM, Windows 11",
        "models": MODELS,
        "summaries": [asdict(s) for s in summaries],
        "runs": {
            model: [asdict(r) for r in runs]
            for model, runs in all_runs.items()
        },
    }
    out_path = os.path.join(
        os.path.dirname(__file__), "..", "results", "model_comparison.json"
    )
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    console.print(f"\n[dim]Full results saved to:[/dim] results/model_comparison.json")

    # Quick winner callout
    ok_summaries = [s for s in summaries if s.parse_failures < len(EVALUATION_PROMPTS)]
    if ok_summaries:
        fastest = min(ok_summaries, key=lambda s: s.avg_latency_ms)
        best_quality = max(ok_summaries, key=lambda s: s.avg_issues_on_buggy)
        lowest_fp = min(ok_summaries, key=lambda s: s.false_positive_rate)
        console.print("\n[bold]Quick callouts:[/bold]")
        console.print(f"  Fastest model      : [green]{fastest.model}[/green] ({fastest.avg_latency_ms:.0f} ms avg)")
        console.print(f"  Most issues found  : [yellow]{best_quality.model}[/yellow] ({best_quality.avg_issues_on_buggy:.1f} avg on buggy)")
        console.print(f"  Lowest false pos.  : [cyan]{lowest_fp.model}[/cyan] ({lowest_fp.false_positive_count}/2 clean snippets flagged)\n")


if __name__ == "__main__":
    run_comparison()
