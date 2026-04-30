from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FileNames:
    stock: str = "stock.json"
    ventas: str = "ventas.json"
    compras: str = "compras.json"
    mermas: str = "mermas.json"
    clientes: str = "clientes.json"
    pricing: str = "pricing_rules.json"


INITIAL_PRODUCTS: list[dict[str, Any]] = [
    {"id": "PICK-EST-071", "name": "Plumilla Estandar Negra 0.71mm", "category": "Plumillas", "stock": 0, "min_stock": 20, "unit_cost": 0.0, "sale_price": 15.0},
    {"id": "PICK-EST-10", "name": "Plumilla Estandar Negra 1.0mm", "category": "Plumillas", "stock": 0, "min_stock": 20, "unit_cost": 0.0, "sale_price": 15.0},
    {"id": "PICK-EST-15", "name": "Plumilla Estandar Negra 1.5mm", "category": "Plumillas", "stock": 0, "min_stock": 20, "unit_cost": 0.0, "sale_price": 15.0},
    {"id": "PICK-J3-12", "name": "Plumilla Jazz III 1.2mm", "category": "Plumillas", "stock": 0, "min_stock": 15, "unit_cost": 0.0, "sale_price": 18.0},
    {"id": "PICK-JXL-12", "name": "Plumilla Jazz XL 1.2mm", "category": "Plumillas", "stock": 0, "min_stock": 15, "unit_cost": 0.0, "sale_price": 18.0},
    {"id": "PICK-JXL-15", "name": "Plumilla Jazz XL 1.5mm", "category": "Plumillas", "stock": 0, "min_stock": 15, "unit_cost": 0.0, "sale_price": 18.0},
    {"id": "PICK-TEAR-15", "name": "Plumilla Teardrop 1.5mm", "category": "Plumillas", "stock": 0, "min_stock": 15, "unit_cost": 0.0, "sale_price": 17.0},
    {"id": "PICK-TRI-114", "name": "Plumilla Triangular 1.14mm", "category": "Plumillas", "stock": 0, "min_stock": 15, "unit_cost": 0.0, "sale_price": 16.0},
    {"id": "PICK-TRI-073", "name": "Plumilla Triangular 0.73mm", "category": "Plumillas", "stock": 0, "min_stock": 15, "unit_cost": 0.0, "sale_price": 16.0},
    {"id": "ALT-STR-BLK", "name": "Straplocks Negro", "category": "Alternos", "stock": 0, "min_stock": 6, "unit_cost": 0.0, "sale_price": 180.0},
    {"id": "ALT-STR-SLV", "name": "Straplocks Plateado", "category": "Alternos", "stock": 0, "min_stock": 6, "unit_cost": 0.0, "sale_price": 180.0},
    {"id": "ALT-PH-BLK", "name": "Pickholder Negro", "category": "Alternos", "stock": 0, "min_stock": 10, "unit_cost": 0.0, "sale_price": 65.0},
    {"id": "ALT-BAQ-5A", "name": "Baquetas Hickory 5A", "category": "Alternos", "stock": 0, "min_stock": 8, "unit_cost": 0.0, "sale_price": 220.0},
    {"id": "ALT-DIJ-BLK", "name": "Dije Negro", "category": "Alternos", "stock": 0, "min_stock": 10, "unit_cost": 0.0, "sale_price": 50.0},
    {"id": "ALT-DIJ-SLV", "name": "Dije Plateado", "category": "Alternos", "stock": 0, "min_stock": 10, "unit_cost": 0.0, "sale_price": 50.0},
]


DEFAULT_PICK_PRICING: dict[str, Any] = {
    "groups": {
        "JAZZ": {
            "name": "Jazz XL y III",
            "tiers": [
                {"qty": 10, "one_side": 180.0, "two_sides": 200.0},
                {"qty": 20, "one_side": 340.0, "two_sides": 370.0},
                {"qty": 30, "one_side": 480.0, "two_sides": 520.0},
            ],
            "bulk": {"min_qty": 40, "one_side_unit": 15.0, "two_sides_unit": 16.0},
        },
        "TRI_TEAR": {
            "name": "Triangular y Teardrop",
            "tiers": [
                {"qty": 10, "one_side": 170.0, "two_sides": 180.0},
                {"qty": 20, "one_side": 320.0, "two_sides": 340.0},
                {"qty": 30, "one_side": 450.0, "two_sides": 490.0},
            ],
            "bulk": {"min_qty": 40, "one_side_unit": 14.0, "two_sides_unit": 15.0},
        },
        "STANDARD": {
            "name": "Estandar",
            "tiers": [
                {"qty": 10, "one_side": 140.0, "two_sides": 160.0},
                {"qty": 20, "one_side": 260.0, "two_sides": 300.0},
                {"qty": 30, "one_side": 360.0, "two_sides": 420.0},
            ],
            "bulk": {"min_qty": 40, "one_side_unit": 11.0, "two_sides_unit": 13.0},
        },
    }
}
