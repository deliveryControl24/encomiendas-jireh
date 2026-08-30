"""Selector de fecha visual (datepicker) reutilizable."""

import tkinter as tk
from tkinter import ttk
from datetime import datetime, date, timedelta

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

class DatePicker(tk.Toplevel):
    def __init__(self, parent, variable, fecha_default=None):
        super().__init__(parent)
        self.variable = variable
        self.title("Seleccionar fecha")
        self.configure(bg="#ffffff")
        self.resizable(False, False)
        hoy = fecha_default or datetime.now()
        try:
            dia_actual = int(hoy.strftime("%d"))
            self.curr_anio = int(hoy.strftime("%Y"))
            self.curr_mes = int(hoy.strftime("%m"))
        except:
            dia_actual = datetime.now().day
            self.curr_anio = datetime.now().year
            self.curr_mes = datetime.now().month
        self.dia_seleccionado = dia_actual
        self._build()
        self._dibujar_calendario()

    def _build(self):
        self.overrideredirect(True)
        self.configure(highlightthickness=1, highlightbackground="#888780")
        nav = tk.Frame(self, bg="#0f6e56", padx=8, pady=4)
        nav.pack(fill="x")
        tk.Button(nav, text="◀", font=("Segoe UI", 10, "bold"),
                  bd=0, bg="#0f6e56", fg="white", cursor="hand2",
                  activebackground="#085041",
                  command=self._mes_anterior).pack(side="left")
        self.lbl_mes = tk.Label(nav, text="", font=("Segoe UI", 11, "bold"),
                                bg="#0f6e56", fg="white")
        self.lbl_mes.pack(side="left", expand=True)
        tk.Button(nav, text="▶", font=("Segoe UI", 10, "bold"),
                  bd=0, bg="#0f6e56", fg="white", cursor="hand2",
                  activebackground="#085041",
                  command=self._mes_siguiente).pack(side="right")

        self.grid_frame = tk.Frame(self, bg="#ffffff", padx=8, pady=6)
        self.grid_frame.pack()
        dias_sem = ["Lu","Ma","Mi","Ju","Vi","Sá","Do"]
        for i, d in enumerate(dias_sem):
            tk.Label(self.grid_frame, text=d, font=("Segoe UI", 8, "bold"),
                     bg="#ffffff", fg="#888780", width=4).grid(row=0, column=i, pady=(0,4))

        self.botones = {}
        for fila in range(1, 7):
            for col in range(7):
                btn = tk.Label(self.grid_frame, text="", font=("Segoe UI", 9),
                               bg="#ffffff", fg="#2c2c2a", width=4, height=2,
                               cursor="hand2")
                btn.grid(row=fila, column=col, padx=1, pady=1)
                btn.bind("<Button-1>", lambda e, f=fila, c=col: self._click(f, c))
                self.botones[(fila, col)] = btn

        btn_frame = tk.Frame(self, bg="#f5f5f0", pady=4)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Hoy", font=("Segoe UI", 9),
                  bd=0, bg="#e1f5ee", fg="#0f6e56", cursor="hand2",
                  command=self._hoy).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancelar", font=("Segoe UI", 9),
                  bd=0, bg="#f5f5f0", fg="#888780", cursor="hand2",
                  command=self.destroy).pack(side="right", padx=8)

        self.geometry(f"+{self.winfo_pointerx()}+{self.winfo_pointery()}")

    def _dibujar_calendario(self):
        self.lbl_mes.config(text=f"{MESES[self.curr_mes-1]} {self.curr_anio}")
        import calendar
        inicio_sem, num_dias = calendar.monthrange(self.curr_anio, self.curr_mes)
        inicio_sem = (inicio_sem + 6) % 7
        for key, btn in self.botones.items():
            btn.config(text="", bg="#ffffff", fg="#2c2c2a")
        dia = 1
        for fila in range(1, 7):
            for col in range(7):
                if (fila == 1 and col < inicio_sem) or dia > num_dias:
                    continue
                btn = self.botones[(fila, col)]
                btn.config(text=str(dia))
                hoy = datetime.now()
                if dia == hoy.day and self.curr_mes == hoy.month and self.curr_anio == hoy.year:
                    btn.config(bg="#e1f5ee", fg="#0f6e56")
                if dia == self.dia_seleccionado and fila == 1 and col >= inicio_sem:
                    btn.config(bg="#0f6e56", fg="white")
                elif dia == self.dia_seleccionado:
                    btn.config(bg="#0f6e56", fg="white")
                dia += 1

    def _click(self, fila, col):
        btn = self.botones[(fila, col)]
        txt = btn.cget("text")
        if txt and txt.strip():
            self.dia_seleccionado = int(txt)
            fecha = date(self.curr_anio, self.curr_mes, self.dia_seleccionado)
            self.variable.set(fecha.strftime("%d/%m/%Y"))
            self.destroy()

    def _mes_anterior(self):
        if self.curr_mes == 1:
            self.curr_mes = 12
            self.curr_anio -= 1
        else:
            self.curr_mes -= 1
        self._dibujar_calendario()

    def _mes_siguiente(self):
        if self.curr_mes == 12:
            self.curr_mes = 1
            self.curr_anio += 1
        else:
            self.curr_mes += 1
        self._dibujar_calendario()

    def _hoy(self):
        today = datetime.now()
        self.variable.set(today.strftime("%d/%m/%Y"))
        self.destroy()

def datepicker_entry(parent, variable, **kwargs):
    """Crea un Entry con botón de calendario al lado."""
    frame = tk.Frame(parent, bg=kwargs.get("bg", parent.cget("bg")))
    entry = ttk.Entry(frame, textvariable=variable, width=kwargs.get("width", 12), font=("Segoe UI", 10))
    entry.pack(side="left")
    btn = tk.Button(frame, text="📅", font=("Segoe UI", 9),
                    bd=0, bg=kwargs.get("bg", "#ffffff"), cursor="hand2",
                    command=lambda: DatePicker(frame, variable, fecha_default=kwargs.get("fecha_default", None)))
    btn.pack(side="left", padx=(2, 0))
    return frame
