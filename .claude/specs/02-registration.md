# Spec: Registration

## Overview

This step implements account creation for Spendly. `GET /register` already renders `register.html`, whose form posts `name`, `email`, and `password` to `/register` — but there is no handler that processes that submission. This step adds the `POST /register` handling so a visitor can actually create an account: validating input, hashing the password, inserting a new row into `users`, and handling duplicate-email attempts. This is the second step on the roadmap and is a prerequisite for any feature that requires a logged-in user (login sessions, profile, expense tracking).

## Depends on

- Step 1 — Database setup (`database/db.py` schema, `get_db()`, `init_db()`) — complete.

## Routes

- `POST /register` — handle registration form submission: validate input, create the user, and either redirect to `/login` on success or re-render `register.html` with an error — public
- `GET /register` — unchanged, continues to render the empty form — public

## Database changes

No schema changes. The `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) already supports registration as-is (verified against `database/db.py`). This step adds new **functions** to `database/db.py` (not new tables/columns):

- `get_user_by_email(email)` — parameterized lookup, used to detect duplicates
- `create_user(name, email, password)` — hashes the password with `werkzeug.security.generate_password_hash` and inserts the row via a parameterized query

## Templates

**Create:** None

**Modify:**
- `templates/register.html` — change `<form method="POST" action="/register">` to `<form method="POST" action="{{ url_for('register') }}">` (currently hardcodes the URL, violating the "always use `url_for()`" rule). The existing `{% if error %}` block is reused as-is to surface validation/duplicate-email errors.

## Files to change

- `app.py` — extend the `/register` route to accept `GET` and `POST`; on `POST`, validate fields, call into `database/db.py`, and either redirect to `/login` or re-render `register.html` with `error`
- `database/db.py` — add `get_user_by_email()` and `create_user()`
- `templates/register.html` — fix hardcoded form action per above

## Files to create

- None

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterized queries only — no string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` — never store or log plaintext passwords
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB access goes through `database/db.py` — no inline SQL in `app.py`
- Validate required fields (name, email, password) and re-render `register.html` with a clear `error` message on failure — do not raise a raw 500 for expected validation failures
- Reject duplicate emails with a friendly error, not a database `IntegrityError` traceback
- On success, redirect to `/login` (login itself is a separate, not-yet-implemented step, so registration does not create a session)

## Definition of done

- [ ] `GET /register` still renders the empty form with no errors
- [ ] Submitting valid name/email/password via the form creates a new row in `users` with a hashed `password_hash` (verifiable by querying the DB)
- [ ] Submitting a duplicate email re-renders `register.html` with an error message and does not insert a new row
- [ ] Submitting with a missing/empty field re-renders `register.html` with an error message and does not insert a row
- [ ] Successful registration redirects the browser to `/login`
- [ ] The register form posts via `{{ url_for('register') }}`, not a hardcoded path
- [ ] App starts on port 5001 without errors and the full flow works end-to-end in a browser
