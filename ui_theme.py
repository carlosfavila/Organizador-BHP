from __future__ import annotations

import flet as ft

colors = {
    "background": "#0E1014",
    "surface": "#121521",
    "card": "#171A26",
    "border": "#24283A",
    "text_primary": "#F4F6FB",
    "text_secondary": "#9EA6C0",
    "accent": "#6E8CFF",
    "success": "#34D399",
    "warning": "#FBBF24",
    "error": "#F87171",
}

text_styles = {
    "title": ft.TextStyle(color=colors["text_primary"], size=22, weight=ft.FontWeight.BOLD),
    "subtitle": ft.TextStyle(color=colors["text_secondary"], size=13),
    "metric": ft.TextStyle(color=colors["text_primary"], size=28, weight=ft.FontWeight.BOLD),
    "metric_label": ft.TextStyle(color=colors["text_secondary"], size=12, weight=ft.FontWeight.BOLD),
    "section": ft.TextStyle(color=colors["text_primary"], size=16, weight=ft.FontWeight.BOLD),
}


def app_theme() -> ft.Theme:
    return ft.Theme(color_scheme_seed=colors["accent"])


def card_container(content: ft.Control | list[ft.Control], padding: int = 20, expand: bool = False, width: int | None = None, height: int | None = None) -> ft.Container:
    if isinstance(content, list):
        content = ft.Column(controls=content, spacing=16)
    return ft.Container(
        bgcolor=colors["card"],
        padding=ft.padding.all(padding),
        border_radius=18,
        border=ft.border.all(1, colors["border"]),
        shadow=ft.BoxShadow(color="#00000030", blur_radius=20, offset=ft.Offset(0, 8)),
        content=content,
        expand=expand,
        width=width,
        height=height,
    )


def kpi_card(title: str, value: str, caption: str = "", accent: bool = False) -> ft.Container:
    color = colors["accent"] if accent else colors["text_primary"]
    return card_container(
        [
            ft.Text(title.upper(), style=ft.TextStyle(color=colors["text_secondary"], size=12, weight=ft.FontWeight.BOLD)),
            ft.Text(value, style=ft.TextStyle(color=color, size=32, weight=ft.FontWeight.BOLD)),
            ft.Text(caption, style=text_styles["subtitle"]),
        ],
        expand=True,
        height=160,
    )


def status_chip(status: str) -> ft.Container:
    mapping = {
        "En proceso": (colors["warning"], colors["text_primary"]),
        "Listas": (colors["accent"], colors["text_primary"]),
        "Entregado": (colors["success"], colors["text_primary"]),
    }
    bg, fg = mapping.get(status, (colors["surface"], colors["text_primary"]))
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        bgcolor=bg,
        border_radius=12,
        content=ft.Text(status, size=12, weight=ft.FontWeight.BOLD, color=fg),
    )


def nav_button(label: str, icon: str, selected: bool = False, on_click: ft.ControlEventHandler | None = None) -> ft.Container:
    return ft.Container(
        height=56,
        padding=ft.padding.symmetric(horizontal=18),
        bgcolor=colors["accent"] if selected else colors["surface"],
        border_radius=16,
        on_click=on_click,
        content=ft.Row(
            [
                ft.Icon(icon, color=colors["text_primary"], size=18),
                ft.Text(label, color=colors["text_primary"], size=14, weight=ft.FontWeight.W_600),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
