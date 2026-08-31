from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash

from database.db import (
    init_db,
    seed_db,
    get_user_by_email,
    create_user,
    get_user_by_id,
    get_expenses_by_user,
    get_expense_summary,
    get_category_breakdown,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def parse_date_filter(args):
    """Validate start_date/end_date query params, or (None, None) if absent/invalid."""
    start_raw = args.get("start_date", "")
    end_raw = args.get("end_date", "")

    if not (start_raw and end_raw):
        return None, None

    try:
        start = datetime.strptime(start_raw, "%Y-%m-%d")
        end = datetime.strptime(end_raw, "%Y-%m-%d")
    except ValueError:
        return None, None

    return (start_raw, end_raw) if start <= end else (None, None)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")

        if get_user_by_email(email):
            return render_template(
                "register.html",
                error="An account with that email already exists.",
            )

        create_user(name, email, password)
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")

        session["user_id"] = user["id"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user_row = get_user_by_id(user_id)
    if user_row is None:
        session.clear()
        return redirect(url_for("login"))

    start_date, end_date = parse_date_filter(request.args)
    filters = {"start_date": start_date or "", "end_date": end_date or ""}

    name = user_row["name"]
    parts = name.split()
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[-1][0]).upper()
    elif parts:
        initials = parts[0][:2].upper()
    else:
        initials = ""

    created_at = datetime.strptime(user_row["created_at"], "%Y-%m-%d %H:%M:%S")

    user = {
        "name": name,
        "email": user_row["email"],
        "initials": initials,
        "member_since": created_at.strftime("%B %Y"),
    }

    summary = get_expense_summary(user_id, start_date=start_date, end_date=end_date)
    stats = {
        "total_spent": summary["total_spent"],
        "transaction_count": summary["transaction_count"],
        "top_category": summary["top_category"] or "—",
    }

    transactions = []
    for row in get_expenses_by_user(user_id, start_date=start_date, end_date=end_date):
        txn_date = datetime.strptime(row["date"], "%Y-%m-%d")
        transactions.append({
            "date": f"{txn_date:%b} {txn_date.day}, {txn_date.year}",
            "description": row["description"],
            "category": row["category"],
            "category_slug": row["category"].lower(),
            "amount": row["amount"],
        })

    categories = [
        {
            "name": row["category"],
            "slug": row["category"].lower(),
            "amount": row["total"],
            "percent": row["percent"],
        }
        for row in get_category_breakdown(user_id, start_date=start_date, end_date=end_date)
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        filters=filters,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)


# karthik.krishnan807@gmail.com
# password123