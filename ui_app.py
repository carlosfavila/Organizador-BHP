from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import flet as ft

from models import DEFAULT_PICK_PRICING
from services import (
    InventoryService,
    calculate_balance,
    calculate_engraving_cost,
    calculate_sale_subtotal,
    generate_sale_id,
    get_month_sales_by_model,
    safe_float,
    safe_int,
    summarize_month,
)
from store import JsonStore
from ui_theme import app_theme, card_container, colors, kpi_card, nav_button, status_chip

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


def _signature(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def export_month_pdf(month: str, sales: list[dict[str, Any]], summary: dict[str, Any], product_map: dict[str, dict[str, Any]]) -> Path:
    report_name = f"reporte_{month.replace('-', '_')}.pdf"
    report_path = Path.cwd() / report_name
    c = canvas.Canvas(str(report_path), pagesize=letter)
    c.setTitle(f"Reporte Mensual Black Hole Picks - {month}")
    _, height = letter
    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Black Hole Picks - Reporte Mensual {month}")
    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Ingresos Totales: ${summary['ingresos']:.2f}")
    y -= 18
    c.drawString(40, y, f"Costos de Inversion: ${summary['inversion']:.2f}")
    y -= 18
    c.drawString(40, y, f"Costos de Mermas: ${summary['mermas']:.2f}")
    y -= 18
    c.drawString(40, y, f"Ganancia Neta: ${summary['ganancia_neta']:.2f}")
    y -= 30
    headers = ["ID", "Fecha", "Cliente", "Producto", "Cant", "Total", "Status"]
    x_positions = [40, 105, 175, 250, 390, 425, 485]
    c.setFont("Helvetica", 9)
    for idx, text in enumerate(headers):
        c.drawString(x_positions[idx], y, text)
    y -= 14
    for sale in sales:
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)
        product_name = product_map.get(sale.get("product_id", ""), {}).get("name", sale.get("product_id", ""))
        row = [sale.get("id", ""), sale.get("date", ""), sale.get("client_name", ""), product_name[:24], str(sale.get("quantity", "")), f"${sale.get('total', 0):.2f}", sale.get("status", "")]
        for idx, text in enumerate(row):
            c.drawString(x_positions[idx], y, str(text))
        y -= 13
    c.save()
    return report_path


