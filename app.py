from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date
from sqlalchemy import func, extract
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "smartspend-dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "expense_tracker.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

os.makedirs(app.instance_path, exist_ok=True)
db = SQLAlchemy(app)

CATEGORIES = [
    "Food", "Travel", "Education", "Rent", "Shopping",
    "Entertainment", "Bills", "Health", "Personal", "Other"
]
INCOME_CATEGORIES = ["Allowance", "Salary", "Scholarship", "Part-time Job", "Other"]

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship("Transaction", backref="user", lazy=True, cascade="all, delete-orphan")
    budgets = db.relationship("Budget", backref="user", lazy=True, cascade="all, delete-orphan")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)  # income / expense
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    note = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "month", "year", name="unique_user_month_budget"),)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def current_period():
    today = date.today()
    return today.month, today.year

def period_budget(user_id, month, year):
    return Budget.query.filter_by(user_id=user_id, month=month, year=year).first()

def dashboard_data(user_id, month=None, year=None):
    if month is None or year is None:
        month, year = current_period()

    expenses = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == month,
        extract("year", Transaction.date) == year
    ).scalar() or 0

    income = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "income",
        extract("month", Transaction.date) == month,
        extract("year", Transaction.date) == year
    ).scalar() or 0

    budget_obj = period_budget(user_id, month, year)
    budget = budget_obj.amount if budget_obj else 0
    remaining = budget - expenses
    percentage = (expenses / budget * 100) if budget > 0 else 0

    if budget <= 0:
        status = "no-budget"
        message = "Set a monthly budget to start tracking your progress."
    elif percentage >= 100:
        status = "exceeded"
        message = f"Budget exceeded by ₹{expenses - budget:,.2f}."
    elif percentage >= 80:
        status = "critical"
        message = f"You have used {percentage:.0f}% of your monthly budget."
    elif percentage >= 60:
        status = "monitor"
        message = f"You have used {percentage:.0f}% of your monthly budget. Keep an eye on spending."
    else:
        status = "safe"
        message = "Your spending is currently within a comfortable range."

    return {
        "total_income": round(income, 2),
        "total_expense": round(expenses, 2),
        "budget": round(budget, 2),
        "remaining": round(remaining, 2),
        "percentage_used": round(percentage, 2),
        "status": status,
        "message": message,
        "month": month,
        "year": year
    }

@app.context_processor
def inject_globals():
    return {"expense_categories": CATEGORIES, "income_categories": INCOME_CATEGORIES}

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "danger")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("register.html")

        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")
        session.clear()
        session["user_id"] = user.id
        session["user_name"] = user.name
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user_name=session.get("user_name", "Student"))

@app.route("/transactions")
@login_required
def transactions_page():
    return render_template("transactions.html")

@app.route("/transaction/new")
@login_required
def transaction_form():
    return render_template("add_transaction.html")

@app.route("/budget")
@login_required
def budget_page():
    return render_template("budget.html")

@app.route("/api/profile")
@login_required
def api_profile():
    user = db.session.get(User, session["user_id"])
    return jsonify({"id": user.id, "name": user.name, "email": user.email})

