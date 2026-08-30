import tkinter as tk
from tkinter import ttk
from datetime import datetime
import math

class KPIDashboardFrame(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#f5f5f0")
        self.db = db
        self.app = app
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#ffffff", pady=14)
        header.pack(fill="x")
        tk.Label(header, text="📊  Dashboard / KPI",
                 font=("Segoe UI", 14, "bold"),
                 bg="#ffffff", fg="#0f6e56").pack(side="left", padx=20)
        tk.Button(header, text="🔄  Refrescar", font=("Segoe UI",9),
                  bd=0, bg="#e1f5ee", fg="#0f6e56", cursor="hand2",
                  pady=4, padx=12, command=self.refresh).pack(side="right", padx=20)

        body = tk.Frame(self, bg="#f5f5f0")
        body.pack(fill="both", expand=True, padx=16, pady=(8,12))

        # ── Fila 1: KPIs principales ─────────────
        kpi = self.db.resumen_kpi()
        kpi_data = [
            ("📦 Hoy", str(kpi["envios_hoy"]), f"${kpi['monto_hoy']:,.0f}", "#0f6e56"),
            ("📅 Este mes", str(kpi["envios_mes"]), f"${kpi['monto_mes']:,.0f}", "#0f6e56"),
            ("📦 Listos", str(kpi["listos"]), "para recoger", "#633806"),
            ("⚠️ Deudores", str(kpi["deudores"]), f"${kpi['total_deuda']:,.0f}", "#791f1f"),
        ]
        kf = tk.Frame(body, bg="#f5f5f0")
        kf.pack(fill="x")
        for label, valor, sub, color in kpi_data:
            card = tk.Frame(kf, bg="#ffffff", padx=16, pady=10,
                            highlightthickness=1, highlightbackground="#e0e0d8")
            card.pack(side="left", fill="x", expand=True, padx=4)
            tk.Label(card, text=label, font=("Segoe UI",9), bg="#ffffff", fg="#888780").pack(anchor="w")
            tk.Label(card, text=valor, font=("Segoe UI",22,"bold"),
                     bg="#ffffff", fg=color).pack(anchor="w")
            tk.Label(card, text=sub, font=("Segoe UI",8), bg="#ffffff", fg="#888780").pack(anchor="w")

        # ── Fila 2: Top clientes + Tendencia ──────
        mid = tk.Frame(body, bg="#f5f5f0")
        mid.pack(fill="both", expand=True, pady=(8,0))

        # Top clientes
        top_card = tk.Frame(mid, bg="#ffffff",
                            highlightthickness=1, highlightbackground="#e0e0d8")
        top_card.pack(side="left", fill="both", expand=True)

        tk.Label(top_card, text="🏆  Top 10 Clientes",
                 font=("Segoe UI",9,"bold"),
                 bg="#f1efe8", fg="#5f5e5a",
                 pady=4, padx=8, anchor="w").pack(fill="x")

        top_inner = tk.Frame(top_card, bg="#ffffff")
        top_inner.pack(fill="both", expand=True, padx=4, pady=4)

        cols = ("#","cliente","envios","total","pagado","deuda")
        self.top_tree = ttk.Treeview(top_inner, columns=cols, show="headings", height=8)
        hdrs = [("#","#",25),("cliente","Cliente",140),("envios","Envios",50),
                ("total","Facturado",80),("pagado","Pagado",80),("deuda","Deuda",80)]
        for col, txt, w in hdrs:
            self.top_tree.heading(col, text=txt)
            self.top_tree.column(col, width=w, anchor="e")
        self.top_tree.column("#", anchor="center")
        self.top_tree.column("cliente", anchor="w")
        vsb = ttk.Scrollbar(top_inner, orient="vertical", command=self.top_tree.yview)
        self.top_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.top_tree.pack(fill="both", expand=True)

        # Tendencia mensual
        tend_card = tk.Frame(mid, bg="#ffffff",
                             highlightthickness=1, highlightbackground="#e0e0d8")
        tend_card.pack(side="right", fill="both", expand=True, padx=(8,0))

        tk.Label(tend_card, text="📈  Tendencia Mensual (últimos 12)",
                 font=("Segoe UI",9,"bold"),
                 bg="#f1efe8", fg="#5f5e5a",
                 pady=4, padx=8, anchor="w").pack(fill="x")

        tend_inner = tk.Frame(tend_card, bg="#ffffff")
        tend_inner.pack(fill="both", expand=True, padx=4, pady=4)

        tcols = ("mes","envios","monto")
        self.tend_tree = ttk.Treeview(tend_inner, columns=tcols, show="headings", height=8)
        thdrs = [("mes","Mes",70),("envios","Envíos",55),("monto","Monto",85)]
        for col, txt, w in thdrs:
            self.tend_tree.heading(col, text=txt)
            self.tend_tree.column(col, width=w, anchor="e")
        self.tend_tree.column("mes", anchor="w")
        tvsb = ttk.Scrollbar(tend_inner, orient="vertical", command=self.tend_tree.yview)
        self.tend_tree.configure(yscrollcommand=tvsb.set)
        tvsb.pack(side="right", fill="y")
        self.tend_tree.pack(fill="both", expand=True)

        # ── Fila 3: Gráfico de barras simple ─────
        graf_card = tk.Frame(body, bg="#ffffff", pady=8, padx=8,
                             highlightthickness=1, highlightbackground="#e0e0d8")
        graf_card.pack(fill="x", pady=(8,0))

        tk.Label(graf_card, text="📊  Envíos por mes (gráfico)",
                 font=("Segoe UI",9,"bold"),
                 bg="#ffffff", fg="#5f5e5a", anchor="w").pack(fill="x", padx=4)

        self.canvas = tk.Canvas(graf_card, bg="#ffffff", height=120,
                                highlightthickness=0)
        self.canvas.pack(fill="x", padx=8, pady=4)

        self.refresh()

    def _dibujar_grafico(self, datos):
        self.canvas.delete("all")
        if not datos:
            self.canvas.create_text(200, 60, text="Sin datos",
                                    font=("Segoe UI",10), fill="#888780")
            return
        w = self.canvas.winfo_width() or 600
        h = 100
        datos = datos[:10]
        max_val = max(d["monto"] for d in datos) or 1
        n = len(datos)
        bar_w = min(40, (w - 40) // n)
        gap = max(4, (w - n * bar_w) // (n + 1))
        for i, d in enumerate(datos):
            x0 = gap + i * (bar_w + gap)
            bh = max(8, (d["monto"] / max_val) * (h - 30))
            y0 = h - bh
            color = "#0f6e56"
            self.canvas.create_rectangle(x0, y0, x0+bar_w, h-5,
                                         fill=color, outline="", width=0)
            if bar_w >= 28:
                self.canvas.create_text(x0+bar_w/2, y0-4,
                                        text=d["mes"][:5], font=("Segoe UI",7),
                                        fill="#888780", anchor="s")
                self.canvas.create_text(x0+bar_w/2, h-3,
                                        text=str(d["cantidad"]), font=("Segoe UI",7),
                                        fill="#888780", anchor="n")

    def refresh(self):
        for row in self.top_tree.get_children():
            self.top_tree.delete(row)
        for row in self.tend_tree.get_children():
            self.tend_tree.delete(row)

        top = self.db.top_clientes(10)
        for i, c in enumerate(top, 1):
            self.top_tree.insert("", "end", values=(
                i, c["ent_nombre"], c["envios"],
                f"{c['total_facturado']:,.2f}",
                f"{c['total_pagado']:,.2f}",
                f"{c['total_deuda']:,.2f}"
            ))

        tend = self.db.tendencia_mensual(12)
        for t in tend:
            mes = t["mes"] or "—"
            monto = t["monto"] or 0
            self.tend_tree.insert("", "end", values=(
                mes, t["cantidad"], f"{monto:,.2f}"
            ))
        tend_validos = [d for d in tend if d.get("mes") and d.get("monto") is not None]
        self.after(100, lambda: self._dibujar_grafico(tend_validos))
