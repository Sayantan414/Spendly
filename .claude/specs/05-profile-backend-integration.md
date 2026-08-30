# Spec: Profile Backend Integration

## Overview
Step 4 (`04-profile-page-design`) built `templates/profile.html` against hardcoded Python dicts in the `/profile` route so the UI could be validated before the database was involved. This step — referred to as "Step 5" in that spec — replaces those hardcoded values with real queries against the `users` and `expenses` tables, so a logged-in user sees their own account info and their own seeded/entered expenses instead of the same static demo data for everyone.

## Depends on
- Step 1: Database setup (`users` / `expenses` tables, `get_db()`)
- Step 2: Registration (accounts exist to look up)
- Step 3: Login + Logout (`session["user_id"]` is set on login)
- Step 4: Profile page design (`profile.html` and its expected context shape: `user`, `stats`, `transactions`, `categories`)

## Routes
- `GET /profile` — modify existing route — logged-in only (redirect to `/login` if `session.get("user_id")` is absent, unchanged from Step 4). Behavior changes from returning hardcoded context to fetching the current user and their expenses from the database and passing computed context to the unchanged `profile.html` template.

No new routes.

## Database changes
No new tables or columns — `users` and `expenses` (from `database/db.py`) are sufficient. This step adds new **query functions** to `database/db.py` (all using `get_db()` and parameterized queries, following the existing style of `get_user_by_email` / `create_user`):

- `get_user_by_id(user_id)` — `SELECT * FROM users WHERE id = ?`, returns one row or `None`. Needed because the session only stores `user_id`, not email.
- `get_expenses_by_user(user_id)` — `SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC`, returns all rows for the transaction history table.
- `get_expense_summary(user_id)` — returns a dict with `total_spent` (SUM(amount)), `transaction_count` (COUNT(*)), and `top_category` (category with the highest SUM(amount)), each via a parameterized aggregate query. Returns sensible zero/`None` defaults when the user has no expenses yet.
- `get_category_breakdown(user_id)` — `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC`, then computes each category's `percent` of the user's `total_spent` before returning, so the route only has to pass the result straight to the template.

## Templates
- Create: none — `templates/profile.html` already exists from Step 4 and its expected context shape (`user`, `stats`, `transactions`, `categories`) is unchanged.
- Modify: none required. If any field name mismatch surfaces between the Step 4 template and real DB rows (e.g. `category_slug` for CSS badge classes, or date formatting), adjust the context dict built in `app.py` to match what `profile.html` already expects — do not change the template's variable names.

## Files to change
- `app.py` — replace the hardcoded `user`, `stats`, `transactions`, `categories` dicts/lists in the `profile()` view with calls to the new `database/db.py` functions, plus the small presentation-only transforms already implicit in the Step 4 data shape (deriving `initials` from `name`, formatting `member_since` from `created_at`, formatting each transaction's `date` for display, deriving `category_slug` from `category` for CSS badge classes).
- `database/db.py` — add `get_user_by_id`, `get_expenses_by_user`, `get_expense_summary`, `get_category_breakdown`.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (unchanged — no auth logic touched in this step)
- Use CSS variables — never hardcode hex values (no template changes expected, but any touch-up must follow this)
- All templates extend `base.html` (unchanged)
- No DB logic inline in `app.py` — every query lives in `database/db.py`; `profile()` only calls those functions, shapes the result for the template, and renders
- Handle the zero-expenses case gracefully (a freshly registered user with no expenses yet) — stats should show zeros/empty state, not raise an error
- Authentication guard unchanged: `session.get("user_id")` missing → `redirect(url_for("login"))`

## Definition of done
- [ ] Visiting `/profile` without being logged in still redirects to `/login`
- [ ] Logging in as the seeded demo user (`demo@spendly.com` / `demo123`) and visiting `/profile` returns HTTP 200 with no server error
- [ ] The user info card shows the demo user's actual `name` and `email` from the `users` table, not "Demo User" hardcoded text
- [ ] The summary stats (`total_spent`, `transaction_count`, `top_category`) match what querying the `expenses` table for the demo user's 8 seeded rows would produce
- [ ] The transaction history table lists the demo user's real expense rows (8 rows, newest first by date)
- [ ] The category breakdown section reflects real `SUM(amount)` per category from the seeded data, with percentages that sum to ~100%
- [ ] Registering a brand-new user, logging in, and visiting `/profile` shows an empty/zeroed state (no expenses yet) without a 500 error
- [ ] No hardcoded transaction/category/user data remains in `app.py`'s `profile()` function
