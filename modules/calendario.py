"""
==============================================
  modules/calendario.py
  Vista calendario mensual con conteo
  de envios por dia
==============================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import calendar


MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


class CalendarioFrame(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#f5f5f0")
        self.db = db
        self.app = app
        hoy = date.today()
        self.anio = hoy.year
        self.mes = hoy.month
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#ffffff", pady=14)
        header.pack(fill="x")

        self.lbl_titulo = tk.Label(header, font=("Segoe UI", 14, "bold"),
                                    bg="#ffffff", fg="#0f6e56")
        self.lbl_titulo.pack(side="left", padx=20)

        tk.Button(header, text="◀", font=("Segoe UI", 12, "bold"),
                  bd=0, bg="#e1f5ee", fg="#0f6e56",
                  activebackground="#9fe1cb",
                  pady=4, padx=12, cursor="hand2",
                  command=self._mes_anterior
                  ).pack(side="right", padx=(0, 4))
        tk.Button(header, text="▶", font=("Segoe UI", 12, "bold"),
                  bd=0, bg="#e1f5ee", fg="#0f6e56",
                  activebackground="#9fe1cb",
                  pady=4, padx=12, cursor="hand2",
                  command=self._mes_siguiente
                  ).pack(side="right", padx=(4, 20))

        self.grid_frame = tk.Frame(self, bg="#f5f5f0", padx=16, pady=10)
        self.grid_frame.pack(fill="both", expand=True)

        self.detalle_frame = tk.Frame(self, bg="#ffffff",
                                       highlightthickness=1,
                                       highlightbackground="#e0e0d8")
        self.detalle_frame.pack(fill="x", padx=16, pady=(0, 12))

        self.refresh()

    def refresh(self):
        self.lbl_titulo.config(text=f"📅  {MESES[self.mes]} {self.anio}")
        self._dibujar_mes()

    def _mes_anterior(self):
        if self.mes == 1:
            self.mes = 12
            self.anio -= 1
        else:
            self.mes -= 1
        self.refresh()

    def _mes_siguiente(self):
        if self.mes == 12:
            self.mes = 1
            self.anio += 1
        else:
            self.mes += 1
        self.refresh()

    def _dibujar_mes(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        for w in self.detalle_frame.winfo_children():
            w.destroy()

        # Obtener datos del mes
        mes_str = f"{self.mes:02d}"
        anio_str = str(self.anio)
        rows = self.db.conn.execute("""
            SELECT substr(fecha, 1, 2) as dia,
                   COUNT(*) as cantidad,
                   COALESCE(SUM(total), 0) as monto
            FROM envios
            WHERE substr(fecha, 4, 2) = ? AND substr(fecha, 7, 4) = ?
            GROUP BY dia ORDER BY dia
        """, (mes_str, anio_str)).fetchall()
        datos_por_dia = {r["dia"]: dict(r) for r in rows}

        # Calendario
        cal = calendar.monthcalendar(self.anio, self.mes)

        # Encabezados de dias
        dias_semana = tk.Frame(self.grid_frame, bg="#f5f5f0")
        dias_semana.pack(fill="x")
        for nombre in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]:
            tk.Label(dias_semana, text=nombre, width=12,
                     font=("Segoe UI", 9, "bold"),
                     bg="#f1efe8", fg="#5f5e5a",
                     anchor="center", padx=4, pady=6).pack(side="left")

        # Semanas
        for semana in cal:
            sem_frame = tk.Frame(self.grid_frame, bg="#f5f5f0")
            sem_frame.pack(fill="x")
            for dia_num in semana:
                if dia_num == 0:
                    tk.Label(sem_frame, text="", width=12,
                             bg="#f5f5f0").pack(side="left", padx=2, pady=2)
                    continue

                dia_str = f"{dia_num:02d}"
                info = datos_por_dia.get(dia_str)
                cantidad = info["cantidad"] if info else 0
                monto = info["monto"] if info else 0

                hoy = date.today()
                es_hoy = (dia_num == hoy.day and self.mes == hoy.month
                          and self.anio == hoy.year)

                bg = "#1d9e75" if es_hoy else ("#ffffff" if cantidad > 0 else "#f9f9f7")
                fg = "#ffffff" if es_hoy else ("#0f6e56" if cantidad > 0 else "#b4b2a9")

                cell = tk.Frame(sem_frame, bg=bg,
                                highlightthickness=1,
                                highlightbackground="#e0e0d8",
                                width=90, height=60)
                cell.pack_propagate(False)
                cell.pack(side="left", padx=2, pady=2)

                tk.Label(cell, text=str(dia_num),
                         font=("Segoe UI", 10, "bold"),
                         bg=bg, fg=fg, anchor="nw",
                         padx=4, pady=2).pack(fill="x")

                if cantidad > 0:
                    tk.Label(cell, text=f"{cantidad} env.",
                             font=("Segoe UI", 8), bg=bg,
                             fg=fg, anchor="se",
                             padx=4).pack(side="bottom", fill="x")

                if es_hoy:
                    tk.Label(cell, text="HOY",
                             font=("Segoe UI", 7, "bold"), bg=bg,
                             fg="#c8f0dc", anchor="sw",
                             padx=4).pack(side="bottom", fill="x")

                cell.bind("<Button-1>", lambda e, d=dia_num: self._clic_dia(d))

        self.detalle_frame.config(height=100)

    def _clic_dia(self, dia):
        anio_str = str(self.anio)
        mes_str = f"{self.mes:02d}"
        dia_str = f"{dia:02d}"

        for w in self.detalle_frame.winfo_children():
            w.destroy()

        rows = self.db.listar_envios()
        envios_dia = [e for e in rows
                      if e["fecha"].startswith(f"{dia_str}/{mes_str}/{anio_str}")]

        if not envios_dia:
            tk.Label(self.detalle_frame,
                     text=f"No hay envíos el {dia}/{self.mes}/{self.anio}",
                     font=("Segoe UI", 10), bg="#ffffff",
                     fg="#b4b2a9", pady=20).pack()
            return

        tk.Label(self.detalle_frame,
                 text=f"📋  Envíos del {dia}/{self.mes}/{self.anio} ({len(envios_dia)} registros)",
                 font=("Segoe UI", 9, "bold"),
                 bg="#ffffff", fg="#0f6e56",
                 pady=8, padx=14, anchor="w").pack(fill="x")

        tree = ttk.Treeview(self.detalle_frame,
                             columns=("cod", "ent", "rec", "total", "est"),
                             show="headings", height=min(len(envios_dia), 6))
        tree.heading("cod", text="Código")
        tree.heading("ent", text="Entrega")
        tree.heading("rec", text="Recibe")
        tree.heading("total", text="Total")
        tree.heading("est", text="Estado")
        tree.column("cod", width=80)
        tree.column("ent", width=120)
        tree.column("rec", width=120)
        tree.column("total", width=80, anchor="e")
        tree.column("est", width=80)

        for e in envios_dia:
            mon = e.get("moneda", "C$")
            tree.insert("", "end", values=(
                e["codigo"],
                e["ent_nombre"],
                e["rec_nombre"],
                f"{mon}{e['total']:,.0f}",
                e["estado"],
            ))

        tree.pack(fill="x", padx=14, pady=(0, 10))
