# Sistema de Encomiendas
App de escritorio para gestión de envíos, construida con Python + Tkinter + SQLite.

## Estructura modular

```
encomiendas/
├── main.py                    ← Punto de entrada, ventana principal, sidebar
├── encomiendas.db             ← Base de datos SQLite (se crea automático)
├── modules/
│   ├── database.py            ← Toda la lógica SQL (CRUD envios, articulos, pagos)
│   ├── nueva_encomienda.py    ← Formulario de nuevo envío
│   ├── historial.py           ← Lista + panel de detalle + acciones
│   ├── pago.py                ← Ventana popup para registrar pagos
│   └── reportes.py            ← Dashboard con gráficas y tablas
```

## Cómo ejecutar

```bash
python main.py
```

Solo requiere Python 3.8+ (Tkinter viene incluido).

## Base de datos SQLite — Tablas

### envios
| Campo       | Tipo  | Descripción                          |
|-------------|-------|--------------------------------------|
| id          | INT   | Clave primaria                       |
| codigo      | TEXT  | Ej: ENV-0001                         |
| fecha       | TEXT  | Fecha de registro                    |
| ent_nombre  | TEXT  | Nombre de quien entrega              |
| ent_tel     | TEXT  | Teléfono de quien entrega            |
| rec_nombre  | TEXT  | Nombre de quien recibe               |
| rec_tel     | TEXT  | Teléfono de quien recibe             |
| peso_total  | REAL  | Suma de pesos de todos los artículos |
| subtotal    | REAL  | Suma de valores de artículos         |
| total       | REAL  | Total a cobrar                       |
| abono       | REAL  | Monto ya cobrado                     |
| restante    | REAL  | total - abono                        |
| moneda      | TEXT  | C$ o $                               |
| estado      | TEXT  | Pagado / Abono / Pendiente / Cancelado|
| cajero      | TEXT  | Quien recibió el pago                |
| tipo_pago   | TEXT  | Efectivo C$, Efectivo $, Transferencia|
| nota        | TEXT  | Observaciones                        |

### articulos (relacionada con envios)
| Campo       | Tipo  | Descripción           |
|-------------|-------|-----------------------|
| id          | INT   | Clave primaria        |
| envio_id    | INT   | FK → envios.id        |
| descripcion | TEXT  | Nombre del artículo   |
| cantidad    | INT   | Cantidad              |
| peso_lb     | REAL  | Peso en libras        |
| valor       | REAL  | Valor declarado       |

### pagos (historial de abonos)
| Campo    | Tipo  | Descripción              |
|----------|-------|--------------------------|
| id       | INT   | Clave primaria           |
| envio_id | INT   | FK → envios.id           |
| fecha    | TEXT  | Fecha del pago           |
| monto    | REAL  | Monto pagado             |
| moneda   | TEXT  | C$ o $                   |
| tipo     | TEXT  | Tipo de pago             |
| cajero   | TEXT  | Quien recibió            |
| nota     | TEXT  | Observación              |
