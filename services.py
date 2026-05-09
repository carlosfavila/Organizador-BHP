from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def month_key_from_date(value: str) -> str:
    return value[:7]


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def calculate_engraving_cost(_: float, __: str) -> float:
    return 0.0


def calculate_balance(subtotal: float, engraving_cost: float, shipping_cost: float, advance: float) -> float:
    return round((subtotal + engraving_cost + shipping_cost) - advance, 2)


def infer_pick_pricing_group(product_name: str) -> str:
    upper = product_name.upper()
    if "JAZZ III" in upper or "JAZZ XL" in upper:
        return "JAZZ"
    if "TRIANGULAR" in upper or "TEARDROP" in upper:
        return "TRI_TEAR"
    return "STANDARD"


def is_pick_product(product: dict[str, Any]) -> bool:
    return str(product.get("category", "")).strip().lower() == "plumillas"


def get_sale_unit_price(product: dict[str, Any], engraving_mode: str) -> float:
    one_side_price = safe_float(str(product.get("sale_price_one_side", product.get("sale_price", 0.0))), 0.0)
    two_sides_price = safe_float(str(product.get("sale_price_two_sides", one_side_price)), one_side_price)
    if is_pick_product(product) and engraving_mode == "2 Lados":
        return round(two_sides_price, 2)
    return round(one_side_price, 2)


def generate_product_id(name: str, category: str, existing_ids: set[str]) -> str:
    prefix = "PICK" if category == "Plumillas" else "ALT"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip().upper()).strip("-")
    slug = slug[:20] if slug else "PRODUCTO"
    base_id = f"{prefix}-{slug}"
    candidate = base_id
    idx = 2
    while candidate in existing_ids:
        candidate = f"{base_id}-{idx}"
        idx += 1
    return candidate


def generate_sale_id(month_key: str, month_sales: list[dict[str, Any]]) -> str:
    yy = month_key[2:4]
    mm = month_key[5:7]
    sequence = len(month_sales) + 1
    return f"BHP-{yy}-{mm}-{sequence:03d}"


def calculate_pick_subtotal_from_rules(
    qty: int,
    engraving_mode: str,
    pricing_group: str,
    pricing_db: dict[str, Any],
) -> tuple[float, float, str]:
    groups = pricing_db.get("groups", {})
    group_data = groups.get(pricing_group) or groups.get("STANDARD", {})
    group_name = group_data.get("name", pricing_group)
    side_key = "two_sides" if engraving_mode == "2 Lados" else "one_side"
    bulk_data = group_data.get("bulk", {})
    bulk_min_qty = max(1, safe_int(str(bulk_data.get("min_qty", 40)), 40))
    if qty >= bulk_min_qty:
        unit_key = "two_sides_unit" if side_key == "two_sides" else "one_side_unit"
        bulk_unit = safe_float(str(bulk_data.get(unit_key, 0.0)), 0.0)
        subtotal = round(qty * bulk_unit, 2)
        return subtotal, bulk_unit, f"{group_name} mayoreo ({qty} x ${bulk_unit:.2f})"

    tiers = sorted(group_data.get("tiers", []), key=lambda t: safe_int(str(t.get("qty", 0)), 0))
    if not tiers:
        return 0.0, 0.0, f"{group_name} sin reglas"
    selected_tier = tiers[0]
    for tier in tiers:
        if qty >= safe_int(str(tier.get("qty", 0)), 0):
            selected_tier = tier
    tier_qty = max(1, safe_int(str(selected_tier.get("qty", 10)), 10))
    tier_price = safe_float(str(selected_tier.get(side_key, 0.0)), 0.0)
    implied_unit = round(tier_price / tier_qty, 2)
    return tier_price, implied_unit, f"{group_name} paquete {tier_qty}"


def calculate_sale_subtotal(
    product: dict[str, Any],
    qty: int,
    engraving_mode: str,
    pricing_mode: str,
    pricing_db: dict[str, Any],
    sponsorship_total: float = 0.0,
) -> tuple[float, float, str]:
    if qty <= 0:
        return 0.0, 0.0, "Cantidad invalida"
    if pricing_mode in ("Patrocinio", "Multi-modelo"):
        amount = max(0.0, sponsorship_total)
        label = "Patrocinio" if pricing_mode == "Patrocinio" else "Multi-modelo"
        return amount, amount, label
    if is_pick_product(product):
        pricing_group = product.get("pricing_group", infer_pick_pricing_group(product.get("name", "")))
        return calculate_pick_subtotal_from_rules(qty, engraving_mode, pricing_group, pricing_db)
    unit_price = get_sale_unit_price(product, engraving_mode)
    subtotal = round(qty * unit_price, 2)
    return subtotal, unit_price, "Precio unitario"


