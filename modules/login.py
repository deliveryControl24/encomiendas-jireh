"""
==============================================
  modules/login.py
  Ventana de login y gestión de sesiones
==============================================
"""

import tkinter as tk
from tkinter import ttk, messagebox


class LoginWindow(tk.Toplevel):
    def __init__(self, db, on_login_success):
        super().__init__()
        self.db = db
        self.on_login_success = on_login_success
        self.usuario_actual = None
        self.title("Encomienda Jireh - Iniciar Sesión")
        self.configure(bg="#f5f5f0")
        self.resizable(False, False)
        self.grab_set()

        w, h = 420, 380
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        try:
            self.iconbitmap("encomienda_jireh.ico")
        except Exception:
            pass

        self._build()

    def _build(self):
        c_fondo = "#f5f5f0"
        c_accent = "#0f6e56"
        c_card = "#ffffff"
        c_text = "#333333"
        c_subtle = "#888780"

        # Header
        hdr = tk.Frame(self, bg=c_accent, pady=20, padx=30)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📦  Encomienda Jireh",
                 font=("Segoe UI", 16, "bold"),
                 bg=c_accent, fg="#ffffff").pack()
        tk.Label(hdr, text="Sistema de Envíos",
                 font=("Segoe UI", 10),
                 bg=c_accent, fg="#9fe1cb").pack(pady=(4, 0))

        # Card
        card = tk.Frame(self, bg=c_card, padx=30, pady=24)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(card, text="Iniciar sesión",
                 font=("Segoe UI", 13, "bold"),
                 bg=c_card, fg=c_text).pack(anchor="w", pady=(0, 16))

        # Usuario
        tk.Label(card, text="Usuario", font=("Segoe UI", 10),
                 bg=c_card, fg=c_subtle).pack(anchor="w")
        self.v_usuario = tk.StringVar()
        e_user = tk.Entry(card, textvariable=self.v_usuario,
                          font=("Segoe UI", 11), bd=1,
                          relief="solid", bg="#f9f9f6")
        e_user.pack(fill="x", pady=(2, 12), ipady=6)
        e_user.focus_set()

        # Contraseña
        tk.Label(card, text="Contraseña", font=("Segoe UI", 10),
                 bg=c_card, fg=c_subtle).pack(anchor="w")
        self.v_password = tk.StringVar()
        e_pass = tk.Entry(card, textvariable=self.v_password,
                          font=("Segoe UI", 11), bd=1,
                          relief="solid", bg="#f9f9f6", show="•")
        e_pass.pack(fill="x", pady=(2, 16), ipady=6)
        e_pass.bind("<Return>", lambda e: self._login())

        # Botón login
        tk.Button(card, text="🔑  Ingresar",
                  font=("Segoe UI", 11, "bold"),
                  bg=c_accent, fg="#ffffff",
                  bd=0, pady=10, cursor="hand2",
                  command=self._login).pack(fill="x")

        # Info
        tk.Label(card, text="Usuario por defecto: admin / admin123",
                 font=("Segoe UI", 8), bg=c_card, fg=c_subtle
                 ).pack(pady=(12, 0))

    def _login(self):
        usuario = self.v_usuario.get().strip()
        password = self.v_password.get().strip()

        if not usuario or not password:
            messagebox.showwarning("Campos vacíos",
                                   "Ingresa usuario y contraseña",
                                   parent=self)
            return

        resultado = self.db.login(usuario, password)
        if resultado:
            self.usuario_actual = resultado
            self.on_login_success(resultado)
            self.destroy()
        else:
            messagebox.showerror("Error",
                                 "Usuario o contraseña incorrectos",
                                 parent=self)


