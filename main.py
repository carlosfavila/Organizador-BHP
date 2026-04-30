import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import flet as ft

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


INITIAL_PRODUCTS = [
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

DEFAULT_PICK_PRICING = {
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


def month_key_from_date(value: str) -> str:
    return value[:7]


def now_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


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


def calculate_engraving_cost(subtotal: float, engraving_mode: str) -> float:
    if engraving_mode in {"1 Lado", "Lado(s)", "2 Lados", "Sin grabado"}:
        return 0.0
    return 0.0


def is_pick_product(product: dict[str, Any]) -> bool:
    return str(product.get("category", "")).strip().lower() == "plumillas"


def infer_pick_pricing_group(product_name: str) -> str:
    upper = product_name.upper()
    if "JAZZ III" in upper or "JAZZ XL" in upper:
        return "JAZZ"
    if "TRIANGULAR" in upper or "TEARDROP" in upper:
        return "TRI_TEAR"
    return "STANDARD"


def get_sale_unit_price(product: dict[str, Any], engraving_mode: str) -> float:
    one_side_price = safe_float(str(product.get("sale_price_one_side", product.get("sale_price", 0.0))), 0.0)
    two_sides_price = safe_float(str(product.get("sale_price_two_sides", one_side_price)), one_side_price)
    if is_pick_product(product) and engraving_mode == "2 Lados":
        return round(two_sides_price, 2)
    return round(one_side_price, 2)


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
        tier_qty = safe_int(str(tier.get("qty", 0)), 0)
        if qty >= tier_qty:
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

    if pricing_mode == "Patrocinio":
        sponsorship_price = max(0.0, sponsorship_total)
        return sponsorship_price, sponsorship_price, "Patrocinio"

    if is_pick_product(product):
        pricing_group = product.get("pricing_group", infer_pick_pricing_group(product.get("name", "")))
        return calculate_pick_subtotal_from_rules(qty, engraving_mode, pricing_group, pricing_db)

    unit_price = get_sale_unit_price(product, engraving_mode)
    subtotal = round(qty * unit_price, 2)
    return subtotal, unit_price, "Precio unitario"


def generate_product_id(name: str, category: str, existing_ids: set[str]) -> str:
    prefix = "PICK" if category == "Plumillas" else "ALT"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip().upper()).strip("-")
    slug = slug[:20] if slug else "PRODUCTO"
    base_id = f"{prefix}-{slug}"
    candidate = base_id
    n = 2
    while candidate in existing_ids:
        candidate = f"{base_id}-{n}"
        n += 1
    return candidate


def calculate_balance(subtotal: float, engraving_cost: float, shipping_cost: float, advance: float) -> float:
    return round((subtotal + engraving_cost + shipping_cost) - advance, 2)


def update_inventory_quantity(product: dict[str, Any], qty_delta: int) -> None:
    product["stock"] = int(product.get("stock", 0)) + qty_delta


@dataclass
class JsonStore:
    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.stock_file = self.base_dir / "stock.json"
        self.ventas_file = self.base_dir / "ventas.json"
        self.compras_file = self.base_dir / "compras.json"
        self.mermas_file = self.base_dir / "mermas.json"
        self.clientes_file = self.base_dir / "clientes.json"
        self.pricing_file = self.base_dir / "pricing_rules.json"
        self._ensure_files()

    def _read_json(self, path: Path, default_value: Any) -> Any:
        if not path.exists():
            self._write_json(path, deepcopy(default_value))
            return deepcopy(default_value)

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            backup_path = path.with_suffix(path.suffix + ".broken")
            try:
                path.replace(backup_path)
            except Exception:
                pass
            self._write_json(path, deepcopy(default_value))
            return deepcopy(default_value)

    def _write_json(self, path: Path, payload: Any) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def _ensure_files(self) -> None:
        stock_default = {"items": deepcopy(INITIAL_PRODUCTS)}
        ventas_default = {"current_month": now_month_key(), "by_month": {now_month_key(): []}}
        compras_default = {"items": []}
        mermas_default = {"items": []}
        clientes_default = {"items": []}
        pricing_default = deepcopy(DEFAULT_PICK_PRICING)

        stock_data = self._read_json(self.stock_file, stock_default)
        if "items" not in stock_data or not isinstance(stock_data["items"], list):
            stock_data = stock_default

        existing_ids = {row.get("id") for row in stock_data["items"]}
        for prod in INITIAL_PRODUCTS:
            if prod["id"] not in existing_ids:
                stock_data["items"].append(deepcopy(prod))

        for row in stock_data["items"]:
            base_price = safe_float(str(row.get("sale_price", row.get("sale_price_one_side", 0.0))), 0.0)
            row["sale_price_one_side"] = safe_float(str(row.get("sale_price_one_side", base_price)), base_price)
            row["sale_price_two_sides"] = safe_float(str(row.get("sale_price_two_sides", row["sale_price_one_side"])), row["sale_price_one_side"])
            row["sale_price"] = row["sale_price_one_side"]
            if is_pick_product(row):
                row["pricing_group"] = row.get("pricing_group", infer_pick_pricing_group(row.get("name", "")))
                row["sponsorship_price"] = max(0.0, safe_float(str(row.get("sponsorship_price", row["sale_price_one_side"])), row["sale_price_one_side"]))
            else:
                row["pricing_group"] = ""
                row["sponsorship_price"] = max(0.0, safe_float(str(row.get("sponsorship_price", row["sale_price_one_side"])), row["sale_price_one_side"]))
        self._write_json(self.stock_file, stock_data)

        ventas_data = self._read_json(self.ventas_file, ventas_default)
        if "by_month" not in ventas_data or not isinstance(ventas_data["by_month"], dict):
            ventas_data = ventas_default
        if "current_month" not in ventas_data:
            ventas_data["current_month"] = now_month_key()
        ventas_data["by_month"].setdefault(ventas_data["current_month"], [])
        self._write_json(self.ventas_file, ventas_data)

        self._write_json(self.compras_file, self._read_json(self.compras_file, compras_default))
        self._write_json(self.mermas_file, self._read_json(self.mermas_file, mermas_default))
        self._write_json(self.clientes_file, self._read_json(self.clientes_file, clientes_default))
        self._write_json(self.pricing_file, self._read_json(self.pricing_file, pricing_default))

    def load_all(self) -> dict[str, Any]:
        return {
            "stock": self._read_json(self.stock_file, {"items": []}),
            "ventas": self._read_json(self.ventas_file, {"current_month": now_month_key(), "by_month": {}}),
            "compras": self._read_json(self.compras_file, {"items": []}),
            "mermas": self._read_json(self.mermas_file, {"items": []}),
            "clientes": self._read_json(self.clientes_file, {"items": []}),
            "pricing": self._read_json(self.pricing_file, deepcopy(DEFAULT_PICK_PRICING)),
        }

    def save_stock(self, payload: dict[str, Any]) -> None:
        self._write_json(self.stock_file, payload)

    def save_ventas(self, payload: dict[str, Any]) -> None:
        self._write_json(self.ventas_file, payload)

    def save_compras(self, payload: dict[str, Any]) -> None:
        self._write_json(self.compras_file, payload)

    def save_mermas(self, payload: dict[str, Any]) -> None:
        self._write_json(self.mermas_file, payload)

    def save_clientes(self, payload: dict[str, Any]) -> None:
        self._write_json(self.clientes_file, payload)

    def save_pricing(self, payload: dict[str, Any]) -> None:
        self._write_json(self.pricing_file, payload)


def build_product_map(stock_items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in stock_items}


def generate_sale_id(month_key: str, month_sales: list[dict[str, Any]]) -> str:
    yy = month_key[2:4]
    mm = month_key[5:7]
    sequence = len(month_sales) + 1
    return f"BHP-{yy}-{mm}-{sequence:03d}"


def summarize_month(
    month: str,
    ventas: dict[str, Any],
    compras: dict[str, Any],
    mermas: dict[str, Any],
) -> dict[str, Any]:
    month_sales = ventas.get("by_month", {}).get(month, [])
    month_purchases = [x for x in compras.get("items", []) if month_key_from_date(x.get("date", "")) == month]
    month_waste = [x for x in mermas.get("items", []) if month_key_from_date(x.get("date", "")) == month]

    ingresos = round(sum(s.get("total", 0) for s in month_sales), 2)
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


def export_month_pdf(
    month: str,
    month_sales: list[dict[str, Any]],
    month_summary: dict[str, Any],
    product_map: dict[str, dict[str, Any]],
) -> Path:
    report_name = f"reporte_{month.replace('-', '_')}.pdf"
    report_path = Path.cwd() / report_name
    c = canvas.Canvas(str(report_path), pagesize=letter)
    c.setTitle(f"Reporte Mensual Black Hole Picks - {month}")
    width, height = letter

    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Black Hole Picks - Reporte Mensual {month}")
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Ingresos Totales: ${month_summary['ingresos']:.2f}")
    y -= 18
    c.drawString(40, y, f"Costos de Inversion: ${month_summary['inversion']:.2f}")
    y -= 18
    c.drawString(40, y, f"Costos de Mermas: ${month_summary['mermas']:.2f}")
    y -= 18
    c.drawString(40, y, f"Ganancia Neta: ${month_summary['ganancia_neta']:.2f}")
    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Tabla de ventas:")
    y -= 20

    c.setFont("Helvetica", 9)
    headers = ["ID", "Fecha", "Cliente", "Producto", "Cant", "Total", "Status"]
    x_positions = [40, 105, 175, 250, 390, 425, 485]
    for idx, text in enumerate(headers):
        c.drawString(x_positions[idx], y, text)
    y -= 14

    for sale in month_sales:
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)
        product_name = product_map.get(sale.get("product_id", ""), {}).get("name", sale.get("product_id", ""))
        row = [
            sale.get("id", ""),
            sale.get("date", ""),
            sale.get("client_name", ""),
            product_name[:24],
            str(sale.get("quantity", "")),
            f"${sale.get('total', 0):.2f}",
            sale.get("status", ""),
        ]
        for idx, text in enumerate(row):
            c.drawString(x_positions[idx], y, str(text))
        y -= 13

    c.save()
    return report_path