def summarize_month(month: str, ventas: dict[str, Any], compras: dict[str, Any], mermas: dict[str, Any]) -> dict[str, Any]:
    month_sales = ventas.get("by_month", {}).get(month, [])
    month_purchases = [x for x in compras.get("items", []) if month_key_from_date(x.get("date", "")) == month]
    month_waste = [x for x in mermas.get("items", []) if month_key_from_date(x.get("date", "")) == month]

    # Ingresos: suma anticipo si está en "Anticipo", suma total si está "Pagado"
    ingresos = round(
        sum(
            s.get("total", 0) if s.get("payment_status", "Anticipo") == "Pagado" 
            else s.get("advance", 0)
            for s in month_sales
        ), 
        2
    )
    inversion = round(sum(p.get("total_cost", 0) for p in month_purchases), 2)
    costo_mermas = round(sum(m.get("loss_cost", 0) for m in month_waste), 2)
    ganancia_neta = round(ingresos - inversion - costo_mermas, 2)

    sold_counter: dict[str, int] = {}
    for sale in month_sales:
        product_id = sale.get("product_id", "")
        sold_counter[product_id] = sold_counter.get(product_id, 0) + int(sale.get("quantity", 0))
    most_sold = max(sold_counter.items(), key=lambda item: item[1])[0] if sold_counter else "Sin ventas"
    return {
        "ingresos": ingresos,
        "inversion": inversion,
        "mermas": costo_mermas,
        "ganancia_neta": ganancia_neta,
        "most_sold_id": most_sold,
        "sales_count": len(month_sales),
    }


def get_month_sales_by_model(month: str, ventas: dict[str, Any]) -> list[tuple[str, int]]:
    month_sales = ventas.get("by_month", {}).get(month, [])
    sold_counter: dict[str, int] = {}
    for sale in month_sales:
        product_id = sale.get("product_id", "")
        sold_counter[product_id] = sold_counter.get(product_id, 0) + int(sale.get("quantity", 0))
    return sorted(sold_counter.items(), key=lambda item: item[1], reverse=True)


