"""Main application blueprint: dashboard, transactions, categories, summary."""

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import text

from app.auth import login_required
from app.db import db
from app.logic import (
    EXPENSE,
    INCOME,
    parse_amount,
    parse_date,
    validate_category_name,
    validate_title,
)
from app.models import Category, Transaction

bp = Blueprint("main", __name__)


def _user_categories():
    return (
        db.session.execute(
            db.select(Category)
            .filter_by(user_id=g.user.id)
            .order_by(Category.name)
        )
        .scalars()
        .all()
    )


def _totals_for_user(user_id):
    """Return income, expense, and balance using the original sign convention."""
    income = (
        db.session.execute(
            db.select(db.func.coalesce(db.func.sum(Transaction.amount), 0)).filter_by(
                user_id=user_id, movement_type=INCOME
            )
        ).scalar()
        or 0
    )
    expense = (
        db.session.execute(
            db.select(db.func.coalesce(db.func.sum(Transaction.amount), 0)).filter_by(
                user_id=user_id, movement_type=EXPENSE
            )
        ).scalar()
        or 0
    )
    return float(income), float(expense), float(income) + float(expense)


@bp.route("/")
@login_required
def dashboard():
    income, expense, balance = _totals_for_user(g.user.id)
    recent = (
        db.session.execute(
            db.select(Transaction)
            .filter_by(user_id=g.user.id)
            .order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
            .limit(8)
        )
        .scalars()
        .all()
    )
    category_count = (
        db.session.execute(
            db.select(db.func.count()).select_from(Category).filter_by(user_id=g.user.id)
        ).scalar()
        or 0
    )
    transaction_count = (
        db.session.execute(
            db.select(db.func.count())
            .select_from(Transaction)
            .filter_by(user_id=g.user.id)
        ).scalar()
        or 0
    )
    return render_template(
        "dashboard.html",
        income=income,
        expense=expense,
        balance=balance,
        recent=recent,
        category_count=category_count,
        transaction_count=transaction_count,
    )


@bp.route("/transactions", methods=("GET", "POST"))
@login_required
def transactions():
    categories = _user_categories()

    if request.method == "POST":
        if not categories:
            flash("Add a category before recording a transaction.", "error")
            return redirect(url_for("main.categories"))

        title = request.form.get("title")
        raw_amount = request.form.get("amount")
        movement_type = request.form.get("movement_type")
        raw_date = request.form.get("occurred_on")
        try:
            category_id = int(request.form.get("category_id") or 0)
        except ValueError:
            category_id = 0

        category = db.session.execute(
            db.select(Category).filter_by(id=category_id, user_id=g.user.id)
        ).scalar_one_or_none()

        error = None
        try:
            title = validate_title(title)
            amount = parse_amount(raw_amount, movement_type)
            occurred_on = parse_date(raw_date)
        except ValueError as exc:
            error = str(exc)
            amount = None
            occurred_on = None

        if error is None and category is None:
            error = "Choose a valid category."

        if error is None:
            txn = Transaction(
                user_id=g.user.id,
                category_id=category.id,
                title=title,
                amount=amount,
                movement_type=movement_type,
                occurred_on=occurred_on,
            )
            db.session.add(txn)
            db.session.commit()
            flash(f"Added “{title}”.", "success")
            return redirect(url_for("main.transactions"))

        flash(error, "error")

    query = db.select(Transaction).filter_by(user_id=g.user.id)
    filter_category = request.args.get("category_id") or ""
    filter_type = request.args.get("type") or ""

    if filter_category:
        try:
            query = query.filter_by(category_id=int(filter_category))
        except ValueError:
            filter_category = ""
    if filter_type in (INCOME, EXPENSE):
        query = query.filter_by(movement_type=filter_type)
    else:
        filter_type = ""

    rows = (
        db.session.execute(
            query.order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
        )
        .scalars()
        .all()
    )
    income, expense, balance = _totals_for_user(g.user.id)

    return render_template(
        "transactions.html",
        transactions=rows,
        categories=categories,
        filter_category=str(filter_category),
        filter_type=filter_type,
        income=income,
        expense=expense,
        balance=balance,
        income_value=INCOME,
        expense_value=EXPENSE,
    )


@bp.route("/transactions/<int:txn_id>/delete", methods=("POST",))
@login_required
def delete_transaction(txn_id):
    txn = db.session.execute(
        db.select(Transaction).filter_by(id=txn_id, user_id=g.user.id)
    ).scalar_one_or_none()
    if txn is None:
        flash("Transaction not found.", "error")
    else:
        title = txn.title
        db.session.delete(txn)
        db.session.commit()
        flash(f"Deleted “{title}”.", "success")
    return redirect(url_for("main.transactions"))


@bp.route("/categories", methods=("GET", "POST"))
@login_required
def categories():
    if request.method == "POST":
        error = None
        try:
            name = validate_category_name(request.form.get("name"))
        except ValueError as exc:
            error = str(exc)
            name = None

        if error is None:
            existing = db.session.execute(
                db.select(Category).filter_by(user_id=g.user.id, name=name)
            ).scalar_one_or_none()
            if existing is not None:
                error = f"You already have a category named “{name}”."

        if error is None:
            db.session.add(Category(user_id=g.user.id, name=name))
            db.session.commit()
            flash(f"Category “{name}” added.", "success")
            return redirect(url_for("main.categories"))

        flash(error, "error")

    categories = _user_categories()
    return render_template("categories.html", categories=categories)


@bp.route("/summary")
@login_required
def summary():
    # Raw SQL showcases GROUP BY / CASE skills employers look for.
    by_category = db.session.execute(
        text(
            """
            SELECT
                c.name AS category,
                COALESCE(SUM(CASE WHEN t.movement_type = :income THEN t.amount ELSE 0 END), 0)
                    AS income,
                COALESCE(SUM(CASE WHEN t.movement_type = :expense THEN t.amount ELSE 0 END), 0)
                    AS expense,
                COALESCE(SUM(t.amount), 0) AS net
            FROM categories AS c
            LEFT JOIN transactions AS t
                ON t.category_id = c.id AND t.user_id = :user_id
            WHERE c.user_id = :user_id
            GROUP BY c.id, c.name
            ORDER BY c.name
            """
        ),
        {"user_id": g.user.id, "income": INCOME, "expense": EXPENSE},
    ).mappings().all()

    by_month = db.session.execute(
        text(
            """
            SELECT
                strftime('%Y-%m', occurred_on) AS month,
                SUM(CASE WHEN movement_type = :income THEN amount ELSE 0 END) AS income,
                SUM(CASE WHEN movement_type = :expense THEN amount ELSE 0 END) AS expense,
                SUM(amount) AS net
            FROM transactions
            WHERE user_id = :user_id
            GROUP BY month
            ORDER BY month
            """
        ),
        {"user_id": g.user.id, "income": INCOME, "expense": EXPENSE},
    ).mappings().all()

    income, expense, balance = _totals_for_user(g.user.id)
    return render_template(
        "summary.html",
        by_category=by_category,
        by_month=by_month,
        income=income,
        expense=expense,
        balance=balance,
    )
