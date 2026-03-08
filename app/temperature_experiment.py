"""
Temperature experiment: run the 3 sample buggy functions at temperature=0 and
temperature=0.7, then compare structured outputs side by side.

Usage:
    python -m app.temperature_experiment
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from pydantic import ValidationError

from app.ollama_client import review_code, extract_json
from app.schemas import CodeReviewResponse, CodeIssue, ReviewMetrics, Severity

console = Console()

SNIPPETS = [
    {
        "label": "calculate_average (division by zero)",
        "language": "python",
        "code": """\
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)
""",
    },
    {
        "label": "append_and_last (off-by-one + mutable default)",
        "language": "python",
        "code": """\
def append_and_last(item, history=[]):
    history.append(item)
    return history[len(history)]
""",
    },
    {
        "label": "fetch_user (SQL injection + bare except)",
        "language": "python",
        "code": """\
def fetch_user(username, db_cursor):
    try:
        query = f"SELECT * FROM users WHERE username = '{username}'"
        db_cursor.execute(query)
        return db_cursor.fetchone()
    except:
        return None
""",
    },
]

TEMPERATURES = [0.0, 0.7]


def run_single(snippet: dict, temperature: float) -> dict:
    result = review_code(
        code=snippet["code"],
        language=snippet["language"],
        temperature=temperature,
    )
    raw = result.raw_text
    try:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        return {
            "ok": True,
            "summary": data.get("summary", ""),
            "overall_severity": data.get("overall_severity", "unknown"),
            "issue_count": len(data.get("issues", [])),
            "suggestion_count": len(data.get("suggestions", [])),
            "issues": data.get("issues", []),
            "suggestions": data.get("suggestions", []),
            "metrics": {
                "tokens_per_second": result.tokens_per_second,
                "time_to_first_token_ms": result.time_to_first_token_ms,
                "total_latency_ms": result.total_latency_ms,
            },
            "raw": raw,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "raw": raw,
            "metrics": {
                "tokens_per_second": result.tokens_per_second,
                "time_to_first_token_ms": result.time_to_first_token_ms,
                "total_latency_ms": result.total_latency_ms,
            },
        }


def run_experiment():
    console.print("\n[bold cyan]Temperature Experiment — Local Code Reviewer[/bold cyan]")
    console.print(f"Snippets: [bold]{len(SNIPPETS)}[/bold]  ·  Temperatures: {TEMPERATURES}\n")

    all_results = {}
    total_runs = len(SNIPPETS) * len(TEMPERATURES)
    run_num = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        for snippet in SNIPPETS:
            all_results[snippet["label"]] = {}
            for temp in TEMPERATURES:
                run_num += 1
                task = progress.add_task(
                    f"[yellow]Run {run_num}/{total_runs}: '{snippet['label']}' @ temp={temp}...",
                    total=None,
                )
                all_results[snippet["label"]][str(temp)] = run_single(snippet, temp)
                progress.remove_task(task)

    # --- Comparison table ---
    table = Table(title="Temperature Comparison Results", show_lines=True)
    table.add_column("Snippet", style="cyan", min_width=30)
    table.add_column("Temp", justify="center", width=6)
    table.add_column("Overall Severity", justify="center", style="bold")
    table.add_column("Issues Found", justify="right", style="yellow")
    table.add_column("Suggestions", justify="right", style="green")
    table.add_column("Latency (ms)", justify="right", style="magenta")
    table.add_column("Status", justify="center")

    for label, temp_results in all_results.items():
        for temp_str, r in temp_results.items():
            sev = r.get("overall_severity", "N/A")
            sev_colors = {"low": "green", "medium": "yellow", "high": "orange3", "critical": "red", "unknown": "dim"}
            sev_color = sev_colors.get(sev, "white")
            status = "[green]OK[/green]" if r.get("ok") else "[red]PARSE ERROR[/red]"
            table.add_row(
                label,
                temp_str,
                f"[{sev_color}]{sev}[/{sev_color}]",
                str(r.get("issue_count", "—")),
                str(r.get("suggestion_count", "—")),
                f"{r['metrics']['total_latency_ms']:.0f}",
                status,
            )

    console.print(table)

    # --- Save raw results ---
    output = {
        "experiment_date": datetime.now().isoformat(),
        "model": "llama3.2:3b",
        "temperatures": TEMPERATURES,
        "results": all_results,
    }
    out_path = os.path.join(os.path.dirname(__file__), "..", "results", "temperature_experiment.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    console.print(f"\n[dim]Raw results saved to:[/dim] results/temperature_experiment.json\n")

    # --- Per-snippet diff summary ---
    console.print("[bold]Differences between temperature=0 and temperature=0.7:[/bold]\n")
    for label, temp_results in all_results.items():
        r0 = temp_results.get("0.0", {})
        r7 = temp_results.get("0.7", {})
        if not r0.get("ok") or not r7.get("ok"):
            console.print(f"  [yellow]{label}[/yellow]: one or both runs had parse errors — skipping diff")
            continue

        sev_same = r0["overall_severity"] == r7["overall_severity"]
        issue_delta = r7["issue_count"] - r0["issue_count"]
        sug_delta = r7["suggestion_count"] - r0["suggestion_count"]

        console.print(f"  [cyan]{label}[/cyan]")
        console.print(
            f"    Overall severity : {r0['overall_severity']} → {r7['overall_severity']} "
            + ("[green](same)[/green]" if sev_same else "[yellow](changed)[/yellow]")
        )
        delta_color = "yellow" if issue_delta != 0 else "green"
        console.print(f"    Issues found     : {r0['issue_count']} → {r7['issue_count']}  [{delta_color}](Δ {issue_delta:+d})[/{delta_color}]")
        delta_color2 = "yellow" if sug_delta != 0 else "green"
        console.print(f"    Suggestions      : {r0['suggestion_count']} → {r7['suggestion_count']}  [{delta_color2}](Δ {sug_delta:+d})[/{delta_color2}]\n")


if __name__ == "__main__":
    run_experiment()
