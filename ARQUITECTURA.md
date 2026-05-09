# 📋 Arquitectura del Proyecto Organizador-BHP

## Descripción General
Es una aplicación de gestión integral de inventario y ventas para **Black Hole Picks** (fabricación y venta de plumillas). Fue construida en **Python** usando **Flet** para la interfaz gráfica y **JSON** como base de datos.

## Arquitectura en Capas

### 1. Capa de Datos (`models.py`)
Define estructuras base y constantes:
- **`FileNames`**: Nombres de archivos JSON
- **`INITIAL_PRODUCTS`**: Catálogo de 15 productos iniciales (plumillas y accesorios)
- **`DEFAULT_PICK_PRICING`**: Reglas de precios por grupo (JAZZ, TRI_TEAR, STANDARD) con tiers y precios mayoristas

### 2. Capa de Persistencia (`store.py`)
**`JsonStore`**: Maneja toda lectura/escritura de datos
- **Archivos principales:**
  - `stock.json` - Inventario de productos
  - `ventas.json` - Índice de ventas
  - `compras.json` - Registro de compras
  - `mermas.json` - Registro de pérdidas/desperdicios
  - `clientes.json` - Datos de clientes
  - `pricing_rules.json` - Reglas de precios dinámicas

- **Organización temporal:**
  - Ventas organizadas por mes en `ventas_mensuales/`
  - Archivos como: `ventas_2026-04.json`, `ventas_2026-05.json`

- **Características:**
  - Validación y recuperación de errores en datos corruptos
  - Backups automáticos con sufijo `.broken`
  - Escritura atómica con archivos temporales `.tmp`

### 3. Capa de Lógica de Negocio (`services.py`)
Funciones de cálculo y utilidad:

#### Cálculo de Precios
- **`calculate_pick_subtotal_from_rules()`**: Precio dinámico según:
  - Cantidad
  - Modo de grabado (1 lado / 2 lados)
  - Grupo de precios (JAZZ, TRI_TEAR, STANDARD)
  - Aplica tiers y precios mayoristas automáticamente

#### Cálculos Financieros
- **`calculate_balance()`**: Saldo = (subtotal + grabado + envío) - adelanto
- **`calculate_engraving_cost()`**: Costo de grabado (actualmente 0.0)
- **`summarize_month()`**: Resumen financiero mensual:
  - Ingresos (adelantos o totales según estatus de pago)
  - Inversión en compras
  - Costo de mermas
  - Ganancia neta
  - Producto más vendido

#### Generación de IDs
- **`generate_sale_id()`**: IDs secuenciales formato `BHP-YY-MM-###`
- **`generate_product_id()`**: IDs de productos con validación de duplicados

#### Validaciones y Utilidades
- **`safe_float()`**: Conversión segura a float con default
- **`safe_int()`**: Conversión segura a int con default
- **`is_pick_product()`**: Verifica si es una plumilla
- **`get_sale_unit_price()`**: Precio unitario según modo grabado
- **`infer_pick_pricing_group()`**: Clasifica plumillas automáticamente
- **`month_key_from_date()`**: Extrae clave de mes (YYYY-MM)

### 4. Capa de Presentación (`ui_app.py`)
Interfaz Flet (Framework multiplataforma):

#### Funcionalidades
- Gestor de inventario (agregar, editar, eliminar productos)
- Sistema de ventas con cálculo dinámico
- Registro de compras y mermas
- Gestión de clientes
- Vistas analíticas con KPI cards

#### Características Avanzadas
- Resúmenes mensuales interactivos
- Generación de reportes PDF mensuales con ReportLab
- Exportación de datos
- Interfaz responsiva y temática

### 5. Punto de Entrada (`main.py`)
Inicia la aplicación Flet:
```python
import flet as ft
from ui_app import run_app

if __name__ == "__main__":
    ft.run(run_app)
```

## Flujo de Datos

```
┌─────────────────────────────────────────────┐
│         Usuario (Interfaz UI)                │
│           (Flet Application)                 │
└────────────────────┬────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────┐
│      Capa de Presentación (ui_app.py)        │
│         - Vistas y componentes               │
│         - Interacción usuario                │
└────────────────────┬────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────┐
│   Capa de Lógica (services.py)               │
│      - Cálculos financieros                  │
│      - Generación de IDs                     │
│      - Validaciones y reglas de negocio      │
└────────────────────┬────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────┐
│    Capa de Persistencia (store.py)           │
│       - Lectura/Escritura JSON               │
│       - Manejo de errores                    │
│       - Backups y recuperación               │
└────────────────────┬────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────┐
│      Almacenamiento (assets/*.json)          │
│    - stock.json                              │
│    - ventas_mensuales/                       │
│    - compras.json, mermas.json, etc.         │
└─────────────────────────────────────────────┘
```

## Características Clave

✅ **Gestión de productos** con categorías (Plumillas, Alternos)  
✅ **Sistema de precios dinámico** con reglas por grupo y cantidad  
✅ **Trazabilidad mensual** de ventas separadas por mes  
✅ **Cálculo automático** de balances y adelantos  
✅ **Generación de reportes** PDF mensuales  
✅ **Persistencia robusta** con backups ante errores  
✅ **Validaciones de datos** en entrada y salida  
✅ **IDs secuenciales y únicos** para auditoría  

## Estructura de Datos

### Producto (Stock)
```json
{
  "id": "PICK-EST-071",
  "name": "Plumilla Estandar Negra 0.71mm",
  "category": "Plumillas",
  "stock": 0,
  "min_stock": 20,
  "unit_cost": 0.0,
  "sale_price": 15.0,
  "sale_price_one_side": 15.0,
  "sale_price_two_sides": 15.0,
  "pricing_group": "STANDARD"
}
```

### Venta
```json
{
  "id": "BHP-26-05-001",
  "product_id": "PICK-EST-071",
  "quantity": 10,
  "engraving_mode": "1 Lado",
  "pricing_mode": "Precio unitario",
  "subtotal": 150.0,
  "engraving_cost": 0.0,
  "shipping_cost": 0.0,
  "advance": 75.0,
  "balance": 75.0,
  "payment_status": "Anticipo",
  "date": "2026-05-09"
}
```

### Resumen Mensual
```json
{
  "month": "2026-05",
  "ingresos": 5000.0,
  "inversion": 2000.0,
  "costo_mermas": 100.0,
  "ganancia_neta": 2900.0,
  "most_sold": "PICK-EST-071",
  "total_sales": 45
}
```

## Patrones de Diseño

- **Single Responsibility**: Cada módulo tiene una responsabilidad clara
- **Separation of Concerns**: Capas independientes (datos, lógica, UI)
- **Factory Pattern**: Generación de IDs y clasificación de grupos
- **Strategy Pattern**: Múltiples modos de cálculo de precios
- **Repository Pattern**: `JsonStore` como abstracción de datos

## Dependencias Clave

- **flet**: Interfaz gráfica multiplataforma
- **reportlab**: Generación de PDF
- **pathlib**: Manejo de rutas
- **json**: Serialización de datos
- **dataclasses**: Definición de estructuras
- **datetime**: Manejo de fechas

---

*Documentación generada: Mayo 2026*
