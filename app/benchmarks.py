import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from app.ollama_client import review_code

console = Console()

TEST_SNIPPETS = [
    {
        "label": "Division by zero",
        "language": "python",
        "code": """
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)
""",
    },
    {
        "label": "Off-by-one loop",
        "language": "python",
        "code": """
def get_last_element(items):
    return items[len(items)]
""",
    },
    {
        "label": "Mutable default arg",
        "language": "python",
        "code": """
def append_item(item, lst=[]):
    lst.append(item)
    return lst
""",
    },
    {
        "label": "SQL injection risk",
        "language": "python",
        "code": """
def get_user(username):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return db.execute(query)
""",
    },
    {
        "label": "Bare except clause",
        "language": "python",
        "code": """
def read_config(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        return None
""",
    },
]


def run_benchmarks():
    console.print("\n[bold cyan]Local Code Reviewer — Benchmark Suite[/bold cyan]")
    console.print(f"Running [bold]{len(TEST_SNIPPETS)}[/bold] test prompts against Ollama...\n")

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        for i, snippet in enumerate(TEST_SNIPPETS, 1):
            task = progress.add_task(
                f"[yellow]Running test {i}/{len(TEST_SNIPPETS)}: {snippet['label']}...", total=None
            )
            try:
                metrics = review_code(
                    code=snippet["code"],
                    language=snippet["language"],
                )
                results.append(
                    {
                        "label": snippet["label"],
                        "tokens_per_second": metrics.tokens_per_second,
                        "time_to_first_token_ms": metrics.time_to_first_token_ms,
                        "total_latency_ms": metrics.total_latency_ms,
                        "status": "OK",
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "label": snippet["label"],
                        "tokens_per_second": 0,
                        "time_to_first_token_ms": 0,
                        "total_latency_ms": 0,
                        "status": f"ERROR: {e}",
                    }
                )
            finally:
                progress.remove_task(task)

    table = Table(title="Benchmark Results", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Test Case", style="cyan", min_width=22)
    table.add_column("Tokens/s", justify="right", style="green")
    table.add_column("TTFT (ms)", justify="right", style="yellow")
    table.add_column("Total (ms)", justify="right", style="magenta")
    table.add_column("Status", style="bold")

    total_tps = total_ttft = total_latency = 0
    ok_count = 0

    for i, r in enumerate(results, 1):
        status_style = "green" if r["status"] == "OK" else "red"
        table.add_row(
            str(i),
            r["label"],
            f"{r['tokens_per_second']:.1f}",
            f"{r['time_to_first_token_ms']:.0f}",
            f"{r['total_latency_ms']:.0f}",
            f"[{status_style}]{r['status']}[/{status_style}]",
        )
        if r["status"] == "OK":
            total_tps += r["tokens_per_second"]
            total_ttft += r["time_to_first_token_ms"]
            total_latency += r["total_latency_ms"]
            ok_count += 1

    console.print(table)

    if ok_count > 0:
        console.print("\n[bold]Averages across successful runs:[/bold]")
        console.print(f"  Tokens/s        : [green]{total_tps / ok_count:.1f}[/green]")
        console.print(f"  Time to 1st token: [yellow]{total_ttft / ok_count:.0f} ms[/yellow]")
        console.print(f"  Total latency   : [magenta]{total_latency / ok_count:.0f} ms[/magenta]")
    console.print()


if __name__ == "__main__":
    run_benchmarks()
