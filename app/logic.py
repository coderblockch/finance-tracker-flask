"""Domain logic ported from the DUAD Gestor Finanzas project.

The original in-memory model is preserved so the bootcamp unit tests still
apply. Helpers were added for validation and for signed income/expense amounts.
"""

from __future__ import annotations

from datetime import date


INCOME = "Ingreso"
EXPENSE = "Gasto"
VALID_TYPES = frozenset({INCOME, EXPENSE})


class Movement:
    def __init__(self, title, amount, category, movement_type, date=None):
        self.title = title
        self.amount = amount
        self.category = category
        self.movement_type = movement_type
        self.date = date


class Category:
    def __init__(self, name):
        self.name = name


class FinanceManager:
    def __init__(self):
        self.movements = []
        self.categories = []

    def add_movement(self, movement):
        self.movements.append(movement)

    def add_category(self, category):
        self.categories.append(category)

    def total_income(self):
        total = 0
        for movement in self.movements:
            if movement.movement_type == INCOME:
                total = total + movement.amount
        return total

    def total_expenses(self):
        total = 0
        for movement in self.movements:
            if movement.movement_type == EXPENSE:
                total = total + movement.amount
        return total

    def balance(self):
        return self.total_income() + self.total_expenses()

    def filter_movements(self, category=None, movement_type=None):
        results = self.movements
        if category:
            results = [m for m in results if m.category == category]
        if movement_type:
            results = [m for m in results if m.movement_type == movement_type]
        return results

    def totals_by_category(self):
        totals = {}
        for movement in self.movements:
            bucket = totals.setdefault(
                movement.category, {"income": 0, "expense": 0, "net": 0}
            )
            if movement.movement_type == INCOME:
                bucket["income"] += movement.amount
            elif movement.movement_type == EXPENSE:
                bucket["expense"] += movement.amount
            bucket["net"] = bucket["income"] + bucket["expense"]
        return totals


def validate_title(title: str) -> str:
    if title is None or not str(title).strip():
        raise ValueError("Title is required.")
    return str(title).strip()


def validate_category_name(name: str) -> str:
    if name is None or not str(name).strip():
        raise ValueError("Category name is required.")
    cleaned = str(name).strip()
    if len(cleaned) > 80:
        raise ValueError("Category name must be 80 characters or fewer.")
    return cleaned


def validate_movement_type(movement_type: str) -> str:
    if movement_type not in VALID_TYPES:
        raise ValueError("Type must be Ingreso (income) or Gasto (expense).")
    return movement_type


def parse_amount(raw_amount, movement_type: str) -> float:
    """Parse a user-entered amount and apply the original sign convention.

    Incomes are stored as positive numbers and expenses as negative numbers,
    matching the original Gestor Finanzas GUI.
    """
    validate_movement_type(movement_type)
    try:
        amount = float(raw_amount)
    except (TypeError, ValueError) as exc:
        raise ValueError("Amount must be a number.") from exc
    if amount == 0:
        raise ValueError("Amount must not be zero.")
    if movement_type == EXPENSE:
        return -abs(amount)
    return abs(amount)


def parse_date(raw_date) -> date:
    if raw_date in (None, ""):
        return date.today()
    if isinstance(raw_date, date):
        return raw_date
    try:
        return date.fromisoformat(str(raw_date))
    except ValueError as exc:
        raise ValueError("Date must be in YYYY-MM-DD format.") from exc
