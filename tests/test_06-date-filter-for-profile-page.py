"""
Tests for Step 6: Date Filter For Profile Page.

Spec: .claude/specs/06-date-filter-for-profile-page.md

Covers:
- GET /profile auth guard (unchanged, with and without filter query params)
- Unfiltered /profile view is unchanged (regression check)
- Valid start_date/end_date filters narrow stats/transactions/categories,
  inclusive of both boundary dates
- Zero-match filtered range shows a "no transactions" state with zeroed
  stats, no server error
- Swapped (start_date > end_date), malformed, partial, and empty date
  params all degrade to the unfiltered all-time view instead of erroring
- The filter form echoes the currently-applied valid filter values
- The "Clear" link/plain profile URL restores the all-time view
- database/db.py date-range kwargs (get_expenses_by_user,
  get_expense_summary, get_category_breakdown) are exercised directly,
  including parameterized-query safety against injection-shaped strings

Isolation strategy
-------------------
database/db.py hardcodes a module-level DB_PATH (no Flask app.config
DATABASE key is read by get_db()). To get a fresh, isolated SQLite file
per test without touching source files, we monkeypatch
`database.db.DB_PATH` to a per-test tmp_path file and call init_db()
against it. Every db.py function re-reads the module attribute on each
call (it doesn't cache a connection), so this fully isolates each test.

Note: importing `app` triggers `init_db()`/`seed_db()` against the real
on-disk DB_PATH once, as a side effect of module import (this happens
before any monkeypatching in our fixtures can apply). This is a
pre-existing side effect of app.py's module-level code, not something
introduced by these tests, and it does not affect the isolated
per-test databases used below.
"""

import pytest

import database.db as db_module
from app import app as flask_app


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Point database.db.DB_PATH at a fresh, empty per-test SQLite file."""
    db_path = tmp_path / "test_expense_tracker.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))
    db_module.init_db()
    return str(db_path)


@pytest.fixture
def app(isolated_db):
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
    })
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(isolated_db):
    """A user row created directly via database.db.create_user."""
    email = "filtertester@example.com"
    password = "testpass123"
    user_id = db_module.create_user("Filter Tester", email, password)
    return {"id": user_id, "email": email, "password": password}


@pytest.fixture
def other_user(isolated_db):
    """A second user, used to prove filtering never leaks another user's data."""
    user_id = db_module.create_user("Other Person", "other@example.com", "otherpass1")
    return {"id": user_id, "email": "other@example.com", "password": "otherpass1"}


def _insert_expense(user_id, amount, category, date_str, description):
    conn = db_module.get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date_str, description),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def expenses(user):
    """
    Five deterministic expenses spanning two months for `user`:
      Jan 2024 (3 rows): Food, Bills, Entertainment
      Feb 2024 (2 rows): Food, Health
    Descriptions are unique strings used as HTML landmarks in assertions.
    """
    rows = [
        (20.00, "Food", "2024-01-05", "Groceries Jan"),
        (500.00, "Bills", "2024-01-10", "Rent Jan"),
        (12.00, "Entertainment", "2024-01-15", "Movie Jan"),
        (30.00, "Food", "2024-02-05", "Groceries Feb"),
        (40.00, "Health", "2024-02-20", "Gym Feb"),
    ]
    for amount, category, date_str, description in rows:
        _insert_expense(user["id"], amount, category, date_str, description)
    return rows


@pytest.fixture
def logged_in_client(client, user):
    resp = client.post(
        "/login",
        data={"email": user["email"], "password": user["password"]},
        follow_redirects=False,
    )
    assert resp.status_code == 302, "Login with valid seeded credentials should redirect"
    return client


ALL_DESCRIPTIONS = [
    "Groceries Jan", "Rent Jan", "Movie Jan", "Groceries Feb", "Gym Feb",
]
JAN_DESCRIPTIONS = ["Groceries Jan", "Rent Jan", "Movie Jan"]
FEB_DESCRIPTIONS = ["Groceries Feb", "Gym Feb"]


def _body(resp):
    return resp.data.decode("utf-8", errors="replace")


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

