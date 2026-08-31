# Spec: Date Filter For Profile Page

## Overview

Step 5 (`05-profile-backend-integration`) made `/profile` show a logged-in user's real stats, transaction history, and category breakdown, but always across their entire expense history. This step adds an optional date-range filter to `/profile` so a user can narrow the summary stats, transaction table, and category breakdown down to a specific window (e.g. this month, or any custom range) instead of always seeing all-time totals. This is the sixth step on the roadmap and only touches the already-implemented profile view — it does not add expense creation/edit/delete (Steps 7–9).

## Depends on

- Step 1: Database setup (`expenses` table, `get_db()`) — complete.
- Step 3: Login + Logout (`session["user_id"]`) — complete.
- Step 5: Profile backend integration (`get_expenses_by_user`, `get_expense_summary`, `get_category_breakdown` in `database/db.py`, and the `user`/`stats`/`transactions`/`categories` context shape `profile.html` expects) — complete.

## Routes

- `GET /profile` — modify existing route — logged-in only (unchanged auth guard: redirect to `/login` if `session.get("user_id")` is absent). Now additionally reads optional query string params `start_date` and `end_date` (both `YYYY-MM-DD`). When both are present and valid, stats/transactions/categories are computed only over expenses with `date` between `start_date` and `end_date` inclusive. When absent, or invalid, or `start_date` is after `end_date`, the route falls back to the existing unfiltered (all-time) behavior — filtering must never raise a 500.

No new routes.

## Database changes

No new tables or columns. This step **modifies** three existing `database/db.py` functions to accept optional `start_date=None, end_date=None` keyword arguments, defaulting to today's all-time behavior when omitted:

- `get_expenses_by_user(user_id, start_date=None, end_date=None)` — adds `AND date BETWEEN ? AND ?` to the existing query, only when both bounds are given; still fully parameterized, ordering (`ORDER BY date DESC`) unchanged.
- `get_expense_summary(user_id, start_date=None, end_date=None)` — same conditional `BETWEEN` added to both the totals query and the top-category query; zero/`None` defaults preserved when the filtered range has no rows.
- `get_category_breakdown(user_id, start_date=None, end_date=None)` — same conditional `BETWEEN`; percentages are computed relative to the filtered `grand_total`, so they still sum to ~100% within the filtered set, not the all-time set.

The SQL template string varies (whether the `BETWEEN` clause is appended), but every value stays a bound parameter — no f-strings or `.format()` on user-supplied dates.

## Templates

**Create:** None

**Modify:**
- `templates/profile.html` — add a small filter form above "Recent Transactions": two `<input type="date">` fields (`start_date`, `end_date`), a submit button ("Filter"), and a "Clear" link back to `{{ url_for('profile') }}` with no query params. Method `GET`, action `{{ url_for('profile') }}`, so the filter is bookmarkable/shareable and needs no JS. Inputs are pre-filled with the current filter values (`value="{{ filters.start_date or '' }}"`) so the form reflects what's currently applied. When a filter is active and the transaction table is empty, show a simple "No transactions in this range" message instead of an empty table body.

## Files to change

- `app.py` — in `profile()`, read `request.args.get("start_date")` / `request.args.get("end_date")`, validate both parse as `YYYY-MM-DD` via `datetime.strptime` and that `start_date <= end_date` (otherwise treat as no filter), pass the (possibly `None`) bounds through to `get_expenses_by_user`, `get_expense_summary`, `get_category_breakdown`, and pass a `filters` dict (`{"start_date": ..., "end_date": ...}`, using the raw validated strings or `None`) to `render_template` so the form can echo the current selection.
- `database/db.py` — extend `get_expenses_by_user`, `get_expense_summary`, `get_category_breakdown` with the optional date-range params described above.

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — the `BETWEEN ? AND ?` clause is conditionally appended to the query template, but the date values themselves are always passed as bound parameters, never interpolated into the SQL string
- Passwords hashed with werkzeug (unchanged — no auth logic touched in this step)
- Use CSS variables — never hardcode hex values in any filter-form styling added to `static/css/profile.css`
- All templates extend `base.html` (unchanged)
- No DB logic inline in `app.py` — date-range filtering logic (the SQL) lives entirely in `database/db.py`; `profile()` only parses/validates the query params and passes them through
- Invalid, partial, or out-of-order date input must degrade to the unfiltered all-time view — never a 500 error
- Authentication guard unchanged: `session.get("user_id")` missing → `redirect(url_for("login"))`

## Definition of done

- [ ] Visiting `/profile` without being logged in still redirects to `/login`
- [ ] Visiting `/profile` with no query params shows the same all-time stats/transactions/categories as before this step (no regression)
- [ ] Visiting `/profile?start_date=<first-of-this-month>&end_date=<today>` shows only the seeded demo user's transactions within that range, with stats and category percentages recomputed for just that subset
- [ ] A filtered range that matches zero transactions shows a "no transactions in this range" state and zeroed stats, with no server error
- [ ] `start_date` after `end_date` (e.g. swapped) falls back to the unfiltered all-time view instead of erroring
- [ ] A malformed date value (e.g. `start_date=notadate`) falls back to the unfiltered all-time view instead of erroring
- [ ] The filter form's date inputs show the currently-applied `start_date`/`end_date` after a filtered submit, not blank fields
- [ ] The "Clear" link returns to `/profile` with no filter and the full all-time view
- [ ] No raw string formatting of `start_date`/`end_date` into SQL anywhere in `database/db.py`
- [ ] App starts on port 5001 without errors and the full filter → view → clear flow works end-to-end in a browser
