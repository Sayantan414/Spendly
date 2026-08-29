from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash

from database.db import init_db, seed_db, get_user_by_email, create_user

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

with app.app_context():
    init_db()
    seed_db()


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
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "March 2024",
    }

    stats = {
        "total_spent": 297.44,
        "transaction_count": 6,
        "top_category": "Entertainment",
    }

    transactions = [
        {"date": "Aug 27, 2026", "description": "Grocery shopping",   "category": "Food",          "category_slug": "food",          "amount": 54.20},
        {"date": "Aug 25, 2026", "description": "Coffee with client", "category": "Food",          "category_slug": "food",          "amount": 8.75},
        {"date": "Aug 24, 2026", "description": "Cab to office",      "category": "Transport",     "category_slug": "transport",     "amount": 22.00},
        {"date": "Aug 20, 2026", "description": "Internet bill",      "category": "Bills",         "category_slug": "bills",         "amount": 59.99},
        {"date": "Aug 18, 2026", "description": "Concert tickets",    "category": "Entertainment", "category_slug": "entertainment", "amount": 85.00},
        {"date": "Aug 12, 2026", "description": "Running shoes",      "category": "Shopping",      "category_slug": "shopping",      "amount": 67.50},
    ]

    categories = [
        {"name": "Entertainment", "slug": "entertainment", "amount": 85.00, "percent": 28.6},
        {"name": "Shopping",      "slug": "shopping",      "amount": 67.50, "percent": 22.7},
        {"name": "Food",          "slug": "food",          "amount": 62.95, "percent": 21.2},
        {"name": "Bills",         "slug": "bills",         "amount": 59.99, "percent": 20.2},
        {"name": "Transport",     "slug": "transport",     "amount": 22.00, "percent": 7.4},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
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