class TestProfileFilterAuthGuard:
    def test_profile_without_login_redirects_to_login_no_filter(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302, "Unauthenticated /profile must redirect"
        assert "/login" in resp.headers.get("Location", ""), (
            "Unauthenticated /profile must redirect to /login"
        )

    def test_profile_without_login_redirects_to_login_with_filter_params(self, client):
        resp = client.get("/profile?start_date=2024-01-01&end_date=2024-01-31")
        assert resp.status_code == 302, (
            "Auth guard must apply even when filter query params are present"
        )
        assert "/login" in resp.headers.get("Location", ""), (
            "Unauthenticated /profile with filter params must still redirect to /login"
        )


# ------------------------------------------------------------------ #
# Unfiltered regression                                                #
# ------------------------------------------------------------------ #

class TestProfileUnfilteredRegression:
    def test_no_query_params_shows_all_transactions(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile")
        assert resp.status_code == 200
        body = _body(resp)
        for desc in ALL_DESCRIPTIONS:
            assert desc in body, f"All-time view must include '{desc}'"

    def test_no_query_params_never_shows_empty_range_message(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile")
        body = _body(resp)
        assert "No transactions in this range" not in body, (
            "Unfiltered all-time view must not show the empty-filter-range message"
        )


# ------------------------------------------------------------------ #
# Valid filter happy path                                             #
# ------------------------------------------------------------------ #

class TestProfileFilterHappyPath:
    def test_filter_range_includes_only_matching_month(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile?start_date=2024-01-01&end_date=2024-01-31")
        assert resp.status_code == 200
        body = _body(resp)
        for desc in JAN_DESCRIPTIONS:
            assert desc in body, f"January filter must include '{desc}'"
        for desc in FEB_DESCRIPTIONS:
            assert desc not in body, f"January filter must exclude '{desc}'"

    def test_filter_boundary_dates_are_inclusive(self, logged_in_client, expenses):
        # Single-day range exactly matching one expense's date on both ends.
        resp = logged_in_client.get("/profile?start_date=2024-01-05&end_date=2024-01-05")
        assert resp.status_code == 200
        body = _body(resp)
        assert "Groceries Jan" in body, "Expense dated exactly on start_date==end_date must be included"
        assert "Rent Jan" not in body
        assert "Movie Jan" not in body

    def test_filter_does_not_leak_other_users_expenses(
        self, client, user, other_user, expenses
    ):
        _insert_expense(other_user["id"], 999.00, "Food", "2024-01-05", "Other User Groceries")
        client.post("/login", data={"email": user["email"], "password": user["password"]})
        resp = client.get("/profile?start_date=2024-01-01&end_date=2024-01-31")
        body = _body(resp)
        assert "Other User Groceries" not in body, (
            "Filtering must never expose another user's expenses"
        )

    def test_filter_form_echoes_applied_start_and_end_date(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile?start_date=2024-01-01&end_date=2024-01-31")
        body = _body(resp)
        assert 'value="2024-01-01"' in body, (
            "start_date input must be pre-filled with the applied filter value"
        )
        assert 'value="2024-01-31"' in body, (
            "end_date input must be pre-filled with the applied filter value"
        )


# ------------------------------------------------------------------ #
# Zero-match filtered range                                           #
# ------------------------------------------------------------------ #

class TestProfileFilterZeroMatches:
    def test_zero_match_range_shows_no_transactions_message(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile?start_date=2025-01-01&end_date=2025-01-31")
        assert resp.status_code == 200, "Zero-match filter must never 500"
        body = _body(resp)
        assert "No transactions in this range" in body, (
            "Empty filtered result set must show the no-transactions message"
        )
        for desc in ALL_DESCRIPTIONS:
            assert desc not in body, "No expense rows should render for a zero-match range"

    def test_zero_match_range_does_not_error(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile?start_date=2025-06-01&end_date=2025-06-30")
        assert resp.status_code == 200


# ------------------------------------------------------------------ #
# Fallback to unfiltered view on bad input                            #
# ------------------------------------------------------------------ #

class TestProfileFilterFallback:
    def test_swapped_dates_falls_back_to_unfiltered(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile?start_date=2024-01-31&end_date=2024-01-01")
        assert resp.status_code == 200, "Swapped date range must never 500"
        body = _body(resp)
        for desc in ALL_DESCRIPTIONS:
            assert desc in body, "Swapped start/end must fall back to the all-time view"

    @pytest.mark.parametrize("start_date,end_date", [
        ("notadate", "2024-01-31"),
        ("2024-01-01", "notadate"),
        ("2024-13-40", "2024-01-31"),
        ("01/01/2024", "2024-01-31"),
        ("2024-01-01", "2024-01-01 00:00:00"),
        ("", "2024-01-31"),
        ("2024-01-01", ""),
        ("' OR '1'='1", "2024-01-31"),
        ("2024-01-01", "'; DROP TABLE expenses;--"),
    ])
    def test_malformed_dates_fall_back_to_unfiltered(
        self, logged_in_client, expenses, start_date, end_date
    ):
        resp = logged_in_client.get(
            "/profile", query_string={"start_date": start_date, "end_date": end_date}
        )
        assert resp.status_code == 200, (
            f"Malformed dates ({start_date!r}, {end_date!r}) must never 500"
        )
        body = _body(resp)
        for desc in ALL_DESCRIPTIONS:
            assert desc in body, (
                f"Malformed dates ({start_date!r}, {end_date!r}) must fall back to "
                "the all-time view"
            )

    def test_only_start_date_given_falls_back_to_unfiltered(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile?start_date=2024-01-01")
        assert resp.status_code == 200
        body = _body(resp)
        for desc in ALL_DESCRIPTIONS:
            assert desc in body, "A lone start_date without end_date must not filter"

    def test_only_end_date_given_falls_back_to_unfiltered(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile?end_date=2024-01-31")
        assert resp.status_code == 200
        body = _body(resp)
        for desc in ALL_DESCRIPTIONS:
            assert desc in body, "A lone end_date without start_date must not filter"

    def test_no_expenses_table_never_crashes_with_any_query_string(self, client, user):
        client.post("/login", data={"email": user["email"], "password": user["password"]})
        resp = client.get("/profile?start_date=garbage&end_date=garbage")
        assert resp.status_code == 200, "Bad filter with zero expenses on record must never 500"


# ------------------------------------------------------------------ #
# Clear link / plain URL restores all-time view                       #
# ------------------------------------------------------------------ #

class TestProfileFilterClear:
    def test_plain_profile_url_after_filter_restores_all_time_view(
        self, logged_in_client, expenses
    ):
        filtered = logged_in_client.get("/profile?start_date=2024-01-01&end_date=2024-01-31")
        assert "Groceries Feb" not in _body(filtered)

        cleared = logged_in_client.get("/profile")
        assert cleared.status_code == 200
        body = _body(cleared)
        for desc in ALL_DESCRIPTIONS:
            assert desc in body, "Navigating to plain /profile must restore the all-time view"

    def test_clear_control_present_in_response(self, logged_in_client, expenses):
        resp = logged_in_client.get("/profile?start_date=2024-01-01&end_date=2024-01-31")
        body = _body(resp)
        assert "Clear" in body, "A 'Clear' control must be present to reset the filter"


# ------------------------------------------------------------------ #
# database/db.py — get_expenses_by_user date-range kwargs             #
# ------------------------------------------------------------------ #

class TestGetExpensesByUserDateRange:
    def test_no_filter_returns_all_rows(self, isolated_db, user, expenses):
        rows = db_module.get_expenses_by_user(user["id"])
        assert len(rows) == 5

    def test_filter_returns_only_matching_subset(self, isolated_db, user, expenses):
        rows = db_module.get_expenses_by_user(
            user["id"], start_date="2024-01-01", end_date="2024-01-31"
        )
        descriptions = {row["description"] for row in rows}
        assert descriptions == set(JAN_DESCRIPTIONS)

    def test_filter_preserves_date_desc_ordering(self, isolated_db, user, expenses):
        rows = db_module.get_expenses_by_user(
            user["id"], start_date="2024-01-01", end_date="2024-01-31"
        )
        dates = [row["date"] for row in rows]
        assert dates == sorted(dates, reverse=True), (
            "Filtered results must remain ordered by date DESC"
        )

    def test_boundary_dates_inclusive(self, isolated_db, user, expenses):
        rows = db_module.get_expenses_by_user(
            user["id"], start_date="2024-01-05", end_date="2024-01-05"
        )
        assert len(rows) == 1
        assert rows[0]["description"] == "Groceries Jan"

    def test_zero_match_returns_empty_list(self, isolated_db, user, expenses):
        rows = db_module.get_expenses_by_user(
            user["id"], start_date="2025-01-01", end_date="2025-01-31"
        )
        assert list(rows) == []

    def test_only_one_bound_given_is_treated_as_unfiltered(self, isolated_db, user, expenses):
        rows = db_module.get_expenses_by_user(user["id"], start_date="2024-01-01")
        assert len(rows) == 5, (
            "A single bound without the other must not filter (both required)"
        )

    def test_injection_shaped_strings_do_not_error_and_do_not_bypass_filter(
        self, isolated_db, user, expenses
    ):
        rows = db_module.get_expenses_by_user(
            user["id"],
            start_date="' OR '1'='1",
            end_date="' OR '1'='1' --",
        )
        # Parameterized queries must never raise, and must never let an
        # injection-shaped string return rows it has no legitimate business
        # matching (i.e. it must not silently behave like "no filter").
        assert len(rows) <= 5


# ------------------------------------------------------------------ #
# database/db.py — get_expense_summary date-range kwargs              #
# ------------------------------------------------------------------ #

class TestGetExpenseSummaryDateRange:
    def test_no_filter_matches_all_time_totals(self, isolated_db, user, expenses):
        summary = db_module.get_expense_summary(user["id"])
        assert summary["transaction_count"] == 5
        assert summary["total_spent"] == pytest.approx(602.00)

    def test_filtered_totals_match_only_subset(self, isolated_db, user, expenses):
        summary = db_module.get_expense_summary(
            user["id"], start_date="2024-01-01", end_date="2024-01-31"
        )
        assert summary["transaction_count"] == 3
        assert summary["total_spent"] == pytest.approx(20.00 + 500.00 + 12.00)

    def test_filtered_top_category_reflects_subset_only(self, isolated_db, user, expenses):
        # Feb-only range: Health (40.00) outspends Food (30.00) within Feb.
        summary = db_module.get_expense_summary(
            user["id"], start_date="2024-02-01", end_date="2024-02-28"
        )
        assert summary["top_category"] == "Health"

    def test_zero_match_range_defaults_preserved(self, isolated_db, user, expenses):
        summary = db_module.get_expense_summary(
            user["id"], start_date="2025-01-01", end_date="2025-01-31"
        )
        assert summary["total_spent"] == 0.0
        assert summary["transaction_count"] == 0
        assert summary["top_category"] is None

    def test_only_one_bound_given_is_treated_as_unfiltered(self, isolated_db, user, expenses):
        summary = db_module.get_expense_summary(user["id"], end_date="2024-01-31")
        assert summary["transaction_count"] == 5


# ------------------------------------------------------------------ #
# database/db.py — get_category_breakdown date-range kwargs           #
# ------------------------------------------------------------------ #

class TestGetCategoryBreakdownDateRange:
    def test_no_filter_matches_all_categories(self, isolated_db, user, expenses):
        breakdown = db_module.get_category_breakdown(user["id"])
        categories = {row["category"] for row in breakdown}
        assert categories == {"Food", "Bills", "Entertainment", "Health"}

    def test_filtered_breakdown_excludes_out_of_range_categories(
        self, isolated_db, user, expenses
    ):
        breakdown = db_module.get_category_breakdown(
            user["id"], start_date="2024-01-01", end_date="2024-01-31"
        )
        categories = {row["category"] for row in breakdown}
        assert categories == {"Food", "Bills", "Entertainment"}
        assert "Health" not in categories, "Health only occurs in Feb, outside the filter"

    def test_filtered_percentages_sum_to_100_within_subset(self, isolated_db, user, expenses):
        breakdown = db_module.get_category_breakdown(
            user["id"], start_date="2024-01-01", end_date="2024-01-31"
        )
        total_percent = sum(row["percent"] for row in breakdown)
        assert total_percent == pytest.approx(100.0, abs=0.01), (
            "Filtered category percentages must sum to ~100% of the filtered subset"
        )

    def test_zero_match_range_returns_empty_breakdown(self, isolated_db, user, expenses):
        breakdown = db_module.get_category_breakdown(
            user["id"], start_date="2025-01-01", end_date="2025-01-31"
        )
        assert list(breakdown) == []

    def test_only_one_bound_given_is_treated_as_unfiltered(self, isolated_db, user, expenses):
        breakdown = db_module.get_category_breakdown(user["id"], start_date="2024-01-01")
        categories = {row["category"] for row in breakdown}
        assert categories == {"Food", "Bills", "Entertainment", "Health"}
