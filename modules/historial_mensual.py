"""
==============================================
  modules/historial_mensual.py
  Resumen historico de pedidos por mes
  con detalle al hacer clic
==============================================
"""

import tkinter as tk
from tkinter import ttk
from modules.config import PAGINA_TAMANO


MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


class HistorialMensualFrame(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#f5f5f0")
        self.db = db
        self.app = app
        self._pagina = 1
        self._por_pagina = PAGINA_TAMANO
        self._total_paginas = 1
        self._mes_sel = None
        self._build()

    def _build(self):
        c = self.app.colores

        hdr = tk.Frame(self, bg=c.get("card_bg", "#ffffff"), pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📅  Historial mensual de pedidos",
                 font=("Segoe UI", 14, "bold"),
                 bg=c.get("card_bg", "#ffffff"),
                 fg=c.get("accent", "#0f6e56")).pack(side="left", padx=20)
        self._lbl_resumen = tk.Label(hdr, text="",
                                      font=("Segoe UI", 9),
                                      bg=c.get("card_bg", "#ffffff"),
                                      fg="#888780")
        self._lbl_resumen.pack(side="right", padx=20)

        paned = tk.PanedWindow(self, orient="horizontal",
                                bg="#d8d6cf", sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=14, pady=(6, 12))

        left = tk.Frame(paned, bg="#ffffff",
                        highlightthickness=1, highlightbackground="#dddbd4")
        paned.add(left, minsize=380)

        self._build_tree_resumen(left)
        self._build_paginacion(left)

        self._detalle_frame = tk.Frame(paned, bg="#ffffff",
                                        highlightthickness=1, highlightbackground="#dddbd4")
        paned.add(self._detalle_frame, minsize=300)
        self._build_detalle_vacio()

        self.refresh()

    def _build_tree_resumen(self, parent):
        style = ttk.Style()
        style.configure("Mes.Treeview",
                         font=("Segoe UI", 9), rowheight=28,
                         background="#ffffff", fieldbackground="#ffffff",
                         borderwidth=0)
        style.configure("Mes.Treeview.Heading",
                         font=("Segoe UI", 9, "bold"),
                         background="#f0efe8", relief="flat")
        style.map("Mes.Treeview",
                  background=[("selected", "#d4f5eb")],
                  foreground=[("selected", "#085041")])

        cols = ("mes", "anio", "envios", "total_vendido", "total_pagado", "pendiente")
        self.tree = ttk.Treeview(parent, columns=cols,
                                  show="headings", selectmode="browse",
                                  style="Mes.Treeview")
        hdrs = [
            ("mes",           "Mes",          110, "w"),
            ("anio",          "Año",           60, "center"),
            ("envios",        "Envíos",        65, "center"),
            ("total_vendido", "Vendido",       90, "e"),
            ("total_pagado",  "Pagado",        90, "e"),
            ("pendiente",     "Pendiente",     90, "e"),
        ]
        for col, txt, w, anc in hdrs:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, minwidth=40, anchor=anc)

        self.tree.tag_configure("par",   background="#f9f9f6")
        self.tree.tag_configure("impar", background="#ffffff")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_seleccionar)

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
            self._cargar_resumen()

    def _build_detalle_vacio(self):
        for w in self._detalle_frame.winfo_children():
            w.destroy()
        tk.Label(self._detalle_frame,
                 text="Selecciona un mes para ver el detalle",
                 font=("Segoe UI", 11), bg="#ffffff", fg="#aaa9a2"
                 ).pack(expand=True)

    def refresh(self):
        self._mes_sel = None
        self._pagina = 1
        self._cargar_resumen()
        self._build_detalle_vacio()

    def _cargar_resumen(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        datos = self.db.obtener_resumen_mensual()

        total_registros = len(datos)
        if total_registros == 0:
            self._total_paginas = 1
            self._lbl_resumen.config(text="Sin registros")
            self._pag_label.config(text="Página 1 de 1")
            return

        self._total_paginas = max(1, (total_registros + self._por_pagina - 1) // self._por_pagina)
        if self._pagina > self._total_paginas:
            self._pagina = self._total_paginas

        inicio = (self._pagina - 1) * self._por_pagina
        fin = inicio + self._por_pagina
        pagina_datos = datos[inicio:fin]

        for i, fila in enumerate(pagina_datos):
            mes_num = fila["mes"]
            mes_nombre = MESES_ES.get(mes_num, str(mes_num))
            anio = fila["anio"]
            envios = fila["envios"]
            vendido = fila["total_vendido"] or 0
            pagado = fila["total_pagado"] or 0
            pendiente = fila["pendiente"] or 0

            tag = "par" if i % 2 == 0 else "impar"
            self.tree.insert("", "end", iid=f"{anio}-{mes_num}",
                             values=(mes_nombre, anio, envios,
                                     f"${vendido:,.2f}",
                                     f"${pagado:,.2f}",
                                     f"${pendiente:,.2f}"),
                             tags=(tag,))

        self._lbl_resumen.config(text=f"{total_registros} meses registrados")
        self._pag_label.config(
            text=f"Página {self._pagina} de {self._total_paginas}  ({total_registros} registros)")

    def _on_seleccionar(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        parts = iid.split("-")
        anio = int(parts[0])
        mes = int(parts[1])
        self._mes_sel = (anio, mes)
        self._cargar_detalle(anio, mes)

    def _cargar_detalle(self, anio, mes):
        for w in self._detalle_frame.winfo_children():
            w.destroy()

        c = self.app.colores

        hdr = tk.Frame(self._detalle_frame, bg=c.get("card_header", "#f0efe8"), pady=10, padx=14)
        hdr.pack(fill="x")
        mes_nombre = MESES_ES.get(mes, str(mes))
        tk.Label(hdr, text=f"📋  {mes_nombre} {anio}",
                 font=("Segoe UI", 12, "bold"),
                 bg=c.get("card_header", "#f0efe8"),
                 fg=c.get("card_header_fg", "#0f6e56")).pack(side="left")

        envios = self.db.obtener_envios_por_mes(anio, mes)

        if not envios:
            tk.Label(self._detalle_frame, text="No hay envíos en este mes",
                     font=("Segoe UI", 10), bg="#ffffff", fg="#aaa9a2"
                     ).pack(expand=True)
            return

        style = ttk.Style()
        style.configure("Det.Treeview",
                         font=("Segoe UI", 9), rowheight=24,
                         background="#ffffff", fieldbackground="#ffffff",
                         borderwidth=0)
        style.configure("Det.Treeview.Heading",
                         font=("Segoe UI", 8, "bold"),
                         background="#f0efe8", relief="flat")

        tree_frame = tk.Frame(self._detalle_frame, bg="#ffffff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("codigo", "fecha", "entrega", "recibe", "total", "estado")
        tree = ttk.Treeview(tree_frame, columns=cols,
                             show="headings", selectmode="browse",
                             style="Det.Treeview")
        hdrs_det = [
            ("codigo",  "Código",    85, "w"),
            ("fecha",   "Fecha",     80, "w"),
            ("entrega", "Entrega",  110, "w"),
            ("recibe",  "Recibe",   110, "w"),
            ("total",   "Total",     80, "e"),
            ("estado",  "Estado",    75, "center"),
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
            tree.insert("", "end",
                        values=(e.get("codigo", ""), fecha,
                                e.get("ent_nombre", ""), e.get("rec_nombre", ""),
                                f"${e.get('total', 0):,.2f}", estado),
                        tags=(estado,))

        total_vendido = sum(e.get("total", 0) for e in envios)
        total_pagado = sum(e.get("abono", 0) for e in envios)

        pie = tk.Frame(self._detalle_frame, bg=c.get("card_header", "#f0efe8"), pady=8, padx=14)
        pie.pack(fill="x")
        tk.Label(pie, text=f"Total vendido: ${total_vendido:,.2f}  |  "
                           f"Pagado: ${total_pagado:,.2f}  |  "
                           f"Envíos: {len(envios)}",
                 font=("Segoe UI", 9),
                 bg=c.get("card_header", "#f0efe8"),
                 fg=c.get("card_header_fg", "#0f6e56")).pack(side="left")
