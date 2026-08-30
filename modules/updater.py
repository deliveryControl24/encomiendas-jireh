"""
==============================================
  modules/updater.py
  Sistema de auto-actualización desde GitHub
==============================================
"""

import json
import os
import sys
import subprocess
import urllib.request
import hashlib
import logging
import tkinter as tk
from tkinter import messagebox

logger = logging.getLogger(__name__)


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_local_version():
    ruta = os.path.join(get_base_dir(), "version.json")
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_local_version(data):
    ruta = os.path.join(get_base_dir(), "version.json")
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("No se pudo guardar version.json: %s", e)


def fetch_remote_version(repo_url, rama="main"):
    url = f"{repo_url.rstrip('/')}/raw/{rama}/version.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EncomiendaJireh-Updater"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("No se pudo obtener versión remota: %s", e)
        return None


def fetch_file(repo_url, rama, filepath):
    url = f"{repo_url.rstrip('/')}/raw/{rama}/{filepath}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EncomiendaJireh-Updater"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        logger.warning("No se pudo descargar %s: %s", filepath, e)
    return None


def file_hash(data):
    return hashlib.md5(data).hexdigest()


def comparar_versiones(local, remote):
    def parse(v):
        return tuple(int(x) for x in v.split("."))
    try:
        return parse(remote) > parse(local)
    except Exception:
        return False


class UpdateDialog(tk.Toplevel):
    def __init__(self, parent, version_remota, archivos_cambiados):
        super().__init__(parent)
        self.title("Actualización disponible")
        self.configure(bg="#f5f5f0")
        self.resizable(False, False)
        self.grab_set()
        self.resultado = False

        w, h = 450, 320
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        hdr = tk.Frame(self, bg="#0f6e56", pady=14, padx=20)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔄  Nueva versión disponible",
                 font=("Segoe UI", 13, "bold"),
                 bg="#0f6e56", fg="#ffffff").pack(anchor="w")
        tk.Label(hdr, text=f"Versión: {version_remota.get('version', '?')}",
                 font=("Segoe UI", 10),
                 bg="#0f6e56", fg="#9fe1cb").pack(anchor="w")

        body = tk.Frame(self, bg="#ffffff", padx=20, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Se encontraron cambios en:",
                 font=("Segoe UI", 10),
                 bg="#ffffff", fg="#333333").pack(anchor="w", pady=(0, 8))

        lista_frame = tk.Frame(body, bg="#f8f8f5",
                               highlightthickness=1, highlightbackground="#e0e0d8")
        lista_frame.pack(fill="both", expand=True, pady=(0, 12))

        for arch in archivos_cambiados[:10]:
            tk.Label(lista_frame, text=f"  📄 {arch}",
                     font=("Segoe UI", 9), bg="#f8f8f5", fg="#555555",
                     anchor="w").pack(fill="x", pady=1)
        if len(archivos_cambiados) > 10:
            tk.Label(lista_frame,
                     text=f"  ... y {len(archivos_cambiados) - 10} más",
                     font=("Segoe UI", 9), bg="#f8f8f5", fg="#888888",
                     anchor="w").pack(fill="x", pady=1)

        btn_frame = tk.Frame(self, bg="#f5f5f0", pady=12, padx=20)
        btn_frame.pack(fill="x")

        tk.Button(btn_frame, text="⬇️  Actualizar ahora",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  bg="#0f6e56", fg="white",
                  pady=8, padx=20, cursor="hand2",
                  command=self._aceptar).pack(side="right")

        tk.Button(btn_frame, text="Omitir",
                  font=("Segoe UI", 9), bd=0,
                  bg="#f1efe8", fg="#5f5e5a",
                  pady=8, padx=14, cursor="hand2",
                  command=self._cancelar).pack(side="right", padx=(0, 8))

    def _aceptar(self):
        self.resultado = True
        self.destroy()

    def _cancelar(self):
        self.resultado = False
        self.destroy()


def buscar_actualizaciones(parent=None):
    """
    Busca actualizaciones y aplica si el usuario confirma.
    Retorna True si se actualizó, False si no.
    """
    local = get_local_version()
    if not local:
        logger.info("No se encontró version.json local, saltando actualización.")
        return False

    repo_url = local.get("repo_url", "")
    rama = local.get("repo_rama", "main")
    if not repo_url:
        return False

    remote = fetch_remote_version(repo_url, rama)
    if not remote:
        return False

    if not comparar_versiones(local.get("version", "0.0.0"), remote.get("version", "0.0.0")):
        logger.info("Versión actual (%s) es igual o superior a la remota (%s).",
                     local.get("version"), remote.get("version"))
        return False

    archivos_remotos = remote.get("archivos", [])
    archivos_cambiados = []

    for filepath in archivos_remotos:
        contenido_remoto = fetch_file(repo_url, rama, filepath)
        if contenido_remoto is None:
            continue

        local_path = os.path.join(get_base_dir(), filepath)
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    contenido_local = f.read()
                if file_hash(contenido_remoto) != file_hash(contenido_local):
                    archivos_cambiados.append(filepath)
            except Exception:
                archivos_cambiados.append(filepath)
        else:
            archivos_cambiados.append(filepath)

    if not archivos_cambiados:
        save_local_version(remote)
        return False

    dialogo = None
    if parent:
        dialogo = UpdateDialog(parent, remote, archivos_cambiados)
        parent.wait_window(dialogo)
        if not dialogo.resultado:
            return False
    else:
        return False

    errores = []
    for filepath in archivos_cambiados:
        contenido = fetch_file(repo_url, rama, filepath)
        if contenido is None:
            errores.append(filepath)
            continue

        local_path = os.path.join(get_base_dir(), filepath)
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(contenido)
            logger.info("Actualizado: %s", filepath)
        except Exception as e:
            logger.error("Error al actualizar %s: %s", filepath, e)
            errores.append(filepath)

    save_local_version(remote)

    if errores:
        messagebox.showwarning("Actualización parcial",
                               f"No se pudieron actualizar:\n" +
                               "\n".join(errores),
                               parent=parent)
    else:
        messagebox.showinfo("Actualización completa",
                            f"Archivos actualizados a versión {remote.get('version')}.\n"
                            "Reinicia la aplicación para aplicar los cambios.",
                            parent=parent)

    return True


def reiniciar_app():
    """Reinicia la aplicación."""
    python = sys.executable
    if getattr(sys, 'frozen', False):
        os.execl(python, python, *sys.argv)
    else:
        os.execl(python, python, *sys.argv)
