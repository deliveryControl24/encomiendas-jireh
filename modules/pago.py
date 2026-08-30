"""
==============================================
  modules/pago.py
  Ventana emergente para registrar un pago
  sobre un envio existente
==============================================
"""

import tkinter as tk
from tkinter import ttk, messagebox


class PagoFrame(tk.Toplevel):
    def __init__(self, parent, db, envio_id, on_success=None):
        super().__init__(parent)
        self.db         = db
        self.envio_id   = envio_id
        self.on_success = on_success

        env = self.db.obtener_envio(envio_id)
        if not env:
            self.destroy()
            return

        self.env = env
        self.title(f"Registrar pago — {env['codigo']}")
        self.geometry("460x420")
        self.resizable(False, False)
        self.configure(bg="#ffffff")
        self.grab_set()
        self._build()

    def _build(self):
        env = self.env
        mon = env.get("moneda", "C$")

        hdr = tk.Frame(self, bg="#0f6e56", pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"💳  Pago — {env['codigo']}",
                 font=("Segoe UI", 13, "bold"),
                 bg="#0f6e56", fg="white").pack(side="left", padx=20)

        body = tk.Frame(self, bg="#ffffff", padx=24, pady=16)
        body.pack(fill="both", expand=True)

        resumen = tk.Frame(body, bg="#e1f5ee")
        resumen.pack(fill="x", pady=(0, 16))

        datos = [
            ("Entrega",   env["ent_nombre"]),
            ("Recibe",    env["rec_nombre"]),
            ("Total",     f"{mon}{env['total']:,.2f}"),
            ("Ya abonado",f"{mon}{env['abono']:,.2f}"),
            ("Restante",  f"{mon}{env['restante']:,.2f}"),
        ]
        for lbl, val in datos:
            row = tk.Frame(resumen, bg="#e1f5ee")
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=lbl + ":", font=("Segoe UI", 9),
                     bg="#e1f5ee", fg="#085041",
                     width=11, anchor="w").pack(side="left")
            tk.Label(row, text=val, font=("Segoe UI", 9, "bold"),
                     bg="#e1f5ee", fg="#085041").pack(side="left")

        # Frame intermedio para usar grid sin conflictos con pack
        campos_frame = tk.Frame(body, bg="#ffffff")
        campos_frame.pack(fill="both", expand=True)

        def campo(lbl, row):
            tk.Label(campos_frame, text=lbl, font=("Segoe UI", 9),
                     bg="#ffffff", fg="#888780").grid(
                row=row*2, column=0, columnspan=2,
                sticky="w", pady=(8, 0))
            var = tk.StringVar()
            entry = ttk.Entry(campos_frame, textvariable=var,
                              width=38, font=("Segoe UI", 10))
            entry.grid(row=row*2+1, column=0, columnspan=2,
                       sticky="ew", pady=(2, 0))
            return var

        def combo(lbl, opciones, row):
            tk.Label(campos_frame, text=lbl, font=("Segoe UI", 9),
                     bg="#ffffff", fg="#888780").grid(
                row=row*2, column=0, columnspan=2,
                sticky="w", pady=(8, 0))
            var = tk.StringVar(value=opciones[0])
            cb = ttk.Combobox(campos_frame, textvariable=var, values=opciones,
                               width=36, state="readonly",
                               font=("Segoe UI", 10))
            cb.grid(row=row*2+1, column=0, columnspan=2,
                    sticky="ew", pady=(2, 0))
            return var

        campos_frame.columnconfigure(0, weight=1)
        campos_frame.columnconfigure(1, weight=1)

        try:
            tasa = self.db.obtener_tasa_cambio()
        except:
            tasa = 36.0
        mon = env.get("moneda", "C$")

        self.lbl_tasa = tk.Label(body, text="",
                                 font=("Segoe UI", 8), bg="#ffffff", fg="#888780")
        self.lbl_tasa.grid(row=4, column=0, columnspan=2,
                           sticky="w", pady=(2, 0))
        if "$" in mon:
            self.lbl_tasa.config(text=f"Tasa de cambio: 1$ = C${tasa:.2f}")
        else:
            self.lbl_tasa.config(text="")

        self.v_monto  = campo("Monto a pagar", 5)
        self.v_monto.set(f"{env['restante']:.2f}")

        self.v_tipo   = combo("Tipo de pago",
                              ["Efectivo C$", "Efectivo $",
                               "Transferencia"], 6)

        self.v_cajero = campo("Recibido por (cajero)", 7)
        self.v_nota   = campo("Nota (opcional)", 8)

        self.lbl_nuevo_rest = tk.Label(body,
            text=f"Nuevo restante: {mon}{env['restante']:,.2f}",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff", fg="#0f6e56")
        self.lbl_nuevo_rest.grid(row=12, column=0, columnspan=2,
                                  sticky="w", pady=(10, 0))

        self.lbl_exceso = tk.Label(body,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="#fcebeb", fg="#791f1f")
        self.lbl_exceso.grid(row=13, column=0, columnspan=2,
                              sticky="ew", pady=(4, 0))
        self.lbl_exceso.grid_remove()

        self.v_monto.trace_add("write", lambda *a: self._actualizar_rest())

        btn_f = tk.Frame(self, bg="#ffffff", padx=24, pady=12)
        btn_f.pack(fill="x")

        tk.Button(btn_f, text="Cancelar",
                  font=("Segoe UI", 10), bd=0,
                  bg="#f1efe8", fg="#5f5e5a",
                  activebackground="#d3d1c7",
                  pady=9, padx=16, cursor="hand2",
                  command=self.destroy).pack(side="left")

        tk.Button(btn_f, text="✓  Confirmar pago",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#0f6e56", fg="white",
                  activebackground="#085041",
                  pady=9, padx=16, cursor="hand2",
                  command=self._confirmar).pack(side="right")

    def _actualizar_rest(self):
        env = self.env
        mon = env.get("moneda", "C$")
        try:
            monto = float(self.v_monto.get())
            if monto > env["restante"]:
                exceso = monto - env["restante"]
                self.lbl_exceso.config(
                    text=f"⚠️  El pago excede el restante por {mon}{exceso:,.2f}. "
                         "El sobrante se registrará como abono adicional.",
                    wraplength=400)
                self.lbl_exceso.grid()
                nuevo_rest = 0
            else:
                self.lbl_exceso.grid_remove()
                nuevo_rest = env["restante"] - monto
            self.lbl_nuevo_rest.config(
                text=f"Nuevo restante: {mon}{nuevo_rest:,.2f}",
                fg="#791f1f" if nuevo_rest > 0 else "#0f6e56")
        except:
            pass

    def _confirmar(self):
        try:
            monto = float(self.v_monto.get())
        except ValueError:
            messagebox.showwarning("Error", "Ingrese un monto válido.", parent=self)
            return

        if monto <= 0:
            messagebox.showwarning("Error", "El monto debe ser mayor a 0.", parent=self)
            return

        cajero = self.v_cajero.get().strip()
        if not cajero:
            messagebox.showwarning("Requerido",
                                   "Ingrese el nombre del cajero.", parent=self)
            return

        env = self.env
        mon_raw = self.v_tipo.get()
        moneda  = "C$" if "C$" in mon_raw else "$"

        # Advertencia de sobrepago
        if monto > env["restante"]:
            exceso = monto - env["restante"]
            if not messagebox.askyesno(
                "Sobrepago detectado",
                f"El monto (C${monto:,.2f}) excede el restante (C${env['restante']:,.2f}).\n"
                f"El sobrante de C${exceso:,.2f} se registrará como abono extra.\n\n"
                "¿Desea continuar?",
                parent=self,
                icon="warning"
            ):
                return

        self.db.registrar_pago(
            envio_id=self.envio_id,
            monto=monto,
            moneda=moneda,
            tipo=self.v_tipo.get(),
            cajero=cajero,
            nota=self.v_nota.get().strip()
        )

        messagebox.showinfo("Pago registrado ✓",
                            f"Se registró el pago de {moneda}{monto:,.2f}",
                            parent=self)

        if self.on_success:
            self.on_success()

        self.destroy()
