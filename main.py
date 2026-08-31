"""
==============================================
  SISTEMA DE ENCOMIENDAS - main.py
  Punto de entrada principal de la aplicacion
==============================================
"""

import tkinter as tk
from tkinter import ttk
from modules.database import Database
from modules.nueva_encomienda import NuevaEncomiendaFrame
from modules.historial import HistorialFrame
from modules.costo_viaje import CostoViajeFrame
from modules.arqueo_caja import ArqueoCajaFrame
from modules.cuentas_cobrar import CuentasCobrarFrame
from modules.kpi_dashboard import KPIDashboardFrame
from modules.reportes import ReportesFrame
from modules.pago import PagoFrame
from modules.configuracion import ConfiguracionFrame, ConfigManager
from modules.historial_mensual import HistorialMensualFrame
from modules.historial_clientes import HistorialClientesFrame
from modules.login import LoginWindow, UserManagementDialog
from modules.config import get_base_dir
import logging
import os
from modules.config import TEMA_LIGHT, TEMA_DARK, MONEDA_DEFAULT

# Ruta del log junto al ejecutable/script
_log_dir = get_base_dir()
_log_path = os.path.join(_log_dir, "encomiendas.log")

try:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename=_log_path,
        filemode="a"
    )
except PermissionError:
    _log_path = os.path.join(_log_dir, "encomiendas_debug.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename=_log_path,
        filemode="a"
    )

