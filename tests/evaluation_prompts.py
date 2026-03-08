"""
Standardized 10-snippet evaluation set for Phase 3 model comparison.

Categories:
  [div]    Division / null safety bugs        (2 snippets — IDs 1, 2)
  [sec]    Security issues                    (2 snippets — IDs 3, 4)
  [perf]   Performance issues                 (2 snippets — IDs 5, 6)
  [anti]   Python anti-patterns               (2 snippets — IDs 7, 8)
  [clean]  Correct functions (false-positive   (2 snippets — IDs 9, 10)
           control set — should have 0 issues)
"""

EVALUATION_PROMPTS = [
    # ── Division / null safety ────────────────────────────────────────────────
    {
        "id": 1,
        "category": "div",
        "label": "Division by zero on empty list",
        "language": "python",
        "expected_min_issues": 1,
        "is_clean": False,
        "code": """\
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)
""",
    },
    {
        "id": 2,
        "category": "div",
        "label": "None dereference before null check",
        "language": "python",
        "expected_min_issues": 1,
        "is_clean": False,
        "code": """\
def get_username(user):
    name = user.get("name")
    return name.strip().lower()
""",
    },
    # ── Security ──────────────────────────────────────────────────────────────
    {
        "id": 3,
        "category": "sec",
        "label": "SQL injection via f-string",
        "language": "python",
        "expected_min_issues": 1,
        "is_clean": False,
        "code": """\
def get_user(username, cursor):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
""",
    },
    {
        "id": 4,
        "category": "sec",
        "label": "Hardcoded secret in source",
        "language": "python",
        "expected_min_issues": 1,
        "is_clean": False,
        "code": """\
import requests

API_KEY = "sk-prod-9f2a1c8e4b7d3f6a"

def fetch_data(endpoint):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    return requests.get(endpoint, headers=headers).json()
""",
    },
    # ── Performance ───────────────────────────────────────────────────────────
    {
        "id": 5,
        "category": "perf",
        "label": "O(n²) nested loop for membership test",
        "language": "python",
        "expected_min_issues": 1,
        "is_clean": False,
        "code": """\
def find_common(list_a, list_b):
    common = []
    for item in list_a:
        for other in list_b:
            if item == other:
                common.append(item)
    return common
""",
    },
    {
        "id": 6,
        "category": "perf",
        "label": "Repeated DB query inside loop",
        "language": "python",
        "expected_min_issues": 1,
        "is_clean": False,
        "code": """\
def get_order_totals(order_ids, db):
    totals = []
    for order_id in order_ids:
        order = db.query(f"SELECT total FROM orders WHERE id = {order_id}")
        totals.append(order["total"])
    return totals
""",
    },
    # ── Anti-patterns ─────────────────────────────────────────────────────────
    {
        "id": 7,
        "category": "anti",
        "label": "Mutable default argument",
        "language": "python",
        "expected_min_issues": 1,
        "is_clean": False,
        "code": """\
def append_item(item, result=[]):
    result.append(item)
    return result
""",
    },
    {
        "id": 8,
        "category": "anti",
        "label": "Bare except swallowing all errors",
        "language": "python",
        "expected_min_issues": 1,
        "is_clean": False,
        "code": """\
def read_config(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        return None
""",
    },
    # ── Clean (false-positive control) ────────────────────────────────────────
    {
        "id": 9,
        "category": "clean",
        "label": "Correct safe average function",
        "language": "python",
        "expected_min_issues": 0,
        "is_clean": True,
        "code": """\
def calculate_average(numbers: list[float]) -> float:
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
""",
    },
    {
        "id": 10,
        "category": "clean",
        "label": "Correct parameterized DB query",
        "language": "python",
        "expected_min_issues": 0,
        "is_clean": True,
        "code": """\
def get_user(username: str, cursor) -> dict | None:
    cursor.execute(
        "SELECT * FROM users WHERE username = %s",
        (username,),
    )
    return cursor.fetchone()
""",
    },
]
