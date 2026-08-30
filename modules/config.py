"""
==============================================
  modules/config.py
  Configuración centralizada del sistema
==============================================
"""

import sys
import os

# ── Directorio base (compatible con PyInstaller) ──────────────────────────────
def get_base_dir():
    """Retorna el directorio donde están los datos (DB, config, recibos)."""
    if getattr(sys, 'frozen', False):
        # Ejecutable PyInstaller - usar directorio del .exe
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_resource_dir():
    """Retorna el directorio de recursos empaquetados (lectura)."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Moneda y unidades ──────────────────────────────────────────────────────────
MONEDA_DEFAULT = "C$"
PESO_UNIDAD = "lb"

# ── Paginación ─────────────────────────────────────────────────────────────────
PAGINA_TAMANO = 20

# ── Reportes ───────────────────────────────────────────────────────────────────
DEUDAS_VENCIDAS_DIAS = 7

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_FILE = "encomiendas.log"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = "DEBUG"


# ── Tarifas por destino ────────────────────────────────────────────────────────
TARIFA_PRECIO_BASE = 0
TARIFA_PRECIO_POR_LB = 0

# ── Tasa de cambio (C$ por $) ─────────────────────────────────────────────────
TASA_CAMBIO_DEFAULT = 36.0

# ── Backup ─────────────────────────────────────────────────────────────────────
BACKUP_DIR = "backups"
BACKUP_MAX = 30


# ── Temas (claro / oscuro) ─────────────────────────────────────────────────────
TEMA_LIGHT = {
    "bg": "#f5f5f0", "fg": "#2c2c2a",
    "sidebar": "#0f6e56", "sidebar_active": "#085041", "sidebar_text": "#ffffff",
    "sidebar_icon": "#5dcaa5",
    "card_bg": "#ffffff", "card_border": "#e0e0d8",
    "card_header": "#f1efe8", "card_header_fg": "#5f5e5a",
    "accent": "#0f6e56", "accent_light": "#e1f5ee",
    "danger_bg": "#fcebeb", "danger_fg": "#791f1f",
    "warning_bg": "#faeeda", "warning_fg": "#633806",
    "input_bg": "#ffffff",
    "select_bg": "#e1f5ee", "select_fg": "#085041",
    "tree_bg": "#ffffff", "tree_fg": "#2c2c2a",
    "progress_fill": "#0f6e56", "progress_bg": "#e1f5ee",
}

TEMA_DARK = {
    "bg": "#1e1e1e", "fg": "#e0e0e0",
    "sidebar": "#1a3a32", "sidebar_active": "#0f6e56", "sidebar_text": "#e0e0e0",
    "sidebar_icon": "#5dcaa5",
    "card_bg": "#2d2d2d", "card_border": "#444444",
    "card_header": "#383838", "card_header_fg": "#bbbbbb",
    "accent": "#1d9e75", "accent_light": "#1a3a32",
    "danger_bg": "#4a2020", "danger_fg": "#ff6b6b",
    "warning_bg": "#4a3a10", "warning_fg": "#ffd700",
    "input_bg": "#3d3d3d",
    "select_bg": "#1a3a32", "select_fg": "#1d9e75",
    "tree_bg": "#2d2d2d", "tree_fg": "#e0e0e0",
    "progress_fill": "#1d9e75", "progress_bg": "#3d3d3d",
}