logger = logging.getLogger("main")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Encomienda Jireh - Sistema de Envios")
        self.usuario_actual = None
        
        # Establecer icono
        try:
            icono_ruta = os.path.join(get_base_dir(), "encomienda_jireh.ico")
            if os.path.exists(icono_ruta):
                self.iconbitmap(icono_ruta)
        except Exception:
            pass

        self.config_mgr = ConfigManager()

        tema_cfg = self.config_mgr.get("tema", "light")
        self.tema_oscuro = tema_cfg == "dark"
        self.colores = dict(TEMA_DARK if self.tema_oscuro else TEMA_LIGHT)

        sidebar_ancho = self.config_mgr.get("sidebar_ancho", 200)
        fuente_tamano = self.config_mgr.get("fuente_tamano", 10)

        self.geometry(f"{sidebar_ancho + 900}x700")
        self.minsize(900, 600)
        self.configure(bg=self.colores["bg"])

        self.db = Database()

        # Mostrar login si está activado
        self.withdraw()
        if self.config_mgr.get("login_activo", True):
            self.after(100, self._mostrar_login)
        else:
            self.usuario_actual = {"usuario": "admin", "nombre_completo": "Administrador", "rol": "admin"}
            self.after(100, self._iniciar_app)

    def _mostrar_login(self):
        def on_login(usuario):
            self.usuario_actual = usuario
            self.deiconify()
            self._iniciar_app()
        LoginWindow(self.db, on_login)

    def _iniciar_app(self):
        # Buscar actualizaciones al iniciar
        import threading
        def _check_updates():
            try:
                from modules.updater import buscar_actualizaciones
                self.after(500, lambda: buscar_actualizaciones(self))
            except Exception as e:
                logger.warning("Error al buscar actualizaciones: %s", e)
        threading.Thread(target=_check_updates, daemon=True).start()

        def _backup_thread():
            try:
                self.db.backup_db()
                logger.info("Backup automatico completado")
            except Exception as e:
                logger.warning("Backup automatico fallo: %s", e)
        threading.Thread(target=_backup_thread, daemon=True).start()

        self._verificar_pin()

        self._setup_style(self.config_mgr.get("fuente_tamano", 10))
        self._build_ui()
        self.show_frame("nueva")
        self.bind("<Control-s>", self._atajos)
        self.bind("<Control-f>", self._atajos)
        self.bind("<Control-d>", self._atajos)
        self.bind("<Control-k>", self._atajos)
        self.bind("<Control-t>", self._atajos)
        self.bind("<Control-i>", self._atajos)
        self._actualizar_badges()
        self._actualizar_totales()
        self.bind("<Configure>", self._on_resize)

        self._setup_timeout()

        if self.config_mgr.get("alerta_deudas_activa", True):
            self.after(500, self._alertar_deudas)

        logger.info("Aplicacion iniciada")

    def _verificar_pin(self):
        if self.config_mgr.get("pin_acceso_activo", False):
            pin_guardado = self.config_mgr.get("pin_acceso", "")
            if pin_guardado:
                from tkinter import simpledialog
                intentos = 0
                while intentos < 3:
                    pin = simpledialog.askstring("PIN de Acceso",
                                                  "Ingrese el PIN para continuar:",
                                                  show="*", parent=self)
                    if pin is None:
                        self.destroy()
                        return
                    if pin == pin_guardado:
                        return
                    intentos += 1
                    if intentos < 3:
                        messagebox.showwarning("PIN incorrecto",
                                               f"PIN incorrecto. Intento {intentos}/3")
                messagebox.showerror("Acceso denegado", "Demasiados intentos fallidos.")
                self.destroy()

    def _setup_timeout(self):
        timeout_min = self.config_mgr.get("timeout_sesion", 0)
        if timeout_min > 0:
            self._timeout_ms = timeout_min * 60 * 1000
            self._timeout_job = None
            self._reset_timeout()
            self.bind("<Any-Key>", self._reset_timeout)
            self.bind("<Any-Button>", self._reset_timeout)
            self.bind("<Motion>", self._reset_timeout)

    def _reset_timeout(self, event=None):
        if hasattr(self, "_timeout_job") and self._timeout_job:
            self.after_cancel(self._timeout_job)
        self._timeout_job = self.after(self._timeout_ms, self._on_timeout)

    def _on_timeout(self):
        self.destroy()

    def _setup_style(self, fuente_tamano=10):
        c = self.colores
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background=c["bg"])
        style.configure("Card.TFrame", background=c["card_bg"], relief="flat")
        style.configure("Sidebar.TFrame", background=c["sidebar"])

        font_base = ("Segoe UI", fuente_tamano)
        font_title = ("Segoe UI", fuente_tamano + 3, "bold")
        font_section = ("Segoe UI", fuente_tamano - 1, "bold")
        font_btn = ("Segoe UI", fuente_tamano, "bold")
        font_btn_normal = ("Segoe UI", fuente_tamano)
        font_sidebar = ("Segoe UI", fuente_tamano + 1)
        font_sidebar_active = ("Segoe UI", fuente_tamano + 1, "bold")
        font_tree = ("Segoe UI", fuente_tamano)
        font_tree_heading = ("Segoe UI", fuente_tamano - 1, "bold")

        style.configure("TLabel", background=c["bg"],
                        font=font_base, foreground=c["fg"])
        style.configure("Title.TLabel", font=font_title,
                        background=c["card_bg"], foreground=c["accent"])
        style.configure("Section.TLabel", font=font_section,
                        background=c["card_bg"], foreground=c["card_header_fg"])
        style.configure("Card.TLabel", background=c["card_bg"],
                        font=font_base, foreground=c["fg"])

        style.configure("TEntry", font=font_base, padding=6,
                        fieldbackground=c["input_bg"], foreground=c["fg"])
        style.configure("TCombobox", font=font_base,
                        fieldbackground=c["input_bg"], foreground=c["fg"])

        style.configure("Primary.TButton",
                        background=c["accent"], foreground="white",
                        font=font_btn,
                        borderwidth=0, relief="flat", padding=(12, 8))
        style.map("Primary.TButton",
                  background=[("active", c["sidebar_active"]), ("pressed", c["sidebar"])])

        style.configure("Secondary.TButton",
                        background=c["accent_light"], foreground=c["accent"],
                        font=font_btn_normal,
                        borderwidth=0, relief="flat", padding=(12, 8))
        style.map("Secondary.TButton",
                  background=[("active", c["progress_fill"])])

        style.configure("Danger.TButton",
                        background=c["danger_bg"], foreground=c["danger_fg"],
                        font=font_btn_normal,
                        borderwidth=0, relief="flat", padding=(12, 8))

        style.configure("Treeview",
                        font=font_tree,
                        rowheight=32,
                        background=c["tree_bg"],
                        fieldbackground=c["tree_bg"],
                        foreground=c["tree_fg"])
        style.configure("Treeview.Heading",
                        font=font_tree_heading,
                        background=c["card_header"],
                        foreground=c["card_header_fg"],
                        relief="flat")
        style.map("Treeview", background=[("selected", c["select_bg"])],
                  foreground=[("selected", c["select_fg"])])

        style.configure("Sidebar.TButton",
                        background=c["sidebar"], foreground=c["sidebar_text"],
                        font=font_sidebar,
                        borderwidth=0, relief="flat",
                        padding=(16, 14), anchor="w")
        style.map("Sidebar.TButton",
                  background=[("active", c["accent"]), ("pressed", c["sidebar_active"])])

        style.configure("SidebarActive.TButton",
                        background=c["sidebar_active"], foreground=c["sidebar_text"],
                        font=font_sidebar_active,
                        borderwidth=0, relief="flat",
                        padding=(16, 14), anchor="w")

    def _build_ui(self):
        c = self.colores
        self.sidebar = tk.Frame(self, bg=c["sidebar"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo_frame = tk.Frame(self.sidebar, bg=c["sidebar_active"], pady=20)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="📦 Encomienda Jireh",
                 font=("Segoe UI", 14, "bold"),
                 bg=c["sidebar_active"], fg=c["sidebar_text"]).pack(padx=16)
        tk.Label(logo_frame, text="Sistema de envíos",
                 font=("Segoe UI", 9),
                 bg=c["sidebar_active"], fg=c["sidebar_icon"]).pack()

        # ── Scrollable menu area ─────────────────
        self.sidebar_canvas = tk.Canvas(self.sidebar, bg=c["sidebar"],
                                         highlightthickness=0, width=200)
        self.sidebar_scroll = ttk.Scrollbar(self.sidebar, orient="vertical",
                                             command=self.sidebar_canvas.yview)
        self.menu_frame = tk.Frame(self.sidebar_canvas, bg=c["sidebar"])
        def _config_canvas(e):
            self.sidebar_canvas.configure(
                scrollregion=self.sidebar_canvas.bbox("all"))
            self.sidebar_canvas.itemconfig(self.canvas_window, width=e.width)
        self.menu_frame.bind("<Configure>", _config_canvas)
        self.canvas_window = self.sidebar_canvas.create_window(
            (0, 0), window=self.menu_frame, anchor="nw", width=200)
        self.sidebar_canvas.bind("<Configure>",
            lambda e: self.sidebar_canvas.itemconfig(
                self.canvas_window, width=e.width))
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scroll.set)

        self.sidebar_canvas.pack(side="left", fill="both", expand=True)
        self.sidebar_scroll.pack(side="right", fill="y")

        c = self.colores
        self.menu_buttons = {}
        menus = [
            ("nueva",     "➕  Nueva encomienda"),
            ("historial", "📋  Historial"),
            ("mensual",   "📅  Hist. mensual"),
            ("clientes",  "👤  Hist. clientes"),
            ("costos",    "💰  Costos viaje"),
            ("cobrar",    "📋  Ctas. cobrar"),
            ("arqueo",    "💵  Arqueo caja"),
            ("kpi",       "📊  Dashboard KPI"),
            ("reportes",  "📈  Reportes"),
            ("config",    "⚙️  Configuracion"),
        ]

        for key, label in menus:
            btn = tk.Button(self.menu_frame, text=label,
                            font=("Segoe UI", 11),
                            bg=c["sidebar"], fg=c["sidebar_text"],
                            activebackground=c["accent"],
                            activeforeground=c["sidebar_text"],
                            bd=0, relief="flat",
                            padx=16, pady=13,
                            anchor="w", cursor="hand2",
                            command=lambda k=key: self.show_frame(k))
            btn.pack(fill="x")
            self.menu_buttons[key] = btn

        c = self.colores
        self.sidebar_bottom = tk.Frame(self.sidebar, bg=c["sidebar"])
        self.sidebar_bottom.pack(side="bottom", fill="x")

        # Backup button
        self.btn_backup = tk.Button(self.sidebar_bottom,
                                      text="💾  Respaldar ahora",
                                      font=("Segoe UI", 9),
                                      bg=c["sidebar"], fg=c["sidebar_text"],
                                      activebackground=c["accent"],
                                      activeforeground=c["sidebar_text"],
                                      bd=0, relief="flat",
                                      padx=16, pady=8,
                                      anchor="w", cursor="hand2",
                                      command=self._respaldo)
        self.btn_backup.pack(side="bottom")

        # Theme toggle
        self.btn_tema = tk.Button(self.sidebar_bottom,
                                   text="🌙  Modo oscuro",
                                   font=("Segoe UI", 9),
                                   bg=c["sidebar"], fg=c["sidebar_text"],
                                   activebackground=c["accent"],
                                   activeforeground=c["sidebar_text"],
                                   bd=0, relief="flat",
                                   padx=16, pady=8,
                                   anchor="w", cursor="hand2",
                                   command=self._alternar_tema)
        self.btn_tema.pack(side="bottom")

        # User info and logout
        if self.usuario_actual:
            user_frame = tk.Frame(self.sidebar_bottom, bg=c["sidebar_active"], padx=16, pady=6)
            user_frame.pack(side="bottom", fill="x", padx=8, pady=(4, 0))
            
            nombre = self.usuario_actual.get("nombre_completo") or self.usuario_actual.get("usuario", "")
            rol = self.usuario_actual.get("rol", "")
            tk.Label(user_frame, text=f"👤 {nombre}",
                     font=("Segoe UI", 9, "bold"),
                     bg=c["sidebar_active"], fg=c["sidebar_text"],
                     anchor="w").pack(fill="x")
            tk.Label(user_frame, text=f"   Rol: {rol}",
                     font=("Segoe UI", 8),
                     bg=c["sidebar_active"], fg=c["sidebar_icon"],
                     anchor="w").pack(fill="x")
            
            tk.Button(user_frame, text="🚪 Cerrar sesión",
                      font=("Segoe UI", 9),
                      bg=c["sidebar_active"], fg="#791f1f",
                      bd=0, relief="flat", anchor="w", cursor="hand2",
                      command=self._cerrar_sesion).pack(fill="x", pady=(4, 0))

        # Today summaries
        self.lbl_hoy = tk.Label(self.sidebar_bottom, text="",
                                 font=("Segoe UI", 8),
                                 bg=c["sidebar_active"],
                                 fg=c["sidebar_icon"],
                                 anchor="w")
        self.lbl_hoy.pack(fill="x", padx=16, pady=4)

        self.lbl_mes = tk.Label(self.sidebar_bottom, text="",
                                 font=("Segoe UI", 8),
                                 bg=c["sidebar_active"],
                                 fg=c["sidebar_icon"],
                                 anchor="w")
        self.lbl_mes.pack(fill="x", padx=16, pady=(0, 6))

        tk.Label(self.sidebar_bottom, text="Encomienda Jireh v2.0",
                 font=("Segoe UI", 8),
                 bg=c["sidebar"], fg=c["sidebar_icon"]).pack(pady=10)

        self.main_container = tk.Frame(self, bg=self.colores["bg"])
        self.main_container.pack(side="left", fill="both", expand=True)

        self.frames = {}
        for FrameClass, key in [
            (NuevaEncomiendaFrame, "nueva"),
            (HistorialFrame, "historial"),
            (HistorialMensualFrame, "mensual"),
            (HistorialClientesFrame, "clientes"),
            (CostoViajeFrame, "costos"),
            (CuentasCobrarFrame, "cobrar"),
            (ArqueoCajaFrame, "arqueo"),
            (KPIDashboardFrame, "kpi"),
            (ReportesFrame, "reportes"),
            (ConfiguracionFrame, "config"),
        ]:
            frame = FrameClass(self.main_container, self.db, self)
            frame._dirty = False
            self.frames[key] = frame

    def abrir_pago(self, envio_id):
        PagoFrame(self, self.db, envio_id, self.frames["historial"].refresh)

    def _alertar_deudas(self):
        try:
            dias = self.config_mgr.get("deudas_vencidas_dias", 7)
            moneda = self.config_mgr.get("moneda", "$")
            deudas = self.db.obtener_deudas_vencidas()
            vencidas = [d for d in deudas if d.get("dias_desde", 0) >= dias]
            if vencidas:
                from tkinter import messagebox
                msg = "CLIENTES CON DEUDAS VENCIDAS:\n\n"
                for v in vencidas[:5]:
                    msg += f"- {v['ent_nombre']} - {moneda}{v['restante']:,.0f} ({int(v['dias_desde'])} dias)\n"
                if len(vencidas) > 5:
                    msg += f"\n... y {len(vencidas)-5} mas"
                messagebox.showwarning("Deudas vencidas", msg)
        except Exception as e:
            logger.warning("Error al verificar deudas: %s", e)

    def mostrar_frame(self, name):
        """Alias publico para show_frame."""
        self.show_frame(name)

    def _sonido(self):
        if self.config_mgr.get("sonido_crear_envio", True):
            self.bell()

    def _respaldo(self):
        import threading
        from tkinter import messagebox
        def _do_backup():
            try:
                ruta = self.db.backup_db()
                self.after(0, lambda: messagebox.showinfo("Respaldo", f"Base de datos respaldada en:\n{ruta}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"No se pudo respaldar:\n{e}"))
        threading.Thread(target=_do_backup, daemon=True).start()

    def _alternar_tema(self):
        self.tema_oscuro = not self.tema_oscuro
        from modules.config import TEMA_LIGHT, TEMA_DARK
        self.colores = dict(TEMA_DARK if self.tema_oscuro else TEMA_LIGHT)
        self.configure(bg=self.colores["bg"])
        self.main_container.configure(bg=self.colores["bg"])

        self.config_mgr.set("tema", "dark" if self.tema_oscuro else "light")
        self.config_mgr.guardar()

        c = self.colores
        self.sidebar.configure(bg=c["sidebar"])
        self.sidebar_canvas.configure(bg=c["sidebar"])
        self.menu_frame.configure(bg=c["sidebar"])
        self.sidebar_bottom.configure(bg=c["sidebar"])
        for w in self.sidebar_bottom.winfo_children():
            if isinstance(w, tk.Label):
                w.configure(bg=c.get(w.cget("bg"), c["sidebar"]),
                            fg=c.get(w.cget("fg"), c["sidebar_text"]))
            elif isinstance(w, tk.Button):
                w.configure(bg=c.get(w.cget("bg"), c["sidebar"]),
                            fg=c.get(w.cget("fg"), c["sidebar_text"]))

        self._setup_style(self.config_mgr.get("fuente_tamano", 10))

        for key, btn in self.menu_buttons.items():
            btn.configure(bg=c["sidebar"], fg=c["sidebar_text"],
                          activebackground=c["accent"])
        self.btn_backup.configure(bg=c["sidebar"], fg=c["sidebar_text"],
                                  activebackground=c["accent"])
        if self.tema_oscuro:
            self.btn_tema.configure(text="☀️  Modo claro",
                                    bg=c["sidebar"], fg=c["sidebar_text"])
        else:
            self.btn_tema.configure(text="🌙  Modo oscuro",
                                    bg=c["sidebar"], fg=c["sidebar_text"])

        self._actualizar_badges()
        if hasattr(self, "current_frame"):
            self.show_frame(self.current_frame)

        self._actualizar_totales()

    def _actualizar_badges(self):
        try:
            deudas = self.db.contar_deudas_vencidas()
            if "cobrar" in self.menu_buttons:
                txt = "📋  Ctas. cobrar"
                if deudas:
                    txt += f"  ({deudas})"
                self.menu_buttons["cobrar"].config(text=txt)
        except:
            pass

    def _cerrar_sesion(self):
        from tkinter import messagebox
        if messagebox.askyesno("Cerrar sesión",
                               "¿Estás seguro de cerrar sesión?"):
            self.usuario_actual = None
            self.withdraw()
            self.after(100, self._mostrar_login)

    def _gestionar_usuarios(self):
        UserManagementDialog(self, self.db)

    def show_frame(self, name):
        for key, frame in self.frames.items():
            frame.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

        if hasattr(self.frames[name], "refresh"):
            if not hasattr(self.frames[name], "_dirty") or self.frames[name]._dirty:
                self.frames[name].refresh()
                self.frames[name]._dirty = False

        c = self.colores
        for key, btn in self.menu_buttons.items():
            btn.config(bg=c["sidebar_active"] if key == name else c["sidebar"],
                       font=("Segoe UI", 11, "bold") if key == name
                       else ("Segoe UI", 11))

        self.current_frame = name

    def mark_dirty(self, frame_names=None):
        if frame_names:
            for name in frame_names:
                if name in self.frames:
                    self.frames[name]._dirty = True
        else:
            for frame in self.frames.values():
                frame._dirty = True

    def _actualizar_totales(self):
        try:
            c = self.colores
            hoy = self.db.resumen_hoy()
            mes = self.db.resumen_mes()
            self.lbl_hoy.config(
                text=f"📅 Hoy: {hoy['cantidad']} env.  C${float(hoy['monto']):,.0f}",
                bg=c["sidebar_active"], fg=c["sidebar_icon"])
            self.lbl_mes.config(
                text=f"📆 Este mes: {mes['cantidad']} env.  C${float(mes['monto']):,.0f}",
                bg=c["sidebar_active"], fg=c["sidebar_icon"])
        except:
            pass

    def _on_resize(self, event=None):
        if event and event.widget != self:
            return
        if hasattr(self, "_resize_job") and self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(200, self._apply_resize)

    def _apply_resize(self):
        self._resize_job = None
        if not hasattr(self, "current_frame") or not self.current_frame:
            return
        f = self.frames.get(self.current_frame)
        if not f:
            return
        if hasattr(f, "on_resize"):
            f.on_resize()
            return
        self._ajustar_treeviews(f)

    def _ajustar_treeviews(self, parent):
        """Busca todos los Treeview en el frame y ajusta columnas."""
        try:
            for child in parent.winfo_children():
                if isinstance(child, ttk.Treeview):
                    cols = child["columns"]
                    if cols:
                        w = child.winfo_width()
                        if w > 50:
                            ancho = max(50, w // len(cols))
                            for col in cols:
                                child.column(col, width=ancho)
                self._ajustar_treeviews(child)
        except Exception:
            pass

    def _atajos(self, event):
        if event.state & 0x4 and event.keysym == 's':
            self.show_frame("nueva")
            return "break"
        if event.state & 0x4 and event.keysym == 'f':
            self.show_frame("historial")
            return "break"
        if event.state & 0x4 and event.keysym == 'd':
            self.show_frame("arqueo")
            return "break"
        if event.state & 0x4 and event.keysym == 'k':
            self.show_frame("kpi")
            return "break"
        if event.state & 0x4 and event.keysym == 't':
            self.show_frame("costos")
            return "break"
        if event.state & 0x4 and event.keysym == 'i':
            self.show_frame("config")
            return "break"
        return None


if __name__ == "__main__":
    app = App()
    app.mainloop()
