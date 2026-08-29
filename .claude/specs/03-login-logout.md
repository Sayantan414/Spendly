# Spec: Login and Logout

## Overview

This step implements session-based authentication for Spendly. `GET /login` already renders `login.html`, whose form posts `email` and `password` to `/login` — but there is no handler that processes that submission, and there is no concept of a logged-in session anywhere in the app yet. This step adds `POST /login` (verify credentials against the `users` table and start a session) and implements the `GET /logout` stub (end the session). This is the third step on the roadmap and is the prerequisite for every feature that needs to know "who is currently signed in" — profile, and all expense CRUD routes.

## Depends on

- Step 1 — Database setup (`database/db.py` schema, `get_db()`) — complete.
- Step 2 — Registration (`get_user_by_email()`, hashed passwords in `users.password_hash`) — complete.

## Routes

- `GET /login` — unchanged, continues to render the empty form — public
- `POST /login` — validate credentials against `users`, start a session on success, or re-render `login.html` with an error — public
- `GET /logout` — clear the current session and redirect to `/` — public (safe to call whether or not a session exists)

## Database changes

No database changes. The `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) and the existing `get_user_by_email(email)` function (from Step 2) are sufficient for this step (verified against `database/db.py`). Password verification uses `werkzeug.security.check_password_hash` against the `password_hash` already returned by `get_user_by_email()` — no new `database/db.py` functions are needed.

## Templates

**Create:** None

**Modify:**
- `templates/login.html` — change `<form method="POST" action="/login">` to `<form method="POST" action="{{ url_for('login') }}">` (currently hardcodes the URL, violating the "always use `url_for()`" rule). The existing `{% if error %}` block is reused as-is to surface invalid-credential errors.
- `templates/base.html` — the nav currently always shows "Sign in" / "Get started". Wrap those two links in `{% if session.get('user_id') %}...{% else %}...{% endif %}` so a logged-in visitor sees a "Log out" link (`{{ url_for('logout') }}`) instead. `session` is available in Jinja templates by default in Flask, so no new context needs to be passed from routes.

## Files to change

- `app.py` — set `app.secret_key` (required for Flask sessions to work at all); extend `/login` to accept `GET` and `POST` — on `POST`, look up the user by email, verify the password with `check_password_hash`, store `user_id` in `session` on success and redirect to `/`, or re-render `login.html` with an error on failure; implement `/logout` to call `session.clear()` and redirect to `/`
- `templates/login.html` — fix hardcoded form action per above
- `templates/base.html` — conditional nav links per above

## Files to create

- None

## New dependencies

No new dependencies. `werkzeug.security.check_password_hash` ships with the Flask/Werkzeug already in `requirements.txt`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterized queries only — no string formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext passwords, never log them
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB access goes through `database/db.py` — `app.py` only calls `get_user_by_email()`, it does not query the database directly
- Store only `user_id` in `session` — never store the password or password hash in the session
- On invalid email or invalid password, re-render `login.html` with a single generic error (e.g. "Invalid email or password") — do not reveal whether the email exists
- `GET /logout` must not error if no one is logged in — clearing an empty session is a no-op
- Do not implement any `@login_required`-style guard on `/profile` or the expense routes — enforcing that access on protected pages is out of scope for this step (Step 4 and later)

## Definition of done

- [ ] `GET /login` still renders the empty form with no errors
- [ ] Submitting the seeded demo user's credentials (`demo@spendly.com` / `demo123`) via the form logs the user in and redirects to `/`
- [ ] After logging in, the navbar shows "Log out" instead of "Sign in" / "Get started"
- [ ] Submitting a wrong password or an email that doesn't exist re-renders `login.html` with a generic error and does not start a session
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/`, after which the navbar shows "Sign in" / "Get started" again
- [ ] Visiting `/logout` while not logged in does not error — it just redirects to `/`
- [ ] The login form posts via `{{ url_for('login') }}`, not a hardcoded path
- [ ] App starts on port 5001 without errors and the full login → logout flow works end-to-end in a browser
