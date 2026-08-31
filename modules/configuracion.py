"""
==============================================
  modules/configuracion.py
  Modulo de configuracion del sistema Encomienda Jireh
==============================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
from datetime import datetime
import logging

try:
    from modules.config import get_base_dir
except ImportError:
    def get_base_dir():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

CONFIG_FILE = "config_app.json"


class ConfigManager:
    """Gestiona la configuracion persistente del sistema."""

    DEFAULTS = {
        "moneda": "$",
        "peso_unidad": "lb",
        "paginacion_tamano": 20,
        "prefijo_codigo": "MERC",
        "deudas_vencidas_dias": 7,
        "tarifa_precio_base": 0,
        "tarifa_precio_por_lb": 0,
        "zonas_envio": {},
        "backup_dir": "backups",
        "backup_max": 30,
        "tema": "light",
        "fuente_tamano": 10,
        "sidebar_ancho": 200,
        "destinos_usa": ["Miami", "Orlando", "Houston", "Los Angeles"],
        "estados_envio": ["Pendiente", "En camino", "Pagado", "Entregado", "Cancelado"],
        "categorias_costo": ["Transporte", "Combustible", "Mantenimiento", "Salarios", "Otros"],
        "tipos_pago": ["Efectivo", "Transferencia", "Tarjeta"],
        "cajeros": ["Admin"],
        "usuarios": [],
        "empresa_nombre": "Encomienda Jireh",
        "empresa_tel": "",
        "empresa_dir": "",
        "empresa_ruc": "",
        "recibo_mostrar_logo": True,
        "recibo_logo_ruta": "",
        "recibo_tamano_papel": "carta",
        "recibo_mostrar_direccion": True,
        "recibo_mostrar_telefono": True,
        "recibo_mostrar_notas_internas": False,
        "recibo_notas": "Gracias por su preferencia",
        "sonido_crear_envio": True,
        "alerta_deudas_activa": True,
        "alerta_listos_recoger": True,
        "reportes_rango_default": "hoy",
        "reportes_exportacion_default": "csv",
        "pin_acceso": "",
        "pin_acceso_activo": False,
        "timeout_sesion": 0,
    }

    def __init__(self, ruta_config=None):
        if ruta_config is None:
            ruta_config = os.path.join(get_base_dir(), CONFIG_FILE)
        self.ruta = ruta_config
        self._config = dict(self.DEFAULTS)
        self._cargar()

    def _cargar(self):
        if os.path.exists(self.ruta):
            try:
                with open(self.ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._config.update(data)
                logger.info("Configuracion cargada desde %s", self.ruta)
            except Exception as e:
                logger.warning("Error al cargar config: %s. Usando defaults.", e)

    def guardar(self):
        try:
            with open(self.ruta, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info("Configuracion guardada en %s", self.ruta)
            return True
        except Exception as e:
            logger.error("Error al guardar config: %s", e)
            return False

    def get(self, clave, default=None):
        return self._config.get(clave, default)

    def set(self, clave, valor):
        self._config[clave] = valor

    def get_all(self):
        return dict(self._config)

    def reset_defaults(self):
        self._config = dict(self.DEFAULTS)
        self.guardar()


class ConfiguracionFrame(ttk.Frame):
    """Interfaz grafica del modulo de configuracion."""

    def __init__(self, parent, db, app):
        super().__init__(parent)
        self.db = db
        self.app = app
        self.config_mgr = ConfigManager()
        self._vars = {}
        self._text_widgets = {}
        self._tree_widgets = {}
        self._build_ui()

    def _build_ui(self):
        c = self.app.colores

        main_canvas = tk.Canvas(self, bg=c["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=main_canvas.yview)
        self.scrollable_frame = ttk.Frame(main_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main_canvas.bind_all("<MouseWheel>", lambda e: main_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._crear_secciones(c)

    def _crear_secciones(self, c):
        frame = self.scrollable_frame
        frame.configure(style="TFrame")

        title = tk.Label(frame, text="Configuracion de Encomienda Jireh",
                         font=("Segoe UI", 16, "bold"),
                         bg=c["bg"], fg=c["accent"])
        title.pack(pady=(20, 10), padx=20, anchor="w")

        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)

        self._tab_general(c)
        self._tab_tarifas(c)
        self._tab_usuarios(c)
        self._tab_apariencia(c)
        self._tab_empresa(c)
        self._tab_recibos(c)
        self._tab_diseno(c)
        self._tab_alertas(c)
        self._tab_reportes(c)
        self._tab_seguridad(c)
        self._tab_listas(c)
        self._tab_respaldo(c)

        btn_frame = tk.Frame(frame, bg=c["bg"])
        btn_frame.pack(fill="x", padx=20, pady=20)

        self.btn_guardar = tk.Button(btn_frame, text="Guardar configuracion",
                                      font=("Segoe UI", 11, "bold"),
                                      bg=c["accent"], fg="white",
                                      activebackground=c["sidebar_active"],
                                      bd=0, relief="flat",
                                      padx=24, pady=10, cursor="hand2",
                                      command=self._guardar_todo)
        self.btn_guardar.pack(side="right")

        self.btn_reset = tk.Button(btn_frame, text="Restablecer defaults",
                                    font=("Segoe UI", 10),
                                    bg=c["danger_bg"], fg=c["danger_fg"],
                                    activebackground=c["danger_bg"],
                                    bd=0, relief="flat",
                                    padx=16, pady=10, cursor="hand2",
                                    command=self._resetear)
        self.btn_reset.pack(side="right", padx=(0, 10))

    def _crear_card(self, parent, titulo, c):
        card = ttk.Frame(parent, style="Card.TFrame")
        card.pack(fill="x", padx=10, pady=8)

        header = tk.Frame(card, bg=c["card_header"])
        header.pack(fill="x")
        tk.Label(header, text=titulo, font=("Segoe UI", 11, "bold"),
                 bg=c["card_header"], fg=c["card_header_fg"]).pack(padx=12, pady=8, anchor="w")

        body = tk.Frame(card, bg=c["card_bg"])
        body.pack(fill="x", padx=12, pady=10)

        return body

    def _add_field(self, parent, label_text, c, default="", tipo="entry", values=None):
        row = tk.Frame(parent, bg=c["card_bg"])
        row.pack(fill="x", pady=4)

        lbl = tk.Label(row, text=label_text, font=("Segoe UI", 10),
                       bg=c["card_bg"], fg=c["fg"], width=24, anchor="w")
        lbl.pack(side="left")

        if tipo == "entry":
            var = tk.StringVar(value=default)
            entry = ttk.Entry(row, textvariable=var, font=("Segoe UI", 10), width=20)
            entry.pack(side="left", padx=10)
            return var
        elif tipo == "int":
            var = tk.StringVar(value=str(default))
            entry = ttk.Entry(row, textvariable=var, font=("Segoe UI", 10), width=10)
            entry.pack(side="left", padx=10)
            return var
        elif tipo == "float":
            var = tk.StringVar(value=str(default))
            entry = ttk.Entry(row, textvariable=var, font=("Segoe UI", 10), width=10)
            entry.pack(side="left", padx=10)
            return var
        elif tipo == "check":
            var = tk.BooleanVar(value=default)
            chk = ttk.Checkbutton(row, variable=var)
            chk.pack(side="left", padx=10)
            return var
        elif tipo == "text":
            var = tk.StringVar(value=default)
            entry = ttk.Entry(row, textvariable=var, font=("Segoe UI", 10), width=40)
            entry.pack(side="left", padx=10, fill="x", expand=True)
            return var
        elif tipo == "password":
            var = tk.StringVar(value=default)
            entry = ttk.Entry(row, textvariable=var, font=("Segoe UI", 10), width=20, show="*")
            entry.pack(side="left", padx=10)
            return var
        elif tipo == "combobox":
            var = tk.StringVar(value=default)
            combo = ttk.Combobox(row, textvariable=var, values=values or [],
                                 font=("Segoe UI", 10), width=18, state="readonly")
            combo.pack(side="left", padx=10)
            return var

    def _tab_general(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  General  ")

        body = self._crear_card(tab, "Configuracion General", c)

        self._vars["moneda"] = self._add_field(body, "Simbolo de moneda:", c,
                                               self.config_mgr.get("moneda", "$"))

        self._vars["peso_unidad"] = self._add_field(body, "Unidad de peso:", c,
                                                    self.config_mgr.get("peso_unidad", "lb"))

        self._vars["prefijo_codigo"] = self._add_field(body, "Prefijo de codigos:", c,
                                                       self.config_mgr.get("prefijo_codigo", "MERC"))

        self._vars["paginacion_tamano"] = self._add_field(body, "Elementos por pagina:", c,
                                                          self.config_mgr.get("paginacion_tamano", 20), "int")

        self._vars["deudas_vencidas_dias"] = self._add_field(body, "Dias para deuda vencida:", c,
                                                             self.config_mgr.get("deudas_vencidas_dias", 7), "int")

        # Estados de envio
        body_estados = self._crear_card(tab, "Estados de Envio", c)

        tk.Label(body_estados, text="Estados disponibles (uno por linea):",
                 font=("Segoe UI", 9), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", pady=(0, 6))

        estados = self.config_mgr.get("estados_envio",
                                      ["Pendiente", "En camino", "Pagado", "Entregado", "Cancelado"])
        self._text_widgets["estados_envio"] = tk.Text(body_estados, height=6, width=40,
                                                      font=("Segoe UI", 10),
                                                      bg=c["input_bg"], fg=c["fg"])
        self._text_widgets["estados_envio"].pack(fill="x", padx=4)
        self._text_widgets["estados_envio"].insert("1.0", "\n".join(estados))

    def _tab_tarifas(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Tarifas  ")

        body = self._crear_card(tab, "Tarifas de envio", c)

        info = tk.Label(body, text="Configure las tarifas base para calculo de envios",
                        font=("Segoe UI", 9), bg=c["card_bg"], fg=c["card_header_fg"])
        info.pack(pady=(0, 10), anchor="w")

        self._vars["tarifa_precio_base"] = self._add_field(body, "Tarifa base:", c,
                                                           self.config_mgr.get("tarifa_precio_base", 0), "float")

        self._vars["tarifa_precio_por_lb"] = self._add_field(body, "Precio por libra:", c,
                                                             self.config_mgr.get("tarifa_precio_por_lb", 0), "float")

        calc_frame = tk.Frame(body, bg=c["accent_light"])
        calc_frame.pack(fill="x", pady=16, padx=8)

        tk.Label(calc_frame, text="Calculadora rapida",
                 font=("Segoe UI", 10, "bold"),
                 bg=c["accent_light"], fg=c["accent"]).pack(pady=(8, 4), anchor="w", padx=10)

        calc_inner = tk.Frame(calc_frame, bg=c["accent_light"])
        calc_inner.pack(fill="x", padx=10, pady=4)

        tk.Label(calc_inner, text="Peso (lb):", font=("Segoe UI", 10),
                 bg=c["accent_light"], fg=c["fg"]).pack(side="left")
        self._vars["calc_peso"] = tk.StringVar(value="10")
        ttk.Entry(calc_inner, textvariable=self._vars["calc_peso"], width=8,
                  font=("Segoe UI", 10)).pack(side="left", padx=8)

        tk.Label(calc_inner, text="Costo estimado:", font=("Segoe UI", 10),
                 bg=c["accent_light"], fg=c["fg"]).pack(side="left", padx=(16, 0))
        self.lbl_calc_result = tk.Label(calc_inner, text="$0.00",
                                        font=("Segoe UI", 10, "bold"),
                                        bg=c["accent_light"], fg=c["accent"])
        self.lbl_calc_result.pack(side="left", padx=8)

        btn_calc = tk.Button(calc_frame, text="Calcular",
                             font=("Segoe UI", 9),
                             bg=c["accent"], fg="white",
                             bd=0, relief="flat", padx=12, pady=4,
                             cursor="hand2", command=self._calcular_ejemplo)
        btn_calc.pack(pady=8, anchor="w", padx=10)

        # Zonas de envio
        body_zonas = self._crear_card(tab, "Zonas de Envio (Tarifas por destino)", c)

        tk.Label(body_zonas, text="Formato: destino | precio_por_lb (uno por linea)",
                 font=("Segoe UI", 9), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", pady=(0, 6))

        zonas = self.config_mgr.get("zonas_envio", {})
        zonas_text = "\n".join(f"{k} | {v}" for k, v in zonas.items()) if zonas else ""
        self._text_widgets["zonas_envio"] = tk.Text(body_zonas, height=8, width=45,
                                                    font=("Segoe UI", 10),
                                                    bg=c["input_bg"], fg=c["fg"])
        self._text_widgets["zonas_envio"].pack(fill="x", padx=4)
        self._text_widgets["zonas_envio"].insert("1.0", zonas_text)

    def _calcular_ejemplo(self):
        try:
            peso = float(self._vars["calc_peso"].get())
            base = float(self._vars["tarifa_precio_base"].get() or 0)
            por_lb = float(self._vars["tarifa_precio_por_lb"].get() or 0)
            total = base + (peso * por_lb)
            moneda = self._vars["moneda"].get() or "$"
            self.lbl_calc_result.config(text=f"{moneda}{total:,.2f}")
        except ValueError:
            self.lbl_calc_result.config(text="Valor invalido")

    def _tab_usuarios(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Usuarios  ")

        body = self._crear_card(tab, "Cajeros / Usuarios", c)

        tk.Label(body, text="Usuarios del sistema (uno por linea). Formato: nombre | PIN (opcional)",
                 font=("Segoe UI", 9), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", pady=(0, 6))

        cajeros = self.config_mgr.get("cajeros", ["Admin"])
        usuarios = self.config_mgr.get("usuarios", [])
        lineas = cajeros + usuarios
        self._text_widgets["usuarios"] = tk.Text(body, height=8, width=45,
                                                 font=("Segoe UI", 10),
                                                 bg=c["input_bg"], fg=c["fg"])
        self._text_widgets["usuarios"].pack(fill="x", padx=4)
        self._text_widgets["usuarios"].insert("1.0", "\n".join(lineas))

        tk.Label(body, text="Ejemplo: Juan Perez | 1234",
                 font=("Segoe UI", 8), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", pady=(6, 0))

    def _tab_apariencia(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Apariencia  ")

        body = self._crear_card(tab, "Tema y Visualizacion", c)

        self._vars["tema"] = self._add_field(body, "Tema:", c,
                                             self.config_mgr.get("tema", "light"), "combobox",
                                             values=["light", "dark"])

        self._vars["fuente_tamano"] = self._add_field(body, "Tamano de fuente:", c,
                                                      self.config_mgr.get("fuente_tamano", 10), "int")

        self._vars["sidebar_ancho"] = self._add_field(body, "Ancho del sidebar (px):", c,
                                                      self.config_mgr.get("sidebar_ancho", 200), "int")

        # Preview
        preview = self._crear_card(tab, "Vista previa del sidebar", c)
        preview_frame = tk.Frame(preview, bg=c["sidebar"], width=180, height=100)
        preview_frame.pack(padx=10, pady=10)
        preview_frame.pack_propagate(False)

        tk.Label(preview_frame, text="📦 Encomienda Jireh",
                 font=("Segoe UI", 12, "bold"),
                 bg=c["sidebar_active"], fg=c["sidebar_text"]).pack(fill="x", pady=10)
        tk.Label(preview_frame, text="Menu item activo",
                 font=("Segoe UI", 10),
                 bg=c["sidebar_active"], fg=c["sidebar_text"]).pack(fill="x", padx=10)
        tk.Label(preview_frame, text="Menu item",
                 font=("Segoe UI", 10),
                 bg=c["sidebar"], fg=c["sidebar_text"]).pack(fill="x", padx=10)

        tk.Label(preview, text="Nota: Los cambios de tema se aplican al guardar y reiniciar la app",
                 font=("Segoe UI", 8), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", padx=12, pady=4)

    def _tab_empresa(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Empresa  ")

        body = self._crear_card(tab, "Datos de la Empresa", c)

        self._vars["empresa_nombre"] = self._add_field(body, "Nombre:", c,
                                                       self.config_mgr.get("empresa_nombre", ""))

        self._vars["empresa_tel"] = self._add_field(body, "Telefono:", c,
                                                    self.config_mgr.get("empresa_tel", ""))

        self._vars["empresa_dir"] = self._add_field(body, "Direccion:", c,
                                                    self.config_mgr.get("empresa_dir", ""), "text")

        self._vars["empresa_ruc"] = self._add_field(body, "RUC / NIT:", c,
                                                    self.config_mgr.get("empresa_ruc", ""))

    def _tab_recibos(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Recibos  ")

        body = self._crear_card(tab, "Configuracion de Recibos", c)

        self._vars["recibo_notas"] = self._add_field(body, "Nota al pie del recibo:", c,
                                                     self.config_mgr.get("recibo_notas",
                                                                         "Gracias por su preferencia"), "text")

        self._vars["recibo_tamano_papel"] = self._add_field(body, "Tamano de papel:", c,
                                                            self.config_mgr.get("recibo_tamano_papel", "carta"),
                                                            "combobox", values=["carta", "ticket", "a4"])

        # Logo
        logo_row = tk.Frame(body, bg=c["card_bg"])
        logo_row.pack(fill="x", pady=6)

        tk.Label(logo_row, text="Ruta del logo:", font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"], width=24, anchor="w").pack(side="left")

        self._vars["recibo_logo_ruta"] = tk.StringVar(
            value=self.config_mgr.get("recibo_logo_ruta", ""))
        ttk.Entry(logo_row, textvariable=self._vars["recibo_logo_ruta"],
                  font=("Segoe UI", 10), width=25).pack(side="left", padx=10)

        tk.Button(logo_row, text="Buscar", font=("Segoe UI", 9),
                  bg=c["accent"], fg="white", bd=0, relief="flat",
                  padx=10, pady=4, cursor="hand2",
                  command=self._buscar_logo).pack(side="left")

        # Toggles
        checks_frame = self._crear_card(tab, "Campos del recibo", c)

        self._vars["recibo_mostrar_logo"] = tk.BooleanVar(
            value=self.config_mgr.get("recibo_mostrar_logo", True))
        tk.Label(checks_frame, text="Mostrar logo", font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"]).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(checks_frame, variable=self._vars["recibo_mostrar_logo"]).pack(anchor="w", padx=20)

        self._vars["recibo_mostrar_direccion"] = tk.BooleanVar(
            value=self.config_mgr.get("recibo_mostrar_direccion", True))
        tk.Label(checks_frame, text="Mostrar direccion", font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"]).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(checks_frame, variable=self._vars["recibo_mostrar_direccion"]).pack(anchor="w", padx=20)

        self._vars["recibo_mostrar_telefono"] = tk.BooleanVar(
            value=self.config_mgr.get("recibo_mostrar_telefono", True))
        tk.Label(checks_frame, text="Mostrar telefono", font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"]).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(checks_frame, variable=self._vars["recibo_mostrar_telefono"]).pack(anchor="w", padx=20)

        self._vars["recibo_mostrar_notas_internas"] = tk.BooleanVar(
            value=self.config_mgr.get("recibo_mostrar_notas_internas", False))
        tk.Label(checks_frame, text="Mostrar notas internas", font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"]).pack(anchor="w", padx=10, pady=2)
        ttk.Checkbutton(checks_frame, variable=self._vars["recibo_mostrar_notas_internas"]).pack(anchor="w", padx=20)

    def _buscar_logo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen de logo",
            filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Todos", "*.*")]
        )
        if ruta:
            self._vars["recibo_logo_ruta"].set(ruta)

    def _tab_diseno(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Diseños  ")

        # Título
        tk.Label(tab, text="Seleccionar Diseño del Recibo",
                 font=("Segoe UI", 12, "bold"),
                 bg=c["bg"], fg=c["accent"]).pack(pady=(15, 5), padx=20, anchor="w")

        # Frame principal
        main_frame = tk.Frame(tab, bg=c["bg"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Panel izquierdo: selector de diseño
        left_frame = tk.Frame(main_frame, bg=c["bg"], width=250)
        left_frame.pack(side="left", fill="y", padx=(0, 10))

        # Card de selección
        card = self._crear_card(left_frame, "Diseño del Recibo", c)

        # Importar diseños disponibles
        try:
            from modules.imprimir import DISENOS_DISPONIBLES
        except:
            DISENOS_DISPONIBLES = {}

        # Variable para el diseño seleccionado
        self._vars["recibo_diseno"] = tk.StringVar(
            value=self.config_mgr.get("recibo_diseno", "clasico"))

        # Botones de selección de diseño
        for key, info in DISENOS_DISPONIBLES.items():
            frame_diseno = tk.Frame(card, bg=c["card_bg"])
            frame_diseno.pack(fill="x", pady=4)

            # Color indicator
            color_hex = info.get("color_principal", "#0f6e56")
            color_indicator = tk.Canvas(frame_diseno, width=20, height=20, 
                                       bg=color_hex, highlightthickness=1)
            color_indicator.pack(side="left", padx=(10, 5))

            # Radio button
            rb = tk.Radiobutton(frame_diseno, text=info.get("nombre", key),
                               variable=self._vars["recibo_diseno"],
                               value=key, font=("Segoe UI", 10),
                               bg=c["card_bg"], fg=c["fg"],
                               selectcolor=c["card_bg"],
                               activebackground=c["card_bg"],
                               activeforeground=c["fg"],
                               command=self._actualizar_preview_diseno)
            rb.pack(side="left", fill="x", expand=True)

            # Descripción
            tk.Label(frame_diseno, text=info.get("desc", ""),
                    font=("Segoe UI", 8), bg=c["card_bg"],
                    fg=c["card_header_fg"]).pack(side="right", padx=10)

        # Panel derecho: vista previa
        right_frame = tk.Frame(main_frame, bg=c["bg"])
        right_frame.pack(side="right", fill="both", expand=True)

        # Card de vista previa
        preview_card = self._crear_card(right_frame, "Vista Previa", c)

        # Canvas para la vista previa
        self.preview_canvas = tk.Canvas(preview_card, bg="white", 
                                       highlightthickness=1,
                                       highlightbackground="#cccccc")
        self.preview_canvas.pack(fill="both", expand=True, padx=10, pady=10)

        # Botón de actualizar
        btn_frame = tk.Frame(preview_card, bg=c["card_bg"])
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        tk.Button(btn_frame, text="Actualizar Vista Previa",
                 font=("Segoe UI", 10),
                 bg=c["accent"], fg="white",
                 bd=0, relief="flat",
                 padx=15, pady=6, cursor="hand2",
                 command=self._actualizar_preview_diseno).pack(side="right")

        # Cargar preview inicial
        self._actualizar_preview_diseno()

    def _actualizar_preview_diseno(self):
        """Actualiza la vista previa del diseño seleccionado."""
        try:
            import tkinter.messagebox as messagebox
            from PIL import Image, ImageTk
        except ImportError:
            return

        diseno = self._vars.get("recibo_diseno")
        if diseno:
            diseno = diseno.get()
        else:
            diseno = "clasico"

        # Limpiar canvas
        self.preview_canvas.delete("all")

        # Obtener tamaño del canvas
        width = self.preview_canvas.winfo_width()
        height = self.preview_canvas.winfo_height()

        if width < 10 or height < 10:
            # Canvas no está listo, usar tamaño por defecto
            width, height = 400, 500

        # Generar imagen de vista previa (usando datos de ejemplo)
        try:
            from modules.imprimir import DISENOS_DISPONIBLES, _estilos_diseno
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.pdfgen import canvas as rl_canvas
            from io import BytesIO
            import tempfile

            # Crear PDF temporal
            temp_file = os.path.join(tempfile.gettempdir(), "preview_temp.pdf")
            doc = SimpleDocTemplate(temp_file, pagesize=A4,
                                   leftMargin=1.5*cm, rightMargin=1.5*cm,
                                   topMargin=1*cm, bottomMargin=1*cm)

            # Estilos del diseño
            st = _estilos_diseno(diseno)
            colores = DISENOS_DISPONIBLES.get(diseno, DISENOS_DISPONIBLES["clasico"])
            c1 = colors.HexColor(colores["color_principal"])

            ancho_util = A4[0] - 3*cm
            story = []

            # Encabezado
            if diseno == "minimalista":
                story.append(Paragraph("Encomienda Jireh", st["titulo"]))
                story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#888888"), spaceAfter=8))
            elif diseno == "elegante":
                hdr_data = [[Paragraph("<b>Encomienda Jireh</b>",
                             ParagraphStyle("hdr_e", fontName="Helvetica-Bold", fontSize=16,
                                           textColor=colors.white, alignment=TA_CENTER))]]
                hdr_t = Table(hdr_data, colWidths=[ancho_util])
                hdr_t.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,-1), c1),
                    ("TOPPADDING", (0,0), (-1,-1), 12),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 12),
                ]))
                story.append(hdr_t)
                story.append(Spacer(1, 8))
            elif diseno == "moderno":
                story.append(Paragraph("📦 Encomienda Jireh", st["titulo"]))
                story.append(HRFlowable(width="100%", thickness=3, color=c1, spaceAfter=8))
            else:  # clasico
                story.append(Paragraph("📦 Encomienda Jireh", st["titulo"]))
                story.append(Paragraph("Envíos rápidos y seguros", st["subtitulo"]))
                story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0f6e56"), spaceAfter=8))

            # Datos de ejemplo
            story.append(Paragraph("ENV-2024-001", st["codigo"]))
            story.append(Spacer(1, 10))

            # Remitente/Destinatario
            personas_data = [[
                [Paragraph("ENTREGA", st["seccion_verde"]),
                 Paragraph("<b>Juan Pérez</b>", st["bold"])],
                [Paragraph("RECIBE", st["seccion_verde"]),
                 Paragraph("<b>Maria López</b>", st["bold"])],
            ]]
            personas_t = Table(personas_data, colWidths=[ancho_util/2, ancho_util/2])
            personas_t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#e1f5ee")),
                ("BACKGROUND", (1,0), (1,-1), colors.HexColor("#e6f1fb")),
                ("BOX", (0,0), (0,-1), 0.5, colors.HexColor("#0f6e56")),
                ("BOX", (1,0), (1,-1), 0.5, colors.HexColor("#0c447c")),
                ("LEFTPADDING", (0,0), (-1,-1), 8),
                ("TOPPADDING", (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(personas_t)
            story.append(Spacer(1, 15))

            # Artículos de ejemplo
            story.append(Paragraph("ARTÍCULOS", st["seccion"]))
            arts_data = [
                [Paragraph("<b>Descripción</b>", st["bold"]),
                 Paragraph("<b>Peso</b>", st["bold"]),
                 Paragraph("<b>Importe</b>", st["bold"])],
                [Paragraph("Caja electrónicos", st["normal"]),
                 Paragraph("5.00 lb", st["normal"]),
                 Paragraph("<b>$50.00</b>", st["bold_verde"])],
            ]
            arts_t = Table(arts_data, colWidths=[ancho_util-6*cm, 3*cm, 3*cm])
            arts_t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0f6e56")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f9f9f6")]),
                ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0d8")),
                ("LEFTPADDING", (0,0), (-1,-1), 8),
                ("TOPPADDING", (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(arts_t)
            story.append(Spacer(1, 15))

            # Total
            tot_data = [
                [Paragraph("<b>Total encomienda</b>", st["bold"]),
                 Paragraph("<b>$50.00</b>", st["monto_total"])],
            ]
            tot_t = Table(tot_data, colWidths=[ancho_util-4*cm, 4*cm], hAlign="RIGHT")
            tot_t.setStyle(TableStyle([
                ("LINEABOVE", (0,0), (-1,0), 1.5, colors.HexColor("#0f6e56")),
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e1f5ee")),
                ("ALIGN", (1,0), (1,0), "RIGHT"),
                ("LEFTPADDING", (0,0), (-1,-1), 10),
                ("RIGHTPADDING", (0,0), (-1,-1), 10),
                ("TOPPADDING", (0,0), (-1,-1), 8),
                ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ]))
            story.append(tot_t)

            # Pie
            story.append(Spacer(1, 25))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0d8"), spaceAfter=6))
            story.append(Paragraph(f"Vista previa - Diseño: {colores.get('nombre', diseno)}", st["pie"]))

            doc.build(story)

            # Convertir PDF a imagen para mostrar en canvas
            # Nota: Para simplificar, mostramos un placeholder
            self.preview_canvas.create_text(width/2, height/2 - 20,
                                          text=f"Diseño: {colores.get('nombre', diseno)}",
                                          font=("Helvetica", 14, "bold"),
                                          fill=colores.get("color_principal", "#0f6e56"))
            self.preview_canvas.create_text(width/2, height/2 + 10,
                                          text=colores.get("desc", ""),
                                          font=("Helvetica", 10),
                                          fill="#666666")
            self.preview_canvas.create_text(width/2, height/2 + 40,
                                          text="Vista previa generada",
                                          font=("Helvetica", 9),
                                          fill="#999999")

        except Exception as e:
            self.preview_canvas.create_text(width/2, height/2,
                                          text=f"Error: {str(e)}",
                                          font=("Helvetica", 10),
                                          fill="#ff0000")

    def _tab_alertas(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Alertas  ")

        body = self._crear_card(tab, "Notificaciones y Sonidos", c)

        self._vars["sonido_crear_envio"] = tk.BooleanVar(
            value=self.config_mgr.get("sonido_crear_envio", True))
        tk.Label(body, text="Sonido al crear envio", font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"]).pack(anchor="w", padx=10, pady=4)
        ttk.Checkbutton(body, variable=self._vars["sonido_crear_envio"]).pack(anchor="w", padx=20)

        self._vars["alerta_deudas_activa"] = tk.BooleanVar(
            value=self.config_mgr.get("alerta_deudas_activa", True))
        tk.Label(body, text="Alerta de deudas vencidas al iniciar", font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"]).pack(anchor="w", padx=10, pady=4)
        ttk.Checkbutton(body, variable=self._vars["alerta_deudas_activa"]).pack(anchor="w", padx=20)

        self._vars["alerta_listos_recoger"] = tk.BooleanVar(
            value=self.config_mgr.get("alerta_listos_recoger", True))
        tk.Label(body, text="Notificar envios listos para recoger", font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"]).pack(anchor="w", padx=10, pady=4)
        ttk.Checkbutton(body, variable=self._vars["alerta_listos_recoger"]).pack(anchor="w", padx=20)

        # Test button
        test_frame = tk.Frame(body, bg=c["card_bg"])
        test_frame.pack(fill="x", pady=12)

        tk.Button(test_frame, text="Probar sonido", font=("Segoe UI", 9),
                  bg=c["accent_light"], fg=c["accent"],
                  bd=0, relief="flat", padx=12, pady=6, cursor="hand2",
                  command=lambda: self.app.bell()).pack(side="left")

    def _tab_reportes(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Reportes  ")

        body = self._crear_card(tab, "Configuracion de Reportes", c)

        self._vars["reportes_rango_default"] = self._add_field(body, "Rango por defecto:", c,
                                                               self.config_mgr.get("reportes_rango_default", "hoy"),
                                                               "combobox", values=["hoy", "semana", "mes", "personalizado"])

        self._vars["reportes_exportacion_default"] = self._add_field(body, "Formato de exportacion:", c,
                                                                     self.config_mgr.get("reportes_exportacion_default", "csv"),
                                                                     "combobox", values=["csv", "pdf"])

    def _tab_seguridad(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Seguridad  ")

        # ── Login ────────────────────────────────────────────────────────────
        body_login = self._crear_card(tab, "Login de Usuarios", c)

        self._vars["login_activo"] = tk.BooleanVar(
            value=self.config_mgr.get("login_activo", True))
        tk.Label(body_login, text="Activar login al iniciar la aplicación",
                 font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"]).pack(anchor="w", padx=10, pady=4)
        ttk.Checkbutton(body_login, variable=self._vars["login_activo"]).pack(anchor="w", padx=20)

        tk.Label(body_login, text="Si se desactiva, la app entra directamente sin pedir usuario/contraseña",
                 font=("Segoe UI", 8), bg=c["card_bg"], fg="#888780").pack(anchor="w", padx=20, pady=(0, 4))

        # Gestión de usuarios
        btn_frame = tk.Frame(body_login, bg=c["card_bg"])
        btn_frame.pack(fill="x", padx=10, pady=(8, 4))
        tk.Button(btn_frame, text="👤  Gestionar usuarios",
                  font=("Segoe UI", 9, "bold"),
                  bg=c["accent"], fg="#ffffff", bd=0, padx=14, pady=6,
                  cursor="hand2",
                  command=lambda: self._gestionar_usuarios()).pack(side="left")

        # ── PIN ──────────────────────────────────────────────────────────────
        body_pin = self._crear_card(tab, "PIN de Acceso (adicional)", c)

        self._vars["pin_acceso_activo"] = tk.BooleanVar(
            value=self.config_mgr.get("pin_acceso_activo", False))
        tk.Label(body_pin, text="Activar PIN de acceso al iniciar", font=("Segoe UI", 10),
                 bg=c["card_bg"], fg=c["fg"]).pack(anchor="w", padx=10, pady=4)
        ttk.Checkbutton(body_pin, variable=self._vars["pin_acceso_activo"]).pack(anchor="w", padx=20)

        self._vars["pin_acceso"] = self._add_field(body_pin, "PIN (4-6 digitos):", c,
                                                   self.config_mgr.get("pin_acceso", ""), "password")

        # Timeout
        body_timeout = self._crear_card(tab, "Timeout de Sesion", c)

        tk.Label(body_timeout, text="Cerrar sesion tras inactividad (0 = desactivado)",
                 font=("Segoe UI", 9), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", pady=(0, 6))

        self._vars["timeout_sesion"] = self._add_field(body_timeout, "Minutos de inactividad:", c,
                                                       self.config_mgr.get("timeout_sesion", 0), "int")

        tk.Label(body_timeout, text="Se cierra la app si no hay actividad por el tiempo configurado",
                 font=("Segoe UI", 8), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", pady=(6, 0))

    def _tab_listas(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Listas  ")

        body_dest = self._crear_card(tab, "Destinos USA", c)

        tk.Label(body_dest, text="Destinos disponibles (uno por linea):",
                 font=("Segoe UI", 9), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", pady=(0, 6))

        destinos = self.config_mgr.get("destinos_usa", ["Miami", "Orlando", "Houston", "Los Angeles"])
        self._text_widgets["destinos_usa"] = tk.Text(body_dest, height=8, width=40,
                                                     font=("Segoe UI", 10),
                                                     bg=c["input_bg"], fg=c["fg"])
        self._text_widgets["destinos_usa"].pack(fill="x", padx=4)
        self._text_widgets["destinos_usa"].insert("1.0", "\n".join(destinos))

        body_cat = self._crear_card(tab, "Categorias de Costo", c)

        tk.Label(body_cat, text="Categorias para costos de viaje (una por linea):",
                 font=("Segoe UI", 9), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", pady=(0, 6))

        categorias = self.config_mgr.get("categorias_costo",
                                         ["Transporte", "Combustible", "Mantenimiento", "Salarios", "Otros"])
        self._text_widgets["categorias_costo"] = tk.Text(body_cat, height=6, width=40,
                                                         font=("Segoe UI", 10),
                                                         bg=c["input_bg"], fg=c["fg"])
        self._text_widgets["categorias_costo"].pack(fill="x", padx=4)
        self._text_widgets["categorias_costo"].insert("1.0", "\n".join(categorias))

        body_pago = self._crear_card(tab, "Tipos de Pago", c)

        tk.Label(body_pago, text="Metodos de pago disponibles (uno por linea):",
                 font=("Segoe UI", 9), bg=c["card_bg"], fg=c["card_header_fg"]).pack(anchor="w", pady=(0, 6))

        tipos = self.config_mgr.get("tipos_pago",
                                    ["Efectivo", "Transferencia", "Tarjeta"])
        self._text_widgets["tipos_pago"] = tk.Text(body_pago, height=6, width=40,
                                                   font=("Segoe UI", 10),
                                                   bg=c["input_bg"], fg=c["fg"])
        self._text_widgets["tipos_pago"].pack(fill="x", padx=4)
        self._text_widgets["tipos_pago"].insert("1.0", "\n".join(tipos))

    def _tab_respaldo(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Respaldo  ")

        body = self._crear_card(tab, "Configuracion de Respaldo", c)

        self._vars["backup_dir"] = self._add_field(body, "Directorio de respaldos:", c,
                                                   self.config_mgr.get("backup_dir", "backups"))

        self._vars["backup_max"] = self._add_field(body, "Maximo respaldos:", c,
                                                   self.config_mgr.get("backup_max", 30), "int")

        acciones = self._crear_card(tab, "Acciones", c)

        btn_frame = tk.Frame(acciones, bg=c["card_bg"])
        btn_frame.pack(fill="x")

        tk.Button(btn_frame, text="Respaldar ahora",
                  font=("Segoe UI", 10),
                  bg=c["accent"], fg="white",
                  bd=0, relief="flat", padx=16, pady=8,
                  cursor="hand2", command=self._respaldar_ahora).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Restaurar seleccionado",
                  font=("Segoe UI", 10),
                  bg=c["warning_bg"], fg=c["warning_fg"],
                  bd=0, relief="flat", padx=16, pady=8,
                  cursor="hand2", command=self._restaurar_seleccionado).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Cargar archivo .db",
                  font=("Segoe UI", 10),
                  bg="#e6f1fb", fg="#0c447c",
                  bd=0, relief="flat", padx=16, pady=8,
                  cursor="hand2", command=self._cargar_archivo_db).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Cambiar directorio",
                  font=("Segoe UI", 10),
                  bg=c["secondary_bg"] if "secondary_bg" in c else c["accent_light"],
                  fg=c["accent"],
                  bd=0, relief="flat", padx=16, pady=8,
                  cursor="hand2", command=self._cambiar_dir_backup).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Eliminar seleccionado",
                  font=("Segoe UI", 10),
                  bg=c["danger_bg"], fg=c["danger_fg"],
                  bd=0, relief="flat", padx=16, pady=8,
                  cursor="hand2", command=self._eliminar_seleccionado).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Recalcular pesos",
                  font=("Segoe UI", 10),
                  bg="#e1f5ee", fg="#085041",
                  bd=0, relief="flat", padx=16, pady=8,
                  cursor="hand2", command=self._recalcular_pesos).pack(side="left", padx=4)

        info_frame = self._crear_card(tab, "Respaldos existentes", c)

        self._tree_widgets["backups"] = ttk.Treeview(info_frame, columns=("nombre", "fecha", "tamano"),
                                                     show="headings", height=6)
        self._tree_widgets["backups"].heading("nombre", text="Archivo")
        self._tree_widgets["backups"].heading("fecha", text="Fecha")
        self._tree_widgets["backups"].heading("tamano", text="Tamano")

        self._tree_widgets["backups"].column("nombre", width=250)
        self._tree_widgets["backups"].column("fecha", width=150)
        self._tree_widgets["backups"].column("tamano", width=100)

        self._tree_widgets["backups"].pack(fill="x", padx=4, pady=4)
        self._tree_widgets["backups"].bind("<Double-1>", lambda e: self._restaurar_seleccionado())

        self._cargar_backups_list()

    def _cargar_backups_list(self):
        tree = self._tree_widgets.get("backups")
        if not tree:
            return
        for item in tree.get_children():
            tree.delete(item)

        backup_dir = self._vars.get("backup_dir")
        dir_val = backup_dir.get() if backup_dir else "backups"
        backup_dir_val = dir_val or "backups"

        if os.path.exists(backup_dir_val):
            archivos = sorted(os.listdir(backup_dir_val), reverse=True)
            max_backups = int(self._vars["backup_max"].get()) if "backup_max" in self._vars else 30
            for arch in archivos[:max_backups]:
                ruta = os.path.join(backup_dir_val, arch)
                stat = os.stat(ruta)
                fecha = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                tamano = f"{stat.st_size / 1024:.1f} KB"
                tree.insert("", "end", values=(arch, fecha, tamano))

    def _respaldar_ahora(self):
        try:
            ruta = self.db.backup_db()
            self._cargar_backups_list()
            messagebox.showinfo("Respaldo", f"Base de datos respaldada en:\n{ruta}")
            logger.info("Respaldo manual desde configuracion: %s", ruta)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo respaldar:\n{e}")

    def _cambiar_dir_backup(self):
        directorio = filedialog.askdirectory(
            title="Seleccionar directorio de respaldos",
            initialdir=self._vars.get("backup_dir", tk.StringVar(value="backups")).get()
        )
        if directorio:
            self._vars["backup_dir"].set(directorio)

    def _restaurar_seleccionado(self):
        tree = self._tree_widgets.get("backups")
        if not tree:
            return
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Restaurar", "Selecciona un respaldo de la lista.")
            return

        item = tree.item(seleccion[0])
        nombre_archivo = item["values"][0]

        backup_dir = self._vars.get("backup_dir")
        dir_val = backup_dir.get() if backup_dir else "backups"
        backup_dir_val = dir_val or "backups"
        ruta_backup = os.path.join(backup_dir_val, nombre_archivo)

        if not os.path.exists(ruta_backup):
            messagebox.showerror("Error", f"No se encontro el archivo:\n{ruta_backup}")
            return

        if not messagebox.askyesno("Restaurar respaldo",
                                    f"Se reemplazara la base de datos actual con:\n{nombre_archivo}\n\n"
                                    f"Se recomienda hacer un respaldo antes.\n\n"
                                    f"¿Desea continuar?"):
            return

        try:
            self.db.close()
            import shutil
            shutil.copy2(ruta_backup, self.db.ruta)
            self.db.__init__(self.db.ruta)
            self._cargar_backups_list()
            messagebox.showinfo("Restaurado",
                                f"Base de datos restaurada desde:\n{nombre_archivo}\n\n"
                                f"La aplicacion se reiniciara para aplicar los cambios.")
            self.app.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo restaurar el respaldo:\n{e}")

    def _cargar_archivo_db(self):
        """Permite cargar una base de datos desde cualquier archivo .db"""
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo de base de datos",
            filetypes=[("Base de datos", "*.db"), ("Todos los archivos", "*.*")],
            initialdir=get_base_dir()
        )
        if not ruta:
            return

        if not os.path.exists(ruta):
            messagebox.showerror("Error", f"No se encontro el archivo:\n{ruta}")
            return

        if not messagebox.askyesno("Cargar base de datos",
                                    f"Se reemplazara la base de datos actual con:\n{os.path.basename(ruta)}\n\n"
                                    "Se hara un respaldo automatico antes.\n\n"
                                    "¿Desea continuar?"):
            return

        try:
            # Hacer respaldo antes de restaurar
            self.db.backup_db()
            # Restaurar
            self.db.restore_db(ruta)
            self._cargar_backups_list()
            messagebox.showinfo("Cargado",
                                f"Base de datos cargada desde:\n{os.path.basename(ruta)}\n\n"
                                "Pesos recalculados automaticamente.\n"
                                "La aplicacion se reiniciara para aplicar los cambios.")
            self.app.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la base de datos:\n{e}")

    def _recalcular_pesos(self):
        """Recalcula el peso_total de todos los envios."""
        if not messagebox.askyesno("Recalcular pesos",
                                    "Se recalculara el peso total de todos los envios.\n\n"
                                    "¿Desea continuar?"):
            return
        try:
            total = self.db.recalcular_pesos()
            messagebox.showinfo("Pesos recalculados",
                                f"Se recalcularon los pesos de {total} envios.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron recalcular los pesos:\n{e}")

    def _eliminar_seleccionado(self):
        tree = self._tree_widgets.get("backups")
        if not tree:
            return
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Eliminar", "Selecciona un respaldo de la lista.")
            return

        item = tree.item(seleccion[0])
        nombre_archivo = item["values"][0]

        backup_dir = self._vars.get("backup_dir")
        dir_val = backup_dir.get() if backup_dir else "backups"
        backup_dir_val = dir_val or "backups"
        ruta_backup = os.path.join(backup_dir_val, nombre_archivo)

        if not os.path.exists(ruta_backup):
            messagebox.showerror("Error", f"No se encontro el archivo:\n{ruta_backup}")
            return

        if not messagebox.askyesno("Eliminar respaldo",
                                    f"¿Eliminar permanentemente?\n{nombre_archivo}"):
            return

        try:
            os.remove(ruta_backup)
            self._cargar_backups_list()
            messagebox.showinfo("Eliminado", f"Respaldo eliminado:\n{nombre_archivo}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}")

    def _gestionar_usuarios(self):
        from modules.login import UserManagementDialog
        UserManagementDialog(self, self.db)

    def _guardar_todo(self):
        try:
            self.config_mgr.set("moneda", self._vars["moneda"].get().strip())
            self.config_mgr.set("peso_unidad", self._vars["peso_unidad"].get().strip())
            self.config_mgr.set("prefijo_codigo", self._vars["prefijo_codigo"].get().strip())
            self.config_mgr.set("paginacion_tamano", int(self._vars["paginacion_tamano"].get() or 20))
            self.config_mgr.set("deudas_vencidas_dias", int(self._vars["deudas_vencidas_dias"].get() or 7))

            self.config_mgr.set("tarifa_precio_base", float(self._vars["tarifa_precio_base"].get() or 0))
            self.config_mgr.set("tarifa_precio_por_lb", float(self._vars["tarifa_precio_por_lb"].get() or 0))

            # Zonas de envio
            zonas_text = self._text_widgets["zonas_envio"].get("1.0", "end-1c")
            zonas = {}
            for linea in zonas_text.split("\n"):
                linea = linea.strip()
                if "|" in linea:
                    partes = linea.split("|")
                    if len(partes) == 2:
                        destino = partes[0].strip()
                        try:
                            precio = float(partes[1].strip())
                            zonas[destino] = precio
                        except ValueError:
                            pass
            self.config_mgr.set("zonas_envio", zonas)

            self.config_mgr.set("empresa_nombre", self._vars["empresa_nombre"].get().strip())
            self.config_mgr.set("empresa_tel", self._vars["empresa_tel"].get().strip())
            self.config_mgr.set("empresa_dir", self._vars["empresa_dir"].get().strip())
            self.config_mgr.set("empresa_ruc", self._vars["empresa_ruc"].get().strip())

            self.config_mgr.set("tema", self._vars["tema"].get())
            self.config_mgr.set("fuente_tamano", int(self._vars["fuente_tamano"].get() or 10))
            self.config_mgr.set("sidebar_ancho", int(self._vars["sidebar_ancho"].get() or 200))

            self.config_mgr.set("recibo_notas", self._vars["recibo_notas"].get().strip())
            self.config_mgr.set("recibo_logo_ruta", self._vars["recibo_logo_ruta"].get().strip())
            self.config_mgr.set("recibo_tamano_papel", self._vars["recibo_tamano_papel"].get())
            self.config_mgr.set("recibo_mostrar_logo", self._vars["recibo_mostrar_logo"].get())
            self.config_mgr.set("recibo_mostrar_direccion", self._vars["recibo_mostrar_direccion"].get())
            self.config_mgr.set("recibo_mostrar_telefono", self._vars["recibo_mostrar_telefono"].get())
            self.config_mgr.set("recibo_mostrar_notas_internas", self._vars["recibo_mostrar_notas_internas"].get())

            self.config_mgr.set("sonido_crear_envio", self._vars["sonido_crear_envio"].get())
            self.config_mgr.set("alerta_deudas_activa", self._vars["alerta_deudas_activa"].get())
            self.config_mgr.set("alerta_listos_recoger", self._vars["alerta_listos_recoger"].get())

            self.config_mgr.set("reportes_rango_default", self._vars["reportes_rango_default"].get())
            self.config_mgr.set("reportes_exportacion_default", self._vars["reportes_exportacion_default"].get())

            pin = self._vars["pin_acceso"].get().strip()
            self.config_mgr.set("pin_acceso", pin)
            self.config_mgr.set("pin_acceso_activo", self._vars["pin_acceso_activo"].get())
            self.config_mgr.set("login_activo", self._vars["login_activo"].get())
            self.config_mgr.set("timeout_sesion", int(self._vars["timeout_sesion"].get() or 0))

            # Listas
            estados = [l.strip() for l in self._text_widgets["estados_envio"].get("1.0", "end-1c").split("\n") if l.strip()]
            self.config_mgr.set("estados_envio", estados)

            destinos = [l.strip() for l in self._text_widgets["destinos_usa"].get("1.0", "end-1c").split("\n") if l.strip()]
            self.config_mgr.set("destinos_usa", destinos)

            categorias = [l.strip() for l in self._text_widgets["categorias_costo"].get("1.0", "end-1c").split("\n") if l.strip()]
            self.config_mgr.set("categorias_costo", categorias)

            tipos_pago = [l.strip() for l in self._text_widgets["tipos_pago"].get("1.0", "end-1c").split("\n") if l.strip()]
            self.config_mgr.set("tipos_pago", tipos_pago)

            # Usuarios
            usuarios_text = self._text_widgets["usuarios"].get("1.0", "end-1c")
            cajeros = []
            usuarios_extra = []
            for linea in usuarios_text.split("\n"):
                linea = linea.strip()
                if linea:
                    if "|" in linea:
                        usuarios_extra.append(linea)
                    else:
                        cajeros.append(linea)
            self.config_mgr.set("cajeros", cajeros)
            self.config_mgr.set("usuarios", usuarios_extra)

            # Respaldo
            self.config_mgr.set("backup_dir", self._vars["backup_dir"].get().strip())
            self.config_mgr.set("backup_max", int(self._vars["backup_max"].get() or 30))

            if self.config_mgr.guardar():
                messagebox.showinfo("Configuracion", "Configuracion guardada correctamente.\nAlgunos cambios requieren reiniciar la aplicacion.")
                logger.info("Configuracion guardada exitosamente")
                self._aplicar_tema()
            else:
                messagebox.showerror("Error", "No se pudo guardar la configuracion")

        except ValueError as e:
            messagebox.showerror("Error de validacion", f"Valor invalido:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar:\n{e}")

    def _aplicar_tema(self):
        tema = self.config_mgr.get("tema", "light")
        if tema == "dark" and not self.app.tema_oscuro:
            self.app._alternar_tema()
        elif tema == "light" and self.app.tema_oscuro:
            self.app._alternar_tema()

        ancho = self.config_mgr.get("sidebar_ancho", 200)
        self.app.sidebar.configure(width=ancho)

    def _resetear(self):
        if messagebox.askyesno("Restablecer",
                               "Se perderan todos los cambios y se restauraran los valores por defecto.\nContinuar?"):
            self.config_mgr.reset_defaults()
            self._recargar_ui()
            messagebox.showinfo("Restablecido", "Configuracion restablecida a valores por defecto")

    def _recargar_ui(self):
        self._vars["moneda"].set(self.config_mgr.get("moneda", "$"))
        self._vars["peso_unidad"].set(self.config_mgr.get("peso_unidad", "lb"))
        self._vars["prefijo_codigo"].set(self.config_mgr.get("prefijo_codigo", "MERC"))
        self._vars["paginacion_tamano"].set(str(self.config_mgr.get("paginacion_tamano", 20)))
        self._vars["deudas_vencidas_dias"].set(str(self.config_mgr.get("deudas_vencidas_dias", 7)))
        self._vars["tarifa_precio_base"].set(str(self.config_mgr.get("tarifa_precio_base", 0)))
        self._vars["tarifa_precio_por_lb"].set(str(self.config_mgr.get("tarifa_precio_por_lb", 0)))
        self._vars["empresa_nombre"].set(self.config_mgr.get("empresa_nombre", ""))
        self._vars["empresa_tel"].set(self.config_mgr.get("empresa_tel", ""))
        self._vars["empresa_dir"].set(self.config_mgr.get("empresa_dir", ""))
        self._vars["empresa_ruc"].set(self.config_mgr.get("empresa_ruc", ""))
        self._vars["tema"].set(self.config_mgr.get("tema", "light"))
        self._vars["fuente_tamano"].set(str(self.config_mgr.get("fuente_tamano", 10)))
        self._vars["sidebar_ancho"].set(str(self.config_mgr.get("sidebar_ancho", 200)))
        self._vars["recibo_notas"].set(self.config_mgr.get("recibo_notas", "Gracias por su preferencia"))
        self._vars["recibo_logo_ruta"].set(self.config_mgr.get("recibo_logo_ruta", ""))
        self._vars["recibo_tamano_papel"].set(self.config_mgr.get("recibo_tamano_papel", "carta"))
        self._vars["recibo_mostrar_logo"].set(self.config_mgr.get("recibo_mostrar_logo", True))
        self._vars["recibo_mostrar_direccion"].set(self.config_mgr.get("recibo_mostrar_direccion", True))
        self._vars["recibo_mostrar_telefono"].set(self.config_mgr.get("recibo_mostrar_telefono", True))
        self._vars["recibo_mostrar_notas_internas"].set(self.config_mgr.get("recibo_mostrar_notas_internas", False))
        self._vars["sonido_crear_envio"].set(self.config_mgr.get("sonido_crear_envio", True))
        self._vars["alerta_deudas_activa"].set(self.config_mgr.get("alerta_deudas_activa", True))
        self._vars["alerta_listos_recoger"].set(self.config_mgr.get("alerta_listos_recoger", True))
        self._vars["reportes_rango_default"].set(self.config_mgr.get("reportes_rango_default", "hoy"))
        self._vars["reportes_exportacion_default"].set(self.config_mgr.get("reportes_exportacion_default", "csv"))
        self._vars["pin_acceso"].set(self.config_mgr.get("pin_acceso", ""))
        self._vars["pin_acceso_activo"].set(self.config_mgr.get("pin_acceso_activo", False))
        self._vars["login_activo"].set(self.config_mgr.get("login_activo", True))
        self._vars["timeout_sesion"].set(str(self.config_mgr.get("timeout_sesion", 0)))
        self._vars["backup_dir"].set(self.config_mgr.get("backup_dir", "backups"))
        self._vars["backup_max"].set(str(self.config_mgr.get("backup_max", 30)))

        self._text_widgets["estados_envio"].delete("1.0", "end")
        self._text_widgets["estados_envio"].insert("1.0", "\n".join(self.config_mgr.get("estados_envio", [])))

        self._text_widgets["destinos_usa"].delete("1.0", "end")
        self._text_widgets["destinos_usa"].insert("1.0", "\n".join(self.config_mgr.get("destinos_usa", [])))

        self._text_widgets["categorias_costo"].delete("1.0", "end")
        self._text_widgets["categorias_costo"].insert("1.0", "\n".join(self.config_mgr.get("categorias_costo", [])))

        self._text_widgets["tipos_pago"].delete("1.0", "end")
        self._text_widgets["tipos_pago"].insert("1.0", "\n".join(self.config_mgr.get("tipos_pago", [])))

        self._text_widgets["usuarios"].delete("1.0", "end")
        cajeros = self.config_mgr.get("cajeros", ["Admin"])
        usuarios = self.config_mgr.get("usuarios", [])
        self._text_widgets["usuarios"].insert("1.0", "\n".join(cajeros + usuarios))

        zonas = self.config_mgr.get("zonas_envio", {})
        zonas_text = "\n".join(f"{k} | {v}" for k, v in zonas.items()) if zonas else ""
        self._text_widgets["zonas_envio"].delete("1.0", "end")
        self._text_widgets["zonas_envio"].insert("1.0", zonas_text)

        self._cargar_backups_list()

    def refresh(self):
        self._recargar_ui()
