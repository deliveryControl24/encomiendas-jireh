"""
==============================================
  modules/costo_viaje.py
  Gestion de costos de viaje / gastos
==============================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


CATEGORIAS = [
    "Pago de equipaje",
    "Pago de boletos",
    "Traslado",
    "Combustible",
    "Peaje",
    "Alimentación",
    "Alojamiento",
    "Mantenimiento",
    "Empaque",
    "Aduana",
    "Planilla",
    "Otros",
]


class CostoViajeFrame(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#f5f5f0")
        self.db = db
        self.app = app
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#ffffff", pady=14)
        header.pack(fill="x")
        tk.Label(header, text="💰  Costos de viaje",
                 font=("Segoe UI", 14, "bold"),
                 bg="#ffffff", fg="#0f6e56").pack(side="left", padx=20)

        # ── Formulario ────────────────────────────
        form_card = tk.Frame(self, bg="#ffffff",
                             highlightthickness=1,
                             highlightbackground="#e0e0d8")
        form_card.pack(fill="x", padx=16, pady=(8, 0))

        tk.Label(form_card, text="➕  AGREGAR GASTO",
                 font=("Segoe UI", 9, "bold"),
                 bg="#f1efe8", fg="#5f5e5a",
                 pady=6, padx=14, anchor="w").pack(fill="x")

        body = tk.Frame(form_card, bg="#ffffff", padx=14, pady=10)
        body.pack(fill="x")
        body.columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Fecha
        tk.Label(body, text="Fecha", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_fecha = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        ttk.Entry(body, textvariable=self.v_fecha,
                  width=14, font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 0))

        # Categoría
        tk.Label(body, text="Categoría", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=1, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_categoria = tk.StringVar(value=CATEGORIAS[0])
        ttk.Combobox(body, textvariable=self.v_categoria,
                     values=CATEGORIAS, state="readonly",
                     width=16, font=("Segoe UI", 10)).grid(
            row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 0))

        # Concepto
        tk.Label(body, text="Concepto", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=2, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_concepto = tk.StringVar()
        ttk.Entry(body, textvariable=self.v_concepto,
                  width=22, font=("Segoe UI", 10)).grid(
            row=1, column=2, sticky="ew", padx=(0, 8), pady=(2, 0))

        # Monto
        tk.Label(body, text="Monto", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=3, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_monto = tk.StringVar()
        ttk.Entry(body, textvariable=self.v_monto,
                  width=12, font=("Segoe UI", 10)).grid(
            row=1, column=3, sticky="ew", padx=(0, 8), pady=(2, 0))

        # Moneda
        tk.Label(body, text="Moneda", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=0, column=4, sticky="w", padx=(0, 8), pady=(4, 0))
        self.v_moneda = tk.StringVar(value="$")
        ttk.Combobox(body, textvariable=self.v_moneda,
                     values=["$"], state="readonly",
                     width=6, font=("Segoe UI", 10)).grid(
            row=1, column=4, sticky="ew", padx=(0, 8), pady=(2, 0))

        # Nota
        tk.Label(body, text="Nota (opcional)", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=(0, 8), pady=(6, 0))
        self.v_nota = tk.StringVar()
        ttk.Entry(body, textvariable=self.v_nota,
                  width=40, font=("Segoe UI", 10)).grid(
            row=3, column=0, columnspan=4, sticky="ew", padx=(0, 8), pady=(2, 0))

        tk.Button(body, text="✓  Agregar gasto",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#0f6e56", fg="white",
                  activebackground="#085041",
                  pady=6, padx=14, cursor="hand2",
                  command=self._agregar
                  ).grid(row=3, column=4, sticky="ew", padx=(0, 4), pady=(2, 0))

        # ── Separador ────────────────────────────
        sep = tk.Frame(self, bg="#f5f5f0", pady=4)
        sep.pack(fill="x")

        # ── Filtros ──────────────────────────────
        filter_bar = tk.Frame(self, bg="#ffffff", padx=16, pady=6,
                              highlightthickness=1,
                              highlightbackground="#e0e0d8")
        filter_bar.pack(fill="x", padx=16)

        tk.Label(filter_bar, text="Filtrar:", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").pack(side="left")
        tk.Label(filter_bar, text="Desde:", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").pack(side="left", padx=(8, 2))
        self.v_fdesde = tk.StringVar()
        ttk.Entry(filter_bar, textvariable=self.v_fdesde,
                  width=10, font=("Segoe UI", 10)).pack(side="left", padx=(0, 4))
        self.v_fdesde.trace_add("write", lambda *a: self.refresh())

        tk.Label(filter_bar, text="Hasta:", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").pack(side="left", padx=(4, 2))
        self.v_fhasta = tk.StringVar()
        ttk.Entry(filter_bar, textvariable=self.v_fhasta,
                  width=10, font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        self.v_fhasta.trace_add("write", lambda *a: self.refresh())

        tk.Label(filter_bar, text="Categoría:", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#888780").pack(side="left")
        self.v_fcat = tk.StringVar(value="Todas")
        cb_fcat = ttk.Combobox(filter_bar, textvariable=self.v_fcat,
                                values=["Todas"] + CATEGORIAS,
                                width=14, state="readonly",
                                font=("Segoe UI", 10))
        cb_fcat.pack(side="left", padx=(4, 8))
        cb_fcat.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Totales
        self.lbl_totales = tk.Label(filter_bar, text="",
                                     font=("Segoe UI", 9, "bold"),
                                     bg="#ffffff", fg="#0f6e56")
        self.lbl_totales.pack(side="right", padx=8)

        # ── Lista de costos ──────────────────────
        list_frame = tk.Frame(self, bg="#ffffff",
                              highlightthickness=1,
                              highlightbackground="#e0e0d8")
        list_frame.pack(fill="both", expand=True, padx=16, pady=(6, 12))

        tree_frame = tk.Frame(list_frame, bg="#ffffff")
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        cols = ("fecha", "categoria", "concepto", "monto", "moneda", "nota")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                  show="headings", height=12)
        hdrs = [
            ("fecha",     "Fecha",      90),
            ("categoria", "Categoría",  120),
            ("concepto",  "Concepto",   200),
            ("monto",     "Monto",      100),
            ("moneda",    "Moneda",     60),
            ("nota",      "Nota",       150),
        ]
        for col, txt, w in hdrs:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w")
        self.tree.column("monto", anchor="e")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-Button-1>", lambda e: self._editar())

        btn_frame = tk.Frame(list_frame, bg="#ffffff", pady=4)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="✏️ Editar",
                  font=("Segoe UI", 9), bd=0,
                  bg="#e6f1fb", fg="#0c447c",
                  activebackground="#b3d4f0",
                  pady=4, padx=12, cursor="hand2",
                  command=self._editar).pack(side="left", padx=8)
        tk.Button(btn_frame, text="💰 Poner $0",
                  font=("Segoe UI", 9), bd=0,
                  bg="#faeeda", fg="#633806",
                  activebackground="#f5deb3",
                  pady=4, padx=12, cursor="hand2",
                  command=self._poner_cero).pack(side="left", padx=8)
        tk.Button(btn_frame, text="🗑 Eliminar",
                  font=("Segoe UI", 9), bd=0,
                  bg="#fcebeb", fg="#791f1f",
                  activebackground="#f09595",
                  pady=4, padx=12, cursor="hand2",
                  command=self._eliminar).pack(side="left", padx=8)

        self.refresh()

    def _agregar(self):
        fecha = self.v_fecha.get().strip()
        categoria = self.v_categoria.get()
        concepto = self.v_concepto.get().strip()
        monto_str = self.v_monto.get().strip()
        moneda = self.v_moneda.get()
        nota = self.v_nota.get().strip()

        if not concepto:
            messagebox.showwarning("Requerido", "Ingrese el concepto del gasto.")
            return
        if not monto_str:
            messagebox.showwarning("Requerido", "Ingrese el monto del gasto.")
            return
        try:
            monto = float(monto_str)
        except ValueError:
            messagebox.showwarning("Error", "El monto debe ser un número válido.")
            return
        if monto <= 0:
            messagebox.showwarning("Error", "El monto debe ser mayor a 0.")
            return

        self.db.agregar_costo(fecha, categoria, concepto, monto, moneda, nota=nota)
        self.v_concepto.set("")
        self.v_monto.set("")
        self.v_nota.set("")
        self.refresh()
        messagebox.showinfo("✓", "Gasto agregado correctamente.")

    def _eliminar(self):
        sel = self.tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Eliminar", "¿Eliminar este gasto permanentemente?",
                               icon="warning"):
            costo_id = int(sel[0])
            self.db.eliminar_costo(costo_id)
            self.refresh()

    def _editar(self):
        sel = self.tree.selection()
        if not sel:
            return

        costo_id = int(sel[0])
        costo = self.db.obtener_costo(costo_id)
        if not costo:
            return

        win = tk.Toplevel(self)
        win.title("Editar gasto")
        win.geometry("400x300")
        win.configure(bg="#f5f5f0")
        win.grab_set()

    def _poner_cero(self):
        sel = self.tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Poner en $0", "¿Poner este gasto en $0?"):
            costo_id = int(sel[0])
            self.db.actualizar_costo(costo_id, "", "", "", 0, "")
            self.refresh()

    def _editar(self):
        sel = self.tree.selection()
        if not sel:
            return

        costo_id = int(sel[0])
        costo = self.db.obtener_costo(costo_id)
        if not costo:
            return

        win = tk.Toplevel(self)
        win.title("Editar gasto")
        win.geometry("400x300")
        win.configure(bg="#f5f5f0")
        win.grab_set()

        main = tk.Frame(win, bg="#f5f5f0", padx=16, pady=16)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Fecha", font=("Segoe UI", 9),
                 bg="#f5f5f0", fg="#888780").grid(row=0, column=0, sticky="w", pady=(4, 0))
        v_fecha = tk.StringVar(value=costo["fecha"])
        ttk.Entry(main, textvariable=v_fecha, width=14, font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="ew", pady=(2, 8))

        tk.Label(main, text="Categoría", font=("Segoe UI", 9),
                 bg="#f5f5f0", fg="#888780").grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(4, 0))
        v_cat = tk.StringVar(value=costo["categoria"])
        ttk.Combobox(main, textvariable=v_cat, values=CATEGORIAS,
                      state="readonly", width=16, font=("Segoe UI", 10)).grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 8))

        tk.Label(main, text="Concepto", font=("Segoe UI", 9),
                 bg="#f5f5f0", fg="#888780").grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        v_concepto = tk.StringVar(value=costo["concepto"])
        ttk.Entry(main, textvariable=v_concepto, width=40, font=("Segoe UI", 10)).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(2, 8))

        tk.Label(main, text="Monto", font=("Segoe UI", 9),
                 bg="#f5f5f0", fg="#888780").grid(row=4, column=0, sticky="w", pady=(4, 0))
        v_monto = tk.StringVar(value=str(costo["monto"]))
        ttk.Entry(main, textvariable=v_monto, width=12, font=("Segoe UI", 10)).grid(
            row=5, column=0, sticky="ew", pady=(2, 8))

        tk.Label(main, text="Nota", font=("Segoe UI", 9),
                 bg="#f5f5f0", fg="#888780").grid(row=4, column=1, sticky="w", padx=(8, 0), pady=(4, 0))
        v_nota = tk.StringVar(value=costo.get("nota", ""))
        ttk.Entry(main, textvariable=v_nota, width=20, font=("Segoe UI", 10)).grid(
            row=5, column=1, sticky="ew", padx=(8, 0), pady=(2, 8))

        def guardar():
            try:
                monto = float(v_monto.get())
            except:
                messagebox.showerror("Error", "Monto inválido")
                return

            self.db.actualizar_costo(costo_id, v_fecha.get(), v_cat.get(),
                                     v_concepto.get(), monto, v_nota.get())
            self.refresh()
            win.destroy()

        btn_frame = tk.Frame(main, bg="#f5f5f0", pady=16)
        btn_frame.grid(row=6, column=0, columnspan=2)
        tk.Button(btn_frame, text="💾  Guardar",
                   font=("Segoe UI", 10, "bold"), bd=0,
                   bg="#0f6e56", fg="white",
                   pady=8, padx=16, cursor="hand2",
                   command=guardar).pack(side="left", padx=4)
        tk.Button(btn_frame, text="✕  Cancelar",
                   font=("Segoe UI", 10), bd=0,
                   bg="#f1efe8", fg="#5f5e5a",
                   pady=8, padx=16, cursor="hand2",
                   command=win.destroy).pack(side="left", padx=4)

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        fdesde = self.v_fdesde.get().strip()
        fhasta = self.v_fhasta.get().strip()
        fcat = "" if self.v_fcat.get() == "Todas" else self.v_fcat.get()

        costos = self.db.listar_costos(fdesde, fhasta, fcat)
        for c in costos:
            self.tree.insert("", "end", iid=str(c["id"]), values=(
                c["fecha"],
                c["categoria"],
                c["concepto"],
                f"{c['monto']:,.2f}",
                c["moneda"],
                c.get("nota", "") or "",
            ))

        totales = self.db.total_costos(fdesde, fhasta, fcat)
        total = totales["total_dolares"]
        if costos:
            self.lbl_totales.config(text=f"Total: ${total:,.2f}  ({len(costos)} gastos)")
        else:
            self.lbl_totales.config(text="Sin gastos")
