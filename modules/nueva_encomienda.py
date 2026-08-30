import tkinter as tk
import os
from datetime import datetime
from tkinter import ttk, messagebox

try:
    from modules.imprimir import imprimir_recibo, imprimir_recibo_termico
    _IMPRIMIR_OK = True
except ImportError:
    _IMPRIMIR_OK = False

try:
    from modules.config import PRECIO_LB
except ImportError:
    PRECIO_LB = 10


class NuevaEncomiendaFrame(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#f5f5f0")
        self.db = db
        self.app = app
        self.filas_articulos = []
        self.filas_varios = []
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#ffffff", pady=14)
        header.pack(fill="x")
        tk.Label(header, text="➕  Nueva encomienda",
                 font=("Segoe UI", 14, "bold"),
                 bg="#ffffff", fg="#0f6e56").pack(side="left", padx=20)

        canvas = tk.Canvas(self, bg="#f5f5f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=16, pady=10)

        self.inner = tk.Frame(canvas, bg="#f5f5f0")
        win_id = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        def on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def on_canvas_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        self.inner.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_canvas_resize)

        self._seccion_remitente()
        self._seccion_destinatario()
        self._seccion_destino()
        self._seccion_articulos()
        self._seccion_notas()
        self._seccion_estado_pago()
        self._seccion_botones()

    def _card(self, titulo, icono=""):
        frame = tk.Frame(self.inner, bg="#ffffff",
                         highlightthickness=1, highlightbackground="#e0e0d8")
        frame.pack(fill="x", pady=(0, 10))
        titulo_completo = f"{icono}  {titulo}" if icono else titulo
        tk.Label(frame, text=titulo_completo,
                 font=("Segoe UI", 10, "bold"),
                 bg="#f1efe8", fg="#0f6e56",
                 pady=8, padx=14, anchor="w").pack(fill="x")
        body = tk.Frame(frame, bg="#ffffff", padx=14, pady=10)
        body.pack(fill="x")
        return body

    def _seccion_remitente(self):
        body = self._card("REMITENTE", "👤")
        body.columnconfigure((0, 1), weight=1)

        tk.Label(body, text="Nombre", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_ent_nombre = tk.StringVar()
        self.ent_nombre_cb = ttk.Combobox(body, textvariable=self.v_ent_nombre,
                                           width=28, font=("Segoe UI", 10))
        self.ent_nombre_cb.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 6))
        self._autocomplete(self.v_ent_nombre, self.ent_nombre_cb, "ent")

        tk.Label(body, text="Teléfono", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=1, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_ent_tel = tk.StringVar()
        ttk.Entry(body, textvariable=self.v_ent_tel, width=16, font=("Segoe UI", 10)).grid(
            row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 6))

        # Dirección eliminada — variable mantenida para compatibilidad
        self.v_ent_dir = tk.StringVar()

    def _seccion_destinatario(self):
        body = self._card("DESTINATARIO", "📦")
        body.columnconfigure((0, 1, 2), weight=1)

        tk.Label(body, text="Nombre", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_rec_nombre = tk.StringVar()
        self.rec_nombre_cb = ttk.Combobox(body, textvariable=self.v_rec_nombre,
                                           width=28, font=("Segoe UI", 10))
        self.rec_nombre_cb.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 6))
        self._autocomplete(self.v_rec_nombre, self.rec_nombre_cb, "rec")

        tk.Label(body, text="Teléfono", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=1, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_rec_tel = tk.StringVar()
        ttk.Entry(body, textvariable=self.v_rec_tel, width=16, font=("Segoe UI", 10)).grid(
            row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 6))

        tk.Label(body, text="Dirección USA", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=2, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_rec_dir = tk.StringVar()
        ttk.Entry(body, textvariable=self.v_rec_dir, width=20, font=("Segoe UI", 10)).grid(
            row=1, column=2, sticky="ew", padx=(0, 8), pady=(2, 6))

    def _seccion_destino(self):
        body = self._card("DESTINO", "🗺️")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=1)

        destinos = [
            "Sin asignar",
            "Miami, FL", "Nueva York, NY", "Los Ángeles, CA",
            "Chicago, IL", "Houston, TX", "Phoenix, AZ",
            "Dallas, TX", "San Antonio, TX", "San Diego, CA",
            "San Francisco, CA", "Las Vegas, NV", "Austin, TX",
            "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH",
            "Charlotte, NC", "Indianapolis, IN", "Seattle, WA",
            "Denver, CO", "Washington, DC", "Boston, MA",
            "El Paso, TX", "Nashville, TN", "Detroit, MI",
            "Oklahoma City, OK", "Portland, OR", "Memphis, TN",
            "Louisville, KY", "Baltimore, MD", "Milwaukee, WI",
            "Albuquerque, NM", "Tucson, AZ", "Fresno, CA",
            "Sacramento, CA", "Kansas City, MO", "Mesa, AZ",
            "Atlanta, GA", "Miami Gardens, FL", "Orlando, FL",
            "Raleigh, NC", "Omaha, NE", "Colorado Springs, CO",
            "Virginia Beach, VA", "Long Beach, CA", "Oakland, CA",
            "Minneapolis, MN", "Tampa, FL", "Arlington, TX",
            "New Orleans, LA", "Wichita, KS", "Cleveland, OH",
            "Tulsa, OK", "Bakersfield, CA", "Louisville, KY",
        ]
        self._destinos_lista = list(destinos)

        tk.Label(body, text="Ciudad destino", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=0, sticky="w", pady=(4, 0))
        self.v_destino_usa = tk.StringVar(value="Sin asignar")
        self._cb_destino = ttk.Combobox(body, textvariable=self.v_destino_usa,
                          values=self._destinos_lista,
                          width=26, state="readonly", font=("Segoe UI", 10))
        self._cb_destino.grid(row=1, column=0, sticky="ew", pady=(4, 4))

        # ── Campo para agregar ciudad personalizada ───────────────
        nueva_frame = tk.Frame(body, bg="#ffffff")
        nueva_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        nueva_frame.columnconfigure(0, weight=1)

        self.v_nueva_ciudad = tk.StringVar()
        e_nueva = ttk.Entry(nueva_frame, textvariable=self.v_nueva_ciudad,
                            font=("Segoe UI", 9))
        e_nueva.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        def _agregar_ciudad():
            ciudad = self.v_nueva_ciudad.get().strip()
            if not ciudad:
                return
            if ciudad not in self._destinos_lista:
                self._destinos_lista.append(ciudad)
                self._cb_destino.config(values=self._destinos_lista)
            self.v_destino_usa.set(ciudad)
            self.v_nueva_ciudad.set("")

        tk.Button(nueva_frame, text="＋ Agregar",
                  font=("Segoe UI", 8), bd=0,
                  bg="#e1f5ee", fg="#0f6e56",
                  padx=8, pady=4, cursor="hand2",
                  command=_agregar_ciudad).grid(row=0, column=1)
        e_nueva.bind("<Return>", lambda e: _agregar_ciudad())

        # ── Correo externo ────────────────────────────────────────
        tk.Label(body, text="📮  Correo externo (lugar)", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=1, sticky="w", padx=(12, 4), pady=(4, 0))
        self.v_correo_lugar = tk.StringVar()
        ttk.Entry(body, textvariable=self.v_correo_lugar,
                  font=("Segoe UI", 10)).grid(
            row=1, column=1, sticky="ew", padx=(12, 4), pady=(4, 8), rowspan=2)

        tk.Label(body, text="Valor correo ($)", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=2, sticky="w", padx=(4, 0), pady=(4, 0))
        self.v_correo_valor = tk.StringVar(value="")
        e_correo = ttk.Entry(body, textvariable=self.v_correo_valor,
                             width=10, font=("Segoe UI", 10))
        e_correo.grid(row=1, column=2, sticky="ew", padx=(4, 0), pady=(4, 8), rowspan=2)
        self.v_correo_valor.trace_add("write", lambda *_: self._calcular_totales())

    def _seccion_articulos(self):
        card = tk.Frame(self.inner, bg="#ffffff",
                        highlightthickness=1, highlightbackground="#e0e0d8")
        card.pack(fill="x", pady=(0, 10))

        # ── Encabezado de sección ─────────────────────────────────
        titulo_frame = tk.Frame(card, bg="#f1efe8")
        titulo_frame.pack(fill="x")
        tk.Label(titulo_frame, text="📋  DETALLE DE ARTÍCULOS",
                 font=("Segoe UI", 10, "bold"),
                 bg="#f1efe8", fg="#0f6e56",
                 pady=9, padx=14, anchor="w").pack(side="left")
        self.lbl_cant_articulos = tk.Label(titulo_frame, text="0 artículos",
                                            font=("Segoe UI", 9, "bold"),
                                            bg="#0f6e56", fg="#ffffff",
                                            padx=10, pady=4)
        self.lbl_cant_articulos.pack(side="right", padx=14, pady=6)

        # ── Cabecera de columnas ──────────────────────────────────
        hdr = tk.Frame(card, bg="#1a8a6a", padx=14, pady=7)
        hdr.pack(fill="x")
        cols = [("#", 3, "center"), ("Tipo", 9, "w"), ("Descripción", 0, "w"),
                ("Cant.", 5, "center"), ("Peso / Valor", 10, "center"),
                ("Importe", 10, "e"), ("", 3, "center")]
        for i, (txt, w, anc) in enumerate(cols):
            kw = {"width": w} if w else {}
            tk.Label(hdr, text=txt, font=("Segoe UI", 8, "bold"),
                     bg="#1a8a6a", fg="#d4f5eb", anchor=anc, **kw
                     ).grid(row=0, column=i, padx=2, sticky="ew")
        hdr.columnconfigure(2, weight=1)

        # ── Zona de filas ─────────────────────────────────────────
        self.articulos_frame = tk.Frame(card, bg="#f9f9f7")
        self.articulos_frame.pack(fill="x")

        # ── Botones ───────────────────────────────────────────────
        btn_frame = tk.Frame(card, bg="#ffffff", pady=8)
        btn_frame.pack(fill="x", padx=14)
        tk.Button(btn_frame, text="⚖️  Por peso",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  bg="#faeeda", fg="#633806",
                  pady=6, padx=14, cursor="hand2",
                  relief="flat",
                  command=self._abrir_envio_por_peso).pack(side="left")
        tk.Button(btn_frame, text="💊  Medicamentos",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  bg="#f0e6f9", fg="#6b2fa0",
                  pady=6, padx=14, cursor="hand2",
                  relief="flat",
                  command=self._abrir_medicamentos).pack(side="left", padx=(8, 0))
        tk.Button(btn_frame, text="📄  Documentos",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  bg="#fce8e8", fg="#791f1f",
                  pady=6, padx=14, cursor="hand2",
                  relief="flat",
                  command=self._abrir_documentos).pack(side="left", padx=(8, 0))
        tk.Button(btn_frame, text="📦  Artículos Varios",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  bg="#e8f0fb", fg="#1a3f6b",
                  pady=6, padx=14, cursor="hand2",
                  relief="flat",
                  command=self._abrir_varios).pack(side="left", padx=(8, 0))

        # ── Sección Por peso (tabla separada) ────────────────────
        self.peso_section = tk.Frame(card, bg="#ffffff")

        peso_hdr = tk.Frame(self.peso_section, bg="#4a2000", padx=14, pady=7)
        peso_hdr.pack(fill="x")
        tk.Label(peso_hdr, text="⚖️  ENVÍOS POR PESO",
                 font=("Segoe UI", 9, "bold"),
                 bg="#4a2000", fg="#f5c97a").pack(side="left")

        peso_cols_hdr = tk.Frame(self.peso_section, bg="#6b3a0f", padx=14, pady=5)
        peso_cols_hdr.pack(fill="x")
        for txt, w in [("#", 3), ("Descripción", 0), ("Peso (lb)", 10), ("Importe", 10), ("", 3)]:
            kw = {"width": w} if w else {}
            tk.Label(peso_cols_hdr, text=txt, font=("Segoe UI", 8, "bold"),
                     bg="#6b3a0f", fg="#f5dab5", anchor="w", **kw).pack(side="left", padx=4)

        self.peso_filas_frame = tk.Frame(self.peso_section, bg="#fffaf5")
        self.peso_filas_frame.pack(fill="x")
        self.filas_peso = []  # lista de filas peso para totales

        # ── Sección Medicamentos (tabla separada) ─────────────────
        self.med_section = tk.Frame(card, bg="#ffffff")

        med_hdr = tk.Frame(self.med_section, bg="#6b2fa0", padx=14, pady=7)
        med_hdr.pack(fill="x")
        tk.Label(med_hdr, text="💊  MEDICAMENTOS",
                 font=("Segoe UI", 9, "bold"),
                 bg="#6b2fa0", fg="#e8d5f5").pack(side="left")

        med_cols_hdr = tk.Frame(self.med_section, bg="#8e44c4", padx=14, pady=5)
        med_cols_hdr.pack(fill="x")
        for txt, w in [("#", 3), ("Medicamento", 0), ("Cant.", 6), ("Precio unit.", 10), ("Importe", 10), ("", 3)]:
            kw = {"width": w} if w else {}
            tk.Label(med_cols_hdr, text=txt, font=("Segoe UI", 8, "bold"),
                     bg="#8e44c4", fg="#e8d5f5", anchor="w", **kw).pack(side="left", padx=4)

        self.med_filas_frame = tk.Frame(self.med_section, bg="#fdf8ff")
        self.med_filas_frame.pack(fill="x")
        self.filas_med = []  # lista de filas medicamento para totales

        # ── Sección Documentos (tabla separada) ───────────────────
        self.doc_section = tk.Frame(card, bg="#ffffff")

        doc_hdr = tk.Frame(self.doc_section, bg="#791f1f", padx=14, pady=7)
        doc_hdr.pack(fill="x")
        tk.Label(doc_hdr, text="📄  DOCUMENTOS",
                 font=("Segoe UI", 9, "bold"),
                 bg="#791f1f", fg="#fce8e8").pack(side="left")

        doc_cols_hdr = tk.Frame(self.doc_section, bg="#9e2a2a", padx=14, pady=5)
        doc_cols_hdr.pack(fill="x")
        for txt, w in [("#", 3), ("Documento", 0), ("Cant.", 6), ("Precio unit.", 10), ("Importe", 10), ("", 3)]:
            kw = {"width": w} if w else {}
            tk.Label(doc_cols_hdr, text=txt, font=("Segoe UI", 8, "bold"),
                     bg="#9e2a2a", fg="#fce8e8", anchor="w", **kw).pack(side="left", padx=4)

        self.doc_filas_frame = tk.Frame(self.doc_section, bg="#fff8f8")
        self.doc_filas_frame.pack(fill="x")
        self.filas_doc = []  # lista de filas documento para totales

        # ── Sección Artículos Varios (tabla separada) ──────────────
        self.varios_section = tk.Frame(card, bg="#ffffff")

        varios_hdr = tk.Frame(self.varios_section, bg="#1a3f6b", padx=14, pady=7)
        varios_hdr.pack(fill="x")
        tk.Label(varios_hdr, text="📦  ARTÍCULOS VARIOS",
                 font=("Segoe UI", 9, "bold"),
                 bg="#1a3f6b", fg="#d4e4f5").pack(side="left")

        varios_cols_hdr = tk.Frame(self.varios_section, bg="#2a5a8a", padx=14, pady=5)
        varios_cols_hdr.pack(fill="x")
        for txt, w in [("#", 3), ("Artículo", 0), ("Cant.", 6), ("Precio unit.", 10), ("Importe", 10), ("", 3)]:
            kw = {"width": w} if w else {}
            tk.Label(varios_cols_hdr, text=txt, font=("Segoe UI", 8, "bold"),
                     bg="#2a5a8a", fg="#d4e4f5", anchor="w", **kw).pack(side="left", padx=4)

        self.varios_filas_frame = tk.Frame(self.varios_section, bg="#f0f5fb")
        self.varios_filas_frame.pack(fill="x")
        self.filas_varios = []  # lista de filas varios para totales

        # ── Barra de total ────────────────────────────────────────
        tot_frame = tk.Frame(card, bg="#0f6e56", padx=16, pady=11)
        tot_frame.pack(fill="x")
        tk.Label(tot_frame, text="TOTAL  →",
                 font=("Segoe UI", 10),
                 bg="#0f6e56", fg="#9fe1cb").pack(side="right")
        self.lbl_total_envio = tk.Label(tot_frame, text="$ 0.00",
                                         font=("Segoe UI", 16, "bold"),
                                         bg="#0f6e56", fg="#ffffff")
        self.lbl_total_envio.pack(side="right", padx=(0, 12))

    # ── Tipos de documento disponibles ────────────────────────────
    TIPOS_DOCUMENTO = [
        "Carta", "Sobre", "Pasaporte", "Visa",
        "Documentos legales", "Fotografías", "Cheque",
        "Tarjeta", "Contrato", "Acta de nacimiento",
        "Diploma / Título", "Otro",
    ]

    # ── Precios fijos por descripción de documento ────────────────
    PRECIOS_DOCUMENTO = {
        "Pasaporte":          70.0,
        "Acta de nacimiento": 30.0,
        "Cédula":             30.0,
        "Licencia":           30.0,
    }

    # ── Tipos de medicamento disponibles ─────────────────────────
    TIPOS_MEDICAMENTO = [
        "Blister de pastilla",
        "Jarabe",
        "Inyección / Ampolla",
        "Pomada",
        "Gotero (ojos / oídos)",
    ]

    # ── Precios fijos por tipo de medicamento ─────────────────────
    PRECIOS_MEDICAMENTO = {
        "Blister de pastilla":  5.0,
        "Jarabe":               5.0,
        "Inyección / Ampolla": 12.0,
        "Pomada":               3.0,
        "Gotero (ojos / oídos)": 3.0,
    }

    # ── Tipos "Otro" disponibles ──────────────────────────────────
    TIPOS_OTRO = [
        "Ropa",
        "Calzado",
        "Electrónico",
        "Juguete",
        "Alimento no perecedero",
        "Accesorio",
        "Otro",
    ]

    def _agregar_fila(self):
        num = len(self.filas_articulos) + 1
        bg = "#ffffff" if num % 2 == 1 else "#f4faf7"

        row_frame = tk.Frame(self.articulos_frame, bg=bg,
                             highlightthickness=1,
                             highlightbackground="#e8f0ec")
        row_frame.pack(fill="x", pady=(0, 1))

        # Número de fila
        lbl_num = tk.Label(row_frame, text=f"{num}", font=("Segoe UI", 8, "bold"),
                           bg=bg, fg="#aaa9a5", width=3, anchor="center")
        lbl_num.pack(side="left", padx=(6, 2), pady=6)

        # Tipo fijo: siempre "producto" — ya no se muestra selector
        v_tipo = tk.StringVar(value="producto")

        # ── Descripción ───────────────────────────────────────────
        v_desc = tk.StringVar()

        desc_frame = tk.Frame(row_frame, bg=bg)
        desc_frame.pack(side="left", padx=2, pady=6, expand=True, fill="x")

        # Entry libre
        e_desc = ttk.Entry(desc_frame, textvariable=v_desc, font=("Segoe UI", 9))
        e_desc.pack(fill="x", expand=True)

        # Cantidad
        v_cant = tk.StringVar(value="1")
        e_cant = ttk.Entry(row_frame, textvariable=v_cant, width=4,
                           font=("Segoe UI", 9), justify="center")
        e_cant.pack(side="left", padx=2, pady=6)

        # Peso/Valor + unidad
        val_frame = tk.Frame(row_frame, bg=bg)
        val_frame.pack(side="left", padx=2, pady=6)
        v_dato = tk.StringVar(value="0")
        e_dato = ttk.Entry(val_frame, textvariable=v_dato, width=7,
                           font=("Segoe UI", 9), justify="right")
        e_dato.pack(side="left")
        lbl_unidad = tk.Label(val_frame, text=" lb", font=("Segoe UI", 7, "bold"),
                              bg=bg, fg="#0f6e56")
        lbl_unidad.pack(side="left")

        # Importe
        lbl_importe = tk.Label(row_frame, text="$ 0.00",
                               font=("Segoe UI", 10, "bold"),
                               bg=bg, fg="#0f6e56",
                               width=9, anchor="e")
        lbl_importe.pack(side="left", padx=(4, 2), pady=6)

        # ── Cálculo de importe ────────────────────────────────────
        def calcular(*args):
            try:
                c = int(v_cant.get()) if v_cant.get() else 0
                d = float(v_dato.get()) if v_dato.get() else 0
                imp = c * d * PRECIO_LB
                lbl_importe.config(text=f"$ {int(imp):,}", fg="#0f6e56")
            except Exception:
                lbl_importe.config(text="$ 0")
            self._calcular_totales()

        v_desc.trace_add("write", calcular)
        v_cant.trace_add("write", calcular)
        v_dato.trace_add("write", calcular)

        # ── Botón eliminar ────────────────────────────────────────
        def eliminar():
            row_frame.destroy()
            self.filas_articulos = [x for x in self.filas_articulos if x[0] != row_frame]
            self._renumerar()
            self._calcular_totales()

        tk.Button(row_frame, text="✕", font=("Segoe UI", 9, "bold"),
                  bd=0, bg="#fde8e8", fg="#c0392b",
                  width=3, cursor="hand2", pady=4,
                  activebackground="#f5c6c6", activeforeground="#7b0000",
                  command=eliminar).pack(side="left", padx=(2, 6), pady=6)

        self.filas_articulos.append((row_frame, v_tipo, v_desc, v_cant, v_dato))
        calcular()
        e_desc.focus_set()


    def _abrir_carga_masiva(self):
        """Ventana emergente tipo hoja de cálculo para agregar múltiples artículos."""
        win = tk.Toplevel(self)
        win.title("📋  Agregar varios artículos")
        win.configure(bg="#f5f5f0")
        win.resizable(True, True)
        win.grab_set()
        w, h = 700, 420
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        hdr = tk.Frame(win, bg="#0f6e56", pady=10, padx=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📋  Carga masiva de artículos",
                 font=("Segoe UI", 11, "bold"), bg="#0f6e56", fg="#ffffff").pack(side="left")
        tk.Label(hdr, text="Llena la tabla y presiona Confirmar",
                 font=("Segoe UI", 8), bg="#0f6e56", fg="#9fe1cb").pack(side="left", padx=12)

        col_hdr = tk.Frame(win, bg="#1a8a6a", padx=10, pady=6)
        col_hdr.pack(fill="x", padx=12, pady=(10, 0))
        for txt, w_col in [("#", 4), ("Tipo", 10), ("Descripción", 32), ("Cant.", 6), ("Peso/Valor", 10)]:
            tk.Label(col_hdr, text=txt, font=("Segoe UI", 8, "bold"),
                     bg="#1a8a6a", fg="#d4f5eb", width=w_col, anchor="w").pack(side="left", padx=2)

        contenedor = tk.Frame(win, bg="#f5f5f0")
        contenedor.pack(fill="both", expand=True, padx=12, pady=4)
        canvas_m = tk.Canvas(contenedor, bg="#f9f9f7", highlightthickness=0)
        vsb_m = ttk.Scrollbar(contenedor, orient="vertical", command=canvas_m.yview)
        canvas_m.configure(yscrollcommand=vsb_m.set)
        vsb_m.pack(side="right", fill="y")
        canvas_m.pack(fill="both", expand=True)
        filas_frame = tk.Frame(canvas_m, bg="#f9f9f7")
        canvas_m.create_window((0, 0), window=filas_frame, anchor="nw")
        filas_frame.bind("<Configure>", lambda e: canvas_m.configure(scrollregion=canvas_m.bbox("all")))

        filas_masiva = []

        def _fila_masiva(num):
            bg = "#ffffff" if num % 2 == 1 else "#f4faf7"
            row = tk.Frame(filas_frame, bg=bg, highlightthickness=1, highlightbackground="#e8f0ec")
            row.pack(fill="x", pady=(0, 1))
            tk.Label(row, text=str(num), font=("Segoe UI", 8),
                     bg=bg, fg="#aaa9a5", width=4, anchor="center").pack(side="left", padx=(4, 2), pady=5)
            v_tipo = tk.StringVar(value="producto")
            ttk.Combobox(row, textvariable=v_tipo, values=["producto", "documento"],
                         width=9, state="readonly", font=("Segoe UI", 9)).pack(side="left", padx=2, pady=5)
            v_desc = tk.StringVar()
            ttk.Entry(row, textvariable=v_desc, font=("Segoe UI", 9)).pack(side="left", padx=2, pady=5, expand=True, fill="x")
            v_cant = tk.StringVar(value="1")
            ttk.Entry(row, textvariable=v_cant, width=5, font=("Segoe UI", 9), justify="center").pack(side="left", padx=2, pady=5)
            v_dato = tk.StringVar(value="0")
            ttk.Entry(row, textvariable=v_dato, width=9, font=("Segoe UI", 9), justify="right").pack(side="left", padx=(2, 8), pady=5)
            filas_masiva.append((v_tipo, v_desc, v_cant, v_dato))

        for i in range(1, 11):
            _fila_masiva(i)

        btn_bar = tk.Frame(win, bg="#f5f5f0", pady=10, padx=12)
        btn_bar.pack(fill="x")

        def _mas_filas():
            inicio = len(filas_masiva) + 1
            for i in range(inicio, inicio + 5):
                _fila_masiva(i)
            canvas_m.update_idletasks()
            canvas_m.yview_moveto(1.0)

        tk.Button(btn_bar, text="＋  5 filas más", font=("Segoe UI", 9), bd=0,
                  bg="#e1f5ee", fg="#0f6e56", pady=6, padx=12, cursor="hand2",
                  command=_mas_filas).pack(side="left")

        def _confirmar():
            for v_tipo, v_desc, v_cant, v_dato in filas_masiva:
                desc = v_desc.get().strip()
                if not desc:
                    continue
                self._agregar_fila()
                _, ult_tipo, ult_desc, ult_cant, ult_dato = self.filas_articulos[-1]
                ult_tipo.set(v_tipo.get())
                ult_desc.set(desc)
                ult_cant.set(v_cant.get() or "1")
                ult_dato.set(v_dato.get() or "0")
            win.destroy()
            self._calcular_totales()

        tk.Button(btn_bar, text="✓  Confirmar y agregar", font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#0f6e56", fg="#ffffff", pady=8, padx=20, cursor="hand2",
                  command=_confirmar).pack(side="right")
        tk.Button(btn_bar, text="Cancelar", font=("Segoe UI", 9), bd=0,
                  bg="#f1efe8", fg="#5f5e5a", pady=8, padx=14, cursor="hand2",
                  command=win.destroy).pack(side="right", padx=(0, 8))

    def _abrir_envio_por_peso(self):
        """Ventana especial: ingresa descripción y peso total, agrega como un artículo."""
        win = tk.Toplevel(self)
        win.title("⚖️  Envío por peso")
        win.configure(bg="#ffffff")
        win.resizable(False, False)
        win.grab_set()
        w, h = 560, 620
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        # ── Encabezado grande ─────────────────────────────────────
        hdr = tk.Frame(win, bg="#4a2000", pady=20, padx=28)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚖️", font=("Segoe UI", 22),
                 bg="#4a2000", fg="#f5c97a").pack(side="left")
        hdr_txt = tk.Frame(hdr, bg="#4a2000")
        hdr_txt.pack(side="left", padx=(12, 0))
        tk.Label(hdr_txt, text="Envío por peso total",
                 font=("Segoe UI", 15, "bold"),
                 bg="#4a2000", fg="#ffffff").pack(anchor="w")
        tk.Label(hdr_txt, text="Ingresa la descripción y el peso del paquete",
                 font=("Segoe UI", 9),
                 bg="#4a2000", fg="#c8a97a").pack(anchor="w")

        # ── Cuerpo ────────────────────────────────────────────────
        body = tk.Frame(win, bg="#ffffff", padx=28, pady=22)
        body.pack(fill="both", expand=True)

        # Descripción
        tk.Label(body, text="DESCRIPCIÓN DEL ENVÍO",
                 font=("Segoe UI", 8, "bold"), bg="#ffffff", fg="#aaa9a5").pack(anchor="w")
        desc_entry = tk.Text(body, height=4, font=("Segoe UI", 11),
                             relief="flat", bd=0,
                             highlightthickness=2,
                             highlightbackground="#e0ddd5",
                             highlightcolor="#633806",
                             padx=12, pady=10, fg="#1a1a1a",
                             bg="#fafaf8")
        desc_entry.pack(fill="x", pady=(6, 18))

        # Fila peso + costo
        mid = tk.Frame(body, bg="#ffffff")
        mid.pack(fill="x", pady=(0, 18))
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)

        # Peso
        peso_col = tk.Frame(mid, bg="#ffffff")
        peso_col.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        tk.Label(peso_col, text="PESO TOTAL",
                 font=("Segoe UI", 8, "bold"), bg="#ffffff", fg="#aaa9a5").pack(anchor="w")
        peso_inner = tk.Frame(peso_col, bg="#fafaf8",
                              highlightthickness=2, highlightbackground="#e0ddd5")
        peso_inner.pack(fill="x", pady=(6, 0))
        v_peso = tk.StringVar(value="")
        e_peso = tk.Entry(peso_inner, textvariable=v_peso, width=8,
                          font=("Segoe UI", 22, "bold"), justify="center",
                          relief="flat", bd=0, bg="#fafaf8", fg="#4a2000",
                          insertbackground="#633806")
        e_peso.pack(side="left", padx=12, pady=10)
        tk.Label(peso_inner, text="lb", font=("Segoe UI", 13, "bold"),
                 bg="#fafaf8", fg="#888780").pack(side="left")

        # Costo estimado
        costo_col = tk.Frame(mid, bg="#4a2000", padx=16, pady=14)
        costo_col.grid(row=0, column=1, sticky="ew")
        tk.Label(costo_col, text="COSTO ESTIMADO",
                 font=("Segoe UI", 8, "bold"), bg="#4a2000", fg="#c8a97a").pack(anchor="w")
        lbl_costo_grande = tk.Label(costo_col, text="$ 0.00",
                                    font=("Segoe UI", 24, "bold"),
                                    bg="#4a2000", fg="#ffffff")
        lbl_costo_grande.pack(anchor="w", pady=(4, 0))
        lbl_detalle = tk.Label(costo_col, text=f"0.00 lb × ${PRECIO_LB} / lb",
                               font=("Segoe UI", 9), bg="#4a2000", fg="#c8a97a")
        lbl_detalle.pack(anchor="w")

        def _actualizar_costo(*args):
            try:
                lb = float(v_peso.get())
                costo = lb * PRECIO_LB
                lbl_costo_grande.config(text=f"$ {int(costo):,}")
                lbl_detalle.config(text=f"{lb} lb × ${PRECIO_LB} / lb")
                peso_inner.config(highlightbackground="#633806")
            except ValueError:
                lbl_costo_grande.config(text="$ 0")
                lbl_detalle.config(text=f"0 lb × ${PRECIO_LB} / lb")
                peso_inner.config(highlightbackground="#e0ddd5")

        v_peso.trace_add("write", _actualizar_costo)

        # ── Botones de fracciones de libra ────────────────────────
        frac_frame = tk.Frame(body, bg="#ffffff")
        frac_frame.pack(fill="x", pady=(0, 10))
        tk.Label(frac_frame, text="Fracciones:", font=("Segoe UI", 8),
                 bg="#ffffff", fg="#888780").pack(side="left", padx=(0, 6))
        fracciones = [
            ("¼ lb", "0.25"), ("½ lb", "0.5"), ("¾ lb", "0.75"),
            ("1 lb", "1"), ("1½ lb", "1.5"), ("2 lb", "2"),
            ("3 lb", "3"), ("5 lb", "5"), ("10 lb", "10"),
        ]
        for etiq, val in fracciones:
            tk.Button(frac_frame, text=etiq, font=("Segoe UI", 8), bd=0,
                      bg="#faeeda", fg="#633806", padx=6, pady=3, cursor="hand2",
                      command=lambda v=val: (v_peso.set(v), _actualizar_costo())
                      ).pack(side="left", padx=2)

        e_peso.focus_set()

        # ── Separador ─────────────────────────────────────────────
        tk.Frame(body, bg="#eeede8", height=1).pack(fill="x", pady=(0, 18))

        # ── Botones ───────────────────────────────────────────────
        btn_bar = tk.Frame(body, bg="#ffffff")
        btn_bar.pack(fill="x")


        def _validar_y_agregar():
            desc = desc_entry.get("1.0", "end").strip()
            if not desc:
                desc = "Envío por peso"
            try:
                peso = float(v_peso.get())
                if peso <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Requerido", "Ingresa un peso válido en libras.", parent=win)
                return False
            self._agregar_fila_peso(desc, peso)
            return True

        def _confirmar():
            if _validar_y_agregar():
                win.destroy()

        def _agregar_otro():
            """Agrega el envío actual y limpia el formulario para ingresar otro."""
            if _validar_y_agregar():
                desc_entry.delete("1.0", "end")
                v_peso.set("")
                lbl_costo_grande.config(text="$ 0")
                lbl_detalle.config(text=f"0 lb × ${PRECIO_LB} / lb")
                desc_entry.focus_set()

        def _guardar_directo():
            if _validar_y_agregar():
                win.destroy()
                self._guardar()

        tk.Button(btn_bar, text="✓  Agregar al envío",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#633806", fg="#ffffff",
                  pady=8, padx=20, cursor="hand2",
                  command=_confirmar).pack(side="right", padx=(0, 8))
        tk.Button(btn_bar, text="➕  Añadir otro",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#faeeda", fg="#633806",
                  pady=8, padx=16, cursor="hand2",
                  command=_agregar_otro).pack(side="right", padx=(0, 8))
        tk.Button(btn_bar, text="Cancelar", font=("Segoe UI", 9), bd=0,
                  bg="#f1efe8", fg="#5f5e5a",
                  pady=8, padx=14, cursor="hand2",
                  command=win.destroy).pack(side="left")

    def _abrir_medicamentos(self):
        """Ventana emergente para agregar medicamentos con precios predefinidos."""
        win = tk.Toplevel(self)
        win.title("💊  Medicamentos")
        win.configure(bg="#ffffff")
        win.resizable(False, False)
        win.grab_set()
        w, h = 580, 680
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        # ── Encabezado ────────────────────────────────────────────
        hdr = tk.Frame(win, bg="#6b2fa0", pady=20, padx=28)
        hdr.pack(fill="x")
        tk.Label(hdr, text="💊", font=("Segoe UI", 22),
                 bg="#6b2fa0", fg="#e8d5f5").pack(side="left")
        hdr_txt = tk.Frame(hdr, bg="#6b2fa0")
        hdr_txt.pack(side="left", padx=(12, 0))
        tk.Label(hdr_txt, text="Medicamentos",
                 font=("Segoe UI", 15, "bold"),
                 bg="#6b2fa0", fg="#ffffff").pack(anchor="w")
        tk.Label(hdr_txt, text="Ingresa la cantidad de cada medicamento a enviar",
                 font=("Segoe UI", 9),
                 bg="#6b2fa0", fg="#d4b0f0").pack(anchor="w")

        # ── Cuerpo ────────────────────────────────────────────────
        body = tk.Frame(win, bg="#ffffff", padx=28, pady=16)
        body.pack(fill="both", expand=True)

        # Cabecera de la tabla
        hdr_tbl = tk.Frame(body, bg="#8e44c4", padx=10, pady=7)
        hdr_tbl.pack(fill="x")
        hdr_tbl.columnconfigure(1, weight=1)
        for col, txt, ancho in [(0, "Medicamento", 0), (1, "Precio unit.", 10), (2, "Cantidad", 9), (3, "Importe", 10)]:
            kw = {} if ancho == 0 else {"width": ancho}
            tk.Label(hdr_tbl, text=txt, font=("Segoe UI", 8, "bold"),
                     bg="#8e44c4", fg="#e8d5f5", anchor="w", **kw).grid(
                row=0, column=col, padx=6, sticky="ew")
        hdr_tbl.columnconfigure(0, weight=1)

        # Filas de medicamentos
        filas_med = []   # (nombre, precio, v_cant, lbl_imp)

        tbl_frame = tk.Frame(body, bg="#fafaf8")
        tbl_frame.pack(fill="x", pady=(0, 12))
        tbl_frame.columnconfigure(0, weight=1)

        items = [
            ("Blister de pastilla",   5.0),
            ("Jarabe",                5.0),
            ("Inyección / Ampolla",  12.0),
            ("Pomada",                3.0),
            ("Gotero (ojos / oídos)", 3.0),
        ]

        lbl_total_med = None  # se define después

        def _recalcular(*_):
            total = 0.0
            for (_, precio, v_c, _lbl) in filas_med:
                try:
                    total += float(v_c.get() or 0) * precio
                except (ValueError, TypeError):
                    pass
            # sumar Otros manuales
            for v_nombre, v_precio, v_cant in otros_filas:
                try:
                    p = float(v_precio.get() or 0)
                    c = float(v_cant.get() or 0)
                    total += p * c
                except (ValueError, TypeError):
                    pass
            lbl_total_med.config(text=f"$ {int(total):,}")
            for nombre, precio, v_cant, lbl_imp in filas_med:
                try:
                    imp = float(v_cant.get() or 0) * precio
                except ValueError:
                    imp = 0.0
                lbl_imp.config(text=f"$ {int(imp):,}" if imp > 0 else "$ 0",
                               fg="#6b2fa0" if imp > 0 else "#aaa9a5")

        for i, (nombre, precio) in enumerate(items):
            bg = "#ffffff" if i % 2 == 0 else "#f8f2fd"
            row = tk.Frame(tbl_frame, bg=bg,
                           highlightthickness=1, highlightbackground="#e8daf5")
            row.pack(fill="x", pady=(0, 1))
            row.columnconfigure(0, weight=1)

            tk.Label(row, text=nombre, font=("Segoe UI", 10),
                     bg=bg, fg="#2c1a40", anchor="w").grid(
                row=0, column=0, padx=(10, 4), pady=8, sticky="ew")
            tk.Label(row, text=f"${precio:.0f}", font=("Segoe UI", 9, "bold"),
                     bg=bg, fg="#8e44c4", width=8, anchor="center").grid(
                row=0, column=1, padx=4, pady=8)

            v_cant = tk.StringVar(value="0")
            e_cant = tk.Entry(row, textvariable=v_cant, width=7,
                              font=("Segoe UI", 11, "bold"),
                              justify="center", relief="flat",
                              bg="#f0e6f9", fg="#6b2fa0",
                              highlightthickness=1, highlightbackground="#c49de0")
            e_cant.grid(row=0, column=2, padx=8, pady=6)

            lbl_imp = tk.Label(row, text="$ 0", font=("Segoe UI", 10, "bold"),
                               bg=bg, fg="#aaa9a5", width=9, anchor="e")
            lbl_imp.grid(row=0, column=3, padx=(4, 10), pady=8)

            v_cant.trace_add("write", _recalcular)
            filas_med.append((nombre, precio, v_cant, lbl_imp))

        # ── Fila "Otro" manual ────────────────────────────────────
        otro_container = tk.Frame(tbl_frame, bg="#ffffff")
        otro_container.pack(fill="x", pady=(6, 1))

        otros_filas = []  # lista de (v_nombre, v_precio, v_cant)

        def _agregar_otro_fila():
            otro_bg = "#f0f8f0"
            otro_row = tk.Frame(otro_container, bg=otro_bg,
                                highlightthickness=2, highlightbackground="#80c080")
            otro_row.pack(fill="x", pady=(0, 4))
            otro_row.columnconfigure(0, weight=1)

            otro_izq = tk.Frame(otro_row, bg=otro_bg)
            otro_izq.grid(row=0, column=0, padx=(10, 4), pady=8, sticky="ew")
            tk.Label(otro_izq, text="✏️  Otro (manual)", font=("Segoe UI", 10, "bold"),
                     bg=otro_bg, fg="#1a5c1a").pack(anchor="w")
            v_nombre = tk.StringVar()
            ttk.Entry(otro_izq, textvariable=v_nombre,
                      font=("Segoe UI", 9)).pack(fill="x", pady=(3, 0))

            otro_pf = tk.Frame(otro_row, bg=otro_bg)
            otro_pf.grid(row=0, column=1, padx=4, pady=8)
            tk.Label(otro_pf, text="$", font=("Segoe UI", 9, "bold"),
                     bg=otro_bg, fg="#1a5c1a").pack(side="left")
            v_precio = tk.StringVar(value="")
            ttk.Entry(otro_pf, textvariable=v_precio,
                      width=6, font=("Segoe UI", 9), justify="center").pack(side="left")

            v_cant = tk.StringVar(value="0")
            tk.Entry(otro_row, textvariable=v_cant, width=7,
                     font=("Segoe UI", 11, "bold"),
                     justify="center", relief="flat",
                     bg="#e8f5e8", fg="#1a5c1a",
                     highlightthickness=1, highlightbackground="#80c080").grid(
                row=0, column=2, padx=8, pady=6)

            lbl_imp = tk.Label(otro_row, text="$ 0", font=("Segoe UI", 10, "bold"),
                               bg=otro_bg, fg="#aaa9a5", width=9, anchor="e")
            lbl_imp.grid(row=0, column=3, padx=(4, 10), pady=8)

            def _recalc_otro(*_):
                try:
                    p = float(v_precio.get() or 0)
                    c = float(v_cant.get() or 0)
                    imp = p * c
                except ValueError:
                    imp = 0.0
                lbl_imp.config(text=f"$ {int(imp):,}" if imp > 0 else "$ 0",
                               fg="#1a5c1a" if imp > 0 else "#aaa9a5")
                _recalcular()

            v_precio.trace_add("write", _recalc_otro)
            v_cant.trace_add("write", _recalc_otro)
            otros_filas.append((v_nombre, v_precio, v_cant))

        _agregar_otro_fila()

        btn_agregar_otro = tk.Button(tbl_frame, text="+ Agregar otro",
                                     font=("Segoe UI", 9, "bold"), bd=0,
                                     bg="#e8f5e8", fg="#1a5c1a",
                                     pady=5, padx=12, cursor="hand2",
                                     command=_agregar_otro_fila)
        btn_agregar_otro.pack(pady=(4, 0))

        # ── Total ─────────────────────────────────────────────────
        tot_frame = tk.Frame(body, bg="#6b2fa0", padx=16, pady=12)
        tot_frame.pack(fill="x", pady=(0, 16))
        tk.Label(tot_frame, text="TOTAL MEDICAMENTOS  →",
                 font=("Segoe UI", 9), bg="#6b2fa0", fg="#d4b0f0").pack(side="right")
        lbl_total_med = tk.Label(tot_frame, text="$ 0",
                                  font=("Segoe UI", 18, "bold"),
                                  bg="#6b2fa0", fg="#ffffff")
        lbl_total_med.pack(side="right", padx=(0, 14))

        # ── Separador ─────────────────────────────────────────────
        tk.Frame(body, bg="#eeede8", height=1).pack(fill="x", pady=(0, 14))

        # ── Botones ───────────────────────────────────────────────
        btn_bar = tk.Frame(body, bg="#ffffff")
        btn_bar.pack(fill="x")

        def _confirmar():
            agregados = 0
            for nombre, precio, v_cant, _ in filas_med:
                try:
                    cant = float(v_cant.get() or 0)
                except ValueError:
                    cant = 0
                if cant <= 0:
                    continue
                self._agregar_fila_med(nombre, cant, precio)
                agregados += 1
            # Agregar "Otros" manuales si tienen cantidad y precio
            for v_nombre, v_precio, v_cant in otros_filas:
                try:
                    oc = float(v_cant.get() or 0)
                    op = float(v_precio.get() or 0)
                except ValueError:
                    oc = 0; op = 0
                if oc > 0 and op > 0:
                    nombre = v_nombre.get().strip() or "Medicamento (otro)"
                    self._agregar_fila_med(nombre, oc, op)
                    agregados += 1
                elif oc > 0 and op <= 0:
                    messagebox.showwarning("Precio requerido",
                        "Ingresa el precio para el medicamento manual.", parent=win)
                    return
            win.destroy()
            self._calcular_totales()
            if agregados == 0:
                messagebox.showinfo("Sin artículos",
                                    "No se ingresó cantidad en ningún medicamento.")

        def _guardar_directo():
            _confirmar()
            self.after(150, self._guardar)

        tk.Button(btn_bar, text="✓  Agregar al envío",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#6b2fa0", fg="#ffffff",
                  pady=8, padx=20, cursor="hand2",
                  command=_confirmar).pack(side="right", padx=(0, 8))
        tk.Button(btn_bar, text="Cancelar", font=("Segoe UI", 9), bd=0,
                  bg="#f1efe8", fg="#5f5e5a",
                  pady=8, padx=14, cursor="hand2",
                  command=win.destroy).pack(side="left")

    def _abrir_documentos(self):
        """Ventana emergente para agregar documentos con precios predefinidos."""
        win = tk.Toplevel(self)
        win.title("📄  Documentos")
        win.configure(bg="#ffffff")
        win.resizable(False, False)
        win.grab_set()
        w, h = 580, 500
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        # ── Encabezado ────────────────────────────────────────────
        hdr = tk.Frame(win, bg="#791f1f", pady=20, padx=28)
        hdr.pack(fill="x", side="top")
        tk.Label(hdr, text="📄", font=("Segoe UI", 22),
                 bg="#791f1f", fg="#fce8e8").pack(side="left")
        hdr_txt = tk.Frame(hdr, bg="#791f1f")
        hdr_txt.pack(side="left", padx=(12, 0))
        tk.Label(hdr_txt, text="Documentos",
                 font=("Segoe UI", 15, "bold"),
                 bg="#791f1f", fg="#ffffff").pack(anchor="w")
        tk.Label(hdr_txt, text="Ingresa la cantidad de cada documento a enviar",
                 font=("Segoe UI", 9),
                 bg="#791f1f", fg="#f5c0c0").pack(anchor="w")

        # ── Pie: Total + Botones (anclados al fondo ANTES del body) ──
        pie = tk.Frame(win, bg="#ffffff", padx=28, pady=10)
        pie.pack(fill="x", side="bottom")

        # filas_doc_popup definida antes para que _confirmar pueda usarla
        filas_doc_popup = []
        lbl_total_doc = None

        def _confirmar():
            agregados = 0
            for nombre, v_precio, v_cant, _, precio_fijo in filas_doc_popup:
                try:
                    cant = int(v_cant.get() or 0)
                except ValueError:
                    cant = 0
                if cant <= 0:
                    continue
                try:
                    precio = float(v_precio.get() or 0)
                except ValueError:
                    precio = 0.0
                if precio <= 0:
                    messagebox.showwarning("Precio requerido",
                        f"Ingresa el precio para «{nombre}» antes de agregar.",
                        parent=win)
                    return
                self._agregar_fila_doc(nombre, cant, precio)
                agregados += 1
            win.destroy()
            self._calcular_totales()
            if agregados == 0:
                messagebox.showinfo("Sin artículos",
                                    "No se ingresó cantidad en ningún documento.")

        def _guardar_directo():
            _confirmar()
            self.after(150, self._guardar)

        # Total (visible siempre arriba del pie)
        tot_frame = tk.Frame(pie, bg="#791f1f", padx=16, pady=12)
        tot_frame.pack(fill="x", pady=(0, 8))
        tk.Label(tot_frame, text="TOTAL DOCUMENTOS  →",
                 font=("Segoe UI", 9), bg="#791f1f", fg="#f5c0c0").pack(side="right")
        lbl_total_doc = tk.Label(tot_frame, text="$ 0.00",
                                  font=("Segoe UI", 18, "bold"),
                                  bg="#791f1f", fg="#ffffff")
        lbl_total_doc.pack(side="right", padx=(0, 14))

        # Separador
        tk.Frame(pie, bg="#eeede8", height=1).pack(fill="x", pady=(0, 10))

        btn_bar = tk.Frame(pie, bg="#ffffff")
        btn_bar.pack(fill="x")
        tk.Button(btn_bar, text="✓  Agregar al envío",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#791f1f", fg="#ffffff",
                  pady=8, padx=20, cursor="hand2",
                  command=_confirmar).pack(side="right", padx=(0, 8))
        tk.Button(btn_bar, text="Cancelar", font=("Segoe UI", 9), bd=0,
                  bg="#f1efe8", fg="#5f5e5a",
                  pady=8, padx=14, cursor="hand2",
                  command=win.destroy).pack(side="left")

        # ── Cuerpo (tabla, ocupa espacio restante entre header y pie) ─
        body = tk.Frame(win, bg="#ffffff", padx=28, pady=16)
        body.pack(fill="both", expand=True, side="top")

        # Cabecera tabla (siempre visible)
        hdr_tbl = tk.Frame(body, bg="#9e2a2a", padx=10, pady=7)
        hdr_tbl.pack(fill="x")
        hdr_tbl.columnconfigure(0, weight=1)
        for col, txt, ancho in [(0, "Documento", 0), (1, "Precio unit.", 10), (2, "Cantidad", 9), (3, "Importe", 10)]:
            kw = {} if ancho == 0 else {"width": ancho}
            tk.Label(hdr_tbl, text=txt, font=("Segoe UI", 8, "bold"),
                     bg="#9e2a2a", fg="#fce8e8", anchor="w", **kw).grid(
                row=0, column=col, padx=6, sticky="ew")

        # Items: (nombre, precio_fijo o None)
        items_doc = [
            ("Pasaporte",             70.0),
            ("Partida de nacimiento", 30.0),
            ("Cédula",                30.0),
            ("Licencia",              30.0),
            ("Carta",                 None),
            ("Sobre",                 None),
            ("Visa",                  None),
            ("Documentos legales",    None),
            ("Fotografías",           None),
            ("Cheque",                None),
            ("Tarjeta",               None),
            ("Contrato",              None),
            ("Diploma / Título",      None),
        ]

        # ── Área desplazable para la tabla ────────────────────────
        scroll_container = tk.Frame(body, bg="#fafaf8")
        scroll_container.pack(fill="both", expand=True, pady=(0, 12))

        canvas_doc = tk.Canvas(scroll_container, bg="#fafaf8",
                               highlightthickness=0, height=280)
        vsb_doc = ttk.Scrollbar(scroll_container, orient="vertical",
                                command=canvas_doc.yview)
        canvas_doc.configure(yscrollcommand=vsb_doc.set)
        vsb_doc.pack(side="right", fill="y")
        canvas_doc.pack(side="left", fill="both", expand=True)

        tbl_frame = tk.Frame(canvas_doc, bg="#fafaf8")
        tbl_win_id = canvas_doc.create_window((0, 0), window=tbl_frame, anchor="nw")
        tbl_frame.columnconfigure(0, weight=1)

        def _on_tbl_configure(e):
            canvas_doc.configure(scrollregion=canvas_doc.bbox("all"))
        def _on_canvas_resize(e):
            canvas_doc.itemconfig(tbl_win_id, width=e.width)
        tbl_frame.bind("<Configure>", _on_tbl_configure)
        canvas_doc.bind("<Configure>", _on_canvas_resize)

        # Mousewheel scroll
        def _on_mousewheel(event):
            canvas_doc.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas_doc.bind("<MouseWheel>", _on_mousewheel)
        tbl_frame.bind("<MouseWheel>", _on_mousewheel)

        def _recalcular(*_):
            total = 0.0
            for nombre, v_precio, v_cant, lbl_imp, _ in filas_doc_popup:
                try:
                    p = float(v_precio.get() or 0)
                    c = int(v_cant.get() or 0)
                    imp = c * p
                except (ValueError, TypeError):
                    imp = 0.0
                total += imp
                lbl_imp.config(text=f"$ {imp:,.2f}",
                               fg="#791f1f" if imp > 0 else "#aaa9a5")
            lbl_total_doc.config(text=f"$ {total:,.2f}")

        for i, (nombre, precio_fijo) in enumerate(items_doc):
            bg = "#ffffff" if i % 2 == 0 else "#fff3f3"
            row = tk.Frame(tbl_frame, bg=bg,
                           highlightthickness=1, highlightbackground="#f5d5d5")
            row.pack(fill="x", pady=(0, 1))
            row.columnconfigure(0, weight=1)

            tk.Label(row, text=nombre, font=("Segoe UI", 10),
                     bg=bg, fg="#3a0a0a", anchor="w").grid(
                row=0, column=0, padx=(10, 4), pady=7, sticky="ew")

            # Columna precio: fijo = label, libre = Entry editable
            v_precio = tk.StringVar(value=str(int(precio_fijo)) if precio_fijo else "")
            if precio_fijo is not None:
                tk.Label(row, text=f"${precio_fijo:.0f}", font=("Segoe UI", 9, "bold"),
                         bg=bg, fg="#9e2a2a", width=8, anchor="center").grid(
                    row=0, column=1, padx=4, pady=7)
            else:
                precio_entry = tk.Entry(row, textvariable=v_precio, width=7,
                                        font=("Segoe UI", 9), justify="center",
                                        relief="flat",
                                        highlightthickness=1,
                                        highlightbackground="#e8a0a0",
                                        bg="#fff8f8", fg="#791f1f")
                precio_entry.grid(row=0, column=1, padx=4, pady=5)
                v_precio.trace_add("write", _recalcular)

            v_cant = tk.StringVar(value="0")
            sp = tk.Spinbox(row, textvariable=v_cant, from_=0, to=999,
                            width=6, font=("Segoe UI", 11, "bold"),
                            justify="center", relief="flat",
                            bg="#fce8e8", fg="#791f1f",
                            buttonbackground="#f5c0c0",
                            highlightthickness=1, highlightbackground="#e8a0a0")
            sp.grid(row=0, column=2, padx=8, pady=5)

            lbl_imp = tk.Label(row, text="$ 0.00", font=("Segoe UI", 10, "bold"),
                               bg=bg, fg="#aaa9a5", width=9, anchor="e")
            lbl_imp.grid(row=0, column=3, padx=(4, 10), pady=7)

            v_cant.trace_add("write", _recalcular)
            filas_doc_popup.append((nombre, v_precio, v_cant, lbl_imp, precio_fijo))
            row.bind("<MouseWheel>", _on_mousewheel)

    def _agregar_fila_doc(self, nombre, cant, precio):
        """Agrega una fila a la tabla separada de documentos."""
        if not self.doc_section.winfo_ismapped():
            self.doc_section.pack(fill="x", before=self.lbl_total_envio.master)

        i = len(self.filas_doc) + 1
        importe = cant * precio
        bg = "#ffffff" if i % 2 == 1 else "#fff3f3"

        row = tk.Frame(self.doc_filas_frame, bg=bg, pady=3)
        row.pack(fill="x")

        tk.Label(row, text=str(i), font=("Segoe UI", 8), bg=bg, fg="#aaa", width=3,
                 anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=nombre, font=("Segoe UI", 9), bg=bg, fg="#3a0a0a",
                 anchor="w").pack(side="left", padx=4, expand=True, fill="x")
        tk.Label(row, text=f"×{cant}", font=("Segoe UI", 9, "bold"), bg=bg, fg="#791f1f",
                 width=5, anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=f"${int(precio)}", font=("Segoe UI", 9), bg=bg, fg="#9e2a2a",
                 width=8, anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=f"$ {int(importe):,}", font=("Segoe UI", 9, "bold"), bg=bg,
                 fg="#791f1f", width=10, anchor="e").pack(side="left", padx=4)

        fila = (row, nombre, cant, precio)
        self.filas_doc.append(fila)

        def _del(r=row, f=fila):
            r.destroy()
            if f in self.filas_doc:
                self.filas_doc.remove(f)
            self._renumerar_doc()
            self._calcular_totales()
            if not self.filas_doc:
                self.doc_section.pack_forget()

        tk.Button(row, text="✕", font=("Segoe UI", 8, "bold"), bd=0,
                  bg="#fde8e8", fg="#c0392b", width=3, cursor="hand2",
                  command=_del).pack(side="left", padx=(2, 8))

        self._calcular_totales()

    def _renumerar_doc(self):
        for i, (row, _, _, _) in enumerate(self.filas_doc, 1):
            bg = "#ffffff" if i % 2 == 1 else "#fff3f3"
            row.config(bg=bg)
            children = row.winfo_children()
            if children:
                children[0].config(text=str(i))
            for w in children:
                try:
                    w.config(bg=bg)
                except Exception:
                    pass

    def _abrir_varios(self):
        """Ventana emergente para agregar artículos varios con nombre y precio libre."""
        win = tk.Toplevel(self)
        win.title("📦  Artículos Varios")
        win.configure(bg="#ffffff")
        win.resizable(False, False)
        win.grab_set()
        w, h = 600, 520
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        # ── Encabezado ────────────────────────────────────────────
        hdr = tk.Frame(win, bg="#1a3f6b", pady=20, padx=28)
        hdr.pack(fill="x", side="top")
        tk.Label(hdr, text="📦", font=("Segoe UI", 22),
                 bg="#1a3f6b", fg="#d4e4f5").pack(side="left")
        hdr_txt = tk.Frame(hdr, bg="#1a3f6b")
        hdr_txt.pack(side="left", padx=(12, 0))
        tk.Label(hdr_txt, text="Artículos Varios",
                 font=("Segoe UI", 15, "bold"),
                 bg="#1a3f6b", fg="#ffffff").pack(anchor="w")
        tk.Label(hdr_txt, text="Artículos pequeños — indica el nombre y su valor en $",
                 font=("Segoe UI", 9),
                 bg="#1a3f6b", fg="#a0c0e0").pack(anchor="w")

        # ── Pie: Total + Botones ──────────────────────────────────
        pie = tk.Frame(win, bg="#ffffff", padx=28, pady=10)
        pie.pack(fill="x", side="bottom")

        filas_varios_popup = []
        lbl_total_varios = None

        def _confirmar():
            agregados = 0
            for nombre, v_precio, v_cant, _ in filas_varios_popup:
                try:
                    cant = int(v_cant.get() or 0)
                except ValueError:
                    cant = 0
                if cant <= 0:
                    continue
                try:
                    precio = float(v_precio.get() or 0)
                except ValueError:
                    precio = 0.0
                if precio <= 0:
                    messagebox.showwarning("Precio requerido",
                        f"Ingresa el precio para «{nombre.get()}» antes de agregar.",
                        parent=win)
                    return
                self._agregar_fila_vario(nombre.get().strip() or "Artículo", cant, precio)
                agregados += 1
            win.destroy()
            self._calcular_totales()
            if agregados == 0:
                messagebox.showinfo("Sin artículos",
                                    "No se ingresó cantidad en ningún artículo.")

        # Total
        tot_frame = tk.Frame(pie, bg="#1a3f6b", padx=16, pady=12)
        tot_frame.pack(fill="x", pady=(0, 8))
        tk.Label(tot_frame, text="TOTAL VARIOS  →",
                 font=("Segoe UI", 9), bg="#1a3f6b", fg="#a0c0e0").pack(side="right")
        lbl_total_varios = tk.Label(tot_frame, text="$ 0.00",
                                    font=("Segoe UI", 18, "bold"),
                                    bg="#1a3f6b", fg="#ffffff")
        lbl_total_varios.pack(side="right", padx=(0, 14))

        tk.Frame(pie, bg="#eeede8", height=1).pack(fill="x", pady=(0, 10))

        btn_bar = tk.Frame(pie, bg="#ffffff")
        btn_bar.pack(fill="x")
        tk.Button(btn_bar, text="✓  Agregar al envío",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#1a3f6b", fg="#ffffff",
                  pady=8, padx=20, cursor="hand2",
                  command=_confirmar).pack(side="right")
        tk.Button(btn_bar, text="Cancelar", font=("Segoe UI", 9), bd=0,
                  bg="#f1efe8", fg="#5f5e5a",
                  pady=8, padx=14, cursor="hand2",
                  command=win.destroy).pack(side="left")

        # ── Cuerpo ────────────────────────────────────────────────
        body = tk.Frame(win, bg="#ffffff", padx=28, pady=16)
        body.pack(fill="both", expand=True, side="top")

        hdr_tbl = tk.Frame(body, bg="#2a5a8a", padx=10, pady=7)
        hdr_tbl.pack(fill="x")
        hdr_tbl.columnconfigure(0, weight=1)
        for col, txt, ancho in [(0, "Artículo", 0), (1, "Precio unit.", 10), (2, "Cantidad", 9), (3, "Importe", 10)]:
            kw = {} if ancho == 0 else {"width": ancho}
            tk.Label(hdr_tbl, text=txt, font=("Segoe UI", 8, "bold"),
                     bg="#2a5a8a", fg="#d4e4f5", anchor="w", **kw).grid(
                row=0, column=col, padx=6, sticky="ew")

        scroll_container = tk.Frame(body, bg="#f0f5fb")
        scroll_container.pack(fill="both", expand=True, pady=(0, 12))

        canvas_v = tk.Canvas(scroll_container, bg="#f0f5fb",
                              highlightthickness=0, height=280)
        vsb_v = ttk.Scrollbar(scroll_container, orient="vertical",
                               command=canvas_v.yview)
        canvas_v.configure(yscrollcommand=vsb_v.set)
        vsb_v.pack(side="right", fill="y")
        canvas_v.pack(side="left", fill="both", expand=True)

        tbl_frame = tk.Frame(canvas_v, bg="#f0f5fb")
        tbl_win_id = canvas_v.create_window((0, 0), window=tbl_frame, anchor="nw")
        tbl_frame.columnconfigure(0, weight=1)

        def _on_tbl_configure(e):
            canvas_v.configure(scrollregion=canvas_v.bbox("all"))
        def _on_canvas_resize(e):
            canvas_v.itemconfig(tbl_win_id, width=e.width)
        tbl_frame.bind("<Configure>", _on_tbl_configure)
        canvas_v.bind("<Configure>", _on_canvas_resize)

        def _on_mousewheel(event):
            canvas_v.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas_v.bind("<MouseWheel>", _on_mousewheel)
        tbl_frame.bind("<MouseWheel>", _on_mousewheel)

        def _recalcular(*_):
            total = 0.0
            for nombre, v_precio, v_cant, lbl_imp in filas_varios_popup:
                try:
                    p = float(v_precio.get() or 0)
                    c = int(v_cant.get() or 0)
                    imp = c * p
                except (ValueError, TypeError):
                    imp = 0.0
                total += imp
                lbl_imp.config(text=f"$ {imp:,.2f}",
                               fg="#1a3f6b" if imp > 0 else "#aaa9a5")
            lbl_total_varios.config(text=f"$ {total:,.2f}")

        # 5 filas iniciales vacías
        for i in range(1, 6):
            bg = "#ffffff" if i % 2 == 0 else "#f0f5fb"
            row = tk.Frame(tbl_frame, bg=bg,
                           highlightthickness=1, highlightbackground="#d0dff0")
            row.pack(fill="x", pady=(0, 1))
            row.columnconfigure(0, weight=1)

            v_nombre = tk.StringVar()
            e_nombre = tk.Entry(row, textvariable=v_nombre, font=("Segoe UI", 10),
                                relief="flat", bg=bg, fg="#1a2a40",
                                highlightthickness=1, highlightbackground="#d0dff0")
            e_nombre.grid(row=0, column=0, padx=(10, 4), pady=7, sticky="ew")

            v_precio = tk.StringVar()
            e_precio = tk.Entry(row, textvariable=v_precio, width=8,
                                font=("Segoe UI", 9), justify="center",
                                relief="flat", bg="#f0f5fb", fg="#1a3f6b",
                                highlightthickness=1, highlightbackground="#c0d5ea")
            e_precio.grid(row=0, column=1, padx=4, pady=7)
            v_precio.trace_add("write", _recalcular)

            v_cant = tk.StringVar(value="0")
            sp = tk.Spinbox(row, textvariable=v_cant, from_=0, to=999,
                            width=6, font=("Segoe UI", 11, "bold"),
                            justify="center", relief="flat",
                            bg="#e0ecf5", fg="#1a3f6b",
                            buttonbackground="#c0d5ea",
                            highlightthickness=1, highlightbackground="#c0d5ea")
            sp.grid(row=0, column=2, padx=8, pady=5)

            lbl_imp = tk.Label(row, text="$ 0.00", font=("Segoe UI", 10, "bold"),
                               bg=bg, fg="#aaa9a5", width=9, anchor="e")
            lbl_imp.grid(row=0, column=3, padx=(4, 10), pady=7)

            v_cant.trace_add("write", _recalcular)
            filas_varios_popup.append((v_nombre, v_precio, v_cant, lbl_imp))
            row.bind("<MouseWheel>", _on_mousewheel)

        def _agregar_5_mas():
            inicio = len(filas_varios_popup) + 1
            for i in range(inicio, inicio + 5):
                bg = "#ffffff" if i % 2 == 0 else "#f0f5fb"
                row = tk.Frame(tbl_frame, bg=bg,
                               highlightthickness=1, highlightbackground="#d0dff0")
                row.pack(fill="x", pady=(0, 1))
                row.columnconfigure(0, weight=1)

                v_nombre = tk.StringVar()
                e_nombre = tk.Entry(row, textvariable=v_nombre, font=("Segoe UI", 10),
                                    relief="flat", bg=bg, fg="#1a2a40",
                                    highlightthickness=1, highlightbackground="#d0dff0")
                e_nombre.grid(row=0, column=0, padx=(10, 4), pady=7, sticky="ew")

                v_precio = tk.StringVar()
                e_precio = tk.Entry(row, textvariable=v_precio, width=8,
                                    font=("Segoe UI", 9), justify="center",
                                    relief="flat", bg="#f0f5fb", fg="#1a3f6b",
                                    highlightthickness=1, highlightbackground="#c0d5ea")
                e_precio.grid(row=0, column=1, padx=4, pady=7)
                v_precio.trace_add("write", _recalcular)

                v_cant = tk.StringVar(value="0")
                sp = tk.Spinbox(row, textvariable=v_cant, from_=0, to=999,
                                width=6, font=("Segoe UI", 11, "bold"),
                                justify="center", relief="flat",
                                bg="#e0ecf5", fg="#1a3f6b",
                                buttonbackground="#c0d5ea",
                                highlightthickness=1, highlightbackground="#c0d5ea")
                sp.grid(row=0, column=2, padx=8, pady=5)

                lbl_imp = tk.Label(row, text="$ 0.00", font=("Segoe UI", 10, "bold"),
                                   bg=bg, fg="#aaa9a5", width=9, anchor="e")
                lbl_imp.grid(row=0, column=3, padx=(4, 10), pady=7)

                v_cant.trace_add("write", _recalcular)
                filas_varios_popup.append((v_nombre, v_precio, v_cant, lbl_imp))
                row.bind("<MouseWheel>", _on_mousewheel)
            canvas_v.update_idletasks()
            canvas_v.yview_moveto(1.0)

        btn_add = tk.Frame(body, bg="#ffffff")
        btn_add.pack(fill="x")
        tk.Button(btn_add, text="＋  5 filas más", font=("Segoe UI", 9), bd=0,
                  bg="#e0ecf5", fg="#1a3f6b", pady=6, padx=12, cursor="hand2",
                  command=_agregar_5_mas).pack(side="left")

    def _renumerar(self):
        for i, item in enumerate(self.filas_articulos, 1):
            row = item[0]
            bg = "#ffffff" if i % 2 == 1 else "#f4faf7"
            row.config(bg=bg, highlightbackground="#e8f0ec")
            for w in row.winfo_children():
                try:
                    w.config(bg=bg)
                except Exception:
                    pass
            lbl = row.winfo_children()[0]
            lbl.config(text=f"{i}")

    def _agregar_fila_peso(self, desc, peso):
        """Agrega una fila a la tabla separada de envíos por peso."""
        # Mostrar la sección si estaba oculta
        if not self.peso_section.winfo_ismapped():
            self.peso_section.pack(fill="x", before=self.lbl_total_envio.master)

        i = len(self.filas_peso) + 1
        importe = peso * PRECIO_LB
        bg = "#ffffff" if i % 2 == 1 else "#fff3e6"

        row = tk.Frame(self.peso_filas_frame, bg=bg, pady=3)
        row.pack(fill="x")

        tk.Label(row, text=str(i), font=("Segoe UI", 8), bg=bg, fg="#aaa", width=3,
                 anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=desc, font=("Segoe UI", 9), bg=bg, fg="#1a1a1a",
                 anchor="w").pack(side="left", padx=4, expand=True, fill="x")
        tk.Label(row, text=f"{peso} lb", font=("Segoe UI", 9), bg=bg, fg="#4a2000",
                 width=10, anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=f"$ {int(importe):,}", font=("Segoe UI", 9, "bold"), bg=bg,
                 fg="#633806", width=10, anchor="e").pack(side="left", padx=4)

        fila = (row, desc, peso)
        self.filas_peso.append(fila)

        def _del(r=row, f=fila):
            r.destroy()
            if f in self.filas_peso:
                self.filas_peso.remove(f)
            self._renumerar_peso()
            self._calcular_totales()
            if not self.filas_peso:
                self.peso_section.pack_forget()

        tk.Button(row, text="✕", font=("Segoe UI", 8, "bold"), bd=0,
                  bg="#fde8e8", fg="#c0392b", width=3, cursor="hand2",
                  command=_del).pack(side="left", padx=(2, 8))

        self._calcular_totales()

    def _renumerar_peso(self):
        for i, (row, _, _) in enumerate(self.filas_peso, 1):
            bg = "#ffffff" if i % 2 == 1 else "#fff3e6"
            row.config(bg=bg)
            children = row.winfo_children()
            if children:
                children[0].config(text=str(i))
            for w in children:
                try:
                    w.config(bg=bg)
                except Exception:
                    pass

    def _agregar_fila_med(self, nombre, cant, precio):
        """Agrega una fila a la tabla separada de medicamentos."""
        if not self.med_section.winfo_ismapped():
            self.med_section.pack(fill="x", before=self.lbl_total_envio.master)

        i = len(self.filas_med) + 1
        importe = cant * precio
        bg = "#ffffff" if i % 2 == 1 else "#f8f2fd"

        row = tk.Frame(self.med_filas_frame, bg=bg, pady=3)
        row.pack(fill="x")

        tk.Label(row, text=str(i), font=("Segoe UI", 8), bg=bg, fg="#aaa", width=3,
                 anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=nombre, font=("Segoe UI", 9), bg=bg, fg="#2c1a40",
                 anchor="w").pack(side="left", padx=4, expand=True, fill="x")
        tk.Label(row, text=f"×{cant:g}", font=("Segoe UI", 9, "bold"), bg=bg, fg="#6b2fa0",
                 width=5, anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=f"${int(precio)}", font=("Segoe UI", 9), bg=bg, fg="#8e44c4",
                 width=8, anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=f"$ {int(importe):,}", font=("Segoe UI", 9, "bold"), bg=bg,
                 fg="#6b2fa0", width=10, anchor="e").pack(side="left", padx=4)

        fila = (row, nombre, cant, precio)
        self.filas_med.append(fila)

        def _del(r=row, f=fila):
            r.destroy()
            if f in self.filas_med:
                self.filas_med.remove(f)
            self._renumerar_med()
            self._calcular_totales()
            if not self.filas_med:
                self.med_section.pack_forget()

        tk.Button(row, text="✕", font=("Segoe UI", 8, "bold"), bd=0,
                  bg="#fde8e8", fg="#c0392b", width=3, cursor="hand2",
                  command=_del).pack(side="left", padx=(2, 8))

        self._calcular_totales()

    def _renumerar_med(self):
        for i, (row, _, _, _) in enumerate(self.filas_med, 1):
            bg = "#ffffff" if i % 2 == 1 else "#f8f2fd"
            row.config(bg=bg)
            children = row.winfo_children()
            if children:
                children[0].config(text=str(i))
            for w in children:
                try:
                    w.config(bg=bg)
                except Exception:
                    pass

    def _agregar_fila_vario(self, nombre, cant, precio):
        """Agrega una fila a la tabla separada de artículos varios."""
        if not self.varios_section.winfo_ismapped():
            self.varios_section.pack(fill="x", before=self.lbl_total_envio.master)

        i = len(self.filas_varios) + 1
        importe = cant * precio
        bg = "#ffffff" if i % 2 == 1 else "#f0f5fb"

        row = tk.Frame(self.varios_filas_frame, bg=bg, pady=3)
        row.pack(fill="x")

        tk.Label(row, text=str(i), font=("Segoe UI", 8), bg=bg, fg="#aaa", width=3,
                 anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=nombre, font=("Segoe UI", 9), bg=bg, fg="#1a2a40",
                 anchor="w").pack(side="left", padx=4, expand=True, fill="x")
        tk.Label(row, text=f"×{cant}", font=("Segoe UI", 9, "bold"), bg=bg, fg="#1a3f6b",
                 width=5, anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=f"${int(precio)}", font=("Segoe UI", 9), bg=bg, fg="#2a5a8a",
                 width=8, anchor="center").pack(side="left", padx=4)
        tk.Label(row, text=f"$ {int(importe):,}", font=("Segoe UI", 9, "bold"), bg=bg,
                 fg="#1a3f6b", width=10, anchor="e").pack(side="left", padx=4)

        fila = (row, nombre, cant, precio)
        self.filas_varios.append(fila)

        def _del(r=row, f=fila):
            r.destroy()
            if f in self.filas_varios:
                self.filas_varios.remove(f)
            self._renumerar_vario()
            self._calcular_totales()
            if not self.filas_varios:
                self.varios_section.pack_forget()

        tk.Button(row, text="✕", font=("Segoe UI", 8, "bold"), bd=0,
                  bg="#fde8e8", fg="#c0392b", width=3, cursor="hand2",
                  command=_del).pack(side="left", padx=(2, 8))

        self._calcular_totales()

    def _renumerar_vario(self):
        for i, (row, _, _, _) in enumerate(self.filas_varios, 1):
            bg = "#ffffff" if i % 2 == 1 else "#f0f5fb"
            row.config(bg=bg)
            children = row.winfo_children()
            if children:
                children[0].config(text=str(i))
            for w in children:
                try:
                    w.config(bg=bg)
                except Exception:
                    pass

    def _calcular_totales(self):
        total = 0.0
        count = 0
        for item in self.filas_articulos:
            row_frame, v_tipo, v_desc, v_cant, v_dato = item
            if v_desc.get().strip():
                count += 1
                try:
                    c = int(v_cant.get()) if v_cant.get() else 1
                    d = float(v_dato.get()) if v_dato.get() else 0
                    if v_tipo.get() == "producto":
                        total += c * d * PRECIO_LB
                    else:
                        total += c * d
                except Exception:
                    pass

        for _, desc, peso in self.filas_peso:
            count += 1
            total += peso * PRECIO_LB

        for _, nombre, cant, precio in self.filas_med:
            count += 1
            total += cant * precio

        for _, nombre, cant, precio in self.filas_doc:
            count += 1
            total += cant * precio

        for _, nombre, cant, precio in getattr(self, 'filas_varios', []):
            count += 1
            total += cant * precio

        # Sumar correo externo si tiene valor
        try:
            correo_val = float(getattr(self, 'v_correo_valor', tk.StringVar()).get() or 0)
            total += correo_val
        except (ValueError, AttributeError):
            pass

        self.lbl_cant_articulos.config(text=f"{count} artículos")
        self.lbl_total_envio.config(text=f"$ {int(total):,}")

    def _seccion_notas(self):
        body = self._card("NOTAS", "📝")
        body.columnconfigure(0, weight=1)

        tk.Label(body, text="Notas", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=0, sticky="w", pady=(4, 0))
        self.v_nota = tk.StringVar()
        ttk.Entry(body, textvariable=self.v_nota, font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="ew", pady=(2, 8))

    def _autocomplete(self, var, entry, rol):
        def on_key(*a):
            term = var.get()
            if len(term) < 1:
                entry.config(values=[])
                return
            clientes = self.db.listar_clientes(term, rol)
            nombres = [c["nombre"] for c in clientes if c["nombre"].strip()]
            if nombres:
                entry.config(values=nombres)
            else:
                entry.config(values=[])
        if not hasattr(self, "_autocomplete_traces"):
            self._autocomplete_traces = set()
        if id(var) not in self._autocomplete_traces:
            var.trace_add("write", on_key)
            self._autocomplete_traces.add(id(var))

    def _seccion_estado_pago(self):
        body = self._card("ESTADO DE PAGO", "💳")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        self.v_estado_pago = tk.StringVar(value="Pagado")

        # Contenedor de los dos botones radio
        opciones_frame = tk.Frame(body, bg="#ffffff")
        opciones_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(4, 8))

        def _radio_btn(parent, texto, valor, color_sel, color_txt):
            """Crea un radio button estilizado como tarjeta."""
            rb = tk.Radiobutton(
                parent,
                text=texto,
                variable=self.v_estado_pago,
                value=valor,
                font=("Segoe UI", 10, "bold"),
                bg="#ffffff",
                fg=color_txt,
                selectcolor=color_sel,
                activebackground="#ffffff",
                activeforeground=color_txt,
                indicatoron=True,
                cursor="hand2",
                command=self._actualizar_estilo_pago,
            )
            return rb

        self.rb_pagado = _radio_btn(
            opciones_frame,
            "✅  Pagado  — monto completo recibido",
            "Pagado",
            "#e1f5ee",
            "#085041",
        )
        self.rb_pagado.pack(side="left", padx=(0, 20), pady=4)

        self.rb_abono = _radio_btn(
            opciones_frame,
            "💵  Abono  — pago parcial",
            "Abono",
            "#e6f1fb",
            "#0c447c",
        )
        self.rb_abono.pack(side="left", padx=(0, 20), pady=4)

        self.rb_pendiente = _radio_btn(
            opciones_frame,
            "⏳  Pendiente  — sin pago aún",
            "Pendiente",
            "#faeeda",
            "#633806",
        )
        self.rb_pendiente.pack(side="left", pady=4)

        # Campo de abono (visible solo cuando se elige "Abono")
        self.abono_frame = tk.Frame(body, bg="#ffffff")
        self.abono_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        tk.Label(self.abono_frame, text="Monto abonado ($)",
                 font=("Segoe UI", 9), bg="#ffffff", fg="#888780").pack(anchor="w")
        self.v_abono_monto = tk.StringVar(value="")
        self.ent_abono = ttk.Entry(self.abono_frame, textvariable=self.v_abono_monto,
                                    width=18, font=("Segoe UI", 10))
        self.ent_abono.pack(anchor="w", pady=(2, 4))

        # Ocultar campo de abono por defecto (inicia en "Pagado")
        self.abono_frame.grid_remove()

    def _actualizar_estilo_pago(self):
        """Muestra u oculta el campo de monto abonado según la opción elegida."""
        if self.v_estado_pago.get() == "Abono":
            self.abono_frame.grid()
            self.ent_abono.focus_set()
        else:
            self.abono_frame.grid_remove()
            self.v_abono_monto.set("")

    def _seccion_botones(self):
        frame = tk.Frame(self.inner, bg="#f5f5f0", pady=16)
        frame.pack(fill="x")

        tk.Button(frame, text="🗑  Limpiar",
                  font=("Segoe UI", 10), bd=0,
                  bg="#f1efe8", fg="#5f5e5a",
                  pady=10, padx=16, cursor="hand2",
                  command=self._limpiar).pack(side="left", padx=(0, 8))

        # Botón guardar + imprimir ticket térmico
        tk.Button(frame, text="🧾  Guardar e imprimir ticket",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#fff3cd", fg="#856404",
                  pady=10, padx=16, cursor="hand2",
                  command=self._guardar_e_imprimir_ticket).pack(side="left", padx=(0, 8))

        # Botón guardar + abrir con la app del sistema para imprimir
        tk.Button(frame, text="🖨  Guardar e imprimir",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#e6f1fb", fg="#0c447c",
                  pady=12, padx=20, cursor="hand2",
                  command=self._guardar_e_imprimir).pack(side="right", padx=(8, 0))

        tk.Button(frame, text="💾  Guardar encomienda",
                  font=("Segoe UI", 11, "bold"), bd=0,
                  bg="#0f6e56", fg="white",
                  pady=12, padx=24, cursor="hand2",
                  command=self._guardar).pack(side="right")


    # ── Vista previa y utilidades ─────────────────────────────────────────────

    def _recopilar_datos(self):
        """
        Valida el formulario y devuelve (datos_dict, articulos_list, total_float).
        Lanza ValueError con un mensaje si falta algo requerido.
        """
        if not self.v_ent_nombre.get().strip():
            raise ValueError("Ingrese el nombre del remitente.")
        if not self.v_rec_nombre.get().strip():
            raise ValueError("Ingrese el nombre del destinatario.")

        articulos = []
        total = 0.0
        peso_total = 0.0

        # ── Filas genéricas ────────────────────────────────────────────
        for _, vt, vd, vc, vdat in getattr(self, 'filas_articulos', []):
            d = vd.get().strip()
            if not d:
                continue
            try:
                cantidad = int(float(vc.get())) if vc.get() else 1
                dato = float(vdat.get()) if vdat.get() else 0
                if vt.get() == "producto":
                    peso_lb = str(dato)
                    val_str = "0"
                    total += cantidad * dato * PRECIO_LB
                    peso_total += cantidad * dato
                else:
                    peso_lb = "0"
                    val_str = str(dato)
                    total += cantidad * dato
            except Exception:
                peso_lb = "0"
                val_str = "0"
            articulos.append({
                "descripcion": d,
                "cantidad": vc.get() or "1",
                "peso_lb": peso_lb,
                "valor": val_str,
                "tipo": vt.get(),
            })

        # Incluir también los artículos de la tabla de peso
        for _, desc, peso in getattr(self, 'filas_peso', []):
            total += peso * PRECIO_LB
            peso_total += peso
            articulos.append({
                "descripcion": desc,
                "cantidad": "1",
                "peso_lb": str(peso),
                "valor": "0",
                "tipo": "producto",
            })

        # Incluir también los medicamentos
        for _, nombre, cant, precio in getattr(self, 'filas_med', []):
            total += cant * precio
            articulos.append({
                "descripcion": nombre,
                "cantidad": str(cant),
                "peso_lb": "0",
                "valor": str(precio),
                "tipo": "medicamento",
            })

        # Incluir también los documentos
        for _, nombre, cant, precio in getattr(self, 'filas_doc', []):
            total += cant * precio
            articulos.append({
                "descripcion": nombre,
                "cantidad": str(cant),
                "peso_lb": "0",
                "valor": str(precio),
                "tipo": "documento",
            })

        # Incluir también los artículos varios
        for _, nombre, cant, precio in getattr(self, 'filas_varios', []):
            total += cant * precio
            articulos.append({
                "descripcion": nombre,
                "cantidad": str(cant),
                "peso_lb": "0",
                "valor": str(precio),
                "tipo": "vario",
            })

        # Incluir correo externo si tiene valor
        correo_lugar = getattr(self, 'v_correo_lugar', tk.StringVar()).get().strip()
        try:
            correo_val = float(getattr(self, 'v_correo_valor', tk.StringVar()).get() or 0)
        except ValueError:
            correo_val = 0.0
        if correo_val > 0:
            total += correo_val
            articulos.append({
                "descripcion": f"Correo externo{(' — ' + correo_lugar) if correo_lugar else ''}",
                "cantidad": "1",
                "peso_lb": "0",
                "valor": str(correo_val),
                "tipo": "documento",
            })

        if not articulos:
            raise ValueError("Agregue al menos un artículo.")

        estado_pago = self.v_estado_pago.get()
        if estado_pago == "Abono":
            try:
                abono = float(self.v_abono_monto.get().replace(",", "."))
                if abono <= 0:
                    raise ValueError("Ingrese un monto de abono válido.")
                if abono > total:
                    raise ValueError(
                        f"El abono (${abono:,.2f}) no puede superar el total (${total:,.2f}).")
            except (ValueError, AttributeError) as exc:
                raise ValueError(str(exc)) from exc
        elif estado_pago == "Pendiente":
            abono = 0.0
        else:
            abono = total

        datos = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ent_nombre":  self.v_ent_nombre.get().strip(),
            "ent_tel":     self.v_ent_tel.get().strip(),
            "ent_dir":     self.v_ent_dir.get().strip(),
            "rec_nombre":  self.v_rec_nombre.get().strip(),
            "rec_tel":     self.v_rec_tel.get().strip(),
            "rec_dir":     self.v_rec_dir.get().strip(),
            "moneda":      "$",
            "peso_total":  peso_total,
            "total":       f"{total:.2f}",
            "abono":       f"{abono:.2f}",
            "restante":    f"{max(0, total - abono):.2f}",
            "cajero":      "",
            "tipo_pago":   "Efectivo",
            "nota":        self.v_nota.get().strip(),
            "destino_usa": self.v_destino_usa.get(),
            "nota_interna": "",
            "estado":      estado_pago,
        }
        return datos, articulos, total, abono


    def _guardar_e_imprimir(self):
        """
        Guarda la encomienda y abre el recibo con la aplicación
        predeterminada del sistema (SumatraPDF, Acrobat, el visor de
        Windows, etc.) para que el usuario imprima desde ahí.
        """
        # ── 1. Validar y guardar ──────────────────────────────────────────────
        try:
            datos, articulos, total, abono = self._recopilar_datos()
        except ValueError as e:
            messagebox.showwarning("Datos incompletos", str(e))
            return

        try:
            envio_id = self.db.crear_envio(
                datos, articulos,
                self.app.config_mgr.get("prefijo_codigo", "MERC"))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")
            return

        self.app.mark_dirty(["historial", "kpi", "reportes", "cobrar", "arqueo"])

        # Obtener código del envío creado
        try:
            env = self.db.obtener_envio(envio_id)
            codigo = env.get("codigo", str(envio_id)) if env else str(envio_id)
        except Exception:
            codigo = str(envio_id)

        if not _IMPRIMIR_OK or not envio_id:
            self._limpiar()
            messagebox.showinfo("✓", f"Encomienda registrada.\nCódigo: {codigo}")
            return

        # ── 2. Generar PDF y abrir en visor predeterminado ────────────────────
        try:
            ruta = imprimir_recibo(self.db, envio_id, abrir=True)
            self._limpiar()
        except Exception as ex:
            self._limpiar()
            messagebox.showerror("Error", f"No se pudo generar el PDF:\n{ex}")
            return

        messagebox.showinfo("✓", f"Encomienda registrada.\nCódigo: {codigo}")

    def _guardar_e_imprimir_ticket(self):
        """Guarda la encomienda y genera un ticket térmico PDF para imprimir."""
        try:
            datos, articulos, total, abono = self._recopilar_datos()
        except ValueError as e:
            messagebox.showwarning("Datos incompletos", str(e))
            return

        try:
            envio_id = self.db.crear_envio(
                datos, articulos,
                self.app.config_mgr.get("prefijo_codigo", "MERC"))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")
            return

        self.app.mark_dirty(["historial", "kpi", "reportes", "cobrar", "arqueo"])

        try:
            env = self.db.obtener_envio(envio_id)
            codigo = env.get("codigo", str(envio_id)) if env else str(envio_id)
        except Exception:
            codigo = str(envio_id)

        # Generar ticket térmico PDF (80mm de ancho)
        try:
            from modules.imprimir import _carpeta_salida, EMPRESA_NOMBRE, PRECIO_LB
            from reportlab.lib.units import cm
            from reportlab.pdfgen import canvas as rl_canvas

            ruta = os.path.join(_carpeta_salida(), f"ticket_{codigo}.pdf")
            ancho_ticket = 8 * cm
            alto_ticket = 20 * cm
            c = rl_canvas.Canvas(ruta, pagesize=(ancho_ticket, alto_ticket))

            y = alto_ticket - 0.5 * cm
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(ancho_ticket / 2, y, EMPRESA_NOMBRE)
            y -= 0.5 * cm
            c.setFont("Helvetica", 7)
            c.drawCentredString(ancho_ticket / 2, y, "Envíos rápidos y seguros")
            y -= 0.6 * cm
            c.line(0.3 * cm, y, ancho_ticket - 0.3 * cm, y)
            y -= 0.5 * cm

            c.setFont("Helvetica-Bold", 9)
            c.drawString(0.5 * cm, y, f"Código: {codigo}")
            y -= 0.4 * cm
            c.setFont("Helvetica", 7)
            c.drawString(0.5 * cm, y, f"Fecha: {env.get('fecha', '')}")
            y -= 0.3 * cm
            c.drawString(0.5 * cm, y, f"Estado: {env.get('estado', '')}")
            y -= 0.5 * cm
            c.line(0.3 * cm, y, ancho_ticket - 0.3 * cm, y)
            y -= 0.5 * cm

            c.setFont("Helvetica-Bold", 8)
            c.drawString(0.5 * cm, y, "ENTREGA:")
            c.setFont("Helvetica", 7)
            c.drawString(2.5 * cm, y, env.get('ent_nombre', '—'))
            y -= 0.35 * cm
            c.setFont("Helvetica-Bold", 8)
            c.drawString(0.5 * cm, y, "RECIBE:")
            c.setFont("Helvetica", 7)
            c.drawString(2.5 * cm, y, env.get('rec_nombre', '—'))
            y -= 0.5 * cm
            c.line(0.3 * cm, y, ancho_ticket - 0.3 * cm, y)
            y -= 0.5 * cm

            c.setFont("Helvetica-Bold", 8)
            c.drawString(0.5 * cm, y, "ARTÍCULOS:")
            y -= 0.4 * cm
            c.setFont("Helvetica", 7)
            for art in articulos:
                desc = art.get("descripcion", "")[:25]
                c.drawString(0.5 * cm, y, f"• {desc}")
                y -= 0.3 * cm
                if y < 2 * cm:
                    break
            y -= 0.3 * cm
            c.line(0.3 * cm, y, ancho_ticket - 0.3 * cm, y)
            y -= 0.5 * cm

            c.setFont("Helvetica-Bold", 10)
            c.drawRightString(ancho_ticket - 0.5 * cm, y, f"TOTAL: ${total:,.2f}")
            y -= 0.35 * cm
            c.setFont("Helvetica", 7)
            c.drawRightString(ancho_ticket - 0.5 * cm, y, f"Abono: ${abono:,.2f}")
            y -= 0.35 * cm
            restante = max(0, total - abono)
            c.drawRightString(ancho_ticket - 0.5 * cm, y, f"Restante: ${restante:,.2f}")
            y -= 0.6 * cm
            c.line(0.3 * cm, y, ancho_ticket - 0.3 * cm, y)
            y -= 0.5 * cm

            c.setFont("Helvetica", 6)
            c.drawCentredString(ancho_ticket / 2, y, "¡Gracias por su preferencia!")
            c.save()

            self._limpiar()
            import sys, subprocess
            if sys.platform.startswith("win"):
                os.startfile(ruta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as ex:
            self._limpiar()
            messagebox.showerror("Error", f"No se pudo generar el ticket:\n{ex}")
            return

        messagebox.showinfo("✓", f"Encomienda registrada.\nCódigo: {codigo}")

    def _guardar(self):
        """Valida, guarda y limpia el formulario."""
        try:
            datos, articulos, total, abono = self._recopilar_datos()
        except ValueError as e:
            messagebox.showwarning("Datos incompletos", str(e))
            return
        try:
            codigo = self.db.crear_envio(datos, articulos, self.app.config_mgr.get("prefijo_codigo", "MERC"))
            messagebox.showinfo("✓", f"Encomienda registrada.\nCódigo: {codigo}")
            self.app.mark_dirty(["historial", "kpi", "reportes", "cobrar", "arqueo"])
            self._limpiar()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")

    def _limpiar(self):
        for var in [self.v_ent_nombre, self.v_ent_tel, self.v_ent_dir,
                    self.v_rec_nombre, self.v_rec_tel, self.v_rec_dir,
                    self.v_nota]:
            var.set("")
        self.v_destino_usa.set("Sin asignar")
        self.v_correo_lugar.set("")
        self.v_correo_valor.set("")
        self.v_estado_pago.set("Pagado")
        self.v_abono_monto.set("")
        self.abono_frame.grid_remove()
        for w in self.articulos_frame.winfo_children():
            w.destroy()
        self.filas_articulos.clear()
        for w in self.med_filas_frame.winfo_children():
            w.destroy()
        self.filas_med.clear()
        self.med_section.pack_forget()
        for w in self.doc_filas_frame.winfo_children():
            w.destroy()
        self.filas_doc.clear()
        self.doc_section.pack_forget()
        for w in self.varios_filas_frame.winfo_children():
            w.destroy()
        self.filas_varios.clear()
        self.varios_section.pack_forget()
        for w in self.peso_filas_frame.winfo_children():
            w.destroy()
        self.filas_peso.clear()
        self.peso_section.pack_forget()
        self._calcular_totales()

    def refresh(self):
        pass