@app.route("/api/transactions", methods=["GET", "POST"])
@login_required
def api_transactions():
    user_id = session["user_id"]
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        tx_type = str(data.get("type", "")).lower().strip()
        category = str(data.get("category", "")).strip()
        note = str(data.get("note", "")).strip()
        try:
            amount = float(data.get("amount", 0))
            tx_date = datetime.strptime(str(data.get("date", "")), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return jsonify({"error": "Enter a valid amount and date."}), 400

        valid_categories = INCOME_CATEGORIES if tx_type == "income" else CATEGORIES
        if tx_type not in ("income", "expense"):
            return jsonify({"error": "Transaction type must be income or expense."}), 400
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than zero."}), 400
        if category not in valid_categories:
            return jsonify({"error": "Please select a valid category."}), 400

        tx = Transaction(user_id=user_id, type=tx_type, amount=amount,
                         category=category, date=tx_date, note=note)
        db.session.add(tx)
        db.session.commit()
        return jsonify({"message": "Transaction added successfully.", "id": tx.id}), 201

    query = Transaction.query.filter_by(user_id=user_id)
    tx_type = request.args.get("type", "")
    category = request.args.get("category", "")
    if tx_type in ("income", "expense"):
        query = query.filter_by(type=tx_type)
    if category:
        query = query.filter_by(category=category)
    items = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
    return jsonify([{
        "id": x.id, "type": x.type, "amount": x.amount, "category": x.category,
        "date": x.date.isoformat(), "note": x.note or ""
    } for x in items])

@app.route("/api/transactions/<int:tx_id>", methods=["PUT", "DELETE"])
@login_required
def api_transaction_detail(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=session["user_id"]).first()
    if not tx:
        return jsonify({"error": "Transaction not found."}), 404

    if request.method == "DELETE":
        db.session.delete(tx)
        db.session.commit()
        return jsonify({"message": "Transaction deleted successfully."})

    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", tx.amount))
        tx_date = datetime.strptime(str(data.get("date", tx.date.isoformat())), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount or date."}), 400
    tx_type = str(data.get("type", tx.type)).lower()
    category = str(data.get("category", tx.category))
    if amount <= 0 or tx_type not in ("income", "expense"):
        return jsonify({"error": "Invalid transaction details."}), 400

    tx.amount = amount
    tx.type = tx_type
    tx.category = category
    tx.date = tx_date
    tx.note = str(data.get("note", tx.note or ""))
    db.session.commit()
    return jsonify({"message": "Transaction updated successfully."})

@app.route("/api/budget", methods=["GET", "POST", "PUT"])
@login_required
def api_budget():
    user_id = session["user_id"]
    today = date.today()
    if request.method == "GET":
        try:
            month = int(request.args.get("month", today.month))
            year = int(request.args.get("year", today.year))
        except ValueError:
            month, year = today.month, today.year
        budget = period_budget(user_id, month, year)
        return jsonify({"month": month, "year": year, "amount": budget.amount if budget else 0})

    data = request.get_json(silent=True) or request.form
    try:
        amount = float(data.get("amount", 0))
        month = int(data.get("month", today.month))
        year = int(data.get("year", today.year))
    except (ValueError, TypeError):
        return jsonify({"error": "Enter valid budget details."}), 400

    if amount <= 0 or month < 1 or month > 12 or year < 2000:
        return jsonify({"error": "Budget amount must be greater than zero."}), 400

    budget = period_budget(user_id, month, year)
    if budget:
        budget.amount = amount
    else:
        budget = Budget(user_id=user_id, month=month, year=year, amount=amount)
        db.session.add(budget)
    db.session.commit()
    return jsonify({"message": "Budget saved successfully.", "amount": amount, "month": month, "year": year})

@app.route("/api/dashboard")
@login_required
def api_dashboard():
    try:
        month = int(request.args.get("month", date.today().month))
        year = int(request.args.get("year", date.today().year))
    except ValueError:
        return jsonify({"error": "Invalid month or year."}), 400
    return jsonify(dashboard_data(session["user_id"], month, year))

@app.route("/api/category-summary")
@login_required
def api_category_summary():
    today = date.today()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
    except ValueError:
        month, year = today.month, today.year

    rows = db.session.query(
        Transaction.category, func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == session["user_id"],
        Transaction.type == "expense",
        extract("month", Transaction.date) == month,
        extract("year", Transaction.date) == year
    ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).all()
    return jsonify([{"category": category, "amount": round(amount, 2)} for category, amount in rows])

@app.route("/api/monthly-summary")
@login_required
def api_monthly_summary():
    today = date.today()
    rows = []
    for day in range(1, today.day + 1):
        total = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == session["user_id"],
            Transaction.type == "expense",
            extract("month", Transaction.date) == today.month,
            extract("year", Transaction.date) == today.year,
            extract("day", Transaction.date) == day
        ).scalar() or 0
        rows.append({"day": day, "amount": round(total, 2)})
    return jsonify(rows)

@app.route("/api/insight")
@login_required
def api_insight():
    data = dashboard_data(session["user_id"])
    categories = db.session.query(
        Transaction.category, func.sum(Transaction.amount).label("total")
    ).filter(
        Transaction.user_id == session["user_id"],
        Transaction.type == "expense",
        extract("month", Transaction.date) == data["month"],
        extract("year", Transaction.date) == data["year"]
    ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).all()
    if categories:
        category, total = categories[0]
        share = (total / data["total_expense"] * 100) if data["total_expense"] else 0
        insight = f"Your highest spending category is {category}: ₹{total:,.2f} ({share:.0f}% of expenses)."
    else:
        insight = "Add some expenses to receive a personalized spending insight."
    return jsonify({"insight": insight})

def seed_demo():
    if User.query.filter_by(email="demo@student.com").first():
        return
    user = User(name="Demo Student", email="demo@student.com",
                password_hash=generate_password_hash("Demo@123"))
    db.session.add(user)
    db.session.flush()
    today = date.today()
    db.session.add(Budget(user_id=user.id, month=today.month, year=today.year, amount=15000))
    sample = [
        ("income", 20000, "Allowance", "Monthly allowance"),
        ("expense", 4000, "Food", "Meals and snacks"),
        ("expense", 2000, "Travel", "Bus and auto"),
        ("expense", 3000, "Education", "Books and study"),
        ("expense", 2000, "Shopping", "Personal items"),
        ("expense", 1000, "Entertainment", "Movies"),
    ]
    for typ, amount, category, note in sample:
        db.session.add(Transaction(
            user_id=user.id, type=typ, amount=amount, category=category,
            date=today, note=note
        ))
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_demo()

if __name__ == "__main__":
    app.run(debug=True)
