"""
==============================================
  modules/historial.py
  Lista de todos los envios con busqueda,
  filtros y panel de detalle
==============================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from modules.imprimir import imprimir_recibo, imprimir_historial
from modules.nueva_encomienda import NuevaEncomiendaFrame
from modules.config import PAGINA_TAMANO
from modules.datepicker import datepicker_entry

# Precio por libra — cambiar aquí si varía la tarifa
try:
    from modules.config import PRECIO_LB
except ImportError:
    PRECIO_LB = 10  # valor por defecto si no está definido en config.py


ESTADOS_COLOR = {
    "Pagado":    ("#e1f5ee", "#085041"),
    "Abono":     ("#e6f1fb", "#0c447c"),
    "Pendiente": ("#faeeda", "#633806"),
    "Cancelado": ("#fcebeb", "#791f1f"),
}

_DEBOUNCE_MS = 350


class HistorialFrame(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#f5f5f0")
        self.db  = db
        self.app = app
        self._orden_col     = "fecha"
        self._orden_reverso = True   # más reciente primero por defecto
        self._pagina        = 1
        self._por_pagina    = PAGINA_TAMANO
        self._total_paginas = 1
        self._debounce_id   = None
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#ffffff", pady=14)
        header.pack(fill="x")
        tk.Label(header, text="📋  Historial de encomiendas",
                 font=("Segoe UI", 14, "bold"),
                 bg="#ffffff", fg="#0f6e56").pack(side="left", padx=20)
        self._lbl_total_hdr = tk.Label(header, text="",
                                        font=("Segoe UI", 9),
                                        bg="#ffffff", fg="#888780")
        self._lbl_total_hdr.pack(side="right", padx=20)

        # ── Barra de filtros en dos filas ─────────────────────────────────────
        bar = tk.Frame(self, bg="#f0efe8", padx=14, pady=6)
        bar.pack(fill="x")
        bar.columnconfigure(1, weight=1)   # búsqueda se estira

        def _lbl(parent, txt, row, col, **kw):
            tk.Label(parent, text=txt, font=("Segoe UI", 8),
                     bg="#f0efe8", fg="#888780", **kw
                     ).grid(row=row, column=col, sticky="w",
                            padx=(0, 2), pady=(2, 0))

        def _sep(parent, row, col):
            """Separador vertical decorativo."""
            tk.Frame(parent, bg="#d8d6cf", width=1
                     ).grid(row=row, column=col, rowspan=2,
                            sticky="ns", padx=8, pady=4)

        # ── FILA 0: etiquetas ────────────────────────────────────────────────
        # ── FILA 1: controles ────────────────────────────────────────────────

        # Búsqueda (col 0-1, ocupa más espacio)
        f_buscar = tk.Frame(bar, bg="#f0efe8")
        f_buscar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 8))
        tk.Label(f_buscar, text="🔍  Buscar", font=("Segoe UI", 8),
                 bg="#f0efe8", fg="#888780").pack(anchor="w")
        self.v_buscar = tk.StringVar()
        self.v_buscar.trace_add("write", self._on_buscar_change)
        ttk.Entry(f_buscar, textvariable=self.v_buscar,
                  width=26, font=("Segoe UI", 10)).pack(fill="x", pady=(2, 0))

        _sep(bar, 0, 1)

        # Estado (col 2)
        _lbl(bar, "Estado", 0, 2)
        self.v_estado = tk.StringVar(value="Todos")
        cb_estado = ttk.Combobox(bar, textvariable=self.v_estado, width=10,
                                  values=["Todos", "Pagado", "Abono",
                                          "Pendiente", "Cancelado"],
                                  state="readonly", font=("Segoe UI", 9))
        cb_estado.grid(row=1, column=2, sticky="ew", padx=(0, 6), pady=(2, 4))
        cb_estado.bind("<<ComboboxSelected>>", lambda e: self._ir_pagina(1))

        # Mes (col 3)
        _lbl(bar, "Mes", 0, 3)
        self.v_mes = tk.StringVar(value="Todos")
        meses = ["Todos","Enero","Febrero","Marzo","Abril","Mayo",
                 "Junio","Julio","Agosto","Septiembre","Octubre",
                 "Noviembre","Diciembre"]
        cb_mes = ttk.Combobox(bar, textvariable=self.v_mes, width=10,
                               values=meses, state="readonly", font=("Segoe UI", 9))
        cb_mes.grid(row=1, column=3, sticky="ew", padx=(0, 6), pady=(2, 4))
        cb_mes.bind("<<ComboboxSelected>>", lambda e: self._ir_pagina(1))

        _sep(bar, 0, 4)

        # Desde (col 5)
        _lbl(bar, "Desde", 0, 5)
        self.v_desde = tk.StringVar()
        self.v_desde.trace_add("write", lambda *a: self._ir_pagina(1))
        datepicker_entry(bar, self.v_desde, width=10
                         ).grid(row=1, column=5, sticky="ew", padx=(0, 4), pady=(2, 4))

        # Hasta (col 6)
        _lbl(bar, "Hasta", 0, 6)
        self.v_hasta = tk.StringVar()
        self.v_hasta.trace_add("write", lambda *a: self._ir_pagina(1))
        datepicker_entry(bar, self.v_hasta, width=10
                         ).grid(row=1, column=6, sticky="ew", padx=(0, 6), pady=(2, 4))

        _sep(bar, 0, 7)

        # Destino (col 8)
        _lbl(bar, "Destino", 0, 8)
        self.v_destino = tk.StringVar(value="Todos")
        _destinos_filtro = ["Todos","Sin asignar","Miami, FL","Nueva York, NY",
                            "Los Ángeles, CA","Chicago, IL","Houston, TX","Phoenix, AZ",
                            "Dallas, TX","San Antonio, TX","San Diego, CA",
                            "San Francisco, CA","Las Vegas, NV","Austin, TX",
                            "Orlando, FL","Atlanta, GA","Boston, MA","Seattle, WA",
                            "Denver, CO","Washington, DC","Otro (especificar en notas)"]
        cb_dest = ttk.Combobox(bar, textvariable=self.v_destino, width=13,
                               values=_destinos_filtro, state="readonly", font=("Segoe UI", 9))
        cb_dest.grid(row=1, column=8, sticky="ew", padx=(0, 6), pady=(2, 4))
        cb_dest.bind("<<ComboboxSelected>>", lambda e: self._ir_pagina(1))

        _sep(bar, 0, 9)

        # Botones de acción (col 10)
        f_btns = tk.Frame(bar, bg="#f0efe8")
        f_btns.grid(row=0, column=10, rowspan=2, sticky="ns", padx=(0, 0))

        def _btn(parent, txt, bg, fg, cmd):
            return tk.Button(parent, text=txt, font=("Segoe UI", 8),
                             bd=0, bg=bg, fg=fg,
                             pady=4, padx=9, cursor="hand2", command=cmd)

        self._btn_limpiar = _btn(f_btns, "↺ Limpiar", "#f1efe8", "#5f5e5a", self._limpiar_filtros)
        self._btn_limpiar.pack(fill="x", pady=(2, 2))
        _btn(f_btns, "🖨 Lista", "#e1f5ee", "#0f6e56", self._imprimir_lista).pack(fill="x", pady=(0, 2))
        _btn(f_btns, "📥 CSV",   "#e6f1fb", "#0c447c", self._exportar_csv).pack(fill="x")

        # Rastrear cambios para indicador de filtros activos
        for v in (self.v_buscar, self.v_estado, self.v_mes, self.v_desde, self.v_hasta, self.v_destino):
            v.trace_add("write", self._actualizar_btn_limpiar)

        paned = tk.PanedWindow(self, orient="horizontal",
                                bg="#d8d6cf", sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=14, pady=(6, 12))

        list_frame = tk.Frame(paned, bg="#ffffff",
                               highlightthickness=1, highlightbackground="#dddbd4")
        paned.add(list_frame, minsize=380)

        self._build_tree(list_frame)
        self._build_paginacion(list_frame)

        self.detail = DetailPanel(paned, self.db, self.app)
        paned.add(self.detail, minsize=300)

        self.refresh()

    def _build_tree(self, parent):
        style = ttk.Style()
        style.configure("Hist.Treeview",
                         font=("Segoe UI", 9), rowheight=26,
                         background="#ffffff", fieldbackground="#ffffff", borderwidth=0)
        style.configure("Hist.Treeview.Heading",
                         font=("Segoe UI", 9, "bold"), background="#f0efe8", relief="flat")
        style.map("Hist.Treeview",
                  background=[("selected", "#d4f5eb")],
                  foreground=[("selected", "#085041")])

        cols = ("codigo","fecha","entrega","recibe","peso","total","estado")
        self.tree = ttk.Treeview(parent, columns=cols,
                                  show="headings", selectmode="browse",
                                  style="Hist.Treeview")
        hdrs = [
            ("codigo",  "Código",   90,  "w"),
            ("fecha",   "Fecha",    88,  "w"),
            ("entrega", "Entrega", 120,  "w"),
            ("recibe",  "Recibe",  120,  "w"),
            ("peso",    "Peso",     65, "center"),
            ("total",   "Total",    85,  "e"),
            ("estado",  "Estado",   82, "center"),
        ]
        for col, txt, w, anc in hdrs:
            self.tree.heading(col, text=txt, command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=w, minwidth=40, anchor=anc)

        self.tree.tag_configure("Pagado",    foreground="#085041", background="#f6fdf9")
        self.tree.tag_configure("Abono",     foreground="#0c447c", background="#f4f8fd")
        self.tree.tag_configure("Pendiente", foreground="#7a4800", background="#fdf8f0")
        self.tree.tag_configure("Cancelado", foreground="#791f1f", background="#fdf3f3")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._editar_seleccionado())

    def _build_paginacion(self, parent):
        pag = tk.Frame(parent, bg="#f0efe8", pady=5)
        pag.pack(fill="x")
        self._pag_label = tk.Label(pag, text="", font=("Segoe UI", 8),
                                    bg="#f0efe8", fg="#888780")
        self._pag_label.pack(side="left", padx=10)

        def _pbtn(txt, cmd):
            return tk.Button(pag, text=txt, font=("Segoe UI", 8),
                             bd=0, bg="#f0efe8", fg="#5f5e5a",
                             pady=2, padx=6, cursor="hand2", command=cmd)

        _pbtn("▶▶ Última",   lambda: self._ir_pagina(self._total_paginas)).pack(side="right", padx=2)
        _pbtn("Siguiente ▶", lambda: self._ir_pagina(self._pagina + 1)).pack(side="right", padx=2)

        # Campo de página directa
        self._v_pag_entry = tk.StringVar()
        e_pag = ttk.Entry(pag, textvariable=self._v_pag_entry,
                          width=4, font=("Segoe UI", 8), justify="center")
        e_pag.pack(side="right", padx=2)
        e_pag.bind("<Return>", self._ir_pagina_directa)
        e_pag.bind("<FocusOut>", self._ir_pagina_directa)
        tk.Label(pag, text="Ir a:", font=("Segoe UI", 8),
                 bg="#f0efe8", fg="#888780").pack(side="right", padx=(4, 0))

        _pbtn("◀ Anterior",  lambda: self._ir_pagina(self._pagina - 1)).pack(side="right", padx=2)
        _pbtn("◀◀ Primera",  lambda: self._ir_pagina(1)).pack(side="right", padx=2)

    def _ir_pagina_directa(self, event=None):
        try:
            n = int(self._v_pag_entry.get())
            self._ir_pagina(n)
        except (ValueError, AttributeError):
            pass
        finally:
            self._v_pag_entry.set("")

    def _on_buscar_change(self, *args):
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(_DEBOUNCE_MS, lambda: self._ir_pagina(1))

    def _actualizar_btn_limpiar(self, *args):
        """Cambia el color del botón Limpiar cuando hay filtros activos."""
        hay_filtros = (
            self.v_buscar.get().strip() or
            self.v_estado.get() != "Todos" or
            self.v_mes.get() != "Todos" or
            self.v_desde.get().strip() or
            self.v_hasta.get().strip() or
            self.v_destino.get() != "Todos"
        )
        if hay_filtros:
            self._btn_limpiar.config(bg="#faeeda", fg="#633806", text="↺ Limpiar ●")
        else:
            self._btn_limpiar.config(bg="#f1efe8", fg="#5f5e5a", text="↺ Limpiar")

    def _ir_pagina(self, n):
        n = max(1, min(n, self._total_paginas))
        self._pagina = n
        self.refresh()

    def _limpiar_filtros(self):
        self.v_buscar.set("")
        self.v_estado.set("Todos")
        self.v_mes.set("Todos")
        self.v_desde.set("")
        self.v_hasta.set("")
        self.v_destino.set("Todos")
        self._ir_pagina(1)

    def refresh(self):
        buscar      = self.v_buscar.get().strip()
        estado      = "" if self.v_estado.get() == "Todos" else self.v_estado.get()
        mes         = "" if self.v_mes.get() == "Todos" else self.v_mes.get()
        fecha_desde = self.v_desde.get().strip()
        fecha_hasta = self.v_hasta.get().strip()
        destino     = "" if self.v_destino.get() == "Todos" else self.v_destino.get()

        try:
            try:
                total = self.db.contar_envios(buscar, estado, mes, fecha_desde, fecha_hasta,
                                              destino=destino)
            except TypeError:
                # Compatibilidad: DB aún no acepta kwarg destino
                total = self.db.contar_envios(buscar, estado, mes, fecha_desde, fecha_hasta)
        except Exception as ex:
            messagebox.showerror("Error de base de datos",
                                  f"No se pudo cargar el historial:\n{ex}")
            return

        self._total_paginas = max(1, (total + self._por_pagina - 1) // self._por_pagina)
        if self._pagina > self._total_paginas:
            self._pagina = self._total_paginas

        self._lbl_total_hdr.config(
            text=f"{total} envío{'s' if total != 1 else ''} encontrado{'s' if total != 1 else ''}")

        self.tree.delete(*self.tree.get_children())

        try:
            envios = self.db.listar_envios(
                buscar, estado, mes,
                pagina=self._pagina,
                por_pagina=self._por_pagina,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                destino=destino,
                orden_col=self._orden_col,
                orden_desc=self._orden_reverso,
            )
        except TypeError:
            # Compatibilidad: si la DB aún no acepta orden_col/destino, llamar sin ellos
            envios = self.db.listar_envios(buscar, estado, mes,
                                           pagina=self._pagina,
                                           por_pagina=self._por_pagina,
                                           fecha_desde=fecha_desde,
                                           fecha_hasta=fecha_hasta)
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo listar envíos:\n{ex}")
            return

        for e in envios:
            fecha = e["fecha"]
            if "T" in fecha:
                fecha = fecha.split("T")[0]
            elif len(fecha) > 10:
                fecha = fecha[:10]

            self.tree.insert("", "end",
                iid=str(e["id"]),
                values=(
                    e["codigo"], fecha,
                    e["ent_nombre"], e["rec_nombre"],
                    f"{e.get('peso_total') or 0:.1f} lb",
                    f"${e['total']:,.2f}",
                    e["estado"],
                ),
                tags=(e["estado"],))

        # Estado vacío informativo
        if total == 0:
            hay_filtros = buscar or estado or mes or fecha_desde or fecha_hasta or destino
            msg = ("No se encontraron envíos con los filtros actuales.\n"
                   "Usa el botón '↺ Limpiar' para ver todos los registros."
                   if hay_filtros else
                   "Aún no hay envíos registrados.")
            self.tree.insert("", "end", iid="__empty__",
                             values=(msg, "", "", "", "", "", ""),
                             tags=("empty",))
            self.tree.tag_configure("empty", foreground="#aaa9a5")

        self._pag_label.config(
            text=f"Pág. {self._pagina} / {self._total_paginas}  ·  {total} registros")

    def _on_select(self, event):
        sel = self.tree.selection()
        if sel:
            self.detail.cargar(int(sel[0]))

    def _editar_seleccionado(self):
        sel = self.tree.selection()
        if sel:
            self.detail._editar(int(sel[0]))

    def _ordenar(self, col):
        if self._orden_col == col:
            self._orden_reverso = not self._orden_reverso
        else:
            self._orden_col     = col
            self._orden_reverso = False

        # Actualizar flechas en cabeceras
        nombres = {"codigo":"Código","fecha":"Fecha","entrega":"Entrega",
                   "recibe":"Recibe","peso":"Peso","total":"Total","estado":"Estado"}
        for c, txt in nombres.items():
            flecha = (" ▲" if not self._orden_reverso else " ▼") if c == col else ""
            self.tree.heading(c, text=txt + flecha)

        # Recargar desde la DB con el nuevo orden (ordena TODOS los registros, no solo la página)
        self._ir_pagina(1)

    def _imprimir_lista(self):
        buscar      = self.v_buscar.get()
        estado      = "" if self.v_estado.get() == "Todos" else self.v_estado.get()
        mes         = "" if self.v_mes.get() == "Todos" else self.v_mes.get()
        fecha_desde = self.v_desde.get().strip()
        fecha_hasta = self.v_hasta.get().strip()
        try:
            ruta = imprimir_historial(self.db, buscar, estado, mes,
                                      fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
            messagebox.showinfo("PDF generado ✓", f"Archivo guardado en:\n{ruta}")
        except TypeError:
            # Compatibilidad si imprimir_historial no acepta kwargs de fecha
            try:
                ruta = imprimir_historial(self.db, buscar, estado, mes)
                messagebox.showinfo("PDF generado ✓", f"Archivo guardado en:\n{ruta}")
            except Exception as e:
                messagebox.showerror("Error al imprimir", f"No se pudo generar el PDF:\n{e}")
        except Exception as e:
            messagebox.showerror("Error al imprimir", f"No se pudo generar el PDF:\n{e}")

    def _exportar_csv(self):
        buscar      = self.v_buscar.get()
        estado      = "" if self.v_estado.get() == "Todos" else self.v_estado.get()
        mes         = "" if self.v_mes.get() == "Todos" else self.v_mes.get()
        fecha_desde = self.v_desde.get().strip()
        fecha_hasta = self.v_hasta.get().strip()
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV","*.csv")],
            title="Guardar como CSV")
        if not ruta:
            return
        try:
            ok = self.db.exportar_csv(ruta, buscar, estado, mes,
                                       fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
            if ok:
                messagebox.showinfo("CSV exportado ✓", f"Archivo guardado en:\n{ruta}")
            else:
                messagebox.showwarning("Sin datos", "No hay registros para exportar.")
        except TypeError:
            # Compatibilidad si exportar_csv no acepta kwargs de fecha
            try:
                ok = self.db.exportar_csv(ruta, buscar, estado, mes)
                if ok:
                    messagebox.showinfo("CSV exportado ✓", f"Archivo guardado en:\n{ruta}")
                else:
                    messagebox.showwarning("Sin datos", "No hay registros para exportar.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")


# ══════════════════════════════════════════════════════════════════════════════
#  PANEL DE DETALLE
# ══════════════════════════════════════════════════════════════════════════════

class DetailPanel(tk.Frame):
    def __init__(self, parent, db, app):
        super().__init__(parent, bg="#ffffff",
                         highlightthickness=1, highlightbackground="#dddbd4")
        self.db       = db
        self.app      = app
        self.envio_id = None
        self._build_empty()

    def _build_empty(self):
        for w in self.winfo_children():
            w.destroy()
        tk.Label(self, text="Selecciona un envío\npara ver el detalle",
                 font=("Segoe UI", 11), bg="#ffffff",
                 fg="#c4c2b9", justify="center").pack(expand=True)

    def cargar(self, envio_id):
        self.envio_id = envio_id
        env  = self.db.obtener_envio(envio_id)
        arts = self.db.obtener_articulos(envio_id)
        pags = self.db.obtener_pagos(envio_id)
        if not env:
            return

        for w in self.winfo_children():
            w.destroy()

        canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg="#ffffff", padx=14, pady=12)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))

        def _scroll(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        canvas.bind_all("<MouseWheel>", _scroll)
        # Desregistrar cuando el panel se reconstruya
        canvas.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._render_detalle(inner, env, arts, pags, envio_id)

    def _render_detalle(self, inner, env, arts, pags, envio_id):
        est = env["estado"]
        est_bg, est_fg = ESTADOS_COLOR.get(est, ("#f1efe8", "#444441"))

        # Código + estado
        top = tk.Frame(inner, bg="#ffffff")
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text=env["codigo"],
                 font=("Segoe UI", 14, "bold"),
                 bg="#ffffff", fg="#0f6e56").pack(side="left")
        tk.Label(top, text=f"  {est}  ",
                 font=("Segoe UI", 9, "bold"),
                 bg=est_bg, fg=est_fg, padx=6, pady=3).pack(side="right")

        # Fecha
        fecha = env["fecha"][:16] if len(env["fecha"]) > 16 else env["fecha"]
        tk.Label(inner, text=f"🕐  {fecha}",
                 font=("Segoe UI", 8), bg="#ffffff", fg="#aaa9a5").pack(anchor="w", pady=(0,6))

        # Destino
        destino = env.get("destino_usa", "")
        if destino and destino != "Sin asignar":
            tk.Label(inner, text=f"🗺️  {destino}",
                     font=("Segoe UI", 9, "bold"),
                     bg="#e1f5ee", fg="#085041",
                     padx=10, pady=4, anchor="w").pack(fill="x", pady=(0, 8))

        tk.Frame(inner, bg="#e8e6df", height=1).pack(fill="x", pady=(0, 8))

        # Tarjetas remitente / destinatario
        personas = tk.Frame(inner, bg="#ffffff")
        personas.pack(fill="x", pady=(0, 8))
        personas.columnconfigure(0, weight=1)
        personas.columnconfigure(1, weight=1)
        self._card_persona(personas, "👤 Entrega",
                           env["ent_nombre"], env.get("ent_tel",""), env.get("ent_dir",""), col=0)
        self._card_persona(personas, "📦 Recibe",
                           env["rec_nombre"], env.get("rec_tel",""), env.get("rec_dir",""), col=1)

        # Artículos
        self._titulo(inner, "📋 ARTÍCULOS")
        art_frame = tk.Frame(inner, bg="#f8f8f5",
                             highlightthickness=1, highlightbackground="#e8e6df")
        art_frame.pack(fill="x", pady=(0, 8))

        for i, a in enumerate(arts):
            bg_row = "#ffffff" if i % 2 == 0 else "#f8f8f5"
            row = tk.Frame(art_frame, bg=bg_row)
            row.pack(fill="x")

            peso  = float(a.get("peso_lb", 0) or 0)
            valor = float(a.get("valor",   0) or 0)
            cant  = int(a.get("cantidad",  1) or 1)
            tipo_art = (a.get("tipo") or "").lower()

            if tipo_art == "medicamento":
                badge    = ("MED",  "#f0e6f9", "#6b2fa0")
                det_txt  = f"$ {valor:,.2f}"
                det_fg   = "#6b2fa0"
                importe  = cant * valor
            elif tipo_art == "vario":
                badge    = ("VAR",  "#e8f0fb", "#1a3f6b")
                det_txt  = f"$ {valor:,.2f}"
                det_fg   = "#1a3f6b"
                importe  = cant * valor
            elif tipo_art == "documento" or (peso == 0 and valor > 0):
                badge    = ("DOC",  "#fcebeb", "#791f1f")
                det_txt  = f"$ {valor:,.2f}"
                det_fg   = "#791f1f"
                importe  = cant * valor
            else:
                badge    = ("PROD", "#e1f5ee", "#085041")
                det_txt  = f"{peso:.1f} lb"
                det_fg   = "#888780"
                importe  = cant * peso * PRECIO_LB

            tk.Label(row, text=f"{cant}×",
                     font=("Segoe UI", 8, "bold"),
                     bg=bg_row, fg="#0f6e56", width=3, anchor="e").pack(side="left", padx=(8,4), pady=5)
            tk.Label(row, text=a["descripcion"],
                     font=("Segoe UI", 9), bg=bg_row,
                     fg="#2c2c2a").pack(side="left", pady=5)

            # Importe calculado al extremo derecho
            imp_color = "#6b2fa0" if tipo_art == "medicamento" else ("#1a3f6b" if tipo_art == "vario" else ("#791f1f" if tipo_art == "documento" or (peso == 0 and valor > 0) else "#0f6e56"))
            tk.Label(row, text=f"${importe:,.2f}",
                     font=("Segoe UI", 9, "bold"),
                     bg=bg_row, fg=imp_color).pack(side="right", padx=(4, 8), pady=5)

            tk.Label(row, text=badge[0],
                     font=("Segoe UI", 7, "bold"),
                     bg=badge[1], fg=badge[2],
                     padx=4, pady=1).pack(side="right", padx=(4, 2), pady=5)
            tk.Label(row, text=det_txt,
                     font=("Segoe UI", 9),
                     bg=bg_row, fg=det_fg).pack(side="right", pady=5)
        tot_frame = tk.Frame(inner, bg="#e8f5ee",
                             highlightthickness=1, highlightbackground="#b8dece")
        tot_frame.pack(fill="x", pady=(0, 8))
        for lbl, val, rojo in [
            ("Total",      f"${env['total']:,.2f}",      False),
            ("Abono",      f"${env['abono']:,.2f}",      False),
            ("Restante",   f"${env['restante']:,.2f}",   env.get("restante", 0) > 0),
            ("Peso total", f"{env.get('peso_total') or 0:.1f} lb", False),
        ]:
            r = tk.Frame(tot_frame, bg="#e8f5ee")
            r.pack(fill="x", padx=12, pady=3)
            tk.Label(r, text=lbl, font=("Segoe UI", 9),
                     bg="#e8f5ee", fg="#085041").pack(side="left")
            tk.Label(r, text=val, font=("Segoe UI", 10, "bold"),
                     bg="#e8f5ee",
                     fg="#c0392b" if rojo else "#085041").pack(side="right")

        # Barra de progreso
        pct = (env["abono"] / env["total"] * 100) if env["total"] > 0 else 0
        cvs = tk.Canvas(inner, bg="#e8e6df", height=20, highlightthickness=0)
        cvs.pack(fill="x", pady=(0, 10))

        def _barra(event=None):
            w = cvs.winfo_width() or 240
            cvs.delete("all")
            fw = int(w * min(pct, 100) / 100)
            color = "#0f6e56" if pct >= 100 else "#1a8a6a" if pct >= 50 else "#e6a817"
            cvs.create_rectangle(0, 0, w, 20, fill="#e8e6df", outline="")
            if fw > 0:
                cvs.create_rectangle(0, 0, fw, 20, fill=color, outline="")
            cvs.create_text(w // 2, 10,
                            text=f"{pct:.0f}% pagado  (${env['abono']:,.0f} / ${env['total']:,.0f})",
                            font=("Segoe UI", 8, "bold"),
                            fill="#ffffff" if pct > 35 else "#444441", anchor="center")

        cvs.bind("<Configure>", _barra)
        cvs.after(50, _barra)

        # Pagos
        if pags:
            self._titulo(inner, "💳 PAGOS")
            for p in pags:
                pf = tk.Frame(inner, bg="#f0f6ff",
                              highlightthickness=1, highlightbackground="#cde0f5")
                pf.pack(fill="x", pady=2)
                tk.Label(pf, text=f"  {str(p['fecha'])[:10]}  ·  {p.get('tipo','—')}",
                         font=("Segoe UI", 9), bg="#f0f6ff", fg="#444441").pack(side="left", padx=4, pady=4)
                tk.Label(pf, text=f"{p['moneda']}{p['monto']:,.2f}",
                         font=("Segoe UI", 9, "bold"),
                         bg="#f0f6ff", fg="#0c447c").pack(side="right", padx=8, pady=4)

        # Nota
        if env.get("nota"):
            self._titulo(inner, "📝 NOTA")
            tk.Label(inner, text=env["nota"],
                     font=("Segoe UI", 9), bg="#fffbf0",
                     fg="#2c2c2a", wraplength=220,
                     justify="left", anchor="nw",
                     padx=10, pady=6).pack(fill="x", pady=(0, 8))

        tk.Frame(inner, bg="#e8e6df", height=1).pack(fill="x", pady=(4, 10))

        # Botones
        self._render_botones(inner, env, envio_id)

    def _render_botones(self, parent, env, envio_id):
        fila1 = tk.Frame(parent, bg="#ffffff")
        fila1.pack(fill="x", pady=(0, 4))
        fila1.columnconfigure(0, weight=1)
        fila1.columnconfigure(1, weight=1)

        tk.Button(fila1, text="🖨 PDF", font=("Segoe UI", 9), bd=0,
                  bg="#e1f5ee", fg="#0f6e56", activebackground="#b8e8d5",
                  pady=7, cursor="hand2",
                  command=lambda: self._imprimir(envio_id)
                  ).grid(row=0, column=0, sticky="ew", padx=(0, 3))

        tk.Button(parent, text="✏️  Editar envío", font=("Segoe UI", 9), bd=0,
                  bg="#e6f1fb", fg="#0c447c", activebackground="#b3d4f0",
                  pady=7, padx=12, cursor="hand2",
                  command=lambda: self._editar(envio_id)
                  ).pack(fill="x", pady=(0, 4))

        if env["estado"] not in ("Pagado", "Cancelado"):
            tk.Button(parent, text="💳 Registrar pago",
                      font=("Segoe UI", 9, "bold"), bd=0,
                      bg="#0f6e56", fg="white", activebackground="#085041",
                      pady=8, padx=12, cursor="hand2",
                      command=lambda: self.app.abrir_pago(envio_id)
                      ).pack(fill="x", pady=(0, 4))

        if env["estado"] != "Cancelado":
            tk.Button(parent, text="✕ Cancelar envío", font=("Segoe UI", 9), bd=0,
                      bg="#fcebeb", fg="#791f1f", activebackground="#f09595",
                      pady=7, padx=12, cursor="hand2",
                      command=lambda: self._cancelar(envio_id)
                      ).pack(fill="x", pady=(0, 4))

        tk.Button(parent, text="🗑 Eliminar registro", font=("Segoe UI", 9), bd=0,
                  bg="#f1efe8", fg="#888780", activebackground="#d3d1c7",
                  pady=7, padx=12, cursor="hand2",
                  command=lambda: self._eliminar(envio_id)
                  ).pack(fill="x")

    # ── Helpers visuales ──────────────────────────────────────────────────────

    def _titulo(self, parent, texto):
        tk.Label(parent, text=texto, font=("Segoe UI", 8, "bold"),
                 bg="#ffffff", fg="#888780", anchor="w").pack(anchor="w", pady=(6, 3))

    def _card_persona(self, parent, titulo, nombre, tel, direccion, col):
        card = tk.Frame(parent, bg="#f8f8f5",
                        highlightthickness=1, highlightbackground="#e4e2db")
        card.grid(row=0, column=col, sticky="nsew",
                  padx=(0, 4) if col == 0 else (4, 0))
        tk.Label(card, text=titulo, font=("Segoe UI", 8, "bold"),
                 bg="#f0efe8", fg="#666563",
                 anchor="w", padx=8, pady=4).pack(fill="x")
        tk.Label(card, text=nombre or "—", font=("Segoe UI", 10, "bold"),
                 bg="#f8f8f5", fg="#1a1a18",
                 anchor="w", padx=8).pack(fill="x", pady=(4, 0))
        if tel:
            tk.Label(card, text=f"📞 {tel}", font=("Segoe UI", 8),
                     bg="#f8f8f5", fg="#666563",
                     anchor="w", padx=8).pack(fill="x")
        if direccion:
            tk.Label(card, text=f"📍 {direccion}", font=("Segoe UI", 8),
                     bg="#f8f8f5", fg="#666563",
                     anchor="w", padx=8).pack(fill="x", pady=(0, 4))

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _imprimir(self, envio_id):
        try:
            ruta = imprimir_recibo(self.db, envio_id, abrir=True)
        except Exception as e:
            messagebox.showerror("Error al imprimir", f"No se pudo generar el PDF:\n{e}")

    def _cancelar(self, envio_id):
        if messagebox.askyesno("Cancelar envío",
                                "¿Confirma que desea cancelar este envío?"):
            self.db.cancelar_envio(envio_id)
            self.app.mark_dirty(["historial", "kpi", "reportes", "cobrar", "arqueo"])
            self.cargar(envio_id)
            if hasattr(self.app.frames.get("historial", None), "refresh"):
                self.app.frames["historial"].refresh()

    def _eliminar(self, envio_id):
        env = self.db.obtener_envio(envio_id)
        nombre = env.get("ent_nombre", "?") if env else "?"
        codigo = env.get("codigo", f"#{envio_id}") if env else f"#{envio_id}"
        if messagebox.askyesno(
                "Eliminar registro",
                f"¿Eliminar permanentemente el envío {codigo} de {nombre}?\n\n"
                "Esta acción no se puede deshacer.",
                icon="warning"):
            self.db.eliminar_envio(envio_id)
            self.app.mark_dirty(["historial", "kpi", "reportes", "cobrar", "arqueo"])
            self._build_empty()
            self.app.frames["historial"].refresh()

    def _editar(self, envio_id):
        env  = self.db.obtener_envio(envio_id)
        arts = self.db.obtener_articulos(envio_id)
        if not env:
            return

        DESTINOS = [
            "Sin asignar",
            "Miami, FL", "Nueva York, NY", "Los Ángeles, CA",
            "Chicago, IL", "Houston, TX", "Phoenix, AZ",
            "Dallas, TX", "San Antonio, TX", "San Diego, CA",
            "San Francisco, CA", "Las Vegas, NV", "Austin, TX",
            "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH",
            "Charlotte, NC", "Indianapolis, IN", "Seattle, WA",
            "Denver, CO", "Washington, DC", "Boston, MA",
            "El Paso, TX", "Nashville, TN", "Detroit, MI",
            "Oklahoma City, OK", "Portland, OR", "Memphis, TN",
            "Louisville, KY", "Baltimore, MD", "Milwaukee, WI",
            "Albuquerque, NM", "Tucson, AZ", "Fresno, CA",
            "Sacramento, CA", "Kansas City, MO", "Mesa, AZ",
            "Atlanta, GA", "Miami Gardens, FL", "Orlando, FL",
            "Raleigh, NC", "Omaha, NE", "Colorado Springs, CO",
            "Virginia Beach, VA", "Long Beach, CA", "Oakland, CA",
            "Minneapolis, MN", "Tampa, FL", "Arlington, TX",
            "New Orleans, LA", "Wichita, KS", "Cleveland, OH",
            "Tulsa, OK", "Bakersfield, CA",
        ]

        win = tk.Toplevel(self)
        win.title(f"Editar {env['codigo']}")
        win.geometry("750x700")
        win.configure(bg="#f8f9fa")
        win.grab_set()
        win.resizable(True, True)

        canvas = tk.Canvas(win, bg="#f8f9fa", highlightthickness=0)
        vsb = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg="#f8f9fa")
        win_id = canvas.create_window((0,0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        def _on_scroll_edit(e):
            try: canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except: pass
        canvas.bind_all("<MouseWheel>", _on_scroll_edit)
        win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # ── Header ─────────────────────────────────────────────────────────────
        hdr = tk.Frame(body, bg="#0f6e56", pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"✏️  Editando {env['codigo']}",
                 font=("Segoe UI", 14, "bold"),
                 bg="#0f6e56", fg="#ffffff").pack(side="left", padx=20)
        estado_colors = {"Pagado":"#28a745","Abono":"#007bff","Pendiente":"#fd7e14","Cancelado":"#dc3545"}
        estado_bg = estado_colors.get(env.get("estado","Pendiente"), "#6c757d")
        tk.Label(hdr, text=f"  {env.get('estado','')}  ",
                 font=("Segoe UI", 9, "bold"),
                 bg=estado_bg, fg="#ffffff", padx=8, pady=3).pack(side="right", padx=20)

        def _card(titulo, icono=""):
            f = tk.Frame(body, bg="#ffffff", highlightthickness=1,
                         highlightbackground="#dee2e6")
            f.pack(fill="x", padx=16, pady=(0, 12))
            tk.Label(f, text=f"{icono}  {titulo}" if icono else titulo,
                     font=("Segoe UI", 10, "bold"),
                     bg="#e9ecef", fg="#0f6e56",
                     pady=7, padx=12, anchor="w").pack(fill="x")
            b = tk.Frame(f, bg="#ffffff", padx=12, pady=10)
            b.pack(fill="x")
            return b

        def _input_row(parent, label, var, row, col=0, width=22, placeholder=""):
            frame = tk.Frame(parent, bg="#ffffff")
            frame.grid(row=row, column=col, sticky="ew", padx=(0,8), pady=(2,6))
            tk.Label(frame, text=label, font=("Segoe UI", 8),
                     bg="#ffffff", fg="#6c757d").pack(anchor="w")
            e = ttk.Entry(frame, textvariable=var, width=width, font=("Segoe UI", 10))
            e.pack(fill="x", pady=(2,0))
            return e

        # ── Remitente ─────────────────────────────────────────────────────────
        b1 = _card("REMITENTE", "👤")
        b1.columnconfigure((0,1), weight=1)
        v_en = tk.StringVar(value=env.get("ent_nombre",""))
        v_et = tk.StringVar(value=env.get("ent_tel",""))
        v_ed = tk.StringVar(value=env.get("ent_dir",""))
        _input_row(b1, "Nombre completo *", v_en, 0, 0)
        _input_row(b1, "Teléfono", v_et, 0, 1)

        # ── Destinatario ──────────────────────────────────────────────────────
        b2 = _card("DESTINATARIO", "📦")
        b2.columnconfigure((0,1), weight=1)
        v_rn = tk.StringVar(value=env.get("rec_nombre",""))
        v_rt = tk.StringVar(value=env.get("rec_tel",""))
        v_rd = tk.StringVar(value=env.get("rec_dir",""))
        _input_row(b2, "Nombre completo *", v_rn, 0, 0)
        _input_row(b2, "Teléfono", v_rt, 0, 1)
        _input_row(b2, "Dirección en USA", v_rd, 1, 0)

        # ── Destino ───────────────────────────────────────────────────────────
        b3 = _card("DESTINO", "🗺️")
        b3.columnconfigure(0, weight=1)
        v_dest = tk.StringVar(value=env.get("destino_usa","Sin asignar"))
        _destinos_ed = list(DESTINOS)
        if v_dest.get() and v_dest.get() not in _destinos_ed:
            _destinos_ed.append(v_dest.get())
        tk.Label(b3, text="Ciudad destino", font=("Segoe UI", 8),
                 bg="#ffffff", fg="#6c757d").pack(anchor="w")
        _cb_dest_ed = ttk.Combobox(b3, textvariable=v_dest, values=_destinos_ed,
                     width=30, state="readonly", font=("Segoe UI", 10))
        _cb_dest_ed.pack(fill="x", pady=(2,8))

        # ── Artículos ──────────────────────────────────────────────────────────
        art_card = tk.Frame(body, bg="#ffffff", highlightthickness=1,
                            highlightbackground="#dee2e6")
        art_card.pack(fill="x", padx=16, pady=(0,12))

        titulo_bar = tk.Frame(art_card, bg="#e9ecef")
        titulo_bar.pack(fill="x")
        tk.Label(titulo_bar, text="📋  ARTÍCULOS",
                 font=("Segoe UI",10,"bold"), bg="#e9ecef", fg="#0f6e56",
                 pady=7, padx=12, anchor="w").pack(side="left")
        lbl_cant = tk.Label(titulo_bar, text="0 artículos",
                            font=("Segoe UI",9,"bold"),
                            bg="#0f6e56", fg="#ffffff", padx=8, pady=3)
        lbl_cant.pack(side="right", padx=12, pady=5)

        # Botones de tipo compactos
        btn_frame = tk.Frame(art_card, bg="#ffffff", pady=8)
        btn_frame.pack(fill="x", padx=12)
        tk.Button(btn_frame, text="⚖️ Peso", font=("Segoe UI",8,"bold"), bd=0,
                  bg="#faeeda", fg="#633806", pady=5, padx=10, cursor="hand2",
                  command=lambda: _abrir_peso_ed()).pack(side="left", padx=(0,6))
        tk.Button(btn_frame, text="💊 Medicamentos", font=("Segoe UI",8,"bold"), bd=0,
                  bg="#f0e6f9", fg="#6b2fa0", pady=5, padx=10, cursor="hand2",
                  command=lambda: _abrir_medicamentos_ed()).pack(side="left", padx=(0,6))
        tk.Button(btn_frame, text="📄 Documentos", font=("Segoe UI",8,"bold"), bd=0,
                  bg="#fce8e8", fg="#791f1f", pady=5, padx=10, cursor="hand2",
                  command=lambda: _abrir_documentos_ed()).pack(side="left", padx=(0,6))
        tk.Button(btn_frame, text="📦 Varios", font=("Segoe UI",8,"bold"), bd=0,
                  bg="#e8f0fb", fg="#1a3f6b", pady=5, padx=10, cursor="hand2",
                  command=lambda: _abrir_varios_ed()).pack(side="left", padx=(0,6))

        # ── Sección Por peso ──────────────────────────────────────
        peso_section = tk.Frame(art_card, bg="#ffffff")
        peso_hdr = tk.Frame(peso_section, bg="#4a2000", padx=12, pady=5)
        peso_hdr.pack(fill="x")
        tk.Label(peso_hdr, text="⚖️  ENVÍOS POR PESO",
                 font=("Segoe UI",9,"bold"),
                 bg="#4a2000", fg="#f5c97a").pack(side="left")
        peso_cols_hdr = tk.Frame(peso_section, bg="#6b3a0f", padx=12, pady=4)
        peso_cols_hdr.pack(fill="x")
        for txt, w in [("#",3),("Descripción",0),("Peso",8),("Importe",9),("",5)]:
            kw = {"width":w} if w else {}
            tk.Label(peso_cols_hdr, text=txt, font=("Segoe UI",8,"bold"),
                     bg="#6b3a0f", fg="#f5dab5", anchor="w", **kw).pack(side="left", padx=4)
        peso_filas_frame = tk.Frame(peso_section, bg="#fffaf5")
        peso_filas_frame.pack(fill="x")
        filas_peso_ed = []

        # ── Sección Medicamentos ──────────────────────────────────
        med_section = tk.Frame(art_card, bg="#ffffff")
        med_hdr = tk.Frame(med_section, bg="#6b2fa0", padx=12, pady=5)
        med_hdr.pack(fill="x")
        tk.Label(med_hdr, text="💊  MEDICAMENTOS",
                 font=("Segoe UI",9,"bold"),
                 bg="#6b2fa0", fg="#e8d5f5").pack(side="left")
        med_cols_hdr = tk.Frame(med_section, bg="#8e44c4", padx=12, pady=4)
        med_cols_hdr.pack(fill="x")
        for txt, w in [("#",3),("Medicamento",0),("Cant.",5),("Precio",8),("Importe",9),("",5)]:
            kw = {"width":w} if w else {}
            tk.Label(med_cols_hdr, text=txt, font=("Segoe UI",8,"bold"),
                     bg="#8e44c4", fg="#e8d5f5", anchor="w", **kw).pack(side="left", padx=4)
        med_filas_frame = tk.Frame(med_section, bg="#fdf8ff")
        med_filas_frame.pack(fill="x")
        filas_med_ed = []

        # ── Sección Documentos ────────────────────────────────────
        doc_section = tk.Frame(art_card, bg="#ffffff")
        doc_hdr = tk.Frame(doc_section, bg="#791f1f", padx=12, pady=5)
        doc_hdr.pack(fill="x")
        tk.Label(doc_hdr, text="📄  DOCUMENTOS",
                 font=("Segoe UI",9,"bold"),
                 bg="#791f1f", fg="#fce8e8").pack(side="left")
        doc_cols_hdr = tk.Frame(doc_section, bg="#9e2a2a", padx=12, pady=4)
        doc_cols_hdr.pack(fill="x")
        for txt, w in [("#",3),("Documento",0),("Cant.",5),("Precio",8),("Importe",9),("",5)]:
            kw = {"width":w} if w else {}
            tk.Label(doc_cols_hdr, text=txt, font=("Segoe UI",8,"bold"),
                     bg="#9e2a2a", fg="#fce8e8", anchor="w", **kw).pack(side="left", padx=4)
        doc_filas_frame = tk.Frame(doc_section, bg="#fff8f8")
        doc_filas_frame.pack(fill="x")
        filas_doc_ed = []

        # ── Sección Artículos Varios ──────────────────────────────
        varios_section = tk.Frame(art_card, bg="#ffffff")
        varios_hdr = tk.Frame(varios_section, bg="#1a3f6b", padx=12, pady=5)
        varios_hdr.pack(fill="x")
        tk.Label(varios_hdr, text="📦  ARTÍCULOS VARIOS",
                 font=("Segoe UI",9,"bold"),
                 bg="#1a3f6b", fg="#d4e4f5").pack(side="left")
        varios_cols_hdr = tk.Frame(varios_section, bg="#2a5a8a", padx=12, pady=4)
        varios_cols_hdr.pack(fill="x")
        for txt, w in [("#",3),("Artículo",0),("Cant.",5),("Precio",8),("Importe",9),("",5)]:
            kw = {"width":w} if w else {}
            tk.Label(varios_cols_hdr, text=txt, font=("Segoe UI",8,"bold"),
                     bg="#2a5a8a", fg="#d4e4f5", anchor="w", **kw).pack(side="left", padx=4)
        varios_filas_frame = tk.Frame(varios_section, bg="#f0f5fb")
        varios_filas_frame.pack(fill="x")
        filas_varios_ed = []

        # ── Barra de total ────────────────────────────────────────
        lbl_total_art = tk.Label(art_card, text="TOTAL  →  $ 0",
                                  font=("Segoe UI",10,"bold"),
                                  bg="#0f6e56", fg="#ffffff",
                                  anchor="e", padx=12, pady=8)
        lbl_total_art.pack(fill="x")

        # ── Precios predefinidos ──────────────────────────────────
        PRECIOS_DOC = {"Pasaporte":70.0,"Acta de nacimiento":30.0,"Cédula":30.0,"Licencia":30.0}
        TIPOS_DOC = ["Carta","Sobre","Pasaporte","Visa","Documentos legales","Fotografías",
                     "Cheque","Tarjeta","Contrato","Acta de nacimiento","Diploma / Título","Otro"]
        PRECIOS_MED = {"Blister de pastilla":5.0,"Jarabe":5.0,"Inyección / Ampolla":12.0,
                       "Pomada":3.0,"Gotero (ojos / oídos)":3.0}
        TIPOS_MED = list(PRECIOS_MED.keys())

        def _recalcular_total_ed():
            total = 0.0
            count = 0
            # Filas principales (productos)
            for item in filas_ed:
                rf, vt, vd, vc, vdat = item
                if vd.get().strip():
                    count += 1
                    try:
                        c = int(vc.get() or 1)
                        d = float(vdat.get() or 0)
                        if vt.get() == "producto":
                            total += c * d * PRECIO_LB
                        else:
                            total += c * d
                    except Exception:
                        pass
            # Peso
            for item in filas_peso_ed:
                count += 1
                total += item[2] * PRECIO_LB
            # Medicamentos
            for item in filas_med_ed:
                count += 1
                total += item[2] * item[3]
            # Documentos
            for item in filas_doc_ed:
                count += 1
                total += item[2] * item[3]
            # Varios
            for item in filas_varios_ed:
                count += 1
                total += item[2] * item[3]

            lbl_cant.config(text=f"{count} artículos")
            lbl_total_art.config(text=f"TOTAL  →  $ {int(total):,}")

        def _agregar_fila_peso_ed(desc, peso):
            if not peso_section.winfo_ismapped():
                peso_section.pack(fill="x", before=lbl_total_art)
            i = len(filas_peso_ed) + 1
            importe = peso * PRECIO_LB
            bg = "#ffffff" if i % 2 == 1 else "#fff3e6"
            row = tk.Frame(peso_filas_frame, bg=bg, pady=3)
            row.pack(fill="x")
            tk.Label(row, text=str(i), font=("Segoe UI",8), bg=bg, fg="#aaa", width=3,
                     anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=desc, font=("Segoe UI",9), bg=bg, fg="#1a1a1a",
                     anchor="w").pack(side="left", padx=4, expand=True, fill="x")
            tk.Label(row, text=f"{peso} lb", font=("Segoe UI",9), bg=bg, fg="#4a2000",
                     width=10, anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=f"$ {int(importe):,}", font=("Segoe UI",9,"bold"), bg=bg,
                     fg="#633806", width=10, anchor="e").pack(side="left", padx=4)
            fila = [row, desc, peso]
            filas_peso_ed.append(fila)
            def _del(r=row, f=fila):
                r.destroy()
                if f in filas_peso_ed: filas_peso_ed.remove(f)
                _renumerar_peso_ed()
                _recalcular_total_ed()
                if not filas_peso_ed: peso_section.pack_forget()
            def _edit(r=row, f=fila):
                _editar_fila_peso(f)
            tk.Button(row, text="✏️", font=("Segoe UI",8), bd=0,
                      bg="#faeeda", fg="#633806", width=3, cursor="hand2",
                      command=_edit).pack(side="left", padx=(2,2))
            tk.Button(row, text="✕", font=("Segoe UI",8,"bold"), bd=0,
                      bg="#fde8e8", fg="#c0392b", width=3, cursor="hand2",
                      command=_del).pack(side="left", padx=(2,8))
            _recalcular_total_ed()

        def _editar_fila_peso(fila):
            win_e = tk.Toplevel(win)
            win_e.title("✏️  Editar peso")
            win_e.configure(bg="#ffffff")
            win_e.resizable(False, False)
            win_e.grab_set()
            we, he = 420, 360
            xe = (win_e.winfo_screenwidth() - we) // 2
            ye = (win_e.winfo_screenheight() - he) // 2
            win_e.geometry(f"{we}x{he}+{xe}+{ye}")
            hdr_e = tk.Frame(win_e, bg="#4a2000", pady=12, padx=16)
            hdr_e.pack(fill="x")
            tk.Label(hdr_e, text="✏️  Editar envío por peso",
                     font=("Segoe UI",11,"bold"), bg="#4a2000", fg="#ffffff").pack(side="left")
            # Botones PRIMERO con side="bottom" para que siempre se vean
            btn_bar = tk.Frame(win_e, bg="#ffffff", padx=20, pady=12)
            btn_bar.pack(side="bottom", fill="x")
            def _ok():
                try:
                    nuevo_peso = float(v_peso_e.get())
                    if nuevo_peso <= 0: raise ValueError
                except ValueError:
                    messagebox.showwarning("Requerido", "Ingresa un peso válido.", parent=win_e)
                    return
                nueva_desc = v_desc_e.get().strip() or "Envío por peso"
                fila[1] = nueva_desc
                fila[2] = nuevo_peso
                children = fila[0].winfo_children()
                children[1].config(text=nueva_desc)
                children[2].config(text=f"{nuevo_peso} lb")
                children[3].config(text=f"$ {int(nuevo_peso * PRECIO_LB):,}")
                _recalcular_total_ed()
                win_e.destroy()
            tk.Button(btn_bar, text="✓  Guardar", font=("Segoe UI",10,"bold"), bd=0,
                      bg="#4a2000", fg="#ffffff", pady=8, padx=16, cursor="hand2",
                      command=_ok).pack(side="right")
            tk.Button(btn_bar, text="Cancelar", font=("Segoe UI",9), bd=0,
                      bg="#f1efe8", fg="#5f5e5a", pady=8, padx=12, cursor="hand2",
                      command=win_e.destroy).pack(side="right", padx=(0,8))
            tk.Frame(btn_bar, bg="#ffffff", height=1).pack(side="bottom", fill="x", pady=(8,0))
            # Cuerpo después de los botones
            body_e = tk.Frame(win_e, bg="#ffffff", padx=20, pady=10)
            body_e.pack(fill="both", expand=True)
            tk.Label(body_e, text="Descripción", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_desc_e = tk.StringVar(value=fila[1])
            ttk.Entry(body_e, textvariable=v_desc_e, font=("Segoe UI",10)).pack(fill="x", pady=(2,12))
            tk.Label(body_e, text="Peso (lb)", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_peso_e = tk.StringVar(value=str(fila[2]))
            ttk.Entry(body_e, textvariable=v_peso_e, width=10,
                      font=("Segoe UI",14,"bold"), justify="center").pack(anchor="w", pady=(2,12))

        def _renumerar_peso_ed():
            for i, (row, _, _) in enumerate(filas_peso_ed, 1):
                bg = "#ffffff" if i % 2 == 1 else "#fff3e6"
                row.config(bg=bg)
                children = row.winfo_children()
                if children: children[0].config(text=str(i))
                for w in children:
                    try: w.config(bg=bg)
                    except: pass

        def _agregar_fila_med_ed(nombre, cant, precio):
            if not med_section.winfo_ismapped():
                med_section.pack(fill="x", before=lbl_total_art)
            i = len(filas_med_ed) + 1
            importe = cant * precio
            bg = "#ffffff" if i % 2 == 1 else "#f8f2fd"
            row = tk.Frame(med_filas_frame, bg=bg, pady=3)
            row.pack(fill="x")
            tk.Label(row, text=str(i), font=("Segoe UI",8), bg=bg, fg="#aaa", width=3,
                     anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=nombre, font=("Segoe UI",9), bg=bg, fg="#2c1a40",
                     anchor="w").pack(side="left", padx=4, expand=True, fill="x")
            tk.Label(row, text=f"×{cant:g}", font=("Segoe UI",9,"bold"), bg=bg, fg="#6b2fa0",
                     width=5, anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=f"${int(precio)}", font=("Segoe UI",9), bg=bg, fg="#8e44c4",
                     width=8, anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=f"$ {int(importe):,}", font=("Segoe UI",9,"bold"), bg=bg,
                     fg="#6b2fa0", width=10, anchor="e").pack(side="left", padx=4)
            fila = [row, nombre, cant, precio]
            filas_med_ed.append(fila)
            def _del(r=row, f=fila):
                r.destroy()
                if f in filas_med_ed: filas_med_ed.remove(f)
                _renumerar_med_ed()
                _recalcular_total_ed()
                if not filas_med_ed: med_section.pack_forget()
            def _edit(r=row, f=fila):
                _editar_fila_med(f)
            tk.Button(row, text="✏️", font=("Segoe UI",8), bd=0,
                      bg="#f0e6f9", fg="#6b2fa0", width=3, cursor="hand2",
                      command=_edit).pack(side="left", padx=(2,2))
            tk.Button(row, text="✕", font=("Segoe UI",8,"bold"), bd=0,
                      bg="#fde8e8", fg="#c0392b", width=3, cursor="hand2",
                      command=_del).pack(side="left", padx=(2,8))
            _recalcular_total_ed()

        def _editar_fila_med(fila):
            win_e = tk.Toplevel(win)
            win_e.title("✏️  Editar medicamento")
            win_e.configure(bg="#ffffff")
            win_e.resizable(False, False)
            win_e.grab_set()
            we, he = 420, 400
            xe = (win_e.winfo_screenwidth() - we) // 2
            ye = (win_e.winfo_screenheight() - he) // 2
            win_e.geometry(f"{we}x{he}+{xe}+{ye}")
            hdr_e = tk.Frame(win_e, bg="#6b2fa0", pady=12, padx=16)
            hdr_e.pack(fill="x")
            tk.Label(hdr_e, text="✏️  Editar medicamento",
                     font=("Segoe UI",11,"bold"), bg="#6b2fa0", fg="#ffffff").pack(side="left")
            # Botones PRIMERO con side="bottom" para que siempre se vean
            btn_bar = tk.Frame(win_e, bg="#ffffff", padx=20, pady=12)
            btn_bar.pack(side="bottom", fill="x")
            def _ok():
                try:
                    nueva_cant = float(v_cant_e.get())
                    nuevo_precio = float(v_prec_e.get())
                    if nueva_cant <= 0 or nuevo_precio <= 0: raise ValueError
                except ValueError:
                    messagebox.showwarning("Requerido", "Ingresa cantidad y precio válidos.", parent=win_e)
                    return
                fila[1] = v_nom_e.get().strip() or "Medicamento"
                fila[2] = nueva_cant
                fila[3] = nuevo_precio
                children = fila[0].winfo_children()
                children[1].config(text=fila[1])
                children[2].config(text=f"×{nueva_cant:g}")
                children[3].config(text=f"${int(nuevo_precio)}")
                children[4].config(text=f"$ {int(nueva_cant * nuevo_precio):,}")
                _recalcular_total_ed()
                win_e.destroy()
            tk.Button(btn_bar, text="✓  Guardar", font=("Segoe UI",10,"bold"), bd=0,
                      bg="#6b2fa0", fg="#ffffff", pady=8, padx=16, cursor="hand2",
                      command=_ok).pack(side="right")
            tk.Button(btn_bar, text="Cancelar", font=("Segoe UI",9), bd=0,
                      bg="#f1efe8", fg="#5f5e5a", pady=8, padx=12, cursor="hand2",
                      command=win_e.destroy).pack(side="right", padx=(0,8))
            tk.Frame(btn_bar, bg="#ffffff", height=1).pack(side="bottom", fill="x", pady=(8,0))
            # Cuerpo después de los botones
            body_e = tk.Frame(win_e, bg="#ffffff", padx=20, pady=10)
            body_e.pack(fill="both", expand=True)
            tk.Label(body_e, text="Nombre", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_nom_e = tk.StringVar(value=fila[1])
            ttk.Entry(body_e, textvariable=v_nom_e, font=("Segoe UI",10)).pack(fill="x", pady=(2,12))
            tk.Label(body_e, text="Cantidad", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_cant_e = tk.StringVar(value=str(int(fila[2])))
            ttk.Entry(body_e, textvariable=v_cant_e, width=10,
                      font=("Segoe UI",14,"bold"), justify="center").pack(anchor="w", pady=(2,12))
            tk.Label(body_e, text="Precio unitario ($)", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_prec_e = tk.StringVar(value=str(int(fila[3])))
            ttk.Entry(body_e, textvariable=v_prec_e, width=10,
                      font=("Segoe UI",14,"bold"), justify="center").pack(anchor="w", pady=(2,12))

        def _renumerar_med_ed():
            for i, (row, _, _, _) in enumerate(filas_med_ed, 1):
                bg = "#ffffff" if i % 2 == 1 else "#f8f2fd"
                row.config(bg=bg)
                children = row.winfo_children()
                if children: children[0].config(text=str(i))
                for w in children:
                    try: w.config(bg=bg)
                    except: pass

        def _agregar_fila_doc_ed(nombre, cant, precio):
            if not doc_section.winfo_ismapped():
                doc_section.pack(fill="x", before=lbl_total_art)
            i = len(filas_doc_ed) + 1
            importe = cant * precio
            bg = "#ffffff" if i % 2 == 1 else "#fff3f3"
            row = tk.Frame(doc_filas_frame, bg=bg, pady=3)
            row.pack(fill="x")
            tk.Label(row, text=str(i), font=("Segoe UI",8), bg=bg, fg="#aaa", width=3,
                     anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=nombre, font=("Segoe UI",9), bg=bg, fg="#3a0a0a",
                     anchor="w").pack(side="left", padx=4, expand=True, fill="x")
            tk.Label(row, text=f"×{cant}", font=("Segoe UI",9,"bold"), bg=bg, fg="#791f1f",
                     width=5, anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=f"${int(precio)}", font=("Segoe UI",9), bg=bg, fg="#9e2a2a",
                     width=8, anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=f"$ {int(importe):,}", font=("Segoe UI",9,"bold"), bg=bg,
                     fg="#791f1f", width=10, anchor="e").pack(side="left", padx=4)
            fila = [row, nombre, cant, precio]
            filas_doc_ed.append(fila)
            def _del(r=row, f=fila):
                r.destroy()
                if f in filas_doc_ed: filas_doc_ed.remove(f)
                _renumerar_doc_ed()
                _recalcular_total_ed()
                if not filas_doc_ed: doc_section.pack_forget()
            def _edit(r=row, f=fila):
                _editar_fila_doc(f)
            tk.Button(row, text="✏️", font=("Segoe UI",8), bd=0,
                      bg="#fce8e8", fg="#791f1f", width=3, cursor="hand2",
                      command=_edit).pack(side="left", padx=(2,2))
            tk.Button(row, text="✕", font=("Segoe UI",8,"bold"), bd=0,
                      bg="#fde8e8", fg="#c0392b", width=3, cursor="hand2",
                      command=_del).pack(side="left", padx=(2,8))
            _recalcular_total_ed()

        def _editar_fila_doc(fila):
            win_e = tk.Toplevel(win)
            win_e.title("✏️  Editar documento")
            win_e.configure(bg="#ffffff")
            win_e.resizable(False, False)
            win_e.grab_set()
            we, he = 420, 400
            xe = (win_e.winfo_screenwidth() - we) // 2
            ye = (win_e.winfo_screenheight() - he) // 2
            win_e.geometry(f"{we}x{he}+{xe}+{ye}")
            hdr_e = tk.Frame(win_e, bg="#791f1f", pady=12, padx=16)
            hdr_e.pack(fill="x")
            tk.Label(hdr_e, text="✏️  Editar documento",
                     font=("Segoe UI",11,"bold"), bg="#791f1f", fg="#ffffff").pack(side="left")
            btn_bar = tk.Frame(win_e, bg="#ffffff", padx=20, pady=12)
            btn_bar.pack(side="bottom", fill="x")
            def _ok():
                try:
                    nueva_cant = int(v_cant_e.get())
                    nuevo_precio = float(v_prec_e.get())
                    if nueva_cant <= 0 or nuevo_precio <= 0: raise ValueError
                except ValueError:
                    messagebox.showwarning("Requerido", "Ingresa cantidad y precio válidos.", parent=win_e)
                    return
                fila[1] = v_nom_e.get().strip() or "Documento"
                fila[2] = nueva_cant
                fila[3] = nuevo_precio
                children = fila[0].winfo_children()
                children[1].config(text=fila[1])
                children[2].config(text=f"×{nueva_cant}")
                children[3].config(text=f"${int(nuevo_precio)}")
                children[4].config(text=f"$ {int(nueva_cant * nuevo_precio):,}")
                _recalcular_total_ed()
                win_e.destroy()
            tk.Button(btn_bar, text="✓  Guardar", font=("Segoe UI",10,"bold"), bd=0,
                      bg="#791f1f", fg="#ffffff", pady=8, padx=16, cursor="hand2",
                      command=_ok).pack(side="right")
            tk.Button(btn_bar, text="Cancelar", font=("Segoe UI",9), bd=0,
                      bg="#f1efe8", fg="#5f5e5a", pady=8, padx=12, cursor="hand2",
                      command=win_e.destroy).pack(side="right", padx=(0,8))
            tk.Frame(btn_bar, bg="#ffffff", height=1).pack(side="bottom", fill="x", pady=(8,0))
            body_e = tk.Frame(win_e, bg="#ffffff", padx=20, pady=10)
            body_e.pack(fill="both", expand=True)
            tk.Label(body_e, text="Nombre", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_nom_e = tk.StringVar(value=fila[1])
            ttk.Entry(body_e, textvariable=v_nom_e, font=("Segoe UI",10)).pack(fill="x", pady=(2,12))
            tk.Label(body_e, text="Cantidad", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_cant_e = tk.StringVar(value=str(int(fila[2])))
            ttk.Entry(body_e, textvariable=v_cant_e, width=10,
                      font=("Segoe UI",14,"bold"), justify="center").pack(anchor="w", pady=(2,12))
            tk.Label(body_e, text="Precio unitario ($)", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_prec_e = tk.StringVar(value=str(int(fila[3])))
            ttk.Entry(body_e, textvariable=v_prec_e, width=10,
                      font=("Segoe UI",14,"bold"), justify="center").pack(anchor="w", pady=(2,12))

        def _renumerar_doc_ed():
            for i, (row, _, _, _) in enumerate(filas_doc_ed, 1):
                bg = "#ffffff" if i % 2 == 1 else "#fff3f3"
                row.config(bg=bg)
                children = row.winfo_children()
                if children: children[0].config(text=str(i))
                for w in children:
                    try: w.config(bg=bg)
                    except: pass

        def _agregar_fila_vario_ed(nombre, cant, precio):
            if not varios_section.winfo_ismapped():
                varios_section.pack(fill="x", before=lbl_total_art)
            i = len(filas_varios_ed) + 1
            importe = cant * precio
            bg = "#ffffff" if i % 2 == 1 else "#f0f5fb"
            row = tk.Frame(varios_filas_frame, bg=bg, pady=3)
            row.pack(fill="x")
            tk.Label(row, text=str(i), font=("Segoe UI",8), bg=bg, fg="#aaa", width=3,
                     anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=nombre, font=("Segoe UI",9), bg=bg, fg="#1a2a40",
                     anchor="w").pack(side="left", padx=4, expand=True, fill="x")
            tk.Label(row, text=f"×{cant}", font=("Segoe UI",9,"bold"), bg=bg, fg="#1a3f6b",
                     width=5, anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=f"${int(precio)}", font=("Segoe UI",9), bg=bg, fg="#2a5a8a",
                     width=8, anchor="center").pack(side="left", padx=4)
            tk.Label(row, text=f"$ {int(importe):,}", font=("Segoe UI",9,"bold"), bg=bg,
                     fg="#1a3f6b", width=10, anchor="e").pack(side="left", padx=4)
            fila = [row, nombre, cant, precio]
            filas_varios_ed.append(fila)
            def _del(r=row, f=fila):
                r.destroy()
                if f in filas_varios_ed: filas_varios_ed.remove(f)
                _renumerar_vario_ed()
                _recalcular_total_ed()
                if not filas_varios_ed: varios_section.pack_forget()
            def _edit(r=row, f=fila):
                _editar_fila_vario(f)
            tk.Button(row, text="✏️", font=("Segoe UI",8), bd=0,
                      bg="#e8f0fb", fg="#1a3f6b", width=3, cursor="hand2",
                      command=_edit).pack(side="left", padx=(2,2))
            tk.Button(row, text="✕", font=("Segoe UI",8,"bold"), bd=0,
                      bg="#fde8e8", fg="#c0392b", width=3, cursor="hand2",
                      command=_del).pack(side="left", padx=(2,8))
            _recalcular_total_ed()

        def _editar_fila_vario(fila):
            win_e = tk.Toplevel(win)
            win_e.title("✏️  Editar artículo")
            win_e.configure(bg="#ffffff")
            win_e.resizable(False, False)
            win_e.grab_set()
            we, he = 420, 400
            xe = (win_e.winfo_screenwidth() - we) // 2
            ye = (win_e.winfo_screenheight() - he) // 2
            win_e.geometry(f"{we}x{he}+{xe}+{ye}")
            hdr_e = tk.Frame(win_e, bg="#1a3f6b", pady=12, padx=16)
            hdr_e.pack(fill="x")
            tk.Label(hdr_e, text="✏️  Editar artículo varios",
                     font=("Segoe UI",11,"bold"), bg="#1a3f6b", fg="#ffffff").pack(side="left")
            # Botones PRIMERO con side="bottom" para que siempre se vean
            btn_bar = tk.Frame(win_e, bg="#ffffff", padx=20, pady=12)
            btn_bar.pack(side="bottom", fill="x")
            def _ok():
                try:
                    nueva_cant = int(v_cant_e.get())
                    nuevo_precio = float(v_prec_e.get())
                    if nueva_cant <= 0 or nuevo_precio <= 0: raise ValueError
                except ValueError:
                    messagebox.showwarning("Requerido", "Ingresa cantidad y precio válidos.", parent=win_e)
                    return
                fila[1] = v_nom_e.get().strip() or "Artículo"
                fila[2] = nueva_cant
                fila[3] = nuevo_precio
                children = fila[0].winfo_children()
                children[1].config(text=fila[1])
                children[2].config(text=f"×{nueva_cant}")
                children[3].config(text=f"${int(nuevo_precio)}")
                children[4].config(text=f"$ {int(nueva_cant * nuevo_precio):,}")
                _recalcular_total_ed()
                win_e.destroy()
            tk.Button(btn_bar, text="✓  Guardar", font=("Segoe UI",10,"bold"), bd=0,
                      bg="#1a3f6b", fg="#ffffff", pady=8, padx=16, cursor="hand2",
                      command=_ok).pack(side="right")
            tk.Button(btn_bar, text="Cancelar", font=("Segoe UI",9), bd=0,
                      bg="#f1efe8", fg="#5f5e5a", pady=8, padx=12, cursor="hand2",
                      command=win_e.destroy).pack(side="right", padx=(0,8))
            tk.Frame(btn_bar, bg="#ffffff", height=1).pack(side="bottom", fill="x", pady=(8,0))
            # Cuerpo después de los botones
            body_e = tk.Frame(win_e, bg="#ffffff", padx=20, pady=10)
            body_e.pack(fill="both", expand=True)
            tk.Label(body_e, text="Nombre del artículo", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_nom_e = tk.StringVar(value=fila[1])
            ttk.Entry(body_e, textvariable=v_nom_e, font=("Segoe UI",10)).pack(fill="x", pady=(2,12))
            tk.Label(body_e, text="Cantidad", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_cant_e = tk.StringVar(value=str(int(fila[2])))
            ttk.Entry(body_e, textvariable=v_cant_e, width=10,
                      font=("Segoe UI",14,"bold"), justify="center").pack(anchor="w", pady=(2,12))
            tk.Label(body_e, text="Precio unitario ($)", font=("Segoe UI",9),
                     bg="#ffffff", fg="#888780").pack(anchor="w")
            v_prec_e = tk.StringVar(value=str(int(fila[3])))
            ttk.Entry(body_e, textvariable=v_prec_e, width=10,
                      font=("Segoe UI",14,"bold"), justify="center").pack(anchor="w", pady=(2,12))

        def _renumerar_vario_ed():
            for i, (row, _, _, _) in enumerate(filas_varios_ed, 1):
                bg = "#ffffff" if i % 2 == 1 else "#f0f5fb"
                row.config(bg=bg)
                children = row.winfo_children()
                if children: children[0].config(text=str(i))
                for w in children:
                    try: w.config(bg=bg)
                    except: pass

        # ── Popups de artículos ───────────────────────────────────
        def _abrir_peso_ed():
            win_p = tk.Toplevel(win)
            win_p.title("⚖️  Envío por peso")
            win_p.configure(bg="#ffffff")
            win_p.resizable(False, False)
            win_p.grab_set()
            wp, hp = 560, 480
            xp = (win_p.winfo_screenwidth() - wp) // 2
            yp = (win_p.winfo_screenheight() - hp) // 2
            win_p.geometry(f"{wp}x{hp}+{xp}+{yp}")
            hdr_p = tk.Frame(win_p, bg="#4a2000", pady=20, padx=28)
            hdr_p.pack(fill="x")
            tk.Label(hdr_p, text="⚖️", font=("Segoe UI",22),
                     bg="#4a2000", fg="#f5c97a").pack(side="left")
            ht = tk.Frame(hdr_p, bg="#4a2000")
            ht.pack(side="left", padx=(12,0))
            tk.Label(ht, text="Envío por peso total",
                     font=("Segoe UI",15,"bold"),
                     bg="#4a2000", fg="#ffffff").pack(anchor="w")
            tk.Label(ht, text="Ingresa la descripción y el peso del paquete",
                     font=("Segoe UI",9),
                     bg="#4a2000", fg="#c8a97a").pack(anchor="w")
            body_p = tk.Frame(win_p, bg="#ffffff", padx=28, pady=22)
            body_p.pack(fill="both", expand=True)
            tk.Label(body_p, text="DESCRIPCIÓN DEL ENVÍO",
                     font=("Segoe UI",8,"bold"), bg="#ffffff", fg="#aaa9a5").pack(anchor="w")
            desc_txt = tk.Text(body_p, height=4, font=("Segoe UI",11),
                               relief="flat", bd=0, highlightthickness=2,
                               highlightbackground="#e0ddd5", highlightcolor="#633806",
                               padx=12, pady=10, fg="#1a1a1a", bg="#fafaf8")
            desc_txt.pack(fill="x", pady=(6,18))
            mid = tk.Frame(body_p, bg="#ffffff")
            mid.pack(fill="x", pady=(0,18))
            mid.columnconfigure(0, weight=1)
            mid.columnconfigure(1, weight=1)
            peso_col = tk.Frame(mid, bg="#ffffff")
            peso_col.grid(row=0, column=0, sticky="ew", padx=(0,12))
            tk.Label(peso_col, text="PESO TOTAL",
                     font=("Segoe UI",8,"bold"), bg="#ffffff", fg="#aaa9a5").pack(anchor="w")
            peso_inner = tk.Frame(peso_col, bg="#fafaf8",
                                  highlightthickness=2, highlightbackground="#e0ddd5")
            peso_inner.pack(fill="x", pady=(6,0))
            v_peso_p = tk.StringVar(value="")
            e_peso_p = tk.Entry(peso_inner, textvariable=v_peso_p, width=8,
                                font=("Segoe UI",22,"bold"), justify="center",
                                relief="flat", bd=0, bg="#fafaf8", fg="#4a2000")
            e_peso_p.pack(side="left", padx=12, pady=10)
            tk.Label(peso_inner, text="lb", font=("Segoe UI",13,"bold"),
                     bg="#fafaf8", fg="#888780").pack(side="left")
            costo_col = tk.Frame(mid, bg="#4a2000", padx=16, pady=14)
            costo_col.grid(row=0, column=1, sticky="ew")
            tk.Label(costo_col, text="COSTO ESTIMADO",
                     font=("Segoe UI",8,"bold"), bg="#4a2000", fg="#c8a97a").pack(anchor="w")
            lbl_costo_grande = tk.Label(costo_col, text="$ 0.00",
                                        font=("Segoe UI",24,"bold"),
                                        bg="#4a2000", fg="#ffffff")
            lbl_costo_grande.pack(anchor="w", pady=(4,0))
            lbl_det = tk.Label(costo_col, text=f"0.00 lb × ${PRECIO_LB} / lb",
                               font=("Segoe UI",9), bg="#4a2000", fg="#c8a97a")
            lbl_det.pack(anchor="w")
            def _upd_costo(*a):
                try:
                    lb = float(v_peso_p.get())
                    costo = lb * PRECIO_LB
                    lbl_costo_grande.config(text=f"$ {int(costo):,}")
                    lbl_det.config(text=f"{lb} lb × ${PRECIO_LB} / lb")
                except ValueError:
                    lbl_costo_grande.config(text="$ 0")
                    lbl_det.config(text=f"0 lb × ${PRECIO_LB} / lb")
            v_peso_p.trace_add("write", _upd_costo)
            e_peso_p.focus_set()
            tk.Frame(body_p, bg="#eeede8", height=1).pack(fill="x", pady=(0,18))
            btn_bar_p = tk.Frame(body_p, bg="#ffffff")
            btn_bar_p.pack(fill="x")
            def _ok_p():
                desc_p = desc_txt.get("1.0","end").strip() or "Envío por peso"
                try:
                    peso_p = float(v_peso_p.get())
                    if peso_p <= 0: raise ValueError
                except ValueError:
                    messagebox.showwarning("Requerido", "Ingresa un peso válido.", parent=win_p)
                    return
                _agregar_fila_peso_ed(desc_p, peso_p)
                win_p.destroy()
            tk.Button(btn_bar_p, text="✓  Agregar al envío",
                      font=("Segoe UI",10,"bold"), bd=0,
                      bg="#633806", fg="#ffffff",
                      pady=8, padx=20, cursor="hand2",
                      command=_ok_p).pack(side="right")
            tk.Button(btn_bar_p, text="Cancelar", font=("Segoe UI",9), bd=0,
                      bg="#f1efe8", fg="#5f5e5a",
                      pady=8, padx=14, cursor="hand2",
                      command=win_p.destroy).pack(side="left")

        def _abrir_medicamentos_ed():
            win_m = tk.Toplevel(win)
            win_m.title("💊  Medicamentos")
            win_m.configure(bg="#ffffff")
            win_m.resizable(False, False)
            win_m.grab_set()
            wm, hm = 580, 600
            xm = (win_m.winfo_screenwidth() - wm) // 2
            ym = (win_m.winfo_screenheight() - hm) // 2
            win_m.geometry(f"{wm}x{hm}+{xm}+{ym}")
            hdr_m = tk.Frame(win_m, bg="#6b2fa0", pady=20, padx=28)
            hdr_m.pack(fill="x")
            tk.Label(hdr_m, text="💊", font=("Segoe UI",22),
                     bg="#6b2fa0", fg="#e8d5f5").pack(side="left")
            ht = tk.Frame(hdr_m, bg="#6b2fa0")
            ht.pack(side="left", padx=(12,0))
            tk.Label(ht, text="Medicamentos",
                     font=("Segoe UI",15,"bold"),
                     bg="#6b2fa0", fg="#ffffff").pack(anchor="w")
            tk.Label(ht, text="Ingresa la cantidad de cada medicamento",
                     font=("Segoe UI",9),
                     bg="#6b2fa0", fg="#d4b0f0").pack(anchor="w")
            body_m = tk.Frame(win_m, bg="#ffffff", padx=28, pady=16)
            body_m.pack(fill="both", expand=True)
            hdr_tbl = tk.Frame(body_m, bg="#8e44c4", padx=10, pady=7)
            hdr_tbl.pack(fill="x")
            for col, txt, ancho in [(0,"Medicamento",0),(1,"Precio unit.",10),(2,"Cantidad",9),(3,"Importe",10)]:
                kw = {} if ancho == 0 else {"width":ancho}
                tk.Label(hdr_tbl, text=txt, font=("Segoe UI",8,"bold"),
                         bg="#8e44c4", fg="#e8d5f5", anchor="w", **kw).grid(
                    row=0, column=col, padx=6, sticky="ew")
            items_med = list(PRECIOS_MED.items())
            filas_med_popup = []
            lbl_total_med = tk.Label(body_m, text="$ 0",
                                     font=("Segoe UI",18,"bold"),
                                     bg="#6b2fa0", fg="#ffffff")
            def _recalc_med(*_):
                total = 0.0
                for _, precio, v_c, _ in filas_med_popup:
                    try: total += float(v_c.get() or 0) * precio
                    except: pass
                for v_n, v_p, v_c in otros_filas_popup:
                    try:
                        p = float(v_p.get() or 0)
                        c = float(v_c.get() or 0)
                        total += p * c
                    except: pass
                lbl_total_med.config(text=f"$ {int(total):,}")
            tbl_m = tk.Frame(body_m, bg="#fafaf8")
            tbl_m.pack(fill="x", pady=(0,12))
            for i, (nombre, precio) in enumerate(items_med):
                bg = "#ffffff" if i % 2 == 0 else "#f8f2fd"
                row = tk.Frame(tbl_m, bg=bg, highlightthickness=1, highlightbackground="#e8daf5")
                row.pack(fill="x", pady=(0,1))
                row.columnconfigure(0, weight=1)
                tk.Label(row, text=nombre, font=("Segoe UI",10),
                         bg=bg, fg="#2c1a40", anchor="w").grid(
                    row=0, column=0, padx=(10,4), pady=8, sticky="ew")
                tk.Label(row, text=f"${precio:.0f}", font=("Segoe UI",9,"bold"),
                         bg=bg, fg="#8e44c4", width=8, anchor="center").grid(
                    row=0, column=1, padx=4, pady=8)
                v_c = tk.StringVar(value="0")
                tk.Entry(row, textvariable=v_c, width=7,
                         font=("Segoe UI",11,"bold"),
                         justify="center", relief="flat",
                         bg="#f0e6f9", fg="#6b2fa0",
                         highlightthickness=1, highlightbackground="#c49de0").grid(
                    row=0, column=2, padx=8, pady=6)
                lbl_imp = tk.Label(row, text="$ 0", font=("Segoe UI",10,"bold"),
                                   bg=bg, fg="#aaa9a5", width=9, anchor="e")
                lbl_imp.grid(row=0, column=3, padx=(4,10), pady=8)
                v_c.trace_add("write", _recalc_med)
                filas_med_popup.append((nombre, precio, v_c, lbl_imp))
            # Contenedor de "Otros" manuales
            otros_container = tk.Frame(tbl_m, bg="#ffffff")
            otros_container.pack(fill="x", pady=(6,1))
            otros_filas_popup = []

            def _agregar_otro_fila_ed():
                otro_bg = "#f0f8f0"
                otro_row = tk.Frame(otros_container, bg=otro_bg, highlightthickness=2, highlightbackground="#80c080")
                otro_row.pack(fill="x", pady=(0,4))
                otro_row.columnconfigure(0, weight=1)
                otro_izq = tk.Frame(otro_row, bg=otro_bg)
                otro_izq.grid(row=0, column=0, padx=(10,4), pady=8, sticky="ew")
                tk.Label(otro_izq, text="✏️  Otro (manual)", font=("Segoe UI",10,"bold"),
                         bg=otro_bg, fg="#1a5c1a").pack(anchor="w")
                v_n = tk.StringVar()
                ttk.Entry(otro_izq, textvariable=v_n, font=("Segoe UI",9)).pack(fill="x", pady=(3,0))
                otro_pf = tk.Frame(otro_row, bg=otro_bg)
                otro_pf.grid(row=0, column=1, padx=4, pady=8)
                tk.Label(otro_pf, text="$", font=("Segoe UI",9,"bold"),
                         bg=otro_bg, fg="#1a5c1a").pack(side="left")
                v_p = tk.StringVar(value="")
                ttk.Entry(otro_pf, textvariable=v_p, width=6,
                          font=("Segoe UI",9), justify="center").pack(side="left")
                v_c = tk.StringVar(value="0")
                tk.Entry(otro_row, textvariable=v_c, width=7,
                         font=("Segoe UI",11,"bold"),
                         justify="center", relief="flat",
                         bg="#e8f5e8", fg="#1a5c1a",
                         highlightthickness=1, highlightbackground="#80c080").grid(
                    row=0, column=2, padx=8, pady=6)
                lbl_imp = tk.Label(otro_row, text="$ 0", font=("Segoe UI",10,"bold"),
                                   bg=otro_bg, fg="#aaa9a5", width=9, anchor="e")
                lbl_imp.grid(row=0, column=3, padx=(4,10), pady=8)
                def _recalc_otro_fila(*_):
                    try:
                        p = float(v_p.get() or 0)
                        c = float(v_c.get() or 0)
                        imp = p * c
                    except: imp = 0.0
                    lbl_imp.config(text=f"$ {int(imp):,}" if imp > 0 else "$ 0",
                                   fg="#1a5c1a" if imp > 0 else "#aaa9a5")
                    _recalc_med()
                v_p.trace_add("write", _recalc_otro_fila)
                v_c.trace_add("write", _recalc_otro_fila)
                otros_filas_popup.append((v_n, v_p, v_c))

            _agregar_otro_fila_ed()
            btn_agregar_otro = tk.Button(otros_container, text="+ Agregar otro",
                                         font=("Segoe UI",9,"bold"), bd=0,
                                         bg="#e8f5e8", fg="#1a5c1a",
                                         pady=5, padx=12, cursor="hand2",
                                         command=_agregar_otro_fila_ed)
            btn_agregar_otro.pack(pady=(4,0))

            tot_frame = tk.Frame(body_m, bg="#6b2fa0", padx=16, pady=12)
            tot_frame.pack(fill="x", pady=(0,16))
            tk.Label(tot_frame, text="TOTAL MEDICAMENTOS  →",
                     font=("Segoe UI",9), bg="#6b2fa0", fg="#d4b0f0").pack(side="right")
            lbl_total_med.pack(side="right", padx=(0,14))
            tk.Frame(body_m, bg="#eeede8", height=1).pack(fill="x", pady=(0,14))
            btn_bar_m = tk.Frame(body_m, bg="#ffffff")
            btn_bar_m.pack(fill="x")
            def _ok_m():
                for nombre, precio, v_c, _ in filas_med_popup:
                    try: cant = float(v_c.get() or 0)
                    except: cant = 0
                    if cant > 0: _agregar_fila_med_ed(nombre, cant, precio)
                for v_n, v_p, v_c in otros_filas_popup:
                    try:
                        oc = float(v_c.get() or 0)
                        op = float(v_p.get() or 0)
                    except: oc = 0; op = 0
                    if oc > 0 and op > 0:
                        _agregar_fila_med_ed(v_n.get().strip() or "Medicamento (otro)", oc, op)
                win_m.destroy()
                _recalcular_total_ed()
            tk.Button(btn_bar_m, text="✓  Agregar al envío",
                      font=("Segoe UI",10,"bold"), bd=0,
                      bg="#6b2fa0", fg="#ffffff",
                      pady=8, padx=20, cursor="hand2",
                      command=_ok_m).pack(side="right")
            tk.Button(btn_bar_m, text="Cancelar", font=("Segoe UI",9), bd=0,
                      bg="#f1efe8", fg="#5f5e5a",
                      pady=8, padx=14, cursor="hand2",
                      command=win_m.destroy).pack(side="left")

        def _abrir_documentos_ed():
            win_d = tk.Toplevel(win)
            win_d.title("📄  Documentos")
            win_d.configure(bg="#ffffff")
            win_d.resizable(False, False)
            win_d.grab_set()
            wd, hd = 580, 580
            xd = (win_d.winfo_screenwidth() - wd) // 2
            yd = (win_d.winfo_screenheight() - hd) // 2
            win_d.geometry(f"{wd}x{hd}+{xd}+{yd}")
            hdr_d = tk.Frame(win_d, bg="#791f1f", pady=20, padx=28)
            hdr_d.pack(fill="x", side="top")
            tk.Label(hdr_d, text="📄", font=("Segoe UI",22),
                     bg="#791f1f", fg="#fce8e8").pack(side="left")
            ht = tk.Frame(hdr_d, bg="#791f1f")
            ht.pack(side="left", padx=(12,0))
            tk.Label(ht, text="Documentos",
                     font=("Segoe UI",15,"bold"),
                     bg="#791f1f", fg="#ffffff").pack(anchor="w")
            tk.Label(ht, text="Ingresa la cantidad de cada documento",
                     font=("Segoe UI",9),
                     bg="#791f1f", fg="#f5c0c0").pack(anchor="w")
            pie_d = tk.Frame(win_d, bg="#ffffff", padx=28, pady=10)
            pie_d.pack(fill="x", side="bottom")
            filas_doc_popup = []
            lbl_total_doc = tk.Label(pie_d, text="$ 0.00",
                                     font=("Segoe UI",18,"bold"),
                                     bg="#791f1f", fg="#ffffff")
            def _recalc_doc(*_):
                total = 0.0
                for _, vp, vc, lbl, _ in filas_doc_popup:
                    try:
                        p = float(vp.get() or 0)
                        c = int(vc.get() or 0)
                        total += c * p
                    except: pass
                    lbl.config(text=f"$ {total:,.2f}" if total > 0 else "$ 0.00",
                               fg="#791f1f" if total > 0 else "#aaa9a5")
                lbl_total_doc.config(text=f"$ {total:,.2f}")
            tot_frame = tk.Frame(pie_d, bg="#791f1f", padx=16, pady=12)
            tot_frame.pack(fill="x", pady=(0,8))
            tk.Label(tot_frame, text="TOTAL DOCUMENTOS  →",
                     font=("Segoe UI",9), bg="#791f1f", fg="#f5c0c0").pack(side="right")
            lbl_total_doc.pack(side="right", padx=(0,14))
            tk.Frame(pie_d, bg="#eeede8", height=1).pack(fill="x", pady=(0,10))
            btn_bar_d = tk.Frame(pie_d, bg="#ffffff")
            btn_bar_d.pack(fill="x")
            def _ok_d():
                for nombre, vp, vc, _, pf in filas_doc_popup:
                    try: c = int(vc.get() or 0)
                    except: c = 0
                    if c <= 0: continue
                    try: p = float(vp.get() or 0)
                    except: p = 0
                    if p <= 0:
                        messagebox.showwarning("Precio requerido",
                            f"Ingresa el precio para «{nombre}».", parent=win_d)
                        return
                    _agregar_fila_doc_ed(nombre, c, p)
                win_d.destroy()
                _recalcular_total_ed()
            tk.Button(btn_bar_d, text="✓  Agregar al envío",
                      font=("Segoe UI",10,"bold"), bd=0,
                      bg="#791f1f", fg="#ffffff",
                      pady=8, padx=20, cursor="hand2",
                      command=_ok_d).pack(side="right")
            tk.Button(btn_bar_d, text="Cancelar", font=("Segoe UI",9), bd=0,
                      bg="#f1efe8", fg="#5f5e5a",
                      pady=8, padx=14, cursor="hand2",
                      command=win_d.destroy).pack(side="left")
            body_d = tk.Frame(win_d, bg="#ffffff", padx=28, pady=16)
            body_d.pack(fill="both", expand=True, side="top")
            hdr_tbl = tk.Frame(body_d, bg="#9e2a2a", padx=10, pady=7)
            hdr_tbl.pack(fill="x")
            for col, txt, ancho in [(0,"Documento",0),(1,"Precio unit.",10),(2,"Cantidad",9),(3,"Importe",10)]:
                kw = {} if ancho == 0 else {"width":ancho}
                tk.Label(hdr_tbl, text=txt, font=("Segoe UI",8,"bold"),
                         bg="#9e2a2a", fg="#fce8e8", anchor="w", **kw).grid(
                    row=0, column=col, padx=6, sticky="ew")
            items_doc = [("Pasaporte",70.0),("Partida de nacimiento",30.0),("Cédula",30.0),
                         ("Licencia",30.0),("Carta",None),("Sobre",None),("Visa",None),
                         ("Documentos legales",None),("Fotografías",None),("Cheque",None),
                         ("Tarjeta",None),("Contrato",None),("Diploma / Título",None)]
            scroll_c = tk.Frame(body_d, bg="#fafaf8")
            scroll_c.pack(fill="both", expand=True, pady=(0,12))
            cvs_d = tk.Canvas(scroll_c, bg="#fafaf8", highlightthickness=0, height=280)
            vsb_d = ttk.Scrollbar(scroll_c, orient="vertical", command=cvs_d.yview)
            cvs_d.configure(yscrollcommand=vsb_d.set)
            vsb_d.pack(side="right", fill="y")
            cvs_d.pack(side="left", fill="both", expand=True)
            tbl_d = tk.Frame(cvs_d, bg="#fafaf8")
            tw_id = cvs_d.create_window((0,0), window=tbl_d, anchor="nw")
            tbl_d.columnconfigure(0, weight=1)
            def _on_tbl_cfg(e): cvs_d.configure(scrollregion=cvs_d.bbox("all"))
            def _on_cvs_rsz(e): cvs_d.itemconfig(tw_id, width=e.width)
            tbl_d.bind("<Configure>", _on_tbl_cfg)
            cvs_d.bind("<Configure>", _on_cvs_rsz)
            def _on_mw(e): cvs_d.yview_scroll(int(-1*(e.delta/120)), "units")
            cvs_d.bind("<MouseWheel>", _on_mw)
            tbl_d.bind("<MouseWheel>", _on_mw)
            for i, (nombre, pf) in enumerate(items_doc):
                bg = "#ffffff" if i % 2 == 0 else "#fff3f3"
                row = tk.Frame(tbl_d, bg=bg, highlightthickness=1, highlightbackground="#f5d5d5")
                row.pack(fill="x", pady=(0,1))
                row.columnconfigure(0, weight=1)
                tk.Label(row, text=nombre, font=("Segoe UI",10),
                         bg=bg, fg="#3a0a0a", anchor="w").grid(
                    row=0, column=0, padx=(10,4), pady=7, sticky="ew")
                vp = tk.StringVar(value=str(int(pf)) if pf else "")
                if pf is not None:
                    tk.Label(row, text=f"${pf:.0f}", font=("Segoe UI",9,"bold"),
                             bg=bg, fg="#9e2a2a", width=8, anchor="center").grid(
                        row=0, column=1, padx=4, pady=7)
                else:
                    pe = tk.Entry(row, textvariable=vp, width=7,
                                  font=("Segoe UI",9), justify="center",
                                  relief="flat", highlightthickness=1,
                                  highlightbackground="#e8a0a0", bg="#fff8f8", fg="#791f1f")
                    pe.grid(row=0, column=1, padx=4, pady=5)
                    vp.trace_add("write", _recalc_doc)
                vc = tk.StringVar(value="0")
                sp = tk.Spinbox(row, textvariable=vc, from_=0, to=999,
                                width=6, font=("Segoe UI",11,"bold"),
                                justify="center", relief="flat",
                                bg="#fce8e8", fg="#791f1f",
                                buttonbackground="#f5c0c0",
                                highlightthickness=1, highlightbackground="#e8a0a0")
                sp.grid(row=0, column=2, padx=8, pady=5)
                lbl_imp = tk.Label(row, text="$ 0.00", font=("Segoe UI",10,"bold"),
                                   bg=bg, fg="#aaa9a5", width=9, anchor="e")
                lbl_imp.grid(row=0, column=3, padx=(4,10), pady=7)
                vc.trace_add("write", _recalc_doc)
                filas_doc_popup.append((nombre, vp, vc, lbl_imp, pf))
                row.bind("<MouseWheel>", _on_mw)

        def _abrir_varios_ed():
            win_v = tk.Toplevel(win)
            win_v.title("📦  Artículos Varios")
            win_v.configure(bg="#ffffff")
            win_v.resizable(False, False)
            win_v.grab_set()
            wv, hv = 600, 520
            xv = (win_v.winfo_screenwidth() - wv) // 2
            yv = (win_v.winfo_screenheight() - hv) // 2
            win_v.geometry(f"{wv}x{hv}+{xv}+{yv}")
            hdr_v = tk.Frame(win_v, bg="#1a3f6b", pady=20, padx=28)
            hdr_v.pack(fill="x", side="top")
            tk.Label(hdr_v, text="📦", font=("Segoe UI",22),
                     bg="#1a3f6b", fg="#d4e4f5").pack(side="left")
            ht = tk.Frame(hdr_v, bg="#1a3f6b")
            ht.pack(side="left", padx=(12,0))
            tk.Label(ht, text="Artículos Varios",
                     font=("Segoe UI",15,"bold"),
                     bg="#1a3f6b", fg="#ffffff").pack(anchor="w")
            tk.Label(ht, text="Artículos pequeños — indica el nombre y su valor en $",
                     font=("Segoe UI",9),
                     bg="#1a3f6b", fg="#a0c0e0").pack(anchor="w")
            pie_v = tk.Frame(win_v, bg="#ffffff", padx=28, pady=10)
            pie_v.pack(fill="x", side="bottom")
            filas_varios_popup = []
            lbl_total_varios = tk.Label(pie_v, text="$ 0.00",
                                        font=("Segoe UI",18,"bold"),
                                        bg="#1a3f6b", fg="#ffffff")
            def _recalc_varios(*_):
                total = 0.0
                for _, vp, vc, lbl in filas_varios_popup:
                    try:
                        p = float(vp.get() or 0)
                        c = int(vc.get() or 0)
                        total += c * p
                    except: pass
                    lbl.config(text=f"$ {total:,.2f}" if total > 0 else "$ 0.00",
                               fg="#1a3f6b" if total > 0 else "#aaa9a5")
                lbl_total_varios.config(text=f"$ {total:,.2f}")
            tot_frame = tk.Frame(pie_v, bg="#1a3f6b", padx=16, pady=12)
            tot_frame.pack(fill="x", pady=(0,8))
            tk.Label(tot_frame, text="TOTAL VARIOS  →",
                     font=("Segoe UI",9), bg="#1a3f6b", fg="#a0c0e0").pack(side="right")
            lbl_total_varios.pack(side="right", padx=(0,14))
            tk.Frame(pie_v, bg="#eeede8", height=1).pack(fill="x", pady=(0,10))
            btn_bar_v = tk.Frame(pie_v, bg="#ffffff")
            btn_bar_v.pack(fill="x")
            def _ok_v():
                for vn, vp, vc, _ in filas_varios_popup:
                    try: c = int(vc.get() or 0)
                    except: c = 0
                    if c <= 0: continue
                    try: p = float(vp.get() or 0)
                    except: p = 0
                    if p <= 0:
                        messagebox.showwarning("Precio requerido",
                            f"Ingresa el precio para «{vn.get()}».", parent=win_v)
                        return
                    _agregar_fila_vario_ed(vn.get().strip() or "Artículo", c, p)
                win_v.destroy()
                _recalcular_total_ed()
            tk.Button(btn_bar_v, text="✓  Agregar al envío",
                      font=("Segoe UI",10,"bold"), bd=0,
                      bg="#1a3f6b", fg="#ffffff",
                      pady=8, padx=20, cursor="hand2",
                      command=_ok_v).pack(side="right")
            tk.Button(btn_bar_v, text="Cancelar", font=("Segoe UI",9), bd=0,
                      bg="#f1efe8", fg="#5f5e5a",
                      pady=8, padx=14, cursor="hand2",
                      command=win_v.destroy).pack(side="left")
            body_v = tk.Frame(win_v, bg="#ffffff", padx=28, pady=16)
            body_v.pack(fill="both", expand=True, side="top")
            hdr_tbl = tk.Frame(body_v, bg="#2a5a8a", padx=10, pady=7)
            hdr_tbl.pack(fill="x")
            for col, txt, ancho in [(0,"Artículo",0),(1,"Precio unit.",10),(2,"Cantidad",9),(3,"Importe",10)]:
                kw = {} if ancho == 0 else {"width":ancho}
                tk.Label(hdr_tbl, text=txt, font=("Segoe UI",8,"bold"),
                         bg="#2a5a8a", fg="#d4e4f5", anchor="w", **kw).grid(
                    row=0, column=col, padx=6, sticky="ew")
            scroll_c = tk.Frame(body_v, bg="#f0f5fb")
            scroll_c.pack(fill="both", expand=True, pady=(0,12))
            cvs_v = tk.Canvas(scroll_c, bg="#f0f5fb", highlightthickness=0, height=280)
            vsb_v2 = ttk.Scrollbar(scroll_c, orient="vertical", command=cvs_v.yview)
            cvs_v.configure(yscrollcommand=vsb_v2.set)
            vsb_v2.pack(side="right", fill="y")
            cvs_v.pack(side="left", fill="both", expand=True)
            tbl_v = tk.Frame(cvs_v, bg="#f0f5fb")
            tw_id = cvs_v.create_window((0,0), window=tbl_v, anchor="nw")
            tbl_v.columnconfigure(0, weight=1)
            def _on_tbl_cfg(e): cvs_v.configure(scrollregion=cvs_v.bbox("all"))
            def _on_cvs_rsz(e): cvs_v.itemconfig(tw_id, width=e.width)
            tbl_v.bind("<Configure>", _on_tbl_cfg)
            cvs_v.bind("<Configure>", _on_cvs_rsz)
            def _on_mw(e): cvs_v.yview_scroll(int(-1*(e.delta/120)), "units")
            cvs_v.bind("<MouseWheel>", _on_mw)
            tbl_v.bind("<MouseWheel>", _on_mw)
            for i in range(1, 6):
                bg = "#ffffff" if i % 2 == 0 else "#f0f5fb"
                row = tk.Frame(tbl_v, bg=bg, highlightthickness=1, highlightbackground="#d0dff0")
                row.pack(fill="x", pady=(0,1))
                row.columnconfigure(0, weight=1)
                vn = tk.StringVar()
                tk.Entry(row, textvariable=vn, font=("Segoe UI",10),
                         relief="flat", bg=bg, fg="#1a2a40",
                         highlightthickness=1, highlightbackground="#d0dff0").grid(
                    row=0, column=0, padx=(10,4), pady=7, sticky="ew")
                vp = tk.StringVar()
                tk.Entry(row, textvariable=vp, width=8,
                         font=("Segoe UI",9), justify="center",
                         relief="flat", bg="#f0f5fb", fg="#1a3f6b",
                         highlightthickness=1, highlightbackground="#c0d5ea").grid(
                    row=0, column=1, padx=4, pady=7)
                vp.trace_add("write", _recalc_varios)
                vc = tk.StringVar(value="0")
                tk.Spinbox(row, textvariable=vc, from_=0, to=999,
                           width=6, font=("Segoe UI",11,"bold"),
                           justify="center", relief="flat",
                           bg="#e0ecf5", fg="#1a3f6b",
                           buttonbackground="#c0d5ea",
                           highlightthickness=1, highlightbackground="#c0d5ea").grid(
                    row=0, column=2, padx=8, pady=5)
                lbl_imp = tk.Label(row, text="$ 0.00", font=("Segoe UI",10,"bold"),
                                   bg=bg, fg="#aaa9a5", width=9, anchor="e")
                lbl_imp.grid(row=0, column=3, padx=(4,10), pady=7)
                vc.trace_add("write", _recalc_varios)
                filas_varios_popup.append((vn, vp, vc, lbl_imp))
                row.bind("<MouseWheel>", _on_mw)
            def _add_5():
                ini = len(filas_varios_popup) + 1
                for i in range(ini, ini+5):
                    bg = "#ffffff" if i % 2 == 0 else "#f0f5fb"
                    row = tk.Frame(tbl_v, bg=bg, highlightthickness=1, highlightbackground="#d0dff0")
                    row.pack(fill="x", pady=(0,1))
                    row.columnconfigure(0, weight=1)
                    vn = tk.StringVar()
                    tk.Entry(row, textvariable=vn, font=("Segoe UI",10),
                             relief="flat", bg=bg, fg="#1a2a40",
                             highlightthickness=1, highlightbackground="#d0dff0").grid(
                        row=0, column=0, padx=(10,4), pady=7, sticky="ew")
                    vp = tk.StringVar()
                    tk.Entry(row, textvariable=vp, width=8,
                             font=("Segoe UI",9), justify="center",
                             relief="flat", bg="#f0f5fb", fg="#1a3f6b",
                             highlightthickness=1, highlightbackground="#c0d5ea").grid(
                        row=0, column=1, padx=4, pady=7)
                    vp.trace_add("write", _recalc_varios)
                    vc = tk.StringVar(value="0")
                    tk.Spinbox(row, textvariable=vc, from_=0, to=999,
                               width=6, font=("Segoe UI",11,"bold"),
                               justify="center", relief="flat",
                               bg="#e0ecf5", fg="#1a3f6b",
                               buttonbackground="#c0d5ea",
                               highlightthickness=1, highlightbackground="#c0d5ea").grid(
                        row=0, column=2, padx=8, pady=5)
                    lbl_imp = tk.Label(row, text="$ 0.00", font=("Segoe UI",10,"bold"),
                                       bg=bg, fg="#aaa9a5", width=9, anchor="e")
                    lbl_imp.grid(row=0, column=3, padx=(4,10), pady=7)
                    vc.trace_add("write", _recalc_varios)
                    filas_varios_popup.append((vn, vp, vc, lbl_imp))
                    row.bind("<MouseWheel>", _on_mw)
                cvs_v.update_idletasks()
                cvs_v.yview_moveto(1.0)
            btn_add_v = tk.Frame(body_v, bg="#ffffff")
            btn_add_v.pack(fill="x")
            tk.Button(btn_add_v, text="＋  5 filas más", font=("Segoe UI",9), bd=0,
                      bg="#e0ecf5", fg="#1a3f6b", pady=6, padx=12, cursor="hand2",
                      command=_add_5).pack(side="left")

        # ── Filas genéricas (productos) ────────────────────────────
        filas_ed = []   # lista de (frame, v_tipo, v_desc, v_cant, v_dato)

        def recalcular():
            total = 0.0
            count = 0
            for _, vt, vd, vc, vdat in filas_ed:
                if vd.get().strip():
                    count += 1
                    try:
                        c = int(vc.get() or 1)
                        d = float(vdat.get() or 0)
                        total += c*d*PRECIO_LB if vt.get()=="producto" else c*d
                    except Exception:
                        pass
            lbl_total_art.config(text=f"TOTAL  →  $ {int(total):,}")
            lbl_cant.config(text=f"{count} artículos")

        def agregar_fila(tipo_ini="producto", desc_ini="", cant_ini="1", dato_ini="0"):
            num = len(filas_ed)+1
            bg  = "#ffffff" if num%2==1 else "#f4faf7"
            row = tk.Frame(filas_frame, bg=bg,
                           highlightthickness=1, highlightbackground="#e8f0ec")
            row.pack(fill="x", pady=(0,1))
            tk.Label(row, text=str(num), font=("Segoe UI",8,"bold"),
                     bg=bg, fg="#aaa9a5", width=3).pack(side="left", padx=(6,2), pady=5)
            v_tipo = tk.StringVar(value=tipo_ini)
            ttk.Combobox(row, textvariable=v_tipo,
                         values=["producto"],
                         width=11, state="readonly", font=("Segoe UI",9)
                         ).pack(side="left", padx=2, pady=5)
            v_desc = tk.StringVar(value=desc_ini)
            ttk.Entry(row, textvariable=v_desc, font=("Segoe UI",9)).pack(
                side="left", padx=2, pady=5, expand=True, fill="x")
            v_cant = tk.StringVar(value=cant_ini)
            ttk.Entry(row, textvariable=v_cant, width=5,
                      font=("Segoe UI",9), justify="center").pack(side="left", padx=2, pady=5)
            val_fr = tk.Frame(row, bg=bg)
            val_fr.pack(side="left", padx=2, pady=5)
            v_dato = tk.StringVar(value=dato_ini)
            ttk.Entry(val_fr, textvariable=v_dato, width=8,
                      font=("Segoe UI",9), justify="right").pack(side="left")
            tk.Label(val_fr, text=" lb", font=("Segoe UI",7,"bold"),
                     bg=bg, fg="#0f6e56").pack(side="left")
            lbl_imp = tk.Label(row, text="$0.00",
                               font=("Segoe UI",10,"bold"),
                               bg=bg, fg="#0f6e56", width=10, anchor="e")
            lbl_imp.pack(side="left", padx=(4,2), pady=5)
            def calcular(*a):
                try:
                    c = int(v_cant.get() or 1)
                    d = float(v_dato.get() or 0)
                    imp = c*d*PRECIO_LB
                    lbl_imp.config(text=f"${imp:,.2f}", fg="#0f6e56")
                except Exception:
                    lbl_imp.config(text="$0.00")
                recalcular()
            v_desc.trace_add("write", calcular)
            v_cant.trace_add("write", calcular)
            v_dato.trace_add("write", calcular)
            def eliminar():
                row.destroy()
                filas_ed[:] = [f for f in filas_ed if f[0] != row]
                recalcular()
            tk.Button(row, text="✕", font=("Segoe UI",9,"bold"),
                      bd=0, bg="#fde8e8", fg="#c0392b",
                      width=3, cursor="hand2", pady=3,
                      command=eliminar).pack(side="left", padx=(2,6), pady=5)
            filas_ed.append((row, v_tipo, v_desc, v_cant, v_dato))
            calcular()

        # Cargar artículos existentes en las tablas correspondientes
        for a in arts:
            tipo_bd = (a.get("tipo") or "").lower()
            peso    = float(a.get("peso_lb", 0) or 0)
            valor   = float(a.get("valor",   0) or 0)
            cant    = int(a.get("cantidad",  1) or 1)
            desc    = a.get("descripcion", "")
            if tipo_bd == "medicamento":
                _agregar_fila_med_ed(desc, cant, valor)
            elif tipo_bd == "vario":
                _agregar_fila_vario_ed(desc, cant, valor)
            elif tipo_bd == "documento":
                _agregar_fila_doc_ed(desc, cant, valor)
            else:
                # Producto por peso
                if peso > 0:
                    _agregar_fila_peso_ed(desc, peso)
                elif valor > 0:
                    _agregar_fila_doc_ed(desc, cant, valor)
                else:
                    agregar_fila(tipo_ini="producto", desc_ini=desc,
                                 cant_ini=str(cant), dato_ini=str(peso))

        # Recalcular total al cargar
        _recalcular_total_ed()

        # ── Nota ─────────────────────────────────────────────────────────────
        b4 = _card("NOTA", "📝")
        b4.columnconfigure(0, weight=1)
        tk.Label(b4, text="Nota interna (opcional)", font=("Segoe UI", 8),
                 bg="#ffffff", fg="#6c757d").pack(anchor="w")
        v_nota = tk.StringVar(value=env.get("nota",""))
        ttk.Entry(b4, textvariable=v_nota, font=("Segoe UI", 10)
                  ).pack(fill="x", pady=(2,4))

        # ── Estado de pago ───────────────────────────────────────────────────
        b5 = _card("ESTADO DE PAGO", "💳")
        b5.columnconfigure(0, weight=1)

        estado_actual = env.get("estado", "Pendiente")
        if estado_actual == "Cancelado":
            estado_actual = "Pendiente"
        v_estado_ed = tk.StringVar(value=estado_actual)

        opciones_ed = tk.Frame(b5, bg="#ffffff")
        opciones_ed.pack(fill="x", pady=(4,8))

        for texto, valor, color in [("✅ Pagado","Pagado","#28a745"),
                                     ("💵 Abono","Abono","#007bff"),
                                     ("⏳ Pendiente","Pendiente","#fd7e14")]:
            tk.Radiobutton(opciones_ed, text=texto, variable=v_estado_ed, value=valor,
                          font=("Segoe UI", 10, "bold"), bg="#ffffff", fg=color,
                          selectcolor="#ffffff", activebackground="#ffffff",
                          activeforeground=color, indicatoron=True, cursor="hand2",
                          command=lambda: _toggle_abono_ed()
                          ).pack(side="left", padx=(0,20))

        abono_ed_frame = tk.Frame(b5, bg="#ffffff")
        abono_ed_frame.pack(fill="x", pady=(0,4))
        tk.Label(abono_ed_frame, text="Monto abonado ($)", font=("Segoe UI", 8),
                 bg="#ffffff", fg="#6c757d").pack(anchor="w")
        abono_ini = str(env.get("abono", "")) if estado_actual == "Abono" else ""
        v_abono_ed = tk.StringVar(value=abono_ini)
        ent_abono_ed = ttk.Entry(abono_ed_frame, textvariable=v_abono_ed,
                                  width=18, font=("Segoe UI", 10))
        ent_abono_ed.pack(anchor="w", pady=(2,4))

        def _toggle_abono_ed():
            if v_estado_ed.get() == "Abono":
                abono_ed_frame.pack(fill="x")
                ent_abono_ed.focus_set()
            else:
                abono_ed_frame.pack_forget()
                v_abono_ed.set("")

        if estado_actual != "Abono":
            abono_ed_frame.pack_forget()

        # ── Botones guardar / cerrar ──────────────────────────────────────────
        btn_bar = tk.Frame(body, bg="#f8f9fa", pady=14)
        btn_bar.pack(fill="x", padx=16)

        tk.Button(btn_bar, text="✕ Cancelar",
                  font=("Segoe UI",10), bd=0,
                  bg="#e9ecef", fg="#495057",
                  pady=10, padx=16, cursor="hand2",
                  command=win.destroy).pack(side="left")

        def guardar():
            if not v_en.get().strip():
                messagebox.showwarning("Requerido", "Ingrese el nombre del remitente.")
                return
            if not v_rn.get().strip():
                messagebox.showwarning("Requerido", "Ingrese el nombre del destinatario.")
                return

            articulos = []
            total = 0.0
            peso_total_calc = 0.0

            # Productos (filas genéricas)
            for _, vt, vd, vc, vdat in filas_ed:
                d = vd.get().strip()
                if not d: continue
                try:
                    cant = int(vc.get() or 1)
                    dato = float(vdat.get() or 0)
                    peso_lb, val_str = str(dato), "0"
                    total += cant * dato * PRECIO_LB
                    peso_total_calc += cant * dato
                except (ValueError, TypeError):
                    peso_lb, val_str = "0", "0"
                articulos.append({"descripcion":d,"cantidad":vc.get() or "1",
                                  "peso_lb":peso_lb,"valor":val_str,"tipo":"producto"})

            # Envíos por peso
            for _, desc, peso in filas_peso_ed:
                total += peso * PRECIO_LB
                peso_total_calc += peso
                articulos.append({"descripcion":desc,"cantidad":"1",
                                  "peso_lb":str(peso),"valor":"0","tipo":"producto"})

            # Medicamentos
            for _, nombre, cant, precio in filas_med_ed:
                total += cant * precio
                articulos.append({"descripcion":nombre,"cantidad":str(cant),
                                  "peso_lb":"0","valor":str(precio),"tipo":"medicamento"})

            # Documentos
            for _, nombre, cant, precio in filas_doc_ed:
                total += cant * precio
                articulos.append({"descripcion":nombre,"cantidad":str(cant),
                                  "peso_lb":"0","valor":str(precio),"tipo":"documento"})

            # Varios
            for _, nombre, cant, precio in filas_varios_ed:
                total += cant * precio
                articulos.append({"descripcion":nombre,"cantidad":str(cant),
                                  "peso_lb":"0","valor":str(precio),"tipo":"vario"})

            if not articulos:
                messagebox.showwarning("Sin artículos", "Agregue al menos un artículo.")
                return

            # Determinar estado y abono
            estado_sel = v_estado_ed.get()
            if estado_sel == "Abono":
                try:
                    abono_val = float(v_abono_ed.get().replace(",", "."))
                    if abono_val <= 0:
                        messagebox.showwarning("Requerido", "Ingrese un monto de abono válido.")
                        return
                    if abono_val > total:
                        messagebox.showwarning("Monto inválido",
                            f"El abono (${abono_val:,.2f}) no puede superar el total (${total:,.2f}).")
                        return
                except ValueError:
                    messagebox.showwarning("Requerido", "Ingrese un monto de abono numérico.")
                    return
            elif estado_sel == "Pagado":
                abono_val = total
            else:  # Pendiente
                abono_val = 0.0

            datos_act = {
                "ent_nombre":  v_en.get().strip(),
                "ent_tel":     v_et.get().strip(),
                "ent_dir":     v_ed.get().strip(),
                "rec_nombre":  v_rn.get().strip(),
                "rec_tel":     v_rt.get().strip(),
                "rec_dir":     v_rd.get().strip(),
                "destino_usa": v_dest.get(),
                "nota":        v_nota.get().strip(),
                "peso_total":  peso_total_calc,
                "total":       total,
                "abono":       abono_val,
                "restante":    max(0, total - abono_val),
                "estado":      estado_sel,
                "articulos":   articulos,
            }
            try:
                self.db.actualizar_envio(envio_id, datos_act)
                messagebox.showinfo("✓", "Envío actualizado correctamente.")
                win.destroy()
                self.cargar(envio_id)
                if hasattr(self.app.frames.get("historial", None), "refresh"):
                    self.app.frames["historial"].refresh()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar:\n{e}")

        tk.Button(btn_bar, text="💾  Guardar cambios",
                  font=("Segoe UI",11,"bold"), bd=0,
                  bg="#0f6e56", fg="white",
                  pady=12, padx=24, cursor="hand2",
                  command=guardar).pack(side="right")