class InventoryService:
    def __init__(self, db: dict[str, Any]) -> None:
        self.db = db
        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        self.stock_items = self.db["stock"]["items"]
        self.product_map: dict[str, dict[str, Any]] = {x["id"]: x for x in self.stock_items}
        self.clients_items = self.db["clientes"].setdefault("items", [])
        self.client_map: dict[str, dict[str, Any]] = {c.get("name", "").lower(): c for c in self.clients_items if c.get("name")}

    def pending_purchase_qty(self, product_id: str) -> int:
        pending = 0
        for rec in self.db["compras"].get("items", []):
            if rec.get("product_id") == product_id and not rec.get("received", False):
                pending += safe_int(str(rec.get("quantity", 0)), 0)
        return pending

    def get_client_names(self) -> list[str]:
        return sorted([c.get("name", "") for c in self.db["clientes"].get("items", []) if c.get("name")])

    def add_sale(self, payload: dict[str, Any]) -> tuple[str, set[str]]:
        product = self.product_map[payload["product_id"]]
        current_month = self.db["ventas"]["current_month"]
        month_sales = self.db["ventas"]["by_month"].setdefault(current_month, [])
        sale_id = generate_sale_id(current_month, month_sales)
        sale_date = datetime.now().strftime("%Y-%m-%d")
        sale_record = {
            "id": sale_id,
            "date": sale_date,
            "month": current_month,
            "client_name": payload["client_name"],
            "product_id": payload["product_id"],
            "quantity": payload["qty"],
            "pricing_mode": payload["pricing_mode"],
            "pricing_note": payload["pricing_note"],
            "engraving_mode": payload["engraving_mode"],
            "engraving_cost": payload["engraving_cost"],
            "shipping_mode": payload["shipping_mode"],
            "shipping_cost": payload["shipping_cost"],
            "advance": payload["advance"],
            "unit_sale_price": payload["unit_price"],
            "subtotal": payload["subtotal"],
            "total": payload["total"],
            "balance": payload["balance"],
            "status": payload["status"],
            "notes": payload["notes"],
        }
        month_sales.append(sale_record)
        product["stock"] = int(product.get("stock", 0)) - payload["qty"]

        client_name = payload["client_name"]
        client_row = self.client_map.get(client_name.lower())
        if not client_row:
            client_row = {"name": client_name, "total_spent": 0.0, "orders": []}
            self.clients_items.append(client_row)
            self.client_map[client_name.lower()] = client_row
        client_row["total_spent"] = round(float(client_row.get("total_spent", 0.0)) + payload["total"], 2)
        client_row.setdefault("orders", []).append(
            {"sale_id": sale_id, "date": sale_date, "product_id": payload["product_id"], "quantity": payload["qty"], "total": payload["total"]}
        )
        return sale_id, {"ventas", "stock", "clientes"}

    def delete_sale(self, sale_id: str, month: str) -> tuple[str, set[str]]:
        month_sales = self.db["ventas"].get("by_month", {}).get(month, [])
        idx = next((i for i, s in enumerate(month_sales) if s.get("id") == sale_id), -1)
        if idx < 0:
            return "No se encontró la venta.", set()
        sale = month_sales[idx]
        if sale.get("status") != "En proceso":
            return "Solo se puede eliminar una venta en proceso.", set()
        product = self.product_map.get(sale.get("product_id", ""))
        if product:
            product["stock"] = int(product.get("stock", 0)) + safe_int(str(sale.get("quantity", 0)), 0)
        client_row = self.client_map.get(str(sale.get("client_name", "")).lower())
        if client_row:
            total = safe_float(str(sale.get("total", 0.0)), 0.0)
            client_row["total_spent"] = round(max(0.0, float(client_row.get("total_spent", 0.0)) - total), 2)
            client_row["orders"] = [o for o in client_row.get("orders", []) if o.get("sale_id") != sale_id]
        month_sales.pop(idx)
        return "Venta eliminada y stock corregido.", {"ventas", "stock", "clientes"}

    def save_stock_row(self, item_id: str, stock_value: str, min_value: str) -> set[str]:
        row = self.product_map[item_id]
        row["stock"] = max(0, safe_int(stock_value, 0))
        row["min_stock"] = max(0, safe_int(min_value, 0))
        return {"stock"}

    def add_product(self, payload: dict[str, Any]) -> tuple[str, set[str]]:
        existing_ids = set(self.product_map.keys())
        product_id = generate_product_id(payload["name"], payload["category"], existing_ids)
        one_side = max(0.0, safe_float(payload["price_one_side"], 0.0))
        two_sides = max(0.0, safe_float(payload["price_two_sides"], one_side))
        if payload["category"] != "Plumillas":
            two_sides = one_side
        new_item = {
            "id": product_id,
            "name": payload["name"],
            "category": payload["category"],
            "stock": max(0, safe_int(payload["stock"], 0)),
            "min_stock": max(0, safe_int(payload["min_stock"], 0)),
            "unit_cost": max(0.0, safe_float(payload["unit_cost"], 0.0)),
            "sale_price": one_side,
            "sale_price_one_side": one_side,
            "sale_price_two_sides": two_sides,
            "pricing_group": infer_pick_pricing_group(payload["name"]) if payload["category"] == "Plumillas" else "",
        }
        self.stock_items.append(new_item)
        self.product_map[product_id] = new_item
        return product_id, {"stock"}

    def add_purchase(self, product_id: str, qty_value: str, total_cost_value: str) -> set[str]:
        qty = safe_int(qty_value, 0)
        total_cost = safe_float(total_cost_value, 0.0)
        rec = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "month": self.db["ventas"]["current_month"],
            "product_id": product_id,
            "quantity": qty,
            "total_cost": round(total_cost, 2),
            "unit_cost": round(total_cost / qty, 2),
            "received": False,
            "received_date": "",
        }
        self.db["compras"].setdefault("items", []).append(rec)
        return {"compras"}

    def toggle_purchase_received(self, item_index: int) -> tuple[str, set[str]]:
        rec = self.db["compras"]["items"][item_index]
        item = self.product_map[rec.get("product_id", "")]
        qty = safe_int(str(rec.get("quantity", 0)), 0)
        if rec.get("received", False):
            if qty > int(item.get("stock", 0)):
                raise ValueError("stock insuficiente")
            item["stock"] = int(item.get("stock", 0)) - qty
            rec["received"] = False
            rec["received_date"] = ""
            return "Recepcion revertida. Se descontó del stock.", {"compras", "stock"}
        item["stock"] = int(item.get("stock", 0)) + qty
        item["unit_cost"] = safe_float(str(rec.get("unit_cost", 0.0)), 0.0)
        rec["received"] = True
        rec["received_date"] = datetime.now().strftime("%Y-%m-%d")
        return "Compra recibida y stock actualizado.", {"compras", "stock"}

    def add_waste(self, product_id: str, qty_value: str, reason: str) -> set[str]:
        item = self.product_map[product_id]
        qty = safe_int(qty_value, 0)
        item["stock"] = int(item.get("stock", 0)) - qty
        rec = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "month": self.db["ventas"]["current_month"],
            "product_id": product_id,
            "quantity": qty,
            "reason": reason,
            "loss_cost": round(float(item.get("unit_cost", 0.0)) * qty, 2),
        }
        self.db["mermas"].setdefault("items", []).append(rec)
        return {"mermas", "stock"}
