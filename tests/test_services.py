import unittest

from services import (
    InventoryService,
    calculate_balance,
    calculate_sale_subtotal,
    generate_sale_id,
)


class ServicesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = {
            "stock": {"items": [{"id": "PICK-J3-12", "name": "Plumilla Jazz III 1.2mm", "category": "Plumillas", "stock": 100, "min_stock": 10, "unit_cost": 8.0, "pricing_group": "JAZZ"}]},
            "ventas": {"current_month": "2026-04", "by_month": {"2026-04": []}},
            "compras": {"items": []},
            "mermas": {"items": []},
            "clientes": {"items": []},
            "pricing": {
                "groups": {
                    "JAZZ": {
                        "name": "Jazz XL y III",
                        "tiers": [
                            {"qty": 10, "one_side": 180.0, "two_sides": 200.0},
                            {"qty": 20, "one_side": 340.0, "two_sides": 370.0},
                            {"qty": 30, "one_side": 480.0, "two_sides": 520.0},
                        ],
                        "bulk": {"min_qty": 40, "one_side_unit": 15.0, "two_sides_unit": 16.0},
                    }
                }
            },
        }
        self.service = InventoryService(self.db)

    def test_generate_sale_id(self) -> None:
        self.assertEqual(generate_sale_id("2026-04", []), "BHP-26-04-001")
        self.assertEqual(generate_sale_id("2026-04", [{}, {}, {}]), "BHP-26-04-004")

    def test_sale_calculation_and_balance(self) -> None:
        product = self.service.product_map["PICK-J3-12"]
        subtotal, _, note = calculate_sale_subtotal(product, 25, "1 Lado", "Normal", self.db["pricing"])
        self.assertEqual(subtotal, 340.0)
        self.assertIn("paquete 20", note)
        total = subtotal + 0.0 + 50.0
        self.assertEqual(calculate_balance(subtotal, 0.0, 50.0, 100.0), total - 100.0)

    def test_receive_purchase_updates_stock(self) -> None:
        self.service.add_purchase("PICK-J3-12", "10", "120")
        self.assertEqual(self.service.product_map["PICK-J3-12"]["stock"], 100)
        msg, sections = self.service.toggle_purchase_received(0)
        self.assertIn("actualizado", msg)
        self.assertEqual(self.service.product_map["PICK-J3-12"]["stock"], 110)
        self.assertIn("stock", sections)

    def test_waste_affects_stock_and_cost(self) -> None:
        sections = self.service.add_waste("PICK-J3-12", "5", "Prueba")
        self.assertEqual(self.service.product_map["PICK-J3-12"]["stock"], 95)
        self.assertEqual(self.db["mermas"]["items"][-1]["loss_cost"], 40.0)
        self.assertIn("mermas", sections)
        self.assertIn("stock", sections)


if __name__ == "__main__":
    unittest.main()
