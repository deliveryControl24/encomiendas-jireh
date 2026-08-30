import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from modules.imprimir import imprimir_arqueo

class ArqueoCajaFrame(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#f5f5f0")
        self.db = db
        self.app = app
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#ffffff", pady=14)
        header.pack(fill="x")
        tk.Label(header, text="💵  Arqueo de Caja",
                 font=("Segoe UI", 14, "bold"),
                 bg="#ffffff", fg="#0f6e56").pack(side="left", padx=20)
        self.lbl_fecha = tk.Label(header, text=datetime.now().strftime("%d/%m/%Y"),
                                  font=("Segoe UI",10), bg="#ffffff", fg="#888780")
        self.lbl_fecha.pack(side="right", padx=20)

        # ── Card principal ────────────────────────
        card = tk.Frame(self, bg="#ffffff",
                        highlightthickness=1, highlightbackground="#e0e0d8")
        card.pack(fill="x", padx=16, pady=(8,0))

        tk.Label(card, text="💰  ARQUEO DEL DÍA",
                 font=("Segoe UI",9,"bold"),
                 bg="#f1efe8", fg="#5f5e5a",
                 pady=6, padx=14, anchor="w").pack(fill="x")

        body = tk.Frame(card, bg="#ffffff", padx=20, pady=16)
        body.pack(fill="x")

        # Apertura
        tk.Label(body, text="APERTURA", font=("Segoe UI",9,"bold"),
                 bg="#ffffff", fg="#0f6e56", anchor="w").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,6))

        tk.Label(body, text="Dólares:", font=("Segoe UI",9), bg="#ffffff", fg="#888780").grid(row=1, column=0, sticky="w", padx=8)
        self.v_aper_us = tk.StringVar(value="0")
        ttk.Entry(body, textvariable=self.v_aper_us, width=14, font=("Segoe UI",11)).grid(row=1, column=1, sticky="w", padx=4)

        # Movimientos del día
        tk.Label(body, text="MOVIMIENTOS", font=("Segoe UI",9,"bold"),
                 bg="#ffffff", fg="#0f6e56", anchor="w").grid(row=2, column=0, columnspan=2, sticky="w", pady=(16,6))

        tk.Label(body, text="Ingresos $:", font=("Segoe UI",9), bg="#ffffff", fg="#888780").grid(row=3, column=0, sticky="w", padx=8)
        self.v_ing_us = tk.StringVar(value="0")
        ttk.Entry(body, textvariable=self.v_ing_us, width=14, font=("Segoe UI",11)).grid(row=3, column=1, sticky="w", padx=4)

        tk.Label(body, text="Egresos $:", font=("Segoe UI",9), bg="#ffffff", fg="#888780").grid(row=4, column=0, sticky="w", padx=8)
        self.v_egr_us = tk.StringVar(value="0")
        ttk.Entry(body, textvariable=self.v_egr_us, width=14, font=("Segoe UI",11)).grid(row=4, column=1, sticky="w", padx=4)

        # Cierre
        tk.Label(body, text="CIERRE", font=("Segoe UI",9,"bold"),
                 bg="#ffffff", fg="#0f6e56", anchor="w").grid(row=5, column=0, columnspan=2, sticky="w", pady=(16,6))

        tk.Label(body, text="Dólares:", font=("Segoe UI",9), bg="#ffffff", fg="#888780").grid(row=6, column=0, sticky="w", padx=8)
        self.v_cie_us = tk.StringVar(value="0")
        ttk.Entry(body, textvariable=self.v_cie_us, width=14, font=("Segoe UI",11)).grid(row=6, column=1, sticky="w", padx=4)
        self.v_cie_us.trace_add("write", lambda *a: self._calcular_diferencia())

        # Diferencia
        sep = tk.Frame(body, bg="#e0e0d8", height=1)
        sep.grid(row=7, column=0, columnspan=2, sticky="ew", pady=12)

        tk.Label(body, text="DIFERENCIA", font=("Segoe UI",10,"bold"),
                 bg="#ffffff", fg="#791f1f").grid(row=8, column=0, sticky="w", padx=8)
        self.lbl_diff_us = tk.Label(body, text="$ 0.00", font=("Segoe UI",12,"bold"),
                                    bg="#ffffff", fg="#791f1f")
        self.lbl_diff_us.grid(row=8, column=1, sticky="w", padx=4)

        # Resumen del día
        sep2 = tk.Frame(body, bg="#e0e0d8", height=1)
        sep2.grid(row=8, column=0, columnspan=4, sticky="ew", pady=4)
        self.lbl_facturado = tk.Label(body, text="",
                                       font=("Segoe UI",9,"bold"),
                                       bg="#ffffff", fg="#0f6e56")
        self.lbl_facturado.grid(row=9, column=0, columnspan=4, sticky="w", padx=8, pady=(4,0))

        # Nota
        tk.Label(body, text="Nota:", font=("Segoe UI",9), bg="#ffffff", fg="#888780").grid(row=10, column=0, sticky="w", padx=8, pady=(12,0))
        self.v_nota = tk.StringVar()
        ttk.Entry(body, textvariable=self.v_nota, width=50, font=("Segoe UI",10)).grid(row=10, column=1, columnspan=3, sticky="ew", padx=4, pady=(12,0))

        # Botones
        btn_frame = tk.Frame(body, bg="#ffffff", pady=16)
        btn_frame.grid(row=11, column=0, columnspan=4)
        self.btn_guardar = tk.Button(btn_frame, text="💾  Guardar arqueo", font=("Segoe UI",10,"bold"),
                     bd=0, bg="#0f6e56", fg="white", cursor="hand2",
                     pady=8, padx=24, command=self._guardar)
        self.btn_guardar.pack(side="left", padx=8)
        tk.Button(btn_frame, text="🖨  Imprimir", font=("Segoe UI",10,"bold"),
                     bd=0, bg="#0f6e56", fg="white", cursor="hand2",
                     pady=8, padx=24, command=self._imprimir).pack(side="left", padx=8)
        self.btn_cerrar = tk.Button(btn_frame, text="🔒  Cerrar caja", font=("Segoe UI",10,"bold"),
                     bd=0, bg="#791f1f", fg="white", cursor="hand2",
                     pady=8, padx=24, command=self._cerrar)
        self.btn_cerrar.pack(side="left", padx=8)

        # ── Historial de arqueos ──────────────────
        tk.Frame(self, bg="#f5f5f0", pady=6).pack(fill="x")

        hist_card = tk.Frame(self, bg="#ffffff",
                             highlightthickness=1, highlightbackground="#e0e0d8")
        hist_card.pack(fill="both", expand=True, padx=16, pady=(0,12))

        tk.Label(hist_card, text="Historial de arqueos", font=("Segoe UI",9,"bold"),
                 bg="#f1efe8", fg="#5f5e5a", pady=4, padx=8, anchor="w").pack(fill="x")

        tree_frame = tk.Frame(hist_card, bg="#ffffff")
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        cols = ("fecha","aper_us","ing_us","egr_us","cie_us","diff_us","cerrado")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=6)
        hdrs = [("fecha","Fecha",70),("aper_us","Apert. $",100),
                ("ing_us","Ingr. $",70),("egr_us","Egr. $",70),
                ("cie_us","Cierre $",80),("diff_us","Dif. $",75),
                ("cerrado","Estado",65)]
        for col, txt, w in hdrs:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="e")
        self.tree.column("fecha", anchor="w")
        self.tree.column("cerrado", anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self._cargar_hoy()
        self._cargar_historial()

    def _calcular_diferencia(self):
        try:
            aper_us = float(self.v_aper_us.get() or 0)
            ing_us = float(self.v_ing_us.get() or 0)
            egr_us = float(self.v_egr_us.get() or 0)
            cie_us = float(self.v_cie_us.get() or 0)
            esperado_us = aper_us + ing_us - egr_us
            diff_us = cie_us - esperado_us
            self.lbl_diff_us.config(text=f"$ {diff_us:+,.2f}",
                                    fg="#791f1f" if abs(diff_us) > 0.01 else "#0f6e56")
        except ValueError:
            pass

    def _cargar_hoy(self):
        arqueo = self.db.obtener_arqueo_hoy()
        if arqueo:
            self.v_aper_us.set(str(arqueo["apertura_dolares"]))
            self.v_ing_us.set(str(arqueo["ingresos_dolares"]))
            self.v_egr_us.set(str(arqueo["egresos_dolares"]))
            self.v_cie_us.set(str(arqueo["cierre_dolares"]))
            self.v_nota.set(arqueo.get("nota","") or "")
            if arqueo["cerrado"]:
                self.btn_cerrar.config(state="disabled", text="✅ Caja cerrada")
                self.btn_guardar.config(text="🔒 Caja cerrada", state="disabled")
        else:
            for v in [self.v_aper_us, self.v_ing_us, self.v_egr_us, self.v_cie_us]:
                v.set("0")

        fact = self.db.total_facturado_hoy()
        cost = self.db.total_costos_hoy()
        self.lbl_facturado.config(
            text=f"💰 Facturado hoy: ${fact:,.2f}   |   📦 Costos hoy: ${cost:,.2f}   |   📊 Neto: ${fact - cost:,.2f}"
        )
        self._calcular_diferencia()

    def _cargar_historial(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        arqueos = self.db.listar_arqueos(por_pagina=30)
        for a in arqueos:
            estado = "🔒 Cerrado" if a["cerrado"] else "📂 Abierto"
            self.tree.insert("", "end", values=(
                a["fecha"],
                f"{a['apertura_dolares']:,.2f}",
                f"{a['ingresos_dolares']:,.2f}",
                f"{a['egresos_dolares']:,.2f}",
                f"{a['cierre_dolares']:,.2f}",
                f"{a['diferencia_dolares']:+,.2f}",
                estado,
            ))

    def _imprimir(self):
        try:
            ruta = imprimir_arqueo(self.db, datetime.now().strftime("%d/%m/%Y"))
            messagebox.showinfo("✓", f"Arqueo impreso:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo imprimir:\n{e}")

    def _guardar(self):
        try:
            aper_us = float(self.v_aper_us.get() or 0)
            ing_us = float(self.v_ing_us.get() or 0)
            egr_us = float(self.v_egr_us.get() or 0)
            cie_us = float(self.v_cie_us.get() or 0)
            diff_us = cie_us - (aper_us + ing_us - egr_us)

            datos = {
                "apertura_dolares": aper_us,
                "ingresos_dolares": ing_us,
                "egresos_dolares": egr_us,
                "cierre_dolares": cie_us,
                "diferencia_dolares": diff_us,
                "nota": self.v_nota.get().strip(),
                "cerrado": False,
            }
            self.db.crear_o_actualizar_arqueo(datos)
            self._cargar_historial()
            messagebox.showinfo("✓", "Arqueo guardado.")
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _cerrar(self):
        if not messagebox.askyesno("Cerrar caja",
                                    "¿Está seguro de cerrar la caja del día?\n"
                                    "No podrá modificarla después."):
            return
        self._guardar()
        arqueo = self.db.obtener_arqueo_hoy()
        if arqueo:
            datos = {
                "apertura_dolares": arqueo["apertura_dolares"],
                "ingresos_dolares": arqueo["ingresos_dolares"],
                "egresos_dolares": arqueo["egresos_dolares"],
                "cierre_dolares": arqueo["cierre_dolares"],
                "diferencia_dolares": arqueo["diferencia_dolares"],
                "nota": arqueo.get("nota",""),
                "cerrado": True,
            }
            self.db.crear_o_actualizar_arqueo(datos)
            self._cargar_hoy()
            self._cargar_historial()
            messagebox.showinfo("🔒", "Caja cerrada.")
