"""Ported from the DUAD Gestor Finanzas test_logic.py suite."""

import unittest

from app.logic import Category, FinanceManager, Movement, parse_amount


class TestFinanceManager(unittest.TestCase):

    def test_add_movement(self):
        manager = FinanceManager()
        movement = Movement("Salario", 1000, "Trabajo", "Ingreso")
        manager.add_movement(movement)
        self.assertEqual(len(manager.movements), 1)

    def test_add_category(self):
        manager = FinanceManager()
        category = Category("Trabajo")
        manager.add_category(category)
        self.assertEqual(len(manager.categories), 1)

    def test_total_income(self):
        manager = FinanceManager()
        manager.add_movement(Movement("Salario", 1000, "Trabajo", "Ingreso"))
        manager.add_movement(Movement("Bono", 500, "Trabajo", "Ingreso"))
        self.assertEqual(manager.total_income(), 1500)

    def test_total_expenses(self):
        manager = FinanceManager()
        manager.add_movement(Movement("Comida", -20, "Comida", "Gasto"))
        manager.add_movement(Movement("Ropa", -50, "Compras", "Gasto"))
        self.assertEqual(manager.total_expenses(), -70)

    def test_balance(self):
        manager = FinanceManager()
        manager.add_movement(Movement("Salario", 1000, "Trabajo", "Ingreso"))
        manager.add_movement(Movement("Comida", -20, "Comida", "Gasto"))
        self.assertEqual(manager.balance(), 980)

    def test_empty_manager(self):
        manager = FinanceManager()
        self.assertEqual(len(manager.movements), 0)
        self.assertEqual(len(manager.categories), 0)

    def test_multiple_movements(self):
        manager = FinanceManager()
        manager.add_movement(Movement("Salario", 1000, "Trabajo", "Ingreso"))
        manager.add_movement(Movement("Bono", 500, "Trabajo", "Ingreso"))
        manager.add_movement(Movement("Comida", -20, "Comida", "Gasto"))
        self.assertEqual(len(manager.movements), 3)

    def test_movement_attributes(self):
        movement = Movement("Salario", 1000, "Trabajo", "Ingreso")
        self.assertEqual(movement.title, "Salario")
        self.assertEqual(movement.amount, 1000)
        self.assertEqual(movement.category, "Trabajo")
        self.assertEqual(movement.movement_type, "Ingreso")

    def test_parse_amount_signs(self):
        self.assertEqual(parse_amount(20, "Gasto"), -20)
        self.assertEqual(parse_amount(-20, "Gasto"), -20)
        self.assertEqual(parse_amount(1000, "Ingreso"), 1000)
        self.assertEqual(parse_amount(-1000, "Ingreso"), 1000)
