import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from modules.imprimir import imprimir_cuentas_cobrar

class CuentasCobrarFrame(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#f5f5f0")
        self.db = db
        self.app = app
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#ffffff", pady=14)
        header.pack(fill="x")
        tk.Label(header, text="📋  Cuentas por Cobrar",
                 font=("Segoe UI", 14, "bold"),
                 bg="#ffffff", fg="#0f6e56").pack(side="left", padx=20)
        tk.Button(header, text="🖨  Imprimir", font=("Segoe UI",9),
                  bd=0, bg="#0f6e56", fg="white", cursor="hand2",
                  pady=4, padx=12, command=self._imprimir).pack(side="right", padx=20)

        # ── Resumen ──────────────────────────────
        res_card = tk.Frame(self, bg="#ffffff",
                            highlightthickness=1, highlightbackground="#e0e0d8")
        res_card.pack(fill="x", padx=16, pady=(8,0))

        tk.Label(res_card, text="📊  RESUMEN DE DEUDAS",
                 font=("Segoe UI",9,"bold"),
                 bg="#f1efe8", fg="#5f5e5a",
                 pady=6, padx=14, anchor="w").pack(fill="x")

        res_body = tk.Frame(res_card, bg="#ffffff", padx=20, pady=14)
        res_body.pack(fill="x")

        deudores = self.db.obtener_clientes_con_deuda()
        total_deuda = sum(d["total_deuda"] for d in deudores)

        kf = tk.Frame(res_body, bg="#ffffff")
        kf.pack()
        items = [
            ("Clientes con deuda", str(len(deudores)), "#791f1f"),
            ("Total cuentas por cobrar", f"$ {total_deuda:,.2f}", "#0f6e56"),
        ]
        for i, (label, valor, color) in enumerate(items):
            f = tk.Frame(kf, bg="#ffffff", padx=24, pady=8,
                         highlightthickness=1, highlightbackground="#e0e0d8")
            f.pack(side="left", padx=8)
            tk.Label(f, text=label, font=("Segoe UI",9), bg="#ffffff", fg="#888780").pack()
            tk.Label(f, text=valor, font=("Segoe UI",16,"bold"),
                     bg="#ffffff", fg=color).pack()

        # ── Tabla de clientes ────────────────────
        tk.Frame(self, bg="#f5f5f0", pady=4).pack(fill="x")

        list_card = tk.Frame(self, bg="#ffffff",
                             highlightthickness=1, highlightbackground="#e0e0d8")
        list_card.pack(fill="both", expand=True, padx=16, pady=(0,12))

        tk.Label(list_card, text="Clientes con deuda",
                 font=("Segoe UI",9,"bold"),
                 bg="#f1efe8", fg="#5f5e5a",
                 pady=4, padx=8, anchor="w").pack(fill="x")

        tree_frame = tk.Frame(list_card, bg="#ffffff")
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        cols = ("cliente","cantidad","total_deuda","desde")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=6)
        hdrs = [("cliente","Cliente",180),("cantidad","Envíos",60),
                ("total_deuda","Total deuda",100),("desde","Deuda desde",120)]
        for col, txt, w in hdrs:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w")
        self.tree.column("total_deuda", anchor="e")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._mostrar_detalle_cliente)

        # ── Detalle del cliente seleccionado ─────
        tk.Frame(self, bg="#f5f5f0", pady=4).pack(fill="x")

        det_card = tk.Frame(self, bg="#ffffff",
                            highlightthickness=1, highlightbackground="#e0e0d8")
        det_card.pack(fill="both", expand=True, padx=16, pady=(0,12))

        tk.Label(det_card, text="Envíos del cliente",
                 font=("Segoe UI",9,"bold"),
                 bg="#f1efe8", fg="#5f5e5a",
                 pady=4, padx=8, anchor="w").pack(fill="x")

        det_frame = tk.Frame(det_card, bg="#ffffff")
        det_frame.pack(fill="both", expand=True, padx=4, pady=4)

        dcols = ("codigo","fecha","total","abono","restante","dias")
        self.det_tree = ttk.Treeview(det_frame, columns=dcols, show="headings", height=5)
        dhdrs = [("codigo","Código",70),("fecha","Fecha",80),
                 ("total","Total",80),("abono","Abono",80),
                 ("restante","Restante",80),("dias","Días",50)]
        for col, txt, w in dhdrs:
            self.det_tree.heading(col, text=txt)
            self.det_tree.column(col, width=w, anchor="e")
        self.det_tree.column("codigo", anchor="w")
        self.det_tree.column("fecha", anchor="w")
        dvsb = ttk.Scrollbar(det_frame, orient="vertical", command=self.det_tree.yview)
        self.det_tree.configure(yscrollcommand=dvsb.set)
        dvsb.pack(side="right", fill="y")
        self.det_tree.pack(fill="both", expand=True)

        self.refresh()

    def _mostrar_detalle_cliente(self, e=None):
        for row in self.det_tree.get_children():
            self.det_tree.delete(row)
        sel = self.tree.selection()
        if not sel:
            return
        cliente = sel[0]
        envios = self.db.listar_envios(buscar=cliente, por_pagina=50)
        for env in envios:
            if env["restante"] > 0 and env["estado"] != "Cancelado":
                try:
                    from datetime import datetime
                    creado = datetime.strptime(env["created_at"].split()[0], "%d/%m/%Y")
                    dias = (datetime.now() - creado).days
                except:
                    dias = 0
                self.det_tree.insert("", "end", values=(
                    env["codigo"], env["fecha"],
                    f"{env['total']:,.2f}", f"{env['abono']:,.2f}",
                    f"{env['restante']:,.2f}", dias
                ))

    def _imprimir(self):
        try:
            ruta = imprimir_cuentas_cobrar(self.db)
            messagebox.showinfo("✓", f"Reporte impreso:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo imprimir:\n{e}")

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        deudores = self.db.obtener_clientes_con_deuda()
        for d in deudores:
            self.tree.insert("", "end", iid=str(d["ent_nombre"]), values=(
                d["ent_nombre"], d["cantidad_deudas"],
                f"$ {d['total_deuda']:,.2f}",
                d.get("deuda_desde", "") or ""
            ))
        self._mostrar_detalle_cliente()
