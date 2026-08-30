"""
==============================================
  modules/historial_clientes.py
  Directorio de clientes con historial de envios
  Muestra nombre, telefono, envios, total
==============================================
"""

import tkinter as tk
from tkinter import ttk
from modules.config import PAGINA_TAMANO


class HistorialClientesFrame(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#f5f5f0")
        self.db = db
        self.app = app
        self._pagina = 1
        self._por_pagina = PAGINA_TAMANO
        self._total_paginas = 1
        self._cliente_sel = None
        self._orden_col = "nombre"
        self._orden_reverso = False
        self._build()

    def _build(self):
        c = self.app.colores

        hdr = tk.Frame(self, bg=c.get("card_bg", "#ffffff"), pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="👤  Historial de clientes",
                 font=("Segoe UI", 14, "bold"),
                 bg=c.get("card_bg", "#ffffff"),
                 fg=c.get("accent", "#0f6e56")).pack(side="left", padx=20)
        self._lbl_resumen = tk.Label(hdr, text="",
                                      font=("Segoe UI", 9),
                                      bg=c.get("card_bg", "#ffffff"),
                                      fg="#888780")
        self._lbl_resumen.pack(side="right", padx=20)

        bar = tk.Frame(self, bg="#f0efe8", padx=14, pady=6)
        bar.pack(fill="x")

        tk.Label(bar, text="🔍  Buscar cliente", font=("Segoe UI", 8),
                 bg="#f0efe8", fg="#888780").pack(side="left", padx=(0, 4))
        self.v_buscar = tk.StringVar()
        self.v_buscar.trace_add("write", lambda *a: self._ir_pagina(1))
        ttk.Entry(bar, textvariable=self.v_buscar,
                  width=28, font=("Segoe UI", 10)).pack(side="left", padx=(0, 12))

        tk.Label(bar, text="📞  Teléfono", font=("Segoe UI", 8),
                 bg="#f0efe8", fg="#888780").pack(side="left", padx=(0, 4))
        self.v_tel = tk.StringVar()
        self.v_tel.trace_add("write", lambda *a: self._ir_pagina(1))
        ttk.Entry(bar, textvariable=self.v_tel,
                  width=16, font=("Segoe UI", 10)).pack(side="left")

        paned = tk.PanedWindow(self, orient="horizontal",
                                bg="#d8d6cf", sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=14, pady=(6, 12))

        left = tk.Frame(paned, bg="#ffffff",
                        highlightthickness=1, highlightbackground="#dddbd4")
        paned.add(left, minsize=400)

        self._build_tree(left)
        self._build_paginacion(left)

        self._detalle_frame = tk.Frame(paned, bg="#ffffff",
                                        highlightthickness=1, highlightbackground="#dddbd4")
        paned.add(self._detalle_frame, minsize=320)
        self._build_detalle_vacio()

        self.refresh()

    def _build_tree(self, parent):
        style = ttk.Style()
        style.configure("Cli.Treeview",
                         font=("Segoe UI", 9), rowheight=28,
                         background="#ffffff", fieldbackground="#ffffff",
                         borderwidth=0)
        style.configure("Cli.Treeview.Heading",
                         font=("Segoe UI", 9, "bold"),
                         background="#f0efe8", relief="flat")
        style.map("Cli.Treeview",
                  background=[("selected", "#d4f5eb")],
                  foreground=[("selected", "#085041")])

        cols = ("nombre", "telefono", "envios", "total_gastado", "ultimo_envio")
        self.tree = ttk.Treeview(parent, columns=cols,
                                  show="headings", selectmode="browse",
                                  style="Cli.Treeview")
        hdrs = [
            ("nombre",       "Nombre",       140, "w"),
            ("telefono",     "Teléfono",     100, "w"),
            ("envios",       "Envíos",        60, "center"),
            ("total_gastado","Total gastado", 95, "e"),
            ("ultimo_envio", "Último envío",  85, "center"),
        ]
        for col, txt, w, anc in hdrs:
            self.tree.heading(col, text=txt,
                              command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=w, minwidth=40, anchor=anc)

        self.tree.tag_configure("par",   background="#f9f9f6")
        self.tree.tag_configure("impar", background="#ffffff")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_seleccionar)

    def _ordenar(self, col):
        if self._orden_col == col:
            self._orden_reverso = not self._orden_reverso
        else:
            self._orden_col = col
            self._orden_reverso = False
        self._cargar_clientes()

    def _build_paginacion(self, parent):
        c = self.app.colores
        pag = tk.Frame(parent, bg=c.get("card_bg", "#f0efe8"), pady=5)
        pag.pack(fill="x")
        self._pag_label = tk.Label(pag, text="", font=("Segoe UI", 8),
                                    bg=c.get("card_bg", "#f0efe8"), fg="#888780")
        self._pag_label.pack(side="left", padx=10)

        def _pbtn(txt, cmd):
            return tk.Button(pag, text=txt, font=("Segoe UI", 8),
                             bd=0, bg=c.get("card_bg", "#f0efe8"), fg="#5f5e5a",
                             pady=2, padx=6, cursor="hand2", command=cmd)

        _pbtn("▶▶ Última",   lambda: self._ir_pagina(self._total_paginas)).pack(side="right", padx=2)
        _pbtn("Siguiente ▶", lambda: self._ir_pagina(self._pagina + 1)).pack(side="right", padx=2)

        self._v_pag_entry = tk.StringVar()
        e_pag = ttk.Entry(pag, textvariable=self._v_pag_entry,
                          width=4, font=("Segoe UI", 8), justify="center")
        e_pag.pack(side="right", padx=2)
        e_pag.bind("<Return>", self._ir_pagina_directa)
        e_pag.bind("<FocusOut>", self._ir_pagina_directa)
        tk.Label(pag, text="Ir a:", font=("Segoe UI", 8),
                 bg=c.get("card_bg", "#f0efe8"), fg="#888780").pack(side="right", padx=(4, 0))

        _pbtn("◀ Anterior", lambda: self._ir_pagina(self._pagina - 1)).pack(side="right", padx=2)
        _pbtn("◀◀ Primera", lambda: self._ir_pagina(1)).pack(side="right", padx=2)

    def _ir_pagina_directa(self, event=None):
        try:
            n = int(self._v_pag_entry.get())
            self._ir_pagina(n)
        except (ValueError, TypeError):
            pass

    def _ir_pagina(self, n):
        if n < 1:
            n = 1
        if n > self._total_paginas:
            n = self._total_paginas
        if n != self._pagina:
            self._pagina = n
            self._cargar_clientes()

    def _build_detalle_vacio(self):
        for w in self._detalle_frame.winfo_children():
            w.destroy()
        tk.Label(self._detalle_frame,
                 text="Selecciona un cliente para ver su historial",
                 font=("Segoe UI", 11), bg="#ffffff", fg="#aaa9a2"
                 ).pack(expand=True)

    def refresh(self):
        self._cliente_sel = None
        self._pagina = 1
        self._cargar_clientes()
        self._build_detalle_vacio()

    def _cargar_clientes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        buscar = self.v_buscar.get().strip()
        tel = self.v_tel.get().strip()
        datos = self.db.obtener_clientes(buscar=buscar, telefono=tel)

        if not datos:
            self._total_paginas = 1
            self._lbl_resumen.config(text="Sin clientes")
            self._pag_label.config(text="Página 1 de 1")
            return

        clave = self._orden_col
        reverse = self._orden_reverso
        if clave == "nombre":
            datos.sort(key=lambda x: (x.get("nombre") or "").lower(), reverse=reverse)
        elif clave == "telefono":
            datos.sort(key=lambda x: (x.get("telefono") or "").lower(), reverse=reverse)
        elif clave == "envios":
            datos.sort(key=lambda x: x.get("envios", 0), reverse=reverse)
        elif clave == "total_gastado":
            datos.sort(key=lambda x: x.get("total_gastado", 0), reverse=reverse)
        elif clave == "ultimo_envio":
            datos.sort(key=lambda x: x.get("ultimo_envio") or "", reverse=reverse)

        total_registros = len(datos)
        self._total_paginas = max(1, (total_registros + self._por_pagina - 1) // self._por_pagina)
        if self._pagina > self._total_paginas:
            self._pagina = self._total_paginas

        inicio = (self._pagina - 1) * self._por_pagina
        fin = inicio + self._por_pagina
        pagina_datos = datos[inicio:fin]

        for i, fila in enumerate(pagina_datos):
            nombre = fila.get("nombre", "")
            telefono = fila.get("telefono", "") or "—"
            envios = fila.get("envios", 0)
            total = fila.get("total_gastado", 0) or 0
            ultimo = (fila.get("ultimo_envio") or "")[:10]

            tag = "par" if i % 2 == 0 else "impar"
            self.tree.insert("", "end", iid=nombre,
                             values=(nombre, telefono, envios,
                                     f"${total:,.2f}", ultimo),
                             tags=(tag,))

        self._lbl_resumen.config(text=f"{total_registros} clientes")
        self._pag_label.config(
            text=f"Página {self._pagina} de {self._total_paginas}  ({total_registros} registros)")

    def _on_seleccionar(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        nombre = sel[0]
        self._cliente_sel = nombre
        self._cargar_detalle(nombre)

    def _cargar_detalle(self, nombre):
        for w in self._detalle_frame.winfo_children():
            w.destroy()

        c = self.app.colores

        envios = self.db.obtener_envios_por_cliente(nombre)

        hdr = tk.Frame(self._detalle_frame, bg=c.get("card_header", "#f0efe8"), pady=10, padx=14)
        hdr.pack(fill="x")

        tel = envios[0].get("ent_tel", "") if envios else ""
        if not tel:
            tel = envios[0].get("rec_tel", "") if envios else ""
        tel_text = f"  📞 {tel}" if tel else ""

        tk.Label(hdr, text=f"👤  {nombre}{tel_text}",
                 font=("Segoe UI", 12, "bold"),
                 bg=c.get("card_header", "#f0efe8"),
                 fg=c.get("card_header_fg", "#0f6e56")).pack(side="left")

        if not envios:
            tk.Label(self._detalle_frame, text="No hay envíos para este cliente",
                     font=("Segoe UI", 10), bg="#ffffff", fg="#aaa9a2"
                     ).pack(expand=True)
            return

        style = ttk.Style()
        style.configure("CliDet.Treeview",
                         font=("Segoe UI", 9), rowheight=24,
                         background="#ffffff", fieldbackground="#ffffff",
                         borderwidth=0)
        style.configure("CliDet.Treeview.Heading",
                         font=("Segoe UI", 8, "bold"),
                         background="#f0efe8", relief="flat")

        tree_frame = tk.Frame(self._detalle_frame, bg="#ffffff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("codigo", "fecha", "recibe", "total", "estado")
        tree = ttk.Treeview(tree_frame, columns=cols,
                             show="headings", selectmode="browse",
                             style="CliDet.Treeview")
        hdrs_det = [
            ("codigo",  "Código",   85, "w"),
            ("fecha",   "Fecha",    80, "w"),
            ("recibe",  "Recibe",  110, "w"),
            ("total",   "Total",    80, "e"),
            ("estado",  "Estado",   75, "center"),
        ]
        for col, txt, w, anc in hdrs_det:
            tree.heading(col, text=txt)
            tree.column(col, width=w, minwidth=35, anchor=anc)

        tree.tag_configure("Pagado",    foreground="#085041", background="#f6fdf9")
        tree.tag_configure("Abono",     foreground="#0c447c", background="#f4f8fd")
        tree.tag_configure("Pendiente", foreground="#7a4800", background="#fdf8f0")
        tree.tag_configure("Cancelado", foreground="#791f1f", background="#fdf3f3")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        for e in envios:
            fecha = (e.get("fecha", "") or "")[:10]
            estado = e.get("estado", "")
            recibe = e.get("rec_nombre", "") if nombre != e.get("rec_nombre", "") else e.get("ent_nombre", "")
            tree.insert("", "end",
                        values=(e.get("codigo", ""), fecha, recibe,
                                f"${e.get('total', 0):,.2f}", estado),
                        tags=(estado,))

        total_vendido = sum(e.get("total", 0) for e in envios)
        total_pagado = sum(e.get("abono", 0) for e in envios)

        pie = tk.Frame(self._detalle_frame, bg=c.get("card_header", "#f0efe8"), pady=8, padx=14)
        pie.pack(fill="x")
        tk.Label(pie, text=f"Envíos: {len(envios)}  |  "
                           f"Total: ${total_vendido:,.2f}  |  "
                           f"Pagado: ${total_pagado:,.2f}",
                 font=("Segoe UI", 9),
                 bg=c.get("card_header", "#f0efe8"),
                 fg=c.get("card_header_fg", "#0f6e56")).pack(side="left")
