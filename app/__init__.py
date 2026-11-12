"""Flask application factory for the Finance Tracker."""

import os

import click
from flask import Flask
from werkzeug.security import generate_password_hash

from app.db import db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    default_db = "sqlite:///" + os.path.join(app.instance_path, "finance.db")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", default_db),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)

    # Models must be imported so SQLAlchemy can register the tables.
    from app import models  # noqa: F401
    from app.auth import bp as auth_bp
    from app.main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)

    return app


@click.command("init-db")
def init_db_command():
    """Create database tables. Run with: flask --app app init-db"""
    db.create_all()
    click.echo("Initialized the database.")


@click.command("seed-db")
def seed_db_command():
    """Insert a demo user and sample transactions. Run with: flask --app app seed-db"""
    from datetime import date, timedelta

    from app.logic import EXPENSE, INCOME, parse_amount
    from app.models import Category, Transaction, User

    db.create_all()

    existing = db.session.execute(
        db.select(User).filter_by(username="demo")
    ).scalar_one_or_none()
    if existing is not None:
        click.echo("Demo user already exists. Nothing to seed.")
        return

    user = User(
        username="demo",
        password_hash=generate_password_hash("demodemo"),
    )
    db.session.add(user)
    db.session.flush()

    names = ["Salary", "Food", "Rent", "Transport", "Shopping"]
    categories = {}
    for name in names:
        category = Category(user_id=user.id, name=name)
        db.session.add(category)
        db.session.flush()
        categories[name] = category

    today = date.today()
    first_this_month = today.replace(day=1)
    last_month = first_this_month - timedelta(days=1)
    first_last_month = last_month.replace(day=1)

    samples = [
        ("Paycheck", 3200, "Salary", INCOME, first_last_month.replace(day=1)),
        ("Rent", 1400, "Rent", EXPENSE, first_last_month.replace(day=3)),
        ("Groceries", 186.40, "Food", EXPENSE, first_last_month.replace(day=8)),
        ("Bus pass", 60, "Transport", EXPENSE, first_last_month.replace(day=10)),
        ("Paycheck", 3200, "Salary", INCOME, first_this_month),
        ("Rent", 1400, "Rent", EXPENSE, first_this_month),
        ("Groceries", 142.15, "Food", EXPENSE, today - timedelta(days=4)),
        ("Coffee", 18.50, "Food", EXPENSE, today - timedelta(days=2)),
        ("New shoes", 79.99, "Shopping", EXPENSE, today - timedelta(days=1)),
        ("Freelance project", 450, "Salary", INCOME, today),
    ]

    for title, raw_amount, category_name, movement_type, occurred_on in samples:
        db.session.add(
            Transaction(
                user_id=user.id,
                category_id=categories[category_name].id,
                title=title,
                amount=parse_amount(raw_amount, movement_type),
                movement_type=movement_type,
                occurred_on=occurred_on,
            )
        )

    db.session.commit()
    click.echo("Seeded demo data. Sign in with username 'demo' and password 'demodemo'.")
