# Sample Python functions with intentional bugs — used for testing the code reviewer.


# Bug 1: Division by zero when the list is empty.
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)  # ZeroDivisionError if numbers is []


# Bug 2: Off-by-one index error; also uses mutable default argument.
def append_and_last(item, history=[]):
    history.append(item)
    # BUG: len(history) is out of range — should be len(history) - 1
    return history[len(history)]


# Bug 3: SQL injection via f-string interpolation; bare except swallows all errors.
def fetch_user(username, db_cursor):
    try:
        query = f"SELECT * FROM users WHERE username = '{username}'"
        db_cursor.execute(query)  # CRITICAL: user input injected directly
        return db_cursor.fetchone()
    except:  # WARNING: bare except hides all exceptions including KeyboardInterrupt
        return None
