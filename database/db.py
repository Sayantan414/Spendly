import os
import sqlite3
import calendar
from datetime import date

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "expense_tracker.db")

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

CREATE_EXPENSES_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id)
)
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute(CREATE_USERS_TABLE)
        conn.execute(CREATE_EXPENSES_TABLE)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        if row["n"] > 0:
            return

        password_hash = generate_password_hash("demo123")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        today = date.today()
        _, days_in_month = calendar.monthrange(today.year, today.month)

        def day(n):
            return date(today.year, today.month, min(n, days_in_month)).isoformat()

        sample_expenses = [
            (user_id, 12.50, "Food", day(2), "Groceries at supermarket"),
            (user_id, 45.00, "Transport", day(4), "Monthly metro pass"),
            (user_id, 89.99, "Bills", day(5), "Electricity bill"),
            (user_id, 25.00, "Health", day(8), "Pharmacy - vitamins"),
            (user_id, 15.00, "Entertainment", day(11), "Movie ticket"),
            (user_id, 60.00, "Shopping", day(15), "New running shoes"),
            (user_id, 9.75, "Food", day(19), "Lunch with coworkers"),
            (user_id, 20.00, "Other", day(23), "Miscellaneous donation"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            sample_expenses,
        )
        conn.commit()
    finally:
        conn.close()