def run_app(page: ft.Page) -> None:
    page.title = "Black Hole Picks - Inventario y Ventas"
    page.theme = app_theme()
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = colors["background"]
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 0
    page.window.width = 1450
    page.window.height = 900

    store = JsonStore(Path.cwd() / "assets")
    db = store.load_all()
    service = InventoryService(db)

    dirty_tabs: set[str] = set()
    active_tab = "dashboard"
    table_signatures: dict[str, str] = {}
    tab_initialized: set[str] = set()

    def save_sections(sections: set[str]) -> None:
        if sections:
            store.save_sections(db, sections)

    def show_message(text: str, color: str = ft.Colors.BLUE_300) -> None:
        page.snack_bar = ft.SnackBar(content=ft.Text(text), bgcolor=color, duration=3200)
        page.snack_bar.open = True
        page.update()

    # Dashboard
    current_month_label = ft.Text("", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300)
    ingresos_text = ft.Text("$0.00")
    inversion_text = ft.Text("$0.00")
    mermas_text = ft.Text("$0.00")
    ganancia_text = ft.Text("$0.00", size=20, weight=ft.FontWeight.BOLD)
    most_sold_text = ft.Text("Sin ventas", color=ft.Colors.AMBER_200)
    model_sales_chart = ft.Column(expand=True, spacing=6)
    month_sales_table = ft.DataTable(columns=[ft.DataColumn(ft.Text(x)) for x in ["ID", "Fecha", "Cliente", "Producto", "Cant", "Total", "Status"]], rows=[], column_spacing=18, heading_row_color=ft.Colors.BLUE_GREY_900)
    
    # Dropdown para seleccionar mes
    month_dropdown = ft.Dropdown(label="Mes", width=150, options=[], on_select=None)

    def render_month_model_sales_graph(month: str) -> None:
        sales_by_model = get_month_sales_by_model(month, db["ventas"])
        if not sales_by_model:
            model_sales_chart.controls = [ft.Text("Sin ventas para este mes.", color=ft.Colors.BLUE_GREY_200)]
            return
        max_qty = max(qty for _, qty in sales_by_model) or 1
        rows: list[ft.Control] = []
        for product_id, qty in sales_by_model[:6]:
            name = service.product_map.get(product_id, {}).get("name", product_id)
            bar_width = 80 + int((qty / max_qty) * 260)
            rows.append(
                ft.Row(
                    controls=[
                        ft.Container(width=220, content=ft.Text(name, size=12, weight=ft.FontWeight.BOLD)),
                        ft.Container(width=bar_width, height=24, bgcolor=ft.Colors.CYAN_400, border_radius=12),
                        ft.Container(width=60, content=ft.Text(str(qty), size=12, text_align=ft.TextAlign.RIGHT)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        model_sales_chart.controls = rows

    def refresh_dashboard() -> None:
        month = db["ventas"]["current_month"]
        summary = summarize_month(month, db["ventas"], db["compras"], db["mermas"])
        current_month_label.value = f"Mes activo: {month}"
        ingresos_text.value = f"${summary['ingresos']:.2f}"
        inversion_text.value = f"${summary['inversion']:.2f}"
        mermas_text.value = f"${summary['mermas']:.2f}"
        ganancia_text.value = f"${summary['ganancia_neta']:.2f}"
        most_sold_text.value = service.product_map.get(summary["most_sold_id"], {}).get("name", summary["most_sold_id"])
        render_month_model_sales_graph(month)
        sales = db["ventas"].get("by_month", {}).get(month, [])
        sig = _signature([s.get("id") for s in sales] + [s.get("status") for s in sales])
        if table_signatures.get("dashboard_sales") == sig:
            return
        table_signatures["dashboard_sales"] = sig
        month_sales_table.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(s.get("id", ""))),
                    ft.DataCell(ft.Text(s.get("date", ""))),
                    ft.DataCell(ft.Text(s.get("client_name", ""))),
                    ft.DataCell(ft.Text(service.product_map.get(s.get("product_id", ""), {}).get("name", s.get("product_id", "")))),
                    ft.DataCell(ft.Text(str(s.get("quantity", 0)))),
                    ft.DataCell(ft.Text(f"${s.get('total', 0):.2f}")),
                    ft.DataCell(ft.Text(s.get("status", ""))),
                ]
            )
            for s in sales
        ]

    # Ventas
    sale_id_preview = ft.Text("ID: --")
    sale_date_preview = ft.Text("Fecha: --")
    client_dropdown = ft.Dropdown(label="Cliente existente", width=240, options=[])
    new_client_name = ft.TextField(label="o crear cliente nuevo", width=240)
    sale_product_dropdown = ft.Dropdown(label="Producto", width=360, options=[])
    sale_qty = ft.TextField(label="Cantidad", value="1", width=90)
    sale_price_mode = ft.Dropdown(label="Modalidad", width=150, value="Normal", options=[ft.dropdown.Option("Normal"), ft.dropdown.Option("Patrocinio"), ft.dropdown.Option("Multi-modelo")])
    sponsorship_total_input = ft.TextField(label="Total patrocinio", value="0", width=150, disabled=True)
    engraving_mode = ft.Dropdown(label="Grabado", width=140, value="1 Lado", options=[ft.dropdown.Option("1 Lado"), ft.dropdown.Option("2 Lados"), ft.dropdown.Option("Sin grabado")])
    shipping_mode = ft.Dropdown(label="Envio", width=180, value="Entrega incluida", options=[ft.dropdown.Option("Entrega incluida"), ft.dropdown.Option("Envio Cotizado")])
    shipping_manual = ft.TextField(label="Envio manual", value="0", width=120, disabled=True)
    advance_input = ft.TextField(label="Anticipo", value="0", width=120)
    sale_status = ft.Dropdown(label="Estatus", width=140, value="En proceso", options=[ft.dropdown.Option("En proceso"), ft.dropdown.Option("Listas"), ft.dropdown.Option("Entregado")])
    notes_input = ft.TextField(label="Notas", multiline=True, min_lines=2, max_lines=3, expand=True)

    subtotal_preview = ft.Text("Subtotal: $0.00")
    pricing_rule_preview = ft.Text("Regla: --", color=ft.Colors.CYAN_200)
    engraving_preview = ft.Text("Grabado: $0.00")
    shipping_preview = ft.Text("Envio: $0.00")
    total_preview = ft.Text("Total: $0.00")
    balance_preview = ft.Text("Saldo pendiente: $0.00", color=ft.Colors.AMBER_300)

    sales_table = ft.DataTable(columns=[ft.DataColumn(ft.Text(x)) for x in ["ID", "Fecha", "Cliente", "Producto", "Cant", "Total", "Anticipo", "Pago", "Estatus", "Eliminar"]], rows=[], heading_row_color=colors["border"], column_spacing=12)
    sale_status_options = ["En proceso", "Listas", "Entregado"]

    def status_color(status: str) -> str:
        return {"En proceso": ft.Colors.ORANGE_400, "Listas": ft.Colors.BLUE_400, "Entregado": ft.Colors.GREEN_500}.get(status, ft.Colors.WHITE)

    def update_sale_status(sale_id: str, new_status: str) -> None:
        month = db["ventas"]["current_month"]
        month_sales = db["ventas"].get("by_month", {}).get(month, [])
        target = next((s for s in month_sales if s.get("id") == sale_id), None)
        if not target:
            show_message("No se encontró la venta.", ft.Colors.RED_400)
            return
        if new_status not in sale_status_options:
            show_message("Estatus no válido.", ft.Colors.RED_400)
            return
        target["status"] = new_status
        save_sections({"ventas"})
        mark_dirty("ventas", "dashboard", update_now=True)
        show_message(f"Estatus actualizado a '{new_status}'.", ft.Colors.GREEN_500)

    def update_payment_status(sale_id: str, payment_status: str) -> None:
        """Actualiza el estado de pago de una venta (Anticipo o Pagado)"""
        month = db["ventas"]["current_month"]
        month_sales = db["ventas"].get("by_month", {}).get(month, [])
        target = next((s for s in month_sales if s.get("id") == sale_id), None)
        if not target:
            show_message("No se encontró la venta.", ft.Colors.RED_400)
            return
        
        old_status = target.get("payment_status", "Anticipo")
        target["payment_status"] = payment_status
        
        # Actualizar balance según el estado de pago
        if payment_status == "Anticipo":
            target["balance"] = target.get("total", 0) - target.get("advance", 0)
        else:  # Pagado
            target["balance"] = 0
        
        save_sections({"ventas"})
        mark_dirty("ventas", "dashboard", update_now=True)
        
        if old_status == "Anticipo" and payment_status == "Pagado":
            remaining = target.get("total", 0) - target.get("advance", 0)
            show_message(f"Venta completada. Se agregó ${remaining:.2f} a las ganancias del mes.", ft.Colors.GREEN_500)
        else:
            show_message(f"Pago marcado como '{payment_status}'.", ft.Colors.GREEN_500)

    def delete_sale(sale_id: str) -> None:
        month = db["ventas"]["current_month"]
        msg, sections = service.delete_sale(sale_id, month)
        if not sections:
            show_message(msg, ft.Colors.RED_400)
            return
        save_sections(sections)
        mark_dirty("ventas", "dashboard", "stock", "clientes", update_now=True)
        show_message(msg, ft.Colors.ORANGE_400)

    def recalc_sale_totals(update: bool = False) -> None:
        product = service.product_map.get(sale_product_dropdown.value or "")
        qty = safe_int(sale_qty.value, 0)
        subtotal, unit_price, pricing_note = (
            calculate_sale_subtotal(product, qty, engraving_mode.value or "", sale_price_mode.value or "Normal", db.get("pricing", {}), sponsorship_total=safe_float(sponsorship_total_input.value, 0.0))
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
        if update:
            page.update()

    def refresh_sales() -> None:
        client_dropdown.options = [ft.dropdown.Option(n) for n in service.get_client_names()]
        sale_product_dropdown.options = [ft.dropdown.Option(key=i["id"], text=f"{i['name']} | stock: {i.get('stock', 0)} | pendiente: {service.pending_purchase_qty(i['id'])}") for i in service.stock_items]
        if not sale_product_dropdown.value and service.stock_items:
            sale_product_dropdown.value = service.stock_items[0]["id"]
        month = db["ventas"]["current_month"]
        sales = db["ventas"]["by_month"].get(month, [])
        sale_id_preview.value = f"ID: {generate_sale_id(month, sales)}"
        sale_date_preview.value = f"Fecha: {datetime.now().strftime('%Y-%m-%d')}"
        sig = _signature([s.get("id") for s in sales] + [s.get("status") for s in sales])
        if table_signatures.get("sales_table") != sig:
            table_signatures["sales_table"] = sig
            sales_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(s.get("id", ""))),
                        ft.DataCell(ft.Text(s.get("date", ""))),
                        ft.DataCell(ft.Text(s.get("client_name", ""))),
                        ft.DataCell(ft.Text(service.product_map.get(s.get("product_id", ""), {}).get("name", s.get("product_id", "")))),
                        ft.DataCell(ft.Text(str(s.get("quantity", 0)))),
                        ft.DataCell(ft.Text(f"${s.get('total', 0):.2f}")),
                        ft.DataCell(ft.Text(f"${s.get('advance', 0):.2f}")),
                        ft.DataCell(
                            ft.Text(
                                "Pagado",
                                color=ft.Colors.GREEN_500,
                                weight=ft.FontWeight.BOLD,
                            ) if s.get("payment_status", "Anticipo") == "Pagado"
                            else ft.Dropdown(
                                width=120,
                                value=s.get("payment_status", "Anticipo"),
                                options=[ft.dropdown.Option(opt) for opt in ["Anticipo", "Pagado"]],
                                text_style=ft.TextStyle(color=ft.Colors.ORANGE_400),
                                disabled=s.get("auto_paid", False),
                                on_select=lambda e, sid=s.get("id", ""): update_payment_status(sid, e.control.value or "Anticipo"),
                            )
                        ),
                        ft.DataCell(
                            ft.Dropdown(
                                width=120,
                                value=s.get("status", "En proceso"),
                                options=[ft.dropdown.Option(opt) for opt in sale_status_options],
                                text_style=ft.TextStyle(color=status_color(s.get("status", "En proceso"))),
                                on_select=lambda e, sid=s.get("id", ""): update_sale_status(sid, e.control.value or "En proceso"),
                            )
                        ),
                        ft.DataCell(ft.IconButton(icon=ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_400, disabled=s.get("status", "") != "En proceso", on_click=lambda e, sid=s.get("id", ""): delete_sale(sid))),
                    ]
                )
                for s in sales
            ]
        recalc_sale_totals(update=False)

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
        product = service.product_map.get(product_id)
        if not product or qty > int(product.get("stock", 0)):
            show_message("Stock insuficiente para esta venta.", ft.Colors.RED_400)
            return
        sponsorship_total = safe_float(sponsorship_total_input.value, 0.0)
        if sale_price_mode.value in ("Patrocinio", "Multi-modelo") and sponsorship_total <= 0:
            if sale_price_mode.value == "Multi-modelo":
                show_message("Captura un total valido para la modalidad multi-modelo.", ft.Colors.RED_400)
            else:
                show_message("Captura un total valido para patrocinio.", ft.Colors.RED_400)
            return
        subtotal, unit_price, pricing_note = calculate_sale_subtotal(product, qty, engraving_mode.value or "", sale_price_mode.value or "Normal", db.get("pricing", {}), sponsorship_total=sponsorship_total)
        engraving_cost = calculate_engraving_cost(subtotal, engraving_mode.value or "")
        shipping_cost = safe_float(shipping_manual.value, 0.0) if shipping_mode.value == "Envio Cotizado" else 0.0
        advance = safe_float(advance_input.value, 0.0)
        total = round(subtotal + engraving_cost + shipping_cost, 2)
        balance = calculate_balance(subtotal, engraving_cost, shipping_cost, advance)
        
        # Si Total == Anticipo, automáticamente es "Pagado" y se bloquea
        is_auto_paid = (total == advance and advance > 0)
        payment_status = "Pagado" if is_auto_paid else "Anticipo"
        
        sale_id, sections = service.add_sale(
            {
                "client_name": client_name,
                "product_id": product_id,
                "qty": qty,
                "pricing_mode": sale_price_mode.value or "Normal",
                "pricing_note": pricing_note,
                "engraving_mode": engraving_mode.value or "1 Lado",
                "shipping_mode": shipping_mode.value or "Entrega incluida",
                "status": sale_status.value or "En proceso",
                "payment_status": payment_status,
                "auto_paid": is_auto_paid,
                "notes": notes_input.value or "",
                "subtotal": subtotal,
                "unit_price": unit_price,
                "engraving_cost": engraving_cost,
                "shipping_cost": shipping_cost,
                "advance": advance,
                "total": total,
                "balance": balance,
            }
        )
        save_sections(sections)
        new_client_name.value = ""
        notes_input.value = ""
        advance_input.value = "0"
        sale_qty.value = "1"
        sale_status.value = "En proceso"
        sale_price_mode.value = "Normal"
        sponsorship_total_input.value = "0"
        sponsorship_total_input.disabled = True
        mark_dirty("dashboard", "ventas", "stock", "clientes", update_now=True)
        show_message(f"Venta registrada: {sale_id}", ft.Colors.GREEN_500)

    # Stock
    stock_table = ft.DataTable(columns=[ft.DataColumn(ft.Text(x)) for x in ["Producto", "Existente", "Pendiente (en camino)", "Minimo", "Guardar"]], rows=[], heading_row_color=colors["border"], column_spacing=16)
    new_product_name = ft.TextField(label="Nuevo producto", width=280)
    new_product_category = ft.Dropdown(label="Categoria", width=160, value="Plumillas", options=[ft.dropdown.Option("Plumillas"), ft.dropdown.Option("Alternos")])
    new_product_stock = ft.TextField(label="Stock inicial", value="0", width=110)
    new_product_min = ft.TextField(label="Stock minimo", value="5", width=110)
    new_product_cost = ft.TextField(label="Costo unitario", value="0", width=130)
    new_product_price_one_side = ft.TextField(label="Precio 1 lado", value="0", width=130)
    new_product_price_two_sides = ft.TextField(label="Precio 2 lados", value="0", width=130)

    def handle_new_product_category() -> None:
        is_pick = new_product_category.value == "Plumillas"
        new_product_price_two_sides.disabled = not is_pick
        if not is_pick:
            new_product_price_two_sides.value = new_product_price_one_side.value

    def refresh_stock() -> None:
        sig = _signature([(x["id"], x.get("stock", 0), x.get("min_stock", 0), service.pending_purchase_qty(x["id"])) for x in service.stock_items])
        if table_signatures.get("stock_table") == sig:
            return
        table_signatures["stock_table"] = sig
        rows = []
        for item in service.stock_items:
            stock_input = ft.TextField(value=str(item.get("stock", 0)), width=90)
            min_input = ft.TextField(value=str(item.get("min_stock", 0)), width=90)
            warning = int(item.get("stock", 0)) < int(item.get("min_stock", 0))
            rows.append(
                ft.DataRow(
                    color=ft.Colors.with_opacity(0.22, ft.Colors.RED_400) if warning else None,
                    cells=[
                        ft.DataCell(ft.Text(item["name"])),
                        ft.DataCell(stock_input),
                        ft.DataCell(ft.Text(str(service.pending_purchase_qty(item["id"])), color=ft.Colors.ORANGE_300)),
                        ft.DataCell(min_input),
                        ft.DataCell(ft.IconButton(icon=ft.Icons.SAVE, on_click=lambda e, pid=item["id"], a=stock_input, b=min_input: save_stock_row(pid, a.value, b.value))),
                    ],
                )
            )
        stock_table.rows = rows

    def save_stock_row(item_id: str, stock_value: str, min_value: str) -> None:
        save_sections(service.save_stock_row(item_id, stock_value, min_value))
        mark_dirty("stock", "ventas", update_now=True)
        show_message(f"Stock actualizado: {service.product_map[item_id]['name']}", ft.Colors.GREEN_500)

    def add_new_product(_: ft.ControlEvent) -> None:
        name = (new_product_name.value or "").strip()
        category = (new_product_category.value or "Plumillas").strip()
        if not name:
            show_message("Escribe el nombre del producto.", ft.Colors.RED_400)
            return
        product_id, sections = service.add_product(
            {
                "name": name,
                "category": category,
                "stock": new_product_stock.value,
                "min_stock": new_product_min.value,
                "unit_cost": new_product_cost.value,
                "price_one_side": new_product_price_one_side.value,
                "price_two_sides": new_product_price_two_sides.value,
            }
        )
        save_sections(sections)
        new_product_name.value = ""
        new_product_stock.value = "0"
        new_product_min.value = "5"
        new_product_cost.value = "0"
        new_product_price_one_side.value = "0"
        new_product_price_two_sides.value = "0"
        handle_new_product_category()
        mark_dirty("stock", "ventas", "compras", "mermas", update_now=True)
        show_message(f"Producto agregado al stock: {service.product_map[product_id]['name']}", ft.Colors.GREEN_500)

    def open_pick_pricing_dialog(_: ft.ControlEvent) -> None:
        groups = db.setdefault("pricing", deepcopy(DEFAULT_PICK_PRICING)).setdefault("groups", {})
        group_keys = ["JAZZ", "TRI_TEAR", "STANDARD"]
        fields: dict[str, dict[str, ft.TextField]] = {}
        controls: list[ft.Control] = []
        for g in group_keys:
            group = groups.get(g, deepcopy(DEFAULT_PICK_PRICING["groups"][g]))
            tiers = sorted(group.get("tiers", []), key=lambda x: safe_int(str(x.get("qty", 0)), 0))
            while len(tiers) < 3:
                tiers.append({"qty": 10 * (len(tiers) + 1), "one_side": 0.0, "two_sides": 0.0})
            bulk = group.get("bulk", {})
            fields[g] = {
                "p10_1": ft.TextField(label="P10 1 lado", value=f"{float(tiers[0].get('one_side', 0)):.2f}", width=120),
                "p10_2": ft.TextField(label="P10 2 lados", value=f"{float(tiers[0].get('two_sides', 0)):.2f}", width=120),
                "p20_1": ft.TextField(label="P20 1 lado", value=f"{float(tiers[1].get('one_side', 0)):.2f}", width=120),
                "p20_2": ft.TextField(label="P20 2 lados", value=f"{float(tiers[1].get('two_sides', 0)):.2f}", width=120),
                "p30_1": ft.TextField(label="P30 1 lado", value=f"{float(tiers[2].get('one_side', 0)):.2f}", width=120),
                "p30_2": ft.TextField(label="P30 2 lados", value=f"{float(tiers[2].get('two_sides', 0)):.2f}", width=120),
                "bulk_min": ft.TextField(label="Mayoreo desde", value=str(int(bulk.get("min_qty", 40))), width=120),
                "bulk_1": ft.TextField(label="Mayoreo 1 lado", value=f"{float(bulk.get('one_side_unit', 0)):.2f}", width=120),
                "bulk_2": ft.TextField(label="Mayoreo 2 lados", value=f"{float(bulk.get('two_sides_unit', 0)):.2f}", width=120),
            }
            controls.extend(
                [
                    ft.Text(group.get("name", g), weight=ft.FontWeight.BOLD),
                    ft.Row([fields[g]["p10_1"], fields[g]["p10_2"], fields[g]["p20_1"], fields[g]["p20_2"]], wrap=True),
                    ft.Row([fields[g]["p30_1"], fields[g]["p30_2"], fields[g]["bulk_min"], fields[g]["bulk_1"], fields[g]["bulk_2"]], wrap=True),
                    ft.Divider(),
                ]
            )

        def close_dialog() -> None:
            dlg.open = False
            page.update()

        def save_changes(_: ft.ControlEvent) -> None:
            for g in group_keys:
                f = fields[g]
                groups[g] = {
                    "name": groups.get(g, {}).get("name", DEFAULT_PICK_PRICING["groups"][g]["name"]),
                    "tiers": [
                        {"qty": 10, "one_side": max(0.0, safe_float(f["p10_1"].value, 0.0)), "two_sides": max(0.0, safe_float(f["p10_2"].value, 0.0))},
                        {"qty": 20, "one_side": max(0.0, safe_float(f["p20_1"].value, 0.0)), "two_sides": max(0.0, safe_float(f["p20_2"].value, 0.0))},
                        {"qty": 30, "one_side": max(0.0, safe_float(f["p30_1"].value, 0.0)), "two_sides": max(0.0, safe_float(f["p30_2"].value, 0.0))},
                    ],
                    "bulk": {"min_qty": max(1, safe_int(f["bulk_min"].value, 40)), "one_side_unit": max(0.0, safe_float(f["bulk_1"].value, 0.0)), "two_sides_unit": max(0.0, safe_float(f["bulk_2"].value, 0.0))},
                }
            save_sections({"pricing"})
            mark_dirty("ventas", update_now=True)
            close_dialog()
            show_message("Costos de plumillas actualizados.", ft.Colors.GREEN_500)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Configurar costos de plumillas"),
            content=ft.Container(width=980, height=560, content=ft.Column(controls=controls, scroll=ft.ScrollMode.ALWAYS)),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: close_dialog()), ft.Button("Guardar costos", icon=ft.Icons.SAVE, on_click=save_changes)],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # Compras
    purchase_product = ft.Dropdown(label="Producto", width=360, options=[])
    purchase_qty = ft.TextField(label="Cantidad", width=140)
    purchase_total = ft.TextField(label="Costo Total (con aranceles)", width=220)
    purchase_table = ft.DataTable(columns=[ft.DataColumn(ft.Text(x)) for x in ["Fecha", "Producto", "Cantidad", "Costo Total", "Costo Unitario", "Estado", "Accion"]], rows=[], heading_row_color=colors["border"])

    def refresh_purchases() -> None:
        purchase_product.options = [ft.dropdown.Option(key=x["id"], text=x["name"]) for x in service.stock_items]
        if not purchase_product.value and service.stock_items:
            purchase_product.value = service.stock_items[0]["id"]
        records = db["compras"].get("items", [])
        sig = _signature([(r.get("date"), r.get("product_id"), r.get("quantity"), r.get("received")) for r in records])
        if table_signatures.get("purchase_table") == sig:
            return
        table_signatures["purchase_table"] = sig
        purchase_table.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(r.get("date", ""))),
                    ft.DataCell(ft.Text(service.product_map.get(r.get("product_id", ""), {}).get("name", r.get("product_id", "")))),
                    ft.DataCell(ft.Text(str(r.get("quantity", 0)))),
                    ft.DataCell(ft.Text(f"${r.get('total_cost', 0):.2f}")),
                    ft.DataCell(ft.Text(f"${r.get('unit_cost', 0):.2f}")),
                    ft.DataCell(ft.Text("Recibido" if r.get("received", True) else "Pendiente", color=ft.Colors.GREEN_400 if r.get("received", True) else ft.Colors.ORANGE_400)),
                    ft.DataCell(ft.Button("Recibir" if not r.get("received", True) else "Quitar", icon=ft.Icons.INVENTORY_2, on_click=lambda e, i=idx: toggle_purchase(i))),
                ]
            )
            for idx, r in reversed(list(enumerate(records)))
        ]

    def add_purchase(_: ft.ControlEvent) -> None:
        pid = purchase_product.value or ""
        qty = safe_int(purchase_qty.value, 0)
        total_cost = safe_float(purchase_total.value, 0.0)
        if not pid or qty <= 0 or total_cost <= 0:
            show_message("Completa producto, cantidad y costo total.", ft.Colors.RED_400)
            return
        save_sections(service.add_purchase(pid, purchase_qty.value, purchase_total.value))
        purchase_qty.value = ""
        purchase_total.value = ""
        mark_dirty("compras", "stock", "ventas", "dashboard", update_now=True)
        show_message("Compra registrada. Usa 'Recibir' cuando llegue producto.", ft.Colors.GREEN_500)

    def toggle_purchase(idx: int) -> None:
        try:
            msg, sections = service.toggle_purchase_received(idx)
        except Exception:
            show_message("No se pudo actualizar la compra.", ft.Colors.RED_400)
            return
        save_sections(sections)
        mark_dirty("compras", "stock", "ventas", update_now=True)
        show_message(msg, ft.Colors.GREEN_500 if "actualizado" in msg else ft.Colors.ORANGE_400)

    # Mermas
    waste_product = ft.Dropdown(label="Producto", width=360, options=[])
    waste_qty = ft.TextField(label="Cantidad perdida", width=160)
    waste_reason = ft.TextField(label="Motivo", width=360)
    waste_table = ft.DataTable(columns=[ft.DataColumn(ft.Text(x)) for x in ["Fecha", "Producto", "Cantidad", "Motivo", "Costo perdida"]], rows=[], heading_row_color=colors["border"])

    def refresh_waste() -> None:
        waste_product.options = [ft.dropdown.Option(key=x["id"], text=x["name"]) for x in service.stock_items]
        if not waste_product.value and service.stock_items:
            waste_product.value = service.stock_items[0]["id"]
        records = db["mermas"].get("items", [])
        sig = _signature([(r.get("date"), r.get("product_id"), r.get("quantity"), r.get("reason")) for r in records])
        if table_signatures.get("waste_table") == sig:
            return
        table_signatures["waste_table"] = sig
        waste_table.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(r.get("date", ""))),
                    ft.DataCell(ft.Text(service.product_map.get(r.get("product_id", ""), {}).get("name", r.get("product_id", "")))),
                    ft.DataCell(ft.Text(str(r.get("quantity", 0)))),
                    ft.DataCell(ft.Text(r.get("reason", ""))),
                    ft.DataCell(ft.Text(f"${r.get('loss_cost', 0):.2f}")),
                ]
            )
            for r in reversed(records)
        ]

    def add_waste(_: ft.ControlEvent) -> None:
        pid = waste_product.value or ""
        qty = safe_int(waste_qty.value, 0)
        reason = (waste_reason.value or "").strip()
        if not pid or qty <= 0 or not reason:
            show_message("Completa producto, cantidad y motivo.", ft.Colors.RED_400)
            return
        item = service.product_map.get(pid)
        if not item or qty > int(item.get("stock", 0)):
            show_message("No puedes registrar merma mayor al stock.", ft.Colors.RED_400)
            return
        save_sections(service.add_waste(pid, waste_qty.value, reason))
        waste_qty.value = ""
        waste_reason.value = ""
        mark_dirty("mermas", "stock", "ventas", "dashboard", update_now=True)
        show_message("Merma registrada.", ft.Colors.ORANGE_400)

    # Clientes
    clients_table = ft.DataTable(columns=[ft.DataColumn(ft.Text(x)) for x in ["Cliente", "Total gastado", "Compras", "Ultima compra"]], rows=[], heading_row_color=colors["border"])
    client_history_dropdown = ft.Dropdown(label="Detalle por cliente", width=360, options=[])
    client_history_table = ft.DataTable(columns=[ft.DataColumn(ft.Text(x)) for x in ["Venta", "Fecha", "Producto", "Cant", "Total"]], rows=[], heading_row_color=ft.Colors.BLUE_GREY_900)

    def render_client_history(update: bool = True) -> None:
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
                            ft.DataCell(ft.Text(service.product_map.get(order.get("product_id", ""), {}).get("name", order.get("product_id", "")))),
                            ft.DataCell(ft.Text(str(order.get("quantity", 0)))),
                            ft.DataCell(ft.Text(f"${order.get('total', 0):.2f}")),
                        ]
                    )
                )
        client_history_table.rows = rows
        if update:
            page.update()

    def refresh_clients() -> None:
        clients = sorted(db["clientes"].get("items", []), key=lambda c: c.get("name", "").lower())
        sig = _signature([(c.get("name"), c.get("total_spent"), len(c.get("orders", []))) for c in clients])
        if table_signatures.get("clients_table") != sig:
            table_signatures["clients_table"] = sig
            clients_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(c.get("name", ""))),
                        ft.DataCell(ft.Text(f"${float(c.get('total_spent', 0.0)):.2f}")),
                        ft.DataCell(ft.Text(str(len(c.get("orders", []))))),
                        ft.DataCell(ft.Text(c.get("orders", [{}])[-1].get("date", "--") if c.get("orders") else "--")),
                    ]
                )
                for c in clients
            ]
        names = [c.get("name", "") for c in clients if c.get("name")]
        client_history_dropdown.options = [ft.dropdown.Option(n) for n in names]
        if names and client_history_dropdown.value not in names:
            client_history_dropdown.value = names[0]
        elif not names:
            client_history_dropdown.value = None
        render_client_history(update=False)

    # Dialogs

    def on_month_change(_: ft.ControlEvent) -> None:
        """Cambiar el mes activo cuando se selecciona en el dropdown."""
        if not month_dropdown.value:
            return
        selected_month = month_dropdown.value
        # Actualizar mes actual
        db["ventas"]["current_month"] = selected_month
        # Asegurar que el mes existe en la estructura de datos
        if selected_month not in db["ventas"]["by_month"]:
            db["ventas"]["by_month"][selected_month] = []
        # Guardar cambios
        save_sections({"ventas"})
        # Limpiar cache de firmas de tabla para forzar refresh
        table_signatures.clear()
        # Actualizar labels del mes
        current_month_label.value = f"Mes activo: {selected_month}"
        # Refrescar directamente ambas vistas
        refresh_dashboard()
        refresh_sales()
        # Actualizar UI
        page.update()
        show_message(f"Mes activo: {selected_month}")

    def refresh_month_dropdown() -> None:
        """Actualiza las opciones del dropdown de meses."""
        available_months = store.get_available_months()
        if not available_months:
            available_months = [datetime.now().strftime("%Y-%m")]
            db["ventas"]["by_month"].setdefault(available_months[0], [])
            save_sections({"ventas"})
        month_dropdown.options = [ft.dropdown.Option(m) for m in available_months]
        current = db["ventas"]["current_month"]
        if current not in [m for m in available_months]:
            current = available_months[0]
            db["ventas"]["current_month"] = current
            save_sections({"ventas"})
        month_dropdown.value = current

    month_dropdown.on_select = on_month_change

    def export_current_month_pdf(_: ft.ControlEvent) -> None:
        if not REPORTLAB_AVAILABLE:
            show_message("Instala reportlab: pip install reportlab", ft.Colors.RED_400)
            return
        month = db["ventas"]["current_month"]
        sales = db["ventas"].get("by_month", {}).get(month, [])
        summary = summarize_month(month, db["ventas"], db["compras"], db["mermas"])
        output = export_month_pdf(month, sales, summary, service.product_map)
        show_message(f"PDF exportado: {output.name}", ft.Colors.GREEN_500)

    refreshers = {"dashboard": refresh_dashboard, "ventas": refresh_sales, "stock": refresh_stock, "compras": refresh_purchases, "mermas": refresh_waste, "clientes": refresh_clients}

    def mark_dirty(*tabs: str, update_now: bool = False) -> None:
        dirty_tabs.update(tabs)
        if active_tab in dirty_tabs:
            refreshers[active_tab]()
            dirty_tabs.discard(active_tab)
        if update_now:
            page.update()

    def on_tab_change(e: ft.ControlEvent) -> None:
        nonlocal active_tab
        tab_ids = ["dashboard", "ventas", "stock", "compras", "mermas", "clientes"]
        active_tab = tab_ids[int(e.control.selected_index or 0)]
        if active_tab not in tab_initialized or active_tab in dirty_tabs:
            refreshers[active_tab]()
            dirty_tabs.discard(active_tab)
            tab_initialized.add(active_tab)
            page.update()

    def handle_sale_mode_change(e: ft.ControlEvent) -> None:
        sale_price_mode.value = e.control.value or "Normal"
        sponsorship_total_input.disabled = sale_price_mode.value not in ("Patrocinio", "Multi-modelo")
        sponsorship_total_input.label = "Total" if sale_price_mode.value == "Multi-modelo" else "Total patrocinio"
        if sponsorship_total_input.disabled:
            sponsorship_total_input.value = "0"
        recalc_sale_totals(update=True)

    shipping_mode.on_select = lambda e: (setattr(shipping_manual, "disabled", shipping_mode.value != "Envio Cotizado"), setattr(shipping_manual, "value", "0" if shipping_manual.disabled else shipping_manual.value), recalc_sale_totals(update=True))
    sale_price_mode.on_select = handle_sale_mode_change
    sale_product_dropdown.on_select = lambda e: recalc_sale_totals(update=True)
    sale_qty.on_change = lambda e: recalc_sale_totals(update=True)
    engraving_mode.on_select = lambda e: recalc_sale_totals(update=True)
    sponsorship_total_input.on_change = lambda e: recalc_sale_totals(update=True)
    shipping_manual.on_change = lambda e: recalc_sale_totals(update=True)
    advance_input.on_change = lambda e: recalc_sale_totals(update=True)
    new_product_category.on_select = lambda e: (handle_new_product_category(), page.update())
    new_product_price_one_side.on_change = lambda e: (handle_new_product_category(), page.update())
    client_history_dropdown.on_select = lambda e: render_client_history(update=True)

    dashboard_tab = ft.Column(
        controls=[
            ft.Row([ft.Text("Black Hole Picks", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_200), current_month_label], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row(
                controls=[
                    ft.Container(padding=12, bgcolor=ft.Colors.BLUE_GREY_900, border_radius=10, content=ft.Column([ft.Text("Ingresos Totales"), ingresos_text]), expand=1),
                    ft.Container(padding=12, bgcolor=ft.Colors.BLUE_GREY_900, border_radius=10, content=ft.Column([ft.Text("Costos de Inversion"), inversion_text]), expand=1),
                    ft.Container(padding=12, bgcolor=ft.Colors.BLUE_GREY_900, border_radius=10, content=ft.Column([ft.Text("Costos de Mermas"), mermas_text]), expand=1),
                    ft.Container(padding=12, bgcolor=ft.Colors.DEEP_PURPLE_900, border_radius=10, content=ft.Column([ft.Text("Ganancia Neta"), ganancia_text]), expand=1),
                ]
            ),
            ft.Row(
                controls=[
                    ft.Container(padding=10, bgcolor=ft.Colors.BLUE_GREY_900, border_radius=8, content=ft.Row([ft.Text("Producto mas vendido:"), most_sold_text]), expand=True),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                expand=True,
                padding=12,
                bgcolor=ft.Colors.BLUE_GREY_900,
                border_radius=10,
                content=ft.Column(
                    controls=[
                        ft.Text("Modelos vendidos en el mes", weight=ft.FontWeight.BOLD),
                        model_sales_chart,
                    ]
                ),
            ),
            ft.Divider(),
            ft.Text("Ventas del mes activo", weight=ft.FontWeight.BOLD),
            ft.Row([ft.Container(expand=True, content=ft.Column([month_sales_table], scroll=ft.ScrollMode.ALWAYS))], expand=True),
        ],
        expand=True,
    )

    ventas_tab = ft.Column(
        controls=[
            ft.Row(
                [
                    card_container(
                        [
                            ft.Row([ft.Text("Registrar venta", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([sale_id_preview, sale_date_preview], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([client_dropdown, new_client_name], wrap=True, spacing=16),
                            ft.Row([sale_product_dropdown, sale_qty, sale_price_mode, sponsorship_total_input, engraving_mode], wrap=True, spacing=16),
                            ft.Row([shipping_mode, shipping_manual, advance_input, sale_status], wrap=True, spacing=16),
                            notes_input,
                            ft.Row([ft.Button("Registrar venta", icon=ft.Icons.POINT_OF_SALE, on_click=add_sale)], alignment=ft.MainAxisAlignment.END),
                        ],
                        expand=True,
                    ),
                    card_container(
                        [
                            ft.Text("Resumen de venta", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD)),
                            ft.Divider(color=colors["border"]),
                            subtotal_preview,
                            engraving_preview,
                            shipping_preview,
                            total_preview,
                            balance_preview,
                            ft.Divider(color=colors["border"]),
                            pricing_rule_preview,
                        ],
                        width=340,
                    ),
                ],
                expand=True,
                spacing=16,
            ),
            card_container(
                [
                    ft.Row([ft.Text("Ventas del mes", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))]),
                    ft.Container(expand=True, height=420, content=ft.Column([sales_table], scroll=ft.ScrollMode.ALWAYS)),
                ],
                expand=True,
            ),
        ],
        expand=True,
        spacing=20,
    )

    stock_tab = ft.Column(
        controls=[
            card_container(
                [
                    ft.Row([ft.Text("Stock y catalogo", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text("Stock actual y productos con stock bajo.", style=ft.TextStyle(color=colors["text_secondary"], size=13)),
                    ft.Row([ft.Button("Configurar costos de modelos de plumilla", icon=ft.Icons.TUNE, on_click=open_pick_pricing_dialog)], alignment=ft.MainAxisAlignment.END),
                ],
                expand=True,
            ),
            card_container(
                [
                    ft.Text("Agregar nuevo producto", style=ft.TextStyle(color=colors["text_primary"], size=16, weight=ft.FontWeight.BOLD)),
                    ft.Row([new_product_name, new_product_category, new_product_stock, new_product_min, new_product_cost, new_product_price_one_side, new_product_price_two_sides, ft.Button("Agregar", icon=ft.Icons.ADD_BOX, on_click=add_new_product)], wrap=True, spacing=16),
                ],
                expand=True,
            ),
            card_container(
                [
                    ft.Row([ft.Text("Inventario editable", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))]),
                    ft.Container(expand=True, height=480, content=ft.Column([stock_table], scroll=ft.ScrollMode.ALWAYS)),
                ],
                expand=True,
            ),
        ],
        expand=True,
        spacing=20,
    )

    compras_tab = ft.Column(
        controls=[
            card_container(
                [
                    ft.Row([ft.Text("Registrar compra", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([purchase_product, purchase_qty, purchase_total, ft.Button("Registrar compra", on_click=add_purchase)], wrap=True, spacing=16),
                ],
                expand=True,
            ),
            card_container(
                [
                    ft.Row([ft.Text("Compras recientes", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))]),
                    ft.Container(expand=True, height=520, content=ft.Column([purchase_table], scroll=ft.ScrollMode.ALWAYS)),
                ],
                expand=True,
            ),
        ],
        expand=True,
        spacing=20,
    )

    mermas_tab = ft.Column(
        controls=[
            card_container(
                [
                    ft.Row([ft.Text("Registrar merma", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([waste_product, waste_qty, waste_reason, ft.Button("Registrar merma", on_click=add_waste)], wrap=True, spacing=16),
                ],
                expand=True,
            ),
            card_container(
                [
                    ft.Row([ft.Text("Registro de mermas", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))]),
                    ft.Container(expand=True, height=520, content=ft.Column([waste_table], scroll=ft.ScrollMode.ALWAYS)),
                ],
                expand=True,
            ),
        ],
        expand=True,
        spacing=20,
    )

    clientes_tab = ft.Column(
        controls=[
            card_container(
                [
                    ft.Row([ft.Text("Base de clientes", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))]),
                    ft.Container(expand=True, height=260, content=ft.Column([clients_table], scroll=ft.ScrollMode.ALWAYS)),
                ],
                expand=True,
            ),
            card_container(
                [
                    ft.Row([ft.Text("Historial de cliente", style=ft.TextStyle(color=colors["text_primary"], size=18, weight=ft.FontWeight.BOLD))]),
                    client_history_dropdown,
                    ft.Container(expand=True, height=260, content=ft.Column([client_history_table], scroll=ft.ScrollMode.ALWAYS)),
                ],
                expand=True,
            ),
        ],
        expand=True,
        spacing=20,
    )

    tab_ids = ["dashboard", "ventas", "stock", "compras", "mermas", "clientes"]
    page_tabs: list[ft.Control] = []
    nav_buttons: list[ft.Container] = []

    def select_tab(index: int) -> None:
        nonlocal active_tab
        active_tab = tab_ids[index]
        for idx, button in enumerate(nav_buttons):
            button.bgcolor = colors["accent"] if idx == index else colors["surface"]
        mark_dirty(active_tab, update_now=True)
        content_view.content = page_tabs[index]
        page.update()

    def build_nav_item(label: str, icon: str, index: int) -> ft.Container:
        button = nav_button(label, icon, selected=index == 0, on_click=lambda e, idx=index: select_tab(idx))
        nav_buttons.append(button)
        return button

    page_tabs = [dashboard_tab, ventas_tab, stock_tab, compras_tab, mermas_tab, clientes_tab]
    content_view = ft.Container(expand=True, content=dashboard_tab)

    sidebar = ft.Column(
        [
            ft.Text("Black Hole Picks", style=ft.TextStyle(color=colors["text_primary"], size=20, weight=ft.FontWeight.BOLD)),
            ft.Text("CRM Dashboard", style=ft.TextStyle(color=colors["text_secondary"], size=12)),
            ft.Divider(color=colors["border"], height=1),
            build_nav_item("Dashboard", ft.Icons.DASHBOARD, 0),
            build_nav_item("Ventas", ft.Icons.POINT_OF_SALE, 1),
            build_nav_item("Stock", ft.Icons.INVENTORY_2, 2),
            build_nav_item("Compras", ft.Icons.SHOPPING_CART, 3),
            build_nav_item("Mermas", ft.Icons.DELETE, 4),
            build_nav_item("Clientes", ft.Icons.GROUP, 5),
        ],
        spacing=16,
        expand=False,
    )

    header_bar = ft.Row(
        [
            ft.Column(
                [
                    ft.Text("Black Hole Picks", style=ft.TextStyle(color=colors["text_primary"], size=24, weight=ft.FontWeight.BOLD)),
                    current_month_label,
                ],
                spacing=6,
            ),
            ft.Row(
                [
                    month_dropdown,
                    ft.Button("Exportar PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_current_month_pdf, bgcolor=colors["surface"], color=colors["text_primary"]),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    dashboard_tab = ft.Column(
        [
            ft.Row(
                [
                    kpi_card("Ingresos", ingresos_text.value, accent=False),
                    kpi_card("Inversión", inversion_text.value),
                    kpi_card("Mermas", mermas_text.value),
                    kpi_card("Ganancia Neta", ganancia_text.value, accent=True),
                ],
                spacing=16,
                expand=True,
            ),
            ft.Row(
                [
                    card_container(
                        [
                            ft.Text("Producto más vendido", style=ft.TextStyle(color=colors["text_primary"], size=16, weight=ft.FontWeight.BOLD)),
                            ft.Text(most_sold_text.value, style=ft.TextStyle(color=colors["accent"], size=18, weight=ft.FontWeight.BOLD)),
                            ft.Divider(color=colors["border"]),
                            model_sales_chart,
                        ],
                        expand=True,
                        height=320,
                    ),
                    card_container(
                        [
                            ft.Text("Ventas recientes", style=ft.TextStyle(color=colors["text_primary"], size=16, weight=ft.FontWeight.BOLD)),
                            ft.Container(expand=True, height=320, content=ft.Column([month_sales_table], scroll=ft.ScrollMode.ALWAYS)),
                        ],
                        expand=True,
                    ),
                ],
                spacing=16,
                expand=True,
            ),
        ],
        spacing=20,
        expand=True,
    )

    main_content = ft.Column(
        [
            header_bar,
            ft.Container(expand=True, content=content_view),
        ],
        spacing=20,
        expand=True,
    )

    page.add(
        ft.Container(
            expand=True,
            padding=24,
            content=ft.Row(
                [
                    ft.Container(
                        width=260,
                        padding=ft.padding.symmetric(vertical=24, horizontal=16),
                        bgcolor=colors["surface"],
                        border_radius=18,
                        border=ft.border.all(1, colors["border"]),
                        shadow=ft.BoxShadow(color="#00000030", blur_radius=20, offset=ft.Offset(0, 8)),
                        content=sidebar,
                    ),
                    ft.VerticalDivider(width=24, color=colors["background"]),
                    ft.Container(expand=True, content=main_content),
                ],
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )
    )
    refresh_month_dropdown()
    refresh_dashboard()
    refresh_sales()
    tab_initialized.update({"dashboard", "ventas"})
    page.update()

