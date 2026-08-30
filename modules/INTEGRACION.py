# ══════════════════════════════════════════════════════════
#  INTEGRACIÓN DE imprimir.py  —  Cambios por archivo
# ══════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────
# PASO 0: Instalar reportlab (una sola vez)
# ─────────────────────────────────────────────────────────
#   pip install reportlab
#
# Los PDFs se guardan automáticamente en la carpeta:
#   encomiendas_app/recibos/
# ══════════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────────
# 1. nueva_encomienda.py  — Imprimir recibo al guardar
# ─────────────────────────────────────────────────────────
# Agrega al inicio del archivo:
from modules.imprimir import imprimir_recibo

# Reemplaza el método _guardar() — bloque try/except final:
# ANTES:
#     try:
#         codigo = self.db.crear_envio(datos, articulos)
#         messagebox.showinfo("Guardado ✓",
#                             f"Encomienda registrada exitosamente.\nCódigo: {codigo}")
#         self._limpiar()
#     except Exception as e:
#         messagebox.showerror("Error", f"No se pudo guardar:\n{e}")

# DESPUÉS:
#     try:
#         codigo = self.db.crear_envio(datos, articulos)
#         # Obtener el id recién creado para imprimir
#         envios = self.db.listar_envios(codigo)
#         if envios:
#             resp = messagebox.askyesno(
#                 "Guardado ✓",
#                 f"Encomienda registrada.\nCódigo: {codigo}\n\n¿Imprimir recibo?")
#             if resp:
#                 imprimir_recibo(self.db, envios[0]["id"])
#         else:
#             messagebox.showinfo("Guardado ✓",
#                                 f"Encomienda registrada exitosamente.\nCódigo: {codigo}")
#         self._limpiar()
#     except Exception as e:
#         messagebox.showerror("Error", f"No se pudo guardar:\n{e}")


# ─────────────────────────────────────────────────────────
# 2. historial.py  — Botón "Imprimir" en la barra de filtros
#                    y botón "Imprimir recibo" en el detalle
# ─────────────────────────────────────────────────────────
# Agrega al inicio del archivo:
from modules.imprimir import imprimir_recibo, imprimir_historial

# En HistorialFrame._build(), justo después del botón "↺ Limpiar":
#     tk.Button(bar, text="🖨 Imprimir lista",
#               font=("Segoe UI", 9), bd=0,
#               bg="#e1f5ee", fg="#0f6e56",
#               activebackground="#9fe1cb",
#               pady=5, padx=10, cursor="hand2",
#               command=self._imprimir_lista).pack(side="left", padx=(8, 0))

# Agrega este método a HistorialFrame:
#     def _imprimir_lista(self):
#         buscar = self.v_buscar.get()
#         estado = "" if self.v_estado.get() == "Todos" else self.v_estado.get()
#         mes    = "" if self.v_mes.get() == "Todos" else self.v_mes.get()
#         try:
#             ruta = imprimir_historial(self.db, buscar, estado, mes)
#             messagebox.showinfo("PDF generado", f"Archivo guardado en:\n{ruta}")
#         except Exception as e:
#             messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")

# En DetailPanel.cargar(), dentro del bloque de botones (btn_frame),
# agrega este botón ANTES del botón "💳 Registrar pago":
#     tk.Button(btn_frame, text="🖨 Imprimir recibo",
#               font=("Segoe UI", 9), bd=0,
#               bg="#e1f5ee", fg="#0f6e56",
#               activebackground="#9fe1cb",
#               pady=6, padx=12, cursor="hand2",
#               command=lambda: self._imprimir(envio_id)
#               ).pack(fill="x", pady=(0, 4))

# Agrega este método a DetailPanel:
#     def _imprimir(self, envio_id):
#         try:
#             ruta = imprimir_recibo(self.db, envio_id)
#             messagebox.showinfo("PDF generado", f"Archivo guardado en:\n{ruta}")
#         except Exception as e:
#             messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")


# ─────────────────────────────────────────────────────────
# 3. reportes.py  — Botón "Imprimir reporte" en el encabezado
# ─────────────────────────────────────────────────────────
# Agrega al inicio del archivo:
from modules.imprimir import imprimir_reporte

# En ReportesFrame._build(), junto al botón "↺ Actualizar":
#     tk.Button(header, text="🖨 Imprimir PDF",
#               font=("Segoe UI", 9), bd=0,
#               bg="#e1f5ee", fg="#0f6e56",
#               activebackground="#9fe1cb",
#               pady=5, padx=12, cursor="hand2",
#               command=self._imprimir).pack(side="right", padx=(0, 8))

# Agrega este método a ReportesFrame:
#     def _imprimir(self):
#         try:
#             ruta = imprimir_reporte(self.db)
#             messagebox.showinfo("PDF generado", f"Archivo guardado en:\n{ruta}")
#         except Exception as e:
#             messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")
#
# También agrega el import de messagebox al inicio:
#     from tkinter import ttk, messagebox