class UserManagementDialog(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("Gestión de usuarios")
        self.configure(bg="#f5f5f0")
        self.resizable(False, False)
        self.grab_set()

        w, h = 550, 420
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build()

    def _build(self):
        c_accent = "#0f6e56"
        c_card = "#ffffff"

        hdr = tk.Frame(self, bg=c_accent, pady=12, padx=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="👤  Gestión de usuarios",
                 font=("Segoe UI", 13, "bold"),
                 bg=c_accent, fg="#ffffff").pack(side="left")

        body = tk.Frame(self, bg=c_card, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        # Formulario
        form = tk.Frame(body, bg=c_card)
        form.pack(fill="x", pady=(0, 10))

        tk.Label(form, text="Usuario:", font=("Segoe UI", 9),
                 bg=c_card).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.v_usuario = tk.StringVar()
        tk.Entry(form, textvariable=self.v_usuario, font=("Segoe UI", 9),
                 width=14).grid(row=0, column=1, padx=(0, 10))

        tk.Label(form, text="Contraseña:", font=("Segoe UI", 9),
                 bg=c_card).grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.v_password = tk.StringVar()
        tk.Entry(form, textvariable=self.v_password, font=("Segoe UI", 9),
                 width=14, show="*").grid(row=0, column=3, padx=(0, 10))

        tk.Label(form, text="Nombre:", font=("Segoe UI", 9),
                 bg=c_card).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
        self.v_nombre = tk.StringVar()
        tk.Entry(form, textvariable=self.v_nombre, font=("Segoe UI", 9),
                 width=14).grid(row=1, column=1, padx=(0, 10), pady=(6, 0))

        tk.Label(form, text="Rol:", font=("Segoe UI", 9),
                 bg=c_card).grid(row=1, column=2, sticky="w", padx=(0, 6), pady=(6, 0))
        self.v_rol = tk.StringVar(value="cajero")
        ttk.Combobox(form, textvariable=self.v_rol, width=12,
                     values=["admin", "cajero", "supervisor"],
                     state="readonly").grid(row=1, column=3, pady=(6, 0))

        btn_frame = tk.Frame(body, bg=c_card)
        btn_frame.pack(fill="x", pady=(0, 8))

        tk.Button(btn_frame, text="➕ Crear usuario",
                  font=("Segoe UI", 9, "bold"),
                  bg=c_accent, fg="#ffffff", bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._crear_usuario).pack(side="left")

        tk.Button(btn_frame, text="🔄 Actualizar",
                  font=("Segoe UI", 9),
                  bg="#f0efe8", fg="#5f5e5a", bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._refrescar).pack(side="left", padx=(8, 0))

        # Lista de usuarios
        cols = ("id", "usuario", "nombre", "rol", "activo")
        self.tree = ttk.Treeview(body, columns=cols, show="headings",
                                  selectmode="browse", height=8)
        self.tree.heading("id", text="ID")
        self.tree.heading("usuario", text="Usuario")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("rol", text="Rol")
        self.tree.heading("activo", text="Activo")
        self.tree.column("id", width=35, anchor="center")
        self.tree.column("usuario", width=100)
        self.tree.column("nombre", width=140)
        self.tree.column("rol", width=80, anchor="center")
        self.tree.column("activo", width=55, anchor="center")
        self.tree.pack(fill="both", expand=True)

        btns_bajo = tk.Frame(body, bg=c_card)
        btns_bajo.pack(fill="x", pady=(8, 0))

        tk.Button(btns_bajo, text="🗑 Desactivar",
                  font=("Segoe UI", 9),
                  bg="#fcebeb", fg="#791f1f", bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._desactivar).pack(side="left")

        self._refrescar()

    def _refrescar(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        usuarios = self.db.obtener_usuarios()
        for u in usuarios:
            self.tree.insert("", "end", iid=str(u["id"]),
                             values=(u["id"], u["usuario"],
                                     u["nombre_completo"], u["rol"],
                                     "Sí" if u["activo"] else "No"))

    def _crear_usuario(self):
        usuario = self.v_usuario.get().strip()
        password = self.v_password.get().strip()
        nombre = self.v_nombre.get().strip()
        rol = self.v_rol.get()

        if not usuario or not password:
            messagebox.showwarning("Campos requeridos",
                                   "Usuario y contraseña son obligatorios",
                                   parent=self)
            return

        if len(password) < 4:
            messagebox.showwarning("Contraseña corta",
                                   "Mínimo 4 caracteres",
                                   parent=self)
            return

        if self.db.crear_usuario(usuario, password, nombre, rol):
            messagebox.showinfo("Éxito", f"Usuario '{usuario}' creado",
                                parent=self)
            self.v_usuario.set("")
            self.v_password.set("")
            self.v_nombre.set("")
            self._refrescar()
        else:
            messagebox.showerror("Error", f"El usuario '{usuario}' ya existe",
                                 parent=self)

    def _desactivar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Selecciona", "Selecciona un usuario",
                                   parent=self)
            return
        uid = int(sel[0])
        if messagebox.askyesno("Confirmar", "¿Desactivar este usuario?", parent=self):
            self.db.eliminar_usuario(uid)
            self._refrescar()
