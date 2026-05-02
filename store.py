from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from models import DEFAULT_PICK_PRICING, FileNames, INITIAL_PRODUCTS
from services import infer_pick_pricing_group, safe_float


def now_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


@dataclass
class JsonStore:
    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.ventas_dir = self.base_dir / "ventas_mensuales"
        self.ventas_dir.mkdir(parents=True, exist_ok=True)
        names = FileNames()
        self.paths: dict[str, Path] = {
            "stock": self.base_dir / names.stock,
            "compras": self.base_dir / names.compras,
            "mermas": self.base_dir / names.mermas,
            "clientes": self.base_dir / names.clientes,
            "pricing": self.base_dir / names.pricing,
        }
        self._ensure_files()

    def _get_ventas_path(self, month: str) -> Path:
        """Retorna la ruta del archivo de ventas para un mes específico."""
        return self.ventas_dir / f"ventas_{month}.json"

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
        ventas_default = {"current_month": now_month_key(), "by_month": {}}
        compras_default = {"items": []}
        mermas_default = {"items": []}
        clientes_default = {"items": []}
        pricing_default = deepcopy(DEFAULT_PICK_PRICING)

        stock_data = self._read_json(self.paths["stock"], stock_default)
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
            if str(row.get("category", "")).strip().lower() == "plumillas":
                row["pricing_group"] = row.get("pricing_group", infer_pick_pricing_group(row.get("name", "")))
            else:
                row["pricing_group"] = ""
        self._write_json(self.paths["stock"], stock_data)

        # Manejar ventas mensuales
        current_month = now_month_key()
        ventas_path = self._get_ventas_path(current_month)
        month_ventas = self._read_json(ventas_path, [])
        if not isinstance(month_ventas, list):
            month_ventas = []
        self._write_json(ventas_path, month_ventas)

        self._write_json(self.paths["compras"], self._read_json(self.paths["compras"], compras_default))
        self._write_json(self.paths["mermas"], self._read_json(self.paths["mermas"], mermas_default))
        self._write_json(self.paths["clientes"], self._read_json(self.paths["clientes"], clientes_default))
        self._write_json(self.paths["pricing"], self._read_json(self.paths["pricing"], pricing_default))

    def load_all(self) -> dict[str, Any]:
        """Carga todos los datos, consolidando ventas de todos los meses."""
        current_month = now_month_key()
        by_month: dict[str, list[dict[str, Any]]] = {}
        
        # Cargar todos los archivos de ventas mensuales
        if self.ventas_dir.exists():
            for ventas_file in sorted(self.ventas_dir.glob("ventas_*.json")):
                try:
                    month = ventas_file.stem.replace("ventas_", "")
                    sales_list = self._read_json(ventas_file, [])
                    if isinstance(sales_list, list):
                        by_month[month] = sales_list
                except Exception:
                    pass
        
        # Asegurar que el mes actual existe
        if current_month not in by_month:
            by_month[current_month] = []
        
        return {
            "stock": self._read_json(self.paths["stock"], {"items": []}),
            "ventas": {"current_month": current_month, "by_month": by_month},
            "compras": self._read_json(self.paths["compras"], {"items": []}),
            "mermas": self._read_json(self.paths["mermas"], {"items": []}),
            "clientes": self._read_json(self.paths["clientes"], {"items": []}),
            "pricing": self._read_json(self.paths["pricing"], deepcopy(DEFAULT_PICK_PRICING)),
        }

    def get_available_months(self) -> list[str]:
        """Retorna lista de meses disponibles en las ventas, ordenados descendentemente."""
        months = []
        if self.ventas_dir.exists():
            for ventas_file in self.ventas_dir.glob("ventas_*.json"):
                try:
                    month = ventas_file.stem.replace("ventas_", "")
                    months.append(month)
                except Exception:
                    pass
        months = sorted(list(set(months)), reverse=True)
        return months

    def save_sections(self, payload: dict[str, Any], sections: set[str]) -> None:
        for section in sections:
            if section == "ventas":
                # Guardar cada mes en su archivo correspondiente
                ventas_data = payload.get("ventas", {})
                current_month = ventas_data.get("current_month", now_month_key())
                by_month = ventas_data.get("by_month", {})
                for month, sales in by_month.items():
                    path = self._get_ventas_path(month)
                    self._write_json(path, sales)
            else:
                path = self.paths.get(section)
                if path:
                    self._write_json(path, payload[section])