def main(page: ft.Page) -> None:
    page.title = "Black Hole Picks - Inventario y Ventas"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0A0A0A"
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 16
    page.window.width = 1450
    page.window.height = 900

    store = JsonStore(Path.cwd() / "assets")
    db = store.load_all()
    stock_items = db["stock"]["items"]
    product_map = build_product_map(stock_items)

    def get_client_names() -> list[str]:
        return sorted([c.get("name", "") for c in db["clientes"].get("items", []) if c.get("name")])

    def get_pending_purchase_qty(product_id: str) -> int:
        pending = 0
        for rec in db["compras"].get("items", []):
            if rec.get("product_id") == product_id and not rec.get("received", False):
                pending += safe_int(str(rec.get("quantity", 0)), 0)
        return pending

    def get_pick_price_brief(product: dict[str, Any]) -> str:
        if not is_pick_product(product):
            return (
                f"1 lado: ${float(product.get('sale_price_one_side', product.get('sale_price', 0))):.2f} | "
                f"2 lados: ${float(product.get('sale_price_two_sides', product.get('sale_price', 0))):.2f}"
            )

        pricing_group = product.get("pricing_group", infer_pick_pricing_group(product.get("name", "")))
        groups = db.get("pricing", {}).get("groups", {})
        group_data = groups.get(pricing_group) or groups.get("STANDARD", {})
        group_name = group_data.get("name", pricing_group)
        bulk = group_data.get("bulk", {})
        return (
            f"{group_name} | P10/P20/P30 | Mayoreo {int(bulk.get('min_qty', 40))}+ "
            f"(${float(bulk.get('one_side_unit', 0)):.2f}/${float(bulk.get('two_sides_unit', 0)):.2f})"
        )

    def show_message(text: str, color: str = ft.Colors.BLUE_300) -> None:
        page.snack_bar = ft.SnackBar(content=ft.Text(text), bgcolor=color, duration=3500)
        page.snack_bar.open = True
        page.update()

    # Dashboard controls
    current_month_label = ft.Text("", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300)
    ingresos_text = ft.Text("$0.00")
    inversion_text = ft.Text("$0.00")
    mermas_text = ft.Text("$0.00")
    ganancia_text = ft.Text("$0.00", size=20, weight=ft.FontWeight.BOLD)
    most_sold_text = ft.Text("Sin ventas", color=ft.Colors.AMBER_200)
    month_sales_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Cliente")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cant")),
            ft.DataColumn(ft.Text("Total")),
            ft.DataColumn(ft.Text("Status")),
        ],
        rows=[],
        column_spacing=18,
        heading_row_color=ft.Colors.BLUE_GREY_900,
        data_row_min_height=40,
    )

    def refresh_dashboard() -> None:
        current_month = db["ventas"]["current_month"]
        summary = summarize_month(current_month, db["ventas"], db["compras"], db["mermas"])
        current_month_label.value = f"Mes activo: {current_month}"
        ingresos_text.value = f"${summary['ingresos']:.2f}"
        inversion_text.value = f"${summary['inversion']:.2f}"
        mermas_text.value = f"${summary['mermas']:.2f}"
        ganancia_text.value = f"${summary['ganancia_neta']:.2f}"
        product_info = product_map.get(summary["most_sold_id"], {})
        most_sold_text.value = product_info.get("name", summary["most_sold_id"])

        rows = []
        for sale in db["ventas"].get("by_month", {}).get(current_month, []):
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(sale.get("id", ""))),
                        ft.DataCell(ft.Text(sale.get("date", ""))),
                        ft.DataCell(ft.Text(sale.get("client_name", ""))),
                        ft.DataCell(ft.Text(product_map.get(sale.get("product_id", ""), {}).get("name", sale.get("product_id", "")))),
                        ft.DataCell(ft.Text(str(sale.get("quantity", 0)))),
                        ft.DataCell(ft.Text(f"${sale.get('total', 0):.2f}")),
                        ft.DataCell(ft.Text(sale.get("status", ""))),
                    ]
                )
            )
        month_sales_table.rows = rows

    def open_history_dialog(_: ft.ControlEvent) -> None:
        month_options = sorted(db["ventas"].get("by_month", {}).keys(), reverse=True)
        selected_month = ft.Dropdown(
            label="Selecciona mes",
            options=[ft.dropdown.Option(key=m, text=m) for m in month_options],
            value=month_options[0] if month_options else None,
            width=260,
        )
        summary_text = ft.Text("")
        sales_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Cliente")),
                ft.DataColumn(ft.Text("Producto")),
                ft.DataColumn(ft.Text("Cant")),
                ft.DataColumn(ft.Text("Total")),
            ],
            rows=[],
            column_spacing=14,
        )

        def render_month(_: ft.ControlEvent | None = None) -> None:
            month = selected_month.value
            if not month:
                return
            summary = summarize_month(month, db["ventas"], db["compras"], db["mermas"])
            summary_text.value = (
                f"Ingresos: ${summary['ingresos']:.2f}  |  Inversion: ${summary['inversion']:.2f}  |  "
                f"Mermas: ${summary['mermas']:.2f}  |  Neta: ${summary['ganancia_neta']:.2f}"
            )

            rows = []
            for sale in db["ventas"].get("by_month", {}).get(month, []):
                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(sale.get("id", ""))),
                            ft.DataCell(ft.Text(sale.get("date", ""))),
                            ft.DataCell(ft.Text(sale.get("client_name", ""))),
                            ft.DataCell(ft.Text(product_map.get(sale.get("product_id", ""), {}).get("name", sale.get("product_id", "")))),
                            ft.DataCell(ft.Text(str(sale.get("quantity", 0)))),
                            ft.DataCell(ft.Text(f"${sale.get('total', 0):.2f}")),
                        ]
                    )
                )
            sales_table.rows = rows
            page.update()

        selected_month.on_change = render_month
        render_month()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Historial Mensual"),
            content=ft.Container(
                width=950,
                height=520,
                content=ft.Column(
                    controls=[
                        selected_month,
                        summary_text,
                        ft.Divider(),
                        ft.Text("Ventas del mes"),
                        ft.Row([ft.Container(expand=True, content=ft.Column([sales_table], scroll=ft.ScrollMode.ALWAYS))], expand=True),
                    ],
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: close_dialog())],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        def close_dialog() -> None:
            dialog.open = False
            page.update()

        page.dialog = dialog
        dialog.open = True
        page.update()

    def create_new_month(_: ft.ControlEvent) -> None:
        default_next = datetime.now().strftime("%Y-%m")
        month_input = ft.TextField(label="Nuevo mes (YYYY-MM)", value=default_next, width=220)

        def submit(_: ft.ControlEvent) -> None:
            month = month_input.value.strip()
            if len(month) != 7 or month[4] != "-":
                show_message("Mes invalido. Usa formato YYYY-MM.", ft.Colors.RED_400)
                return
            db["ventas"]["current_month"] = month
            db["ventas"]["by_month"].setdefault(month, [])
            store.save_ventas(db["ventas"])
            refresh_dashboard()
            refresh_sales_views()
            close_dialog()
            show_message(f"Mes activo actualizado a {month}.")

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Crear / cambiar mes"),
            content=month_input,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: close_dialog()),
                ft.Button("Guardar", on_click=submit),
            ],
        )

        def close_dialog() -> None:
            dialog.open = False
            page.update()

        page.dialog = dialog
        dialog.open = True
        page.update()

    def export_current_month_pdf(_: ft.ControlEvent) -> None:
        if not REPORTLAB_AVAILABLE:
            show_message("Instala reportlab: pip install reportlab", ft.Colors.RED_400)
            return

        month = db["ventas"]["current_month"]
        month_sales = db["ventas"].get("by_month", {}).get(month, [])
        summary = summarize_month(month, db["ventas"], db["compras"], db["mermas"])
        output = export_month_pdf(month, month_sales, summary, product_map)
        show_message(f"PDF exportado: {output.name}", ft.Colors.GREEN_500)

    dashboard_tab = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("Black Hole Picks", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_200),
                    current_month_label,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Row(
                controls=[
                    ft.Container(
                        padding=12,
                        bgcolor=ft.Colors.BLUE_GREY_900,
                        border_radius=10,
                        content=ft.Column([ft.Text("Ingresos Totales"), ingresos_text]),
                        expand=1,
                    ),
                    ft.Container(
                        padding=12,
                        bgcolor=ft.Colors.BLUE_GREY_900,
                        border_radius=10,
                        content=ft.Column([ft.Text("Costos de Inversion"), inversion_text]),
                        expand=1,
                    ),
                    ft.Container(
                        padding=12,
                        bgcolor=ft.Colors.BLUE_GREY_900,
                        border_radius=10,
                        content=ft.Column([ft.Text("Costos de Mermas"), mermas_text]),
                        expand=1,
                    ),
                    ft.Container(
                        padding=12,
                        bgcolor=ft.Colors.DEEP_PURPLE_900,
                        border_radius=10,
                        content=ft.Column([ft.Text("Ganancia Neta"), ganancia_text]),
                        expand=1,
                    ),
                ]
            ),
            ft.Row(
                controls=[
                    ft.Container(
                        padding=10,
                        bgcolor=ft.Colors.BLUE_GREY_900,
                        border_radius=8,
                        content=ft.Row([ft.Text("Producto mas vendido:"), most_sold_text]),
                        expand=True,
                    ),
                    ft.Button("Crear Nuevo Mes", icon=ft.Icons.CALENDAR_MONTH, on_click=create_new_month),
                    ft.Button("Historial", icon=ft.Icons.HISTORY, on_click=open_history_dialog),
                    ft.Button("Exportar PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_current_month_pdf),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(),
            ft.Text("Ventas del mes activo", weight=ft.FontWeight.BOLD),
            ft.Row([ft.Container(expand=True, content=ft.Column([month_sales_table], scroll=ft.ScrollMode.ALWAYS))], expand=True),
        ],
        expand=True,
    )

    # Ventas controls
    sale_id_preview = ft.Text("ID: --")
    sale_date_preview = ft.Text("Fecha: --")
    client_dropdown = ft.Dropdown(label="Cliente existente", width=240, options=[])
    new_client_name = ft.TextField(label="o crear cliente nuevo", width=240)
    sale_product_dropdown = ft.Dropdown(label="Producto", width=330, options=[])
    sale_qty = ft.TextField(label="Cantidad", value="1", width=100)
    sale_price_mode = ft.Dropdown(
        label="Modalidad",
        width=160,
        value="Normal",
        options=[ft.dropdown.Option("Normal"), ft.dropdown.Option("Patrocinio")],
    )
    sponsorship_total_input = ft.TextField(label="Total patrocinio", value="0", width=150, disabled=True)
    engraving_mode = ft.Dropdown(
        label="Grabado",
        width=140,
        value="1 Lado",
        options=[ft.dropdown.Option("1 Lado"), ft.dropdown.Option("2 Lados"), ft.dropdown.Option("Sin grabado")],
    )
    shipping_mode = ft.Dropdown(
        label="Envio",
        width=180,
        value="Entrega incluida",
        options=[ft.dropdown.Option("Entrega incluida"), ft.dropdown.Option("Envio Cotizado")],
    )
    shipping_manual = ft.TextField(label="Envio manual", value="0", width=120, disabled=True)
    advance_input = ft.TextField(label="Anticipo", value="0", width=120)
    sale_status = ft.Dropdown(
        label="Estatus",
        width=140,
        value="En proceso",
        options=[ft.dropdown.Option("En proceso"), ft.dropdown.Option("Listas"), ft.dropdown.Option("Entregado")],
    )
    notes_input = ft.TextField(label="Notas", multiline=True, min_lines=2, max_lines=3, expand=True)

    subtotal_preview = ft.Text("Subtotal: $0.00")
    pricing_rule_preview = ft.Text("Regla: --", color=ft.Colors.CYAN_200)
    engraving_preview = ft.Text("Grabado: $0.00")
    shipping_preview = ft.Text("Envio: $0.00")
    total_preview = ft.Text("Total: $0.00")
    balance_preview = ft.Text("Saldo pendiente: $0.00", color=ft.Colors.AMBER_300)

    sales_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Cliente")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cant")),
            ft.DataColumn(ft.Text("Total")),
            ft.DataColumn(ft.Text("Estatus")),
        ],
        rows=[],
        heading_row_color=ft.Colors.BLUE_GREY_900,
        column_spacing=14,
    )

    def status_color(status: str) -> str:
        if status == "En proceso":
            return ft.Colors.ORANGE_400
        if status == "Listas":
            return ft.Colors.BLUE_400
        if status == "Entregado":
            return ft.Colors.GREEN_500
        return ft.Colors.WHITE

    def shipping_mode_changed(_: ft.ControlEvent) -> None:
        shipping_manual.disabled = shipping_mode.value != "Envio Cotizado"
        if shipping_manual.disabled:
            shipping_manual.value = "0"
        recalc_sale_totals(trigger_update=True)

    def sale_mode_changed(event: ft.ControlEvent | None = None) -> None:
        selected_mode = sale_price_mode.value
        if event and getattr(event, "control", None):
            selected_mode = event.control.value
            sale_price_mode.value = selected_mode

        sponsorship_total_input.disabled = selected_mode != "Patrocinio"
        if sponsorship_total_input.disabled:
            sponsorship_total_input.value = "0"
        recalc_sale_totals(trigger_update=True)

    def recalc_sale_totals(_: ft.ControlEvent | None = None, trigger_update: bool = False) -> None:
        product = product_map.get(sale_product_dropdown.value or "")
        qty = safe_int(sale_qty.value, 0)
        subtotal, unit_price, pricing_note = (
            calculate_sale_subtotal(
                product,
                qty,
                engraving_mode.value or "",
                sale_price_mode.value or "Normal",
                db.get("pricing", {}),
                sponsorship_total=safe_float(sponsorship_total_input.value, 0.0),
            )
            if product
            else (0.0, 0.0, "--")
        )
        engraving_cost = calculate_engraving_cost(subtotal, engraving_mode.value or "")
        shipping_cost = safe_float(shipping_manual.value, 0.0) if shipping_mode.value == "Envio Cotizado" else 0.0
        total = round(subtotal + engraving_cost + shipping_cost, 2)
        balance = calculate_balance(subtotal, engraving_cost, shipping_cost, safe_float(advance_input.value, 0.0))

        subtotal_preview.value = f"Subtotal: ${subtotal:.2f}"
        pricing_rule_preview.value = f"Regla: {pricing_note} | ref: ${unit_price:.2f}"
        engraving_preview.value = f"Grabado: ${engraving_cost:.2f}"
        shipping_preview.value = f"Envio: ${shipping_cost:.2f}"
        total_preview.value = f"Total: ${total:.2f}"
        balance_preview.value = f"Saldo pendiente: ${balance:.2f}"
        if trigger_update:
            page.update()

    def add_sale(_: ft.ControlEvent) -> None:
        client_name = (new_client_name.value or "").strip() or (client_dropdown.value or "").strip()
        product_id = sale_product_dropdown.value or ""
        qty = safe_int(sale_qty.value, 0)

        if not client_name:
            show_message("Selecciona o captura un cliente.", ft.Colors.RED_400)
            return
        if not product_id or qty <= 0:
            show_message("Producto y cantidad validos son obligatorios.", ft.Colors.RED_400)
            return

        product = product_map.get(product_id)
        if not product:
            show_message("Producto no encontrado.", ft.Colors.RED_400)
            return
        if qty > int(product.get("stock", 0)):
            show_message("Stock insuficiente para esta venta.", ft.Colors.RED_400)
            return
        if sale_price_mode.value == "Patrocinio" and safe_float(sponsorship_total_input.value, 0.0) <= 0:
            show_message("Captura un total valido para patrocinio.", ft.Colors.RED_400)
            return

        current_month = db["ventas"]["current_month"]
        month_sales = db["ventas"]["by_month"].setdefault(current_month, [])
        sale_date = datetime.now().strftime("%Y-%m-%d")
        sale_id = generate_sale_id(current_month, month_sales)
        subtotal, unit_price, pricing_note = calculate_sale_subtotal(
            product,
            qty,
            engraving_mode.value or "",
            sale_price_mode.value or "Normal",
            db.get("pricing", {}),
            sponsorship_total=safe_float(sponsorship_total_input.value, 0.0),
        )
        engraving_cost = calculate_engraving_cost(subtotal, engraving_mode.value or "")
        shipping_cost = safe_float(shipping_manual.value, 0.0) if shipping_mode.value == "Envio Cotizado" else 0.0
        advance = safe_float(advance_input.value, 0.0)
        total = round(subtotal + engraving_cost + shipping_cost, 2)
        balance = calculate_balance(subtotal, engraving_cost, shipping_cost, advance)

        sale_record = {
            "id": sale_id,
            "date": sale_date,
            "month": current_month,
            "client_name": client_name,
            "product_id": product_id,
            "quantity": qty,
            "pricing_mode": sale_price_mode.value,
            "pricing_note": pricing_note,
            "engraving_mode": engraving_mode.value,
            "engraving_cost": engraving_cost,
            "shipping_mode": shipping_mode.value,
            "shipping_cost": shipping_cost,
            "advance": advance,
            "unit_sale_price": unit_price,
            "subtotal": subtotal,
            "total": total,
            "balance": balance,
            "status": sale_status.value,
            "notes": notes_input.value or "",
        }
        month_sales.append(sale_record)

        update_inventory_quantity(product, -qty)

        clients = db["clientes"].setdefault("items", [])
        client_row = next((c for c in clients if c.get("name", "").lower() == client_name.lower()), None)
        if not client_row:
            client_row = {"name": client_name, "total_spent": 0.0, "orders": []}
            clients.append(client_row)
        client_row["total_spent"] = round(float(client_row.get("total_spent", 0.0)) + total, 2)
        client_row.setdefault("orders", []).append(
            {
                "sale_id": sale_id,
                "date": sale_date,
                "product_id": product_id,
                "quantity": qty,
                "total": total,
            }
        )

        store.save_ventas(db["ventas"])
        store.save_stock(db["stock"])
        store.save_clientes(db["clientes"])

        new_client_name.value = ""
        notes_input.value = ""
        advance_input.value = "0"
        sale_qty.value = "1"
        sale_price_mode.value = "Normal"
        sponsorship_total_input.value = "0"
        sponsorship_total_input.disabled = True

        refresh_views(dashboard=True, sales=True, stock=True, clients=True)
        show_message(f"Venta registrada: {sale_id}", ft.Colors.GREEN_500)

    def refresh_sales_views() -> None:
        clients = get_client_names()
        client_dropdown.options = [ft.dropdown.Option(name) for name in clients]
        sale_product_dropdown.options = [
            ft.dropdown.Option(
                key=item["id"],
                text=(
                    f"{item['name']} | stock: {item.get('stock', 0)} | "
                    f"pendiente: {get_pending_purchase_qty(item['id'])} | "
                    f"{get_pick_price_brief(item)}"
                ),
            )
            for item in stock_items
        ]
        if not sale_product_dropdown.value and stock_items:
            sale_product_dropdown.value = stock_items[0]["id"]

        current_month = db["ventas"]["current_month"]
        month_sales = db["ventas"]["by_month"].get(current_month, [])
        preview_id = generate_sale_id(current_month, month_sales)
        sale_id_preview.value = f"ID: {preview_id}"
        sale_date_preview.value = f"Fecha: {datetime.now().strftime('%Y-%m-%d')}"

        rows = []
        for sale in month_sales:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(sale.get("id", ""))),
                        ft.DataCell(ft.Text(sale.get("date", ""))),
                        ft.DataCell(ft.Text(sale.get("client_name", ""))),
                        ft.DataCell(ft.Text(product_map.get(sale.get("product_id", ""), {}).get("name", sale.get("product_id", "")))),
                        ft.DataCell(ft.Text(str(sale.get("quantity", 0)))),
                        ft.DataCell(ft.Text(f"${sale.get('total', 0):.2f}")),
                        ft.DataCell(ft.Text(sale.get("status", ""), color=status_color(sale.get("status", "")))),
                    ]
                )
            )
        sales_table.rows = rows
        recalc_sale_totals()

    shipping_mode.on_change = shipping_mode_changed
    sale_product_dropdown.on_change = lambda e: recalc_sale_totals(e, trigger_update=True)
    sale_price_mode.on_change = lambda e: sale_mode_changed(e)
    engraving_mode.on_change = lambda e: recalc_sale_totals(e, trigger_update=True)
    sponsorship_total_input.on_change = lambda e: recalc_sale_totals(e, trigger_update=True)
    sale_qty.on_change = lambda e: recalc_sale_totals(e, trigger_update=True)
    shipping_manual.on_change = lambda e: recalc_sale_totals(e, trigger_update=True)
    advance_input.on_change = lambda e: recalc_sale_totals(e, trigger_update=True)

    ventas_tab = ft.Column(
        controls=[
            ft.Row([sale_id_preview, sale_date_preview], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([client_dropdown, new_client_name]),
            ft.Row([sale_product_dropdown, sale_qty, sale_price_mode, sponsorship_total_input, engraving_mode]),
            ft.Row([shipping_mode, shipping_manual, advance_input, sale_status]),
            notes_input,
            ft.Row([subtotal_preview, pricing_rule_preview, engraving_preview, shipping_preview, total_preview, balance_preview]),
            ft.Row([ft.Button("Registrar venta", icon=ft.Icons.POINT_OF_SALE, on_click=add_sale)]),
            ft.Divider(),
            ft.Text("Ventas del mes", weight=ft.FontWeight.BOLD),
            ft.Row([ft.Container(expand=True, content=ft.Column([sales_table], scroll=ft.ScrollMode.ALWAYS))], expand=True),
        ],
        expand=True,
    )

    # Stock tab
    stock_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Existente")),
            ft.DataColumn(ft.Text("Pendiente (en camino)")),
            ft.DataColumn(ft.Text("Minimo")),
            ft.DataColumn(ft.Text("Guardar")),
        ],
        rows=[],
        heading_row_color=ft.Colors.BLUE_GREY_900,
        column_spacing=16,
    )

    def save_stock_row(
        item_id: str,
        stock_value: str,
        min_value: str,
    ) -> None:
        row = product_map.get(item_id)
        if not row:
            return
        row["stock"] = max(0, safe_int(stock_value, 0))
        row["min_stock"] = max(0, safe_int(min_value, 0))
        store.save_stock(db["stock"])
        refresh_views(stock=True, sales=True, purchases=True, waste=True)
        show_message(f"Stock actualizado: {row['name']}", ft.Colors.GREEN_500)

    def refresh_stock_table() -> None:
        rows = []
        for item in stock_items:
            stock_input = ft.TextField(value=str(item.get("stock", 0)), width=90)
            min_input = ft.TextField(value=str(item.get("min_stock", 0)), width=90)
            warning = int(item.get("stock", 0)) < int(item.get("min_stock", 0))
            rows.append(
                ft.DataRow(
                    color=ft.Colors.with_opacity(0.22, ft.Colors.RED_400) if warning else None,
                    cells=[
                        ft.DataCell(ft.Text(item["name"])),
                        ft.DataCell(stock_input),
                        ft.DataCell(
                            ft.Text(
                                str(get_pending_purchase_qty(item["id"])),
                                color=ft.Colors.ORANGE_300,
                            )
                        ),
                        ft.DataCell(min_input),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.SAVE,
                                tooltip="Guardar",
                                on_click=lambda e, pid=item["id"], a=stock_input, b=min_input: save_stock_row(
                                    pid, a.value, b.value
                                ),
                            )
                        ),
                    ],
                )
            )
        stock_table.rows = rows

    new_product_name = ft.TextField(label="Nuevo producto", width=280)
    new_product_category = ft.Dropdown(
        label="Categoria",
        width=160,
        value="Plumillas",
        options=[ft.dropdown.Option("Plumillas"), ft.dropdown.Option("Alternos")],
    )
    new_product_stock = ft.TextField(label="Stock inicial", value="0", width=110)
    new_product_min = ft.TextField(label="Stock minimo", value="5", width=110)
    new_product_cost = ft.TextField(label="Costo unitario", value="0", width=130)
    new_product_price_one_side = ft.TextField(label="Precio 1 lado", value="0", width=130)
    new_product_price_two_sides = ft.TextField(label="Precio 2 lados", value="0", width=130)

    def handle_new_product_category(_: ft.ControlEvent | None = None, trigger_update: bool = True) -> None:
        is_pick = new_product_category.value == "Plumillas"
        new_product_price_two_sides.disabled = not is_pick
        if not is_pick:
            new_product_price_two_sides.value = new_product_price_one_side.value
        if trigger_update:
            page.update()

    def add_new_product(_: ft.ControlEvent) -> None:
        name = (new_product_name.value or "").strip()
        category = (new_product_category.value or "Plumillas").strip()
        if not name:
            show_message("Escribe el nombre del producto.", ft.Colors.RED_400)
            return

        existing_ids = set(product_map.keys())
        product_id = generate_product_id(name, category, existing_ids)
        one_side_price = max(0.0, safe_float(new_product_price_one_side.value, 0.0))
        two_sides_price = max(0.0, safe_float(new_product_price_two_sides.value, one_side_price))
        if category != "Plumillas":
            two_sides_price = one_side_price

        new_item = {
            "id": product_id,
            "name": name,
            "category": category,
            "stock": max(0, safe_int(new_product_stock.value, 0)),
            "min_stock": max(0, safe_int(new_product_min.value, 0)),
            "unit_cost": max(0.0, safe_float(new_product_cost.value, 0.0)),
            "sale_price": one_side_price,
            "sale_price_one_side": one_side_price,
            "sale_price_two_sides": two_sides_price,
            "pricing_group": infer_pick_pricing_group(name) if category == "Plumillas" else "",
            "sponsorship_price": one_side_price,
        }
        stock_items.append(new_item)
        product_map[product_id] = new_item
        store.save_stock(db["stock"])

        new_product_name.value = ""
        new_product_stock.value = "0"
        new_product_min.value = "5"
        new_product_cost.value = "0"
        new_product_price_one_side.value = "0"
        new_product_price_two_sides.value = "0"
        handle_new_product_category(trigger_update=False)
        refresh_views(stock=True, sales=True, purchases=True, waste=True)
        show_message(f"Producto agregado al stock: {name}", ft.Colors.GREEN_500)

    new_product_category.on_change = lambda e: handle_new_product_category(e, trigger_update=True)
    new_product_price_one_side.on_change = lambda e: handle_new_product_category(e, trigger_update=True)

    def open_pick_pricing_dialog(_: ft.ControlEvent) -> None:
        groups = db.setdefault("pricing", deepcopy(DEFAULT_PICK_PRICING)).setdefault("groups", {})
        group_keys = ["JAZZ", "TRI_TEAR", "STANDARD"]
        controls: list[ft.Control] = []
        fields: dict[str, dict[str, ft.TextField]] = {}

        for group_key in group_keys:
            group_data = groups.get(group_key, deepcopy(DEFAULT_PICK_PRICING["groups"][group_key]))
            tiers = sorted(group_data.get("tiers", []), key=lambda t: safe_int(str(t.get("qty", 0)), 0))
            while len(tiers) < 3:
                tiers.append({"qty": 10 * (len(tiers) + 1), "one_side": 0.0, "two_sides": 0.0})
            bulk = group_data.get("bulk", {})

            field_bucket = {
                "t1_one": ft.TextField(label="P10 1 lado", value=f"{float(tiers[0].get('one_side', 0.0)):.2f}", width=120),
                "t1_two": ft.TextField(label="P10 2 lados", value=f"{float(tiers[0].get('two_sides', 0.0)):.2f}", width=120),
                "t2_one": ft.TextField(label="P20 1 lado", value=f"{float(tiers[1].get('one_side', 0.0)):.2f}", width=120),
                "t2_two": ft.TextField(label="P20 2 lados", value=f"{float(tiers[1].get('two_sides', 0.0)):.2f}", width=120),
                "t3_one": ft.TextField(label="P30 1 lado", value=f"{float(tiers[2].get('one_side', 0.0)):.2f}", width=120),
                "t3_two": ft.TextField(label="P30 2 lados", value=f"{float(tiers[2].get('two_sides', 0.0)):.2f}", width=120),
                "bulk_min": ft.TextField(label="Mayoreo desde", value=str(int(bulk.get("min_qty", 40))), width=120),
                "bulk_one": ft.TextField(label="Mayoreo 1 lado", value=f"{float(bulk.get('one_side_unit', 0.0)):.2f}", width=120),
                "bulk_two": ft.TextField(label="Mayoreo 2 lados", value=f"{float(bulk.get('two_sides_unit', 0.0)):.2f}", width=120),
            }
            fields[group_key] = field_bucket
            controls.extend(
                [
                    ft.Text(group_data.get("name", group_key), weight=ft.FontWeight.BOLD, size=15),
                    ft.Row([field_bucket["t1_one"], field_bucket["t1_two"], field_bucket["t2_one"], field_bucket["t2_two"]], wrap=True),
                    ft.Row([field_bucket["t3_one"], field_bucket["t3_two"], field_bucket["bulk_min"], field_bucket["bulk_one"], field_bucket["bulk_two"]], wrap=True),
                    ft.Divider(),
                ]
            )

        def close_dialog() -> None:
            dialog.open = False
            page.update()

        def save_pricing_changes(_: ft.ControlEvent) -> None:
            for group_key in group_keys:
                f = fields[group_key]
                groups[group_key] = {
                    "name": groups.get(group_key, {}).get("name", DEFAULT_PICK_PRICING["groups"][group_key]["name"]),
                    "tiers": [
                        {"qty": 10, "one_side": max(0.0, safe_float(f["t1_one"].value, 0.0)), "two_sides": max(0.0, safe_float(f["t1_two"].value, 0.0))},
                        {"qty": 20, "one_side": max(0.0, safe_float(f["t2_one"].value, 0.0)), "two_sides": max(0.0, safe_float(f["t2_two"].value, 0.0))},
                        {"qty": 30, "one_side": max(0.0, safe_float(f["t3_one"].value, 0.0)), "two_sides": max(0.0, safe_float(f["t3_two"].value, 0.0))},
                    ],
                    "bulk": {
                        "min_qty": max(1, safe_int(f["bulk_min"].value, 40)),
                        "one_side_unit": max(0.0, safe_float(f["bulk_one"].value, 0.0)),
                        "two_sides_unit": max(0.0, safe_float(f["bulk_two"].value, 0.0)),
                    },
                }

            store.save_pricing(db["pricing"])
            refresh_views(sales=True, stock=True)
            close_dialog()
            show_message("Costos de plumillas actualizados.", ft.Colors.GREEN_500)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Configurar costos de plumillas"),
            content=ft.Container(
                width=980,
                height=560,
                content=ft.Column(controls=controls, scroll=ft.ScrollMode.ALWAYS),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: close_dialog()),
                ft.Button("Guardar costos", icon=ft.Icons.SAVE, on_click=save_pricing_changes),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    stock_tab = ft.Column(
        controls=[
            ft.Text("Stock general (edicion rapida)", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Las filas en rojo estan por debajo del minimo."),
            ft.Button("Configurar costos de modelos de plumilla", icon=ft.Icons.TUNE, on_click=open_pick_pricing_dialog),
            ft.Divider(),
            ft.Text("Agregar nuevo producto", weight=ft.FontWeight.BOLD),
            ft.Row(
                [
                    new_product_name,
                    new_product_category,
                    new_product_stock,
                    new_product_min,
                    new_product_cost,
                    new_product_price_one_side,
                    new_product_price_two_sides,
                    ft.Button("Agregar", icon=ft.Icons.ADD_BOX, on_click=add_new_product),
                ],
                wrap=True,
            ),
            ft.Divider(),
            ft.Row([ft.Container(expand=True, content=ft.Column([stock_table], scroll=ft.ScrollMode.ALWAYS))], expand=True),
        ],
        expand=True,
    )

    # Compras tab
    purchase_product = ft.Dropdown(label="Producto", width=360, options=[])
    purchase_qty = ft.TextField(label="Cantidad", width=140)
    purchase_total = ft.TextField(label="Costo Total (con aranceles)", width=220)
    purchase_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cantidad")),
            ft.DataColumn(ft.Text("Costo Total")),
            ft.DataColumn(ft.Text("Costo Unitario")),
            ft.DataColumn(ft.Text("Estado")),
            ft.DataColumn(ft.Text("Accion")),
        ],
        rows=[],
        heading_row_color=ft.Colors.BLUE_GREY_900,
    )

    def add_purchase(_: ft.ControlEvent) -> None:
        pid = purchase_product.value or ""
        qty = safe_int(purchase_qty.value, 0)
        total_cost = safe_float(purchase_total.value, 0.0)
        if not pid or qty <= 0 or total_cost <= 0:
            show_message("Completa producto, cantidad y costo total.", ft.Colors.RED_400)
            return

        item = product_map.get(pid)
        if not item:
            show_message("Producto no valido.", ft.Colors.RED_400)
            return

        unit_cost = round(total_cost / qty, 2)

        record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "month": db["ventas"]["current_month"],
            "product_id": pid,
            "quantity": qty,
            "total_cost": round(total_cost, 2),
            "unit_cost": unit_cost,
            "received": False,
            "received_date": "",
        }
        db["compras"].setdefault("items", []).append(record)
        store.save_compras(db["compras"])

        purchase_qty.value = ""
        purchase_total.value = ""
        refresh_views(dashboard=True, purchases=True, stock=True, sales=True)
        show_message("Compra registrada. Usa 'Recibir' cuando llegue producto.", ft.Colors.GREEN_500)

    def receive_purchase(item_index: int) -> None:
        purchase_items = db["compras"].setdefault("items", [])
        if item_index < 0 or item_index >= len(purchase_items):
            return
        rec = purchase_items[item_index]

        item = product_map.get(rec.get("product_id", ""))
        if not item:
            show_message("Producto no encontrado para esta compra.", ft.Colors.RED_400)
            return

        qty = safe_int(str(rec.get("quantity", 0)), 0)
        unit_cost = safe_float(str(rec.get("unit_cost", 0.0)), 0.0)
        if qty <= 0:
            show_message("Cantidad invalida en la compra.", ft.Colors.RED_400)
            return

        if rec.get("received", False):
            if qty > int(item.get("stock", 0)):
                show_message("No se puede revertir: stock actual insuficiente.", ft.Colors.RED_400)
                return
            update_inventory_quantity(item, -qty)
            rec["received"] = False
            rec["received_date"] = ""
            message = "Recepcion revertida. Se descontó del stock."
            color = ft.Colors.ORANGE_400
        else:
            update_inventory_quantity(item, qty)
            item["unit_cost"] = unit_cost
            rec["received"] = True
            rec["received_date"] = datetime.now().strftime("%Y-%m-%d")
            message = "Compra recibida y stock actualizado."
            color = ft.Colors.GREEN_500

        store.save_compras(db["compras"])
        store.save_stock(db["stock"])
        refresh_views(purchases=True, stock=True, sales=True)
        show_message(message, color)

    def refresh_purchase_table() -> None:
        purchase_product.options = [ft.dropdown.Option(key=x["id"], text=x["name"]) for x in stock_items]
        if not purchase_product.value and stock_items:
            purchase_product.value = stock_items[0]["id"]

        rows = []
        all_items = db["compras"].get("items", [])
        for idx, rec in reversed(list(enumerate(all_items))):
            received = rec.get("received", True)
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(rec.get("date", ""))),
                        ft.DataCell(ft.Text(product_map.get(rec.get("product_id", ""), {}).get("name", rec.get("product_id", "")))),
                        ft.DataCell(ft.Text(str(rec.get("quantity", 0)))),
                        ft.DataCell(ft.Text(f"${rec.get('total_cost', 0):.2f}")),
                        ft.DataCell(ft.Text(f"${rec.get('unit_cost', 0):.2f}")),
                        ft.DataCell(
                            ft.Text(
                                "Recibido" if received else "Pendiente",
                                color=ft.Colors.GREEN_400 if received else ft.Colors.ORANGE_400,
                            )
                        ),
                        ft.DataCell(
                            ft.Button(
                                "Recibir" if not received else "Quitar",
                                icon=ft.Icons.INVENTORY_2,
                                on_click=lambda e, item_idx=idx: receive_purchase(item_idx),
                            )
                        ),
                    ]
                )
            )
        purchase_table.rows = rows

    compras_tab = ft.Column(
        controls=[
            ft.Row([purchase_product, purchase_qty, purchase_total, ft.Button("Registrar compra", on_click=add_purchase)]),
            ft.Divider(),
            ft.Row([ft.Container(expand=True, content=ft.Column([purchase_table], scroll=ft.ScrollMode.ALWAYS))], expand=True),
        ],
        expand=True,
    )

    # Mermas tab
    waste_product = ft.Dropdown(label="Producto", width=360, options=[])
    waste_qty = ft.TextField(label="Cantidad perdida", width=160)
    waste_reason = ft.TextField(label="Motivo", width=360)
    waste_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cantidad")),
            ft.DataColumn(ft.Text("Motivo")),
            ft.DataColumn(ft.Text("Costo perdida")),
        ],
        rows=[],
        heading_row_color=ft.Colors.BLUE_GREY_900,
    )

    def add_waste(_: ft.ControlEvent) -> None:
        pid = waste_product.value or ""
        qty = safe_int(waste_qty.value, 0)
        reason = (waste_reason.value or "").strip()
        if not pid or qty <= 0 or not reason:
            show_message("Completa producto, cantidad y motivo.", ft.Colors.RED_400)
            return

        item = product_map.get(pid)
        if not item:
            show_message("Producto no valido.", ft.Colors.RED_400)
            return
        if qty > int(item.get("stock", 0)):
            show_message("No puedes registrar merma mayor al stock.", ft.Colors.RED_400)
            return

        update_inventory_quantity(item, -qty)
        loss_cost = round(float(item.get("unit_cost", 0.0)) * qty, 2)
        record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "month": db["ventas"]["current_month"],
            "product_id": pid,
            "quantity": qty,
            "reason": reason,
            "loss_cost": loss_cost,
        }
        db["mermas"].setdefault("items", []).append(record)

        store.save_mermas(db["mermas"])
        store.save_stock(db["stock"])

        waste_qty.value = ""
        waste_reason.value = ""
        refresh_views(dashboard=True, waste=True, stock=True, sales=True)
        show_message("Merma registrada.", ft.Colors.ORANGE_400)

    def refresh_waste_table() -> None:
        waste_product.options = [ft.dropdown.Option(key=x["id"], text=x["name"]) for x in stock_items]
        if not waste_product.value and stock_items:
            waste_product.value = stock_items[0]["id"]

        rows = []
        for rec in reversed(db["mermas"].get("items", [])):
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(rec.get("date", ""))),
                        ft.DataCell(ft.Text(product_map.get(rec.get("product_id", ""), {}).get("name", rec.get("product_id", "")))),
                        ft.DataCell(ft.Text(str(rec.get("quantity", 0)))),
                        ft.DataCell(ft.Text(rec.get("reason", ""))),
                        ft.DataCell(ft.Text(f"${rec.get('loss_cost', 0):.2f}")),
                    ]
                )
            )
        waste_table.rows = rows

    mermas_tab = ft.Column(
        controls=[
            ft.Row([waste_product, waste_qty, waste_reason, ft.Button("Registrar merma", on_click=add_waste)]),
            ft.Divider(),
            ft.Row([ft.Container(expand=True, content=ft.Column([waste_table], scroll=ft.ScrollMode.ALWAYS))], expand=True),
        ],
        expand=True,
    )

    # Clientes tab
    clients_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Cliente")),
            ft.DataColumn(ft.Text("Total gastado")),
            ft.DataColumn(ft.Text("Compras")),
            ft.DataColumn(ft.Text("Ultima compra")),
        ],
        rows=[],
        heading_row_color=ft.Colors.BLUE_GREY_900,
    )
    client_history_dropdown = ft.Dropdown(label="Detalle por cliente", width=360, options=[])
    client_history_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Venta")),
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cant")),
            ft.DataColumn(ft.Text("Total")),
        ],
        rows=[],
        heading_row_color=ft.Colors.BLUE_GREY_900,
    )

    def refresh_clients_views() -> None:
        rows = []
        names = []
        for client in sorted(db["clientes"].get("items", []), key=lambda x: x.get("name", "").lower()):
            orders = client.get("orders", [])
            names.append(client.get("name", ""))
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(client.get("name", ""))),
                        ft.DataCell(ft.Text(f"${float(client.get('total_spent', 0.0)):.2f}")),
                        ft.DataCell(ft.Text(str(len(orders)))),
                        ft.DataCell(ft.Text(orders[-1]["date"] if orders else "--")),
                    ]
                )
            )
        clients_table.rows = rows
        client_history_dropdown.options = [ft.dropdown.Option(x) for x in names]
        if names and client_history_dropdown.value not in names:
            client_history_dropdown.value = names[0]
        elif not names:
            client_history_dropdown.value = None
        render_client_history(trigger_update=False)

    def render_client_history(_: ft.ControlEvent | None = None, trigger_update: bool = True) -> None:
        selected = client_history_dropdown.value
        client = next((c for c in db["clientes"].get("items", []) if c.get("name") == selected), None)
        rows = []
        if client:
            for order in reversed(client.get("orders", [])):
                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(order.get("sale_id", ""))),
                            ft.DataCell(ft.Text(order.get("date", ""))),
                            ft.DataCell(ft.Text(product_map.get(order.get("product_id", ""), {}).get("name", order.get("product_id", "")))),
                            ft.DataCell(ft.Text(str(order.get("quantity", 0)))),
                            ft.DataCell(ft.Text(f"${order.get('total', 0):.2f}")),
                        ]
                    )
                )
        client_history_table.rows = rows
        if trigger_update:
            page.update()

    client_history_dropdown.on_change = lambda e: render_client_history(e, trigger_update=True)

    clientes_tab = ft.Column(
        controls=[
            ft.Text("Base de clientes", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([ft.Container(expand=True, content=ft.Column([clients_table], scroll=ft.ScrollMode.ALWAYS))], expand=True),
            ft.Divider(),
            client_history_dropdown,
            ft.Row([ft.Container(expand=True, content=ft.Column([client_history_table], scroll=ft.ScrollMode.ALWAYS))], expand=True),
        ],
        expand=True,
    )

    tabs = ft.Tabs(
        length=6,
        content=ft.Column(
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Dashboard"),
                        ft.Tab(label="Ventas"),
                        ft.Tab(label="Stock"),
                        ft.Tab(label="Compras"),
                        ft.Tab(label="Mermas"),
                        ft.Tab(label="Clientes"),
                    ],
                    indicator_color=ft.Colors.CYAN_300,
                    label_color=ft.Colors.CYAN_200,
                    unselected_label_color=ft.Colors.BLUE_GREY_200,
                ),
                ft.Container(
                    expand=True,
                    content=ft.TabBarView(
                        controls=[
                            dashboard_tab,
                            ventas_tab,
                            stock_tab,
                            compras_tab,
                            mermas_tab,
                            clientes_tab,
                        ],
                        expand=True,
                    ),
                ),
            ],
            expand=True,
        ),
        expand=1,
    )

    def refresh_views(
        dashboard: bool = False,
        sales: bool = False,
        stock: bool = False,
        purchases: bool = False,
        waste: bool = False,
        clients: bool = False,
        do_update: bool = True,
    ) -> None:
        if dashboard:
            refresh_dashboard()
        if sales:
            refresh_sales_views()
        if stock:
            refresh_stock_table()
        if purchases:
            refresh_purchase_table()
        if waste:
            refresh_waste_table()
        if clients:
            refresh_clients_views()
        if do_update:
            page.update()

    def refresh_all_views() -> None:
        refresh_views(
            dashboard=True,
            sales=True,
            stock=True,
            purchases=True,
            waste=True,
            clients=True,
            do_update=True,
        )

    page.add(tabs)
    refresh_all_views()


if __name__ == "__main__":
    ft.run(main)
