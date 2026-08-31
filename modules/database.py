"""
==============================================
  modules/database.py
  Capa de datos - SQLite
  Solo USD ($), sin Córdoba
==============================================
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
import logging

try:
    from modules.config import get_base_dir
except ImportError:
    def get_base_dir():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


logger = logging.getLogger(__name__)

class Database:
    def __init__(self, ruta_db=None):
        if ruta_db is None:
            ruta_db = os.path.join(get_base_dir(), "encomiendas.db")
        self.ruta = ruta_db
        self.conn = sqlite3.connect(ruta_db, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._apply_pragmas()
        self._init_tablas()
        self._init_indexes()
        self._client_cache = {}
        self._client_cache_time = 0

    def _apply_pragmas(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA cache_size=-64000")
        cur.execute("PRAGMA temp_store=MEMORY")
        cur.execute("PRAGMA mmap_size=268435456")
        cur.execute("PRAGMA foreign_keys=ON")
        self.conn.commit()

    def _init_tablas(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS envios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo      TEXT    UNIQUE,
                fecha       TEXT    NOT NULL,
                ent_nombre  TEXT    NOT NULL,
                ent_tel     TEXT,
                ent_dir     TEXT    DEFAULT '',
                rec_nombre  TEXT    NOT NULL,
                rec_tel     TEXT,
                rec_dir     TEXT    DEFAULT '',
                peso_total  REAL    DEFAULT 0,
                subtotal    REAL    DEFAULT 0,
                total       REAL    DEFAULT 0,
                abono       REAL    DEFAULT 0,
                restante    REAL    DEFAULT 0,
                moneda      TEXT    DEFAULT '$',
                estado      TEXT    DEFAULT 'Pendiente',
                cajero      TEXT,
                tipo_pago   TEXT,
                nota        TEXT,
                nota_interna TEXT   DEFAULT '',
                destino_usa TEXT    DEFAULT 'Sin asignar',
                listo_para_recoger INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS articulos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                envio_id    INTEGER NOT NULL REFERENCES envios(id) ON DELETE CASCADE,
                descripcion TEXT    NOT NULL,
                cantidad    INTEGER DEFAULT 1,
                peso_lb     REAL    DEFAULT 0,
                valor       REAL    DEFAULT 0,
                tipo        TEXT    DEFAULT 'producto'
            );

            CREATE TABLE IF NOT EXISTS pagos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                envio_id    INTEGER NOT NULL REFERENCES envios(id) ON DELETE CASCADE,
                fecha       TEXT    NOT NULL,
                monto       REAL    NOT NULL,
                moneda      TEXT    DEFAULT '$',
                tipo        TEXT,
                cajero      TEXT
            );

            CREATE TABLE IF NOT EXISTS costos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT    NOT NULL,
                categoria   TEXT,
                concepto    TEXT,
                monto       REAL    NOT NULL,
                moneda      TEXT    DEFAULT '$',
                nota        TEXT
            );

            CREATE TABLE IF NOT EXISTS arqueos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT    NOT NULL,
                apertura_dolares REAL DEFAULT 0,
                ingresos_dolares REAL DEFAULT 0,
                egresos_dolares  REAL DEFAULT 0,
                cierre_dolares   REAL DEFAULT 0,
                diferencia_dolares REAL DEFAULT 0,
                nota        TEXT,
                cerrado     INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario     TEXT    UNIQUE NOT NULL,
                password    TEXT    NOT NULL,
                nombre_completo TEXT DEFAULT '',
                rol         TEXT    DEFAULT 'cajero',
                activo      INTEGER DEFAULT 1,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );
        """)
        self.conn.commit()
        self._ensure_admin_user()

    def _init_indexes(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE INDEX IF NOT EXISTS idx_envios_fecha ON envios(fecha);
            CREATE INDEX IF NOT EXISTS idx_envios_estado ON envios(estado);
            CREATE INDEX IF NOT EXISTS idx_envios_codigo ON envios(codigo);
            CREATE INDEX IF NOT EXISTS idx_envios_destino ON envios(destino_usa);
            CREATE INDEX IF NOT EXISTS idx_envios_restante ON envios(restante);
            CREATE INDEX IF NOT EXISTS idx_envios_ent_nombre ON envios(ent_nombre);
            CREATE INDEX IF NOT EXISTS idx_envios_rec_nombre ON envios(rec_nombre);
            CREATE INDEX IF NOT EXISTS idx_articulos_envio ON articulos(envio_id);
            CREATE INDEX IF NOT EXISTS idx_pagos_envio ON pagos(envio_id);
            CREATE INDEX IF NOT EXISTS idx_costos_fecha ON costos(fecha);
            CREATE INDEX IF NOT EXISTS idx_costos_categoria ON costos(categoria);
            CREATE INDEX IF NOT EXISTS idx_arqueos_fecha ON arqueos(fecha);
        """)
        self.conn.commit()

    def _ensure_admin_user(self):
        """Crea usuario admin por defecto si no existe ninguno."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM usuarios")
        if cur.fetchone()[0] == 0:
            import hashlib
            salt = "encomienda_jireh_2024"
            pw_hash = hashlib.sha256(f"{salt}admin123".encode()).hexdigest()
            cur.execute(
                "INSERT INTO usuarios (usuario, password, nombre_completo, rol) VALUES (?, ?, ?, ?)",
                ("admin", pw_hash, "Administrador", "admin")
            )
            self.conn.commit()

    # ── Gestión de usuarios ──────────────────────────────────────────────────

    @staticmethod
    def _hash_password(password, salt="encomienda_jireh_2024"):
        import hashlib
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def login(self, usuario, password):
        """Verifica credenciales. Retorna dict del usuario o None."""
        cur = self.conn.cursor()
        pw_hash = self._hash_password(password)
        cur.execute(
            "SELECT id, usuario, nombre_completo, rol, activo FROM usuarios WHERE usuario = ? AND password = ?",
            (usuario, pw_hash)
        )
        row = cur.fetchone()
        if row and row["activo"]:
            return dict(row)
        return None

    def crear_usuario(self, usuario, password, nombre_completo="", rol="cajero"):
        """Crea un nuevo usuario. Retorna True si éxito, False si ya existe."""
        cur = self.conn.cursor()
        pw_hash = self._hash_password(password)
        try:
            cur.execute(
                "INSERT INTO usuarios (usuario, password, nombre_completo, rol) VALUES (?, ?, ?, ?)",
                (usuario, pw_hash, nombre_completo, rol)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def actualizar_usuario(self, usuario_id, password=None, nombre_completo=None, rol=None, activo=None):
        """Actualiza campos de un usuario."""
        cur = self.conn.cursor()
        campos = []
        valores = []
        if password is not None:
            campos.append("password = ?")
            valores.append(self._hash_password(password))
        if nombre_completo is not None:
            campos.append("nombre_completo = ?")
            valores.append(nombre_completo)
        if rol is not None:
            campos.append("rol = ?")
            valores.append(rol)
        if activo is not None:
            campos.append("activo = ?")
            valores.append(1 if activo else 0)
        if not campos:
            return False
        valores.append(usuario_id)
        cur.execute(f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?", valores)
        self.conn.commit()
        return True

    def eliminar_usuario(self, usuario_id):
        """Desactiva un usuario (no lo elimina físicamente)."""
        cur = self.conn.cursor()
        cur.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (usuario_id,))
        self.conn.commit()

    def obtener_usuarios(self):
        """Retorna lista de todos los usuarios activos."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, usuario, nombre_completo, rol, activo, created_at FROM usuarios ORDER BY usuario"
        )
        return [dict(r) for r in cur.fetchall()]

    def generar_codigo(self, prefijo="MERC"):
        now = datetime.now()
        return f"{prefijo}-{now.strftime('%d%m%y')}-{now.strftime('%H%M%S')}"

    def crear_envio(self, datos, articulos, prefijo="MERC"):
        cur = self.conn.cursor()
        codigo = self.generar_codigo(prefijo)
        fecha = datos.get("fecha", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Calcular peso_total sumando solo artículos de tipo producto (ignorar documentos)
        peso_total = 0.0
        for a in articulos:
            peso = float(a.get("peso_lb", 0) or 0)
            if peso > 0:
                try:
                    cant = int(a.get("cantidad", 1) or 1)
                    peso_total += cant * peso
                except (ValueError, TypeError):
                    pass

        cur.execute("""
            INSERT INTO envios (codigo, fecha, ent_nombre, ent_tel, ent_dir, rec_nombre, rec_tel, rec_dir,
                peso_total, subtotal, total, abono, restante, moneda, estado, cajero, tipo_pago, nota, nota_interna, destino_usa)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (codigo, fecha,
              datos.get("ent_nombre", ""), datos.get("ent_tel", ""), datos.get("ent_dir", ""),
              datos.get("rec_nombre", ""), datos.get("rec_tel", ""), datos.get("rec_dir", ""),
              peso_total, datos.get("subtotal", 0), datos.get("total", 0),
              datos.get("abono", 0), datos.get("restante", 0), datos.get("moneda", "$"),
              datos.get("estado", "Pendiente"), datos.get("cajero", ""),
              datos.get("tipo_pago", "Efectivo $"), datos.get("nota", ""),
              datos.get("nota_interna", ""), datos.get("destino_usa", "Sin asignar")))

        envio_id = cur.lastrowid

        for a in articulos:
            cur.execute("""
                INSERT INTO articulos (envio_id, descripcion, cantidad, peso_lb, valor, tipo)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (envio_id, a.get("descripcion", ""), a.get("cantidad", 1),
                  a.get("peso_lb", 0), a.get("valor", 0), a.get("tipo", "producto")))

        self.conn.commit()
        self.invalidate_client_cache()
        return envio_id

    def listar_envios(self, buscar="", estado="", mes="", fecha_desde="", fecha_hasta="", pagina=1, por_pagina=0):
        cur = self.conn.cursor()
        sql = """SELECT e.id, e.codigo, e.fecha, e.ent_nombre, e.ent_tel, e.rec_nombre, e.rec_tel,
                        e.destino_usa, COALESCE(e.peso_total, 0) as peso_total, e.total, e.abono, e.restante, e.moneda, e.estado,
                        e.cajero, e.tipo_pago, e.nota, e.nota_interna, e.listo_para_recoger, e.created_at
                 FROM envios e WHERE 1=1"""
        params = []

        if buscar:
            sql += " AND (e.codigo LIKE ? OR e.ent_nombre LIKE ? OR e.rec_nombre LIKE ?)"
            params.extend([f"%{buscar}%", f"%{buscar}%", f"%{buscar}%"])

        if estado:
            sql += " AND e.estado = ?"
            params.append(estado)

        if mes:
            sql += " AND strftime('%Y-%m', e.fecha) = ?"
            params.append(mes)

        if fecha_desde:
            sql += " AND e.fecha >= ?"
            params.append(fecha_desde)

        if fecha_hasta:
            sql += " AND e.fecha <= ?"
            params.append(fecha_hasta)

        sql += " ORDER BY e.fecha DESC, e.id DESC"

        if por_pagina > 0:
            offset = (pagina - 1) * por_pagina
            sql += " LIMIT ? OFFSET ?"
            params.extend([por_pagina, offset])

        cur.execute(sql, params)
        envios = [dict(row) for row in cur.fetchall()]
        return envios

    def obtener_envio(self, envio_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM envios WHERE id = ?", (envio_id,))
        row = cur.fetchone()
        if not row:
            return None

        env = dict(row)
        cur.execute("SELECT * FROM articulos WHERE envio_id = ?", (envio_id,))
        env["articulos"] = [dict(r) for r in cur.fetchall()]
        return env

    def actualizar_envio(self, envio_id, datos):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE envios SET ent_nombre=?, ent_tel=?, rec_nombre=?, rec_tel=?,
                destino_usa=?, peso_total=?, subtotal=?, total=?, abono=?, restante=?,
                estado=?, nota=? WHERE id=?
        """, (datos.get("ent_nombre"), datos.get("ent_tel"), datos.get("rec_nombre"),
              datos.get("rec_tel"), datos.get("destino_usa", datos.get("destino")), datos.get("peso_total"),
              datos.get("subtotal"), datos.get("total"), datos.get("abono"),
              datos.get("restante"), datos.get("estado"), datos.get("nota"), envio_id))

        if "articulos" in datos:
            cur.execute("DELETE FROM articulos WHERE envio_id = ?", (envio_id,))
            for a in datos["articulos"]:
                cur.execute("""
                    INSERT INTO articulos (envio_id, descripcion, cantidad, peso_lb, valor, tipo)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (envio_id, a.get("descripcion", ""), a.get("cantidad", 1),
                      a.get("peso_lb", 0), a.get("valor", 0), a.get("tipo", "producto")))

        self.conn.commit()

    def eliminar_envio(self, envio_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM envios WHERE id = ?", (envio_id,))
        self.conn.commit()

    def agregar_pago(self, envio_id, monto, tipo="Efectivo", cajero=""):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO pagos (envio_id, fecha, monto, moneda, tipo, cajero)
            VALUES (?, ?, ?, '$', ?, ?)
        """, (envio_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), monto, tipo, cajero))

        cur.execute("SELECT abono, total FROM envios WHERE id = ?", (envio_id,))
        row = cur.fetchone()
        if row:
            nuevo_abono = row["abono"] + monto
            restante = max(0, row["total"] - nuevo_abono)
            estado = "Pagado" if restante == 0 else "Pendiente"
            cur.execute("UPDATE envios SET abono=?, restante=?, estado=? WHERE id=?",
                       (nuevo_abono, restante, estado, envio_id))

        self.conn.commit()

    def total_facturado_hoy(self):
        cur = self.conn.cursor()
        hoy = datetime.now().strftime("%Y-%m-%d")
        cur.execute("SELECT COALESCE(SUM(total), 0) as total FROM envios WHERE fecha LIKE ?", (f"{hoy}%",))
        return cur.fetchone()["total"]

    def total_costos_hoy(self):
        cur = self.conn.cursor()
        hoy = datetime.now().strftime("%Y-%m-%d")
        cur.execute("SELECT COALESCE(SUM(monto), 0) as total FROM costos WHERE fecha LIKE ?", (f"{hoy}%",))
        return cur.fetchone()["total"]

    def agregar_costo(self, fecha, categoria, concepto, monto, moneda="$", nota=""):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO costos (fecha, categoria, concepto, monto, moneda, nota)
            VALUES (?, ?, ?, ?, '$', ?)
        """, (fecha, categoria, concepto, monto, nota))
        self.conn.commit()
        return cur.lastrowid

    def listar_costos(self, fdesde="", fhasta="", categoria=""):
        cur = self.conn.cursor()
        sql = "SELECT * FROM costos WHERE 1=1"
        params = []

        if fdesde:
            sql += " AND fecha >= ?"
            params.append(fdesde)
        if fhasta:
            sql += " AND fecha <= ?"
            params.append(fhasta)
        if categoria:
            sql += " AND categoria = ?"
            params.append(categoria)

        sql += " ORDER BY fecha DESC"
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def obtener_costo(self, costo_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM costos WHERE id = ?", (costo_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def actualizar_costo(self, costo_id, fecha, categoria, concepto, monto, nota):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE costos SET fecha=?, categoria=?, concepto=?, monto=?, nota=? WHERE id=?
        """, (fecha, categoria, concepto, monto, nota, costo_id))
        self.conn.commit()

    def eliminar_costo(self, costo_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM costos WHERE id = ?", (costo_id,))
        self.conn.commit()

    def total_costos(self, fdesde="", fhasta="", categoria=""):
        cur = self.conn.cursor()
        sql = "SELECT COALESCE(SUM(monto), 0) as total FROM costos WHERE 1=1"
        params = []
        if fdesde:
            sql += " AND fecha >= ?"
            params.append(fdesde)
        if fhasta:
            sql += " AND fecha <= ?"
            params.append(fhasta)
        if categoria:
            sql += " AND categoria = ?"
            params.append(categoria)
        cur.execute(sql, params)
        return {"total_dolares": cur.fetchone()["total"]}

    def crear_o_actualizar_arqueo(self, datos):
        cur = self.conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d")
        cur.execute("SELECT id FROM arqueos WHERE fecha LIKE ?", (f"{fecha}%",))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE arqueos SET apertura_dolares=?, ingresos_dolares=?, egresos_dolares=?,
                    cierre_dolares=?, diferencia_dolares=?, nota=?, cerrado=? WHERE id=?
            """, (datos.get("apertura_dolares", 0), datos.get("ingresos_dolares", 0),
                  datos.get("egresos_dolares", 0), datos.get("cierre_dolares", 0),
                  datos.get("diferencia_dolares", 0), datos.get("nota", ""),
                  1 if datos.get("cerrado") else 0, existing["id"]))
        else:
            cur.execute("""
                INSERT INTO arqueos (fecha, apertura_dolares, ingresos_dolares, egresos_dolares,
                    cierre_dolares, diferencia_dolares, nota, cerrado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (fecha, datos.get("apertura_dolares", 0), datos.get("ingresos_dolares", 0),
                  datos.get("egresos_dolares", 0), datos.get("cierre_dolares", 0),
                  datos.get("diferencia_dolares", 0), datos.get("nota", ""),
                  1 if datos.get("cerrado") else 0))

        self.conn.commit()

    def obtener_arqueo_hoy(self):
        cur = self.conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d")
        cur.execute("SELECT * FROM arqueos WHERE fecha LIKE ?", (f"{fecha}%",))
        row = cur.fetchone()
        return dict(row) if row else None

    def listar_arqueos(self, por_pagina=30):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM arqueos ORDER BY fecha DESC LIMIT ?", (por_pagina,))
        return [dict(row) for row in cur.fetchall()]

    def stats_resumen(self, fecha_desde="", fecha_hasta=""):
        cur = self.conn.cursor()
        where = ""
        params = []

        if fecha_desde and fecha_hasta:
            where = "WHERE fecha BETWEEN ? AND ?"
            params = [fecha_desde, fecha_hasta]

        cur.execute(f"SELECT COUNT(*) as total, COALESCE(SUM(total), 0) as facturado, COALESCE(SUM(abono), 0) as cobrado FROM envios {where}", params)
        r = cur.fetchone()

        cur.execute(f"SELECT COALESCE(SUM(monto), 0) as total FROM costos {where}", params)
        c = cur.fetchone()

        cur.execute(f"SELECT COALESCE(SUM(peso_total), 0) as peso FROM envios {where}", params)
        p = cur.fetchone()

        return {
            "envios": r["total"],
            "facturado": r["facturado"],
            "cobrado": r["cobrado"],
            "pendiente": r["facturado"] - r["cobrado"],
            "costos": c["total"],
            "peso_total": p["peso"]
        }

    def envios_por_estado(self):
        cur = self.conn.cursor()
        cur.execute("SELECT estado, COUNT(*) as cantidad, COALESCE(SUM(total), 0) as monto FROM envios GROUP BY estado")
        return [dict(row) for row in cur.fetchall()]

    def envios_por_destino(self):
        cur = self.conn.cursor()
        cur.execute("SELECT destino_usa as destino, COUNT(*) as cantidad, SUM(total) as total FROM envios WHERE destino_usa IS NOT NULL AND destino_usa != '' GROUP BY destino_usa")
        return [dict(row) for row in cur.fetchall()]

    def resumen_general(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as total, COALESCE(SUM(total), 0) as facturado, COALESCE(SUM(abono), 0) as cobrado FROM envios")
        r = cur.fetchone()
        return {
            "total_envios": r["total"],
            "total_facturado": r["facturado"],
            "total_cobrado": r["cobrado"],
            "total_pendiente": r["facturado"] - r["cobrado"]
        }

    def envios_por_mes(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', fecha) as mes, COUNT(*) as cantidad, SUM(total) as monto
            FROM envios GROUP BY mes ORDER BY mes DESC LIMIT 12
        """)
        return [dict(row) for row in cur.fetchall()]

    def obtener_deudas_vencidas(self, dias=7):
        cur = self.conn.cursor()
        limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        cur.execute("""
            SELECT * FROM envios WHERE restante > 0 AND fecha < ? AND estado != 'Cancelado'
            ORDER BY fecha ASC
        """, (limite,))
        return [dict(row) for row in cur.fetchall()]

    def contar_deudas_vencidas(self, dias=7):
        cur = self.conn.cursor()
        limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        cur.execute("SELECT COUNT(*) as c FROM envios WHERE restante > 0 AND fecha < ? AND estado != 'Cancelado'", (limite,))
        return cur.fetchone()["c"]

    def resumen_hoy(self):
        cur = self.conn.cursor()
        hoy = datetime.now().strftime("%Y-%m-%d")
        cur.execute("SELECT COUNT(*) as cantidad, COALESCE(SUM(total), 0) as monto FROM envios WHERE fecha LIKE ?", (f"{hoy}%",))
        return dict(cur.fetchone())

    def resumen_mes(self):
        cur = self.conn.cursor()
        mes = datetime.now().strftime("%Y-%m")
        cur.execute("SELECT COUNT(*) as cantidad, COALESCE(SUM(total), 0) as monto FROM envios WHERE strftime('%Y-%m', fecha) = ?", (mes,))
        return dict(cur.fetchone())

    def obtener_clientes_con_deuda(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT ent_nombre, SUM(restante) as total_deuda, COUNT(*) as cantidad_deudas,
                   MIN(fecha) as deuda_desde
            FROM envios WHERE restante > 0 GROUP BY ent_nombre ORDER BY total_deuda DESC
        """)
        return [dict(row) for row in cur.fetchall()]

    def listar_clientes(self, term="", rol="remitente"):
        import time
        now = time.time()
        cache_key = f"{rol}"
        if cache_key not in self._client_cache or (now - self._client_cache_time) > 30:
            cur = self.conn.cursor()
            if rol == "remitente":
                cur.execute("SELECT DISTINCT ent_nombre as nombre, ent_tel as tel FROM envios WHERE ent_nombre != '' ORDER BY ent_nombre")
            else:
                cur.execute("SELECT DISTINCT rec_nombre as nombre, rec_tel as tel FROM envios WHERE rec_nombre != '' ORDER BY rec_nombre")
            self._client_cache[cache_key] = [dict(row) for row in cur.fetchall()]
            self._client_cache_time = now

        clientes = self._client_cache[cache_key]
        if term:
            term_lower = term.lower()
            clientes = [c for c in clientes if term_lower in c["nombre"].lower()]
        return clientes

    def invalidate_client_cache(self):
        self._client_cache.clear()
        self._client_cache_time = 0

    def obtener_articulos(self, envio_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM articulos WHERE envio_id = ?", (envio_id,))
        return [dict(row) for row in cur.fetchall()]

    def obtener_pagos(self, envio_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM pagos WHERE envio_id = ? ORDER BY fecha DESC", (envio_id,))
        return [dict(row) for row in cur.fetchall()]

    def exportar_csv(self, ruta, buscar="", estado="", mes="", fecha_desde="", fecha_hasta=""):
        import csv
        cur = self.conn.cursor()
        sql = """SELECT codigo, fecha, ent_nombre, ent_tel, rec_nombre, rec_tel, destino_usa,
                        peso_total, total, abono, restante, moneda, estado
                 FROM envios WHERE 1=1"""
        params = []
        if buscar:
            sql += " AND (codigo LIKE ? OR ent_nombre LIKE ? OR rec_nombre LIKE ?)"
            params.extend([f"%{buscar}%", f"%{buscar}%", f"%{buscar}%"])
        if estado:
            sql += " AND estado = ?"
            params.append(estado)
        if mes:
            sql += " AND strftime('%Y-%m', fecha) = ?"
            params.append(mes)
        if fecha_desde:
            sql += " AND fecha >= ?"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND fecha <= ?"
            params.append(fecha_hasta)
        sql += " ORDER BY fecha DESC"

        cur.execute(sql, params)
        fieldnames = ["codigo", "fecha", "ent_nombre", "ent_tel", "rec_nombre", "rec_tel",
                      "destino_usa", "peso_total", "total", "abono", "restante", "moneda", "estado"]
        with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            while True:
                rows = cur.fetchmany(500)
                if not rows:
                    break
                for row in rows:
                    w.writerow(dict(row))
        return True

    def contar_envios(self, buscar="", estado="", mes="", fecha_desde="", fecha_hasta=""):
        cur = self.conn.cursor()
        sql = "SELECT COUNT(*) as total FROM envios WHERE 1=1"
        params = []
        if buscar:
            sql += " AND (codigo LIKE ? OR ent_nombre LIKE ? OR rec_nombre LIKE ?)"
            params.extend([f"%{buscar}%", f"%{buscar}%", f"%{buscar}%"])
        if estado:
            sql += " AND estado = ?"
            params.append(estado)
        if mes:
            sql += " AND strftime('%Y-%m', fecha) = ?"
            params.append(mes)
        if fecha_desde:
            sql += " AND fecha >= ?"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND fecha <= ?"
            params.append(fecha_hasta)
        cur.execute(sql, params)
        return cur.fetchone()["total"]

    def cancelar_envio(self, envio_id):
        cur = self.conn.cursor()
        cur.execute("UPDATE envios SET estado='Cancelado' WHERE id=?", (envio_id,))
        self.conn.commit()

    def marcar_listo_para_recoger(self, envio_id, marcar=True):
        cur = self.conn.cursor()
        cur.execute("UPDATE envios SET listo_para_recoger=? WHERE id=?", (1 if marcar else 0, envio_id))
        self.conn.commit()

    def resumen_kpi(self):
        cur = self.conn.cursor()
        hoy = datetime.now().strftime("%Y-%m-%d")
        mes_actual = datetime.now().strftime("%Y-%m")

        # Hoy
        cur.execute("SELECT COUNT(*) as c, COALESCE(SUM(total), 0) as m FROM envios WHERE fecha LIKE ?", (f"{hoy}%",))
        r = cur.fetchone()

        # Este mes
        cur.execute("SELECT COUNT(*) as c, COALESCE(SUM(total), 0) as m FROM envios WHERE strftime('%Y-%m', fecha) = ?", (mes_actual,))
        m = cur.fetchone()

        # Listos para recoger
        cur.execute("SELECT COUNT(*) as c FROM envios WHERE listo_para_recoger = 1 AND estado != 'Pagado'")
        listos = cur.fetchone()["c"]

        # Deudores
        cur.execute("SELECT COUNT(*) as c, COALESCE(SUM(restante), 0) as total FROM envios WHERE restante > 0")
        d = cur.fetchone()

        return {
            "envios_hoy": r["c"],
            "monto_hoy": r["m"],
            "envios_mes": m["c"],
            "monto_mes": m["m"],
            "listos": listos,
            "deudores": d["c"],
            "total_deuda": d["total"]
        }

    def top_clientes(self, limite=10):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT ent_nombre as ent_nombre, COUNT(*) as envios,
                SUM(total) as total_facturado,
                SUM(abono) as total_pagado,
                SUM(restante) as total_deuda
            FROM envios GROUP BY ent_nombre ORDER BY total_facturado DESC LIMIT ?
        """, (limite,))
        return [dict(row) for row in cur.fetchall()]

    def tendencia_mensual(self, meses=12):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', fecha) as mes, COUNT(*) as cantidad, SUM(total) as monto
            FROM envios GROUP BY mes ORDER BY mes DESC LIMIT ?
        """, (meses,))
        return [dict(row) for row in cur.fetchall()]

    def obtener_tasa_cambio(self):
        return 1.0

    def registrar_pago(self, envio_id, monto, tipo_pago, cajero):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO pagos (envio_id, fecha, monto, moneda, tipo, cajero)
            VALUES (?, ?, ?, '$', ?, ?)
        """, (envio_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), monto, tipo_pago, cajero))

        cur.execute("SELECT abono, total FROM envios WHERE id = ?", (envio_id,))
        row = cur.fetchone()
        if row:
            nuevo_abono = row["abono"] + monto
            restante = max(0, row["total"] - nuevo_abono)
            estado = "Pagado" if restante == 0 else "Pendiente"
            cur.execute("UPDATE envios SET abono=?, restante=?, estado=? WHERE id=?",
                       (nuevo_abono, restante, estado, envio_id))
        self.conn.commit()

    def backup_db(self, backup_dir=None):
        """Crea un respaldo de la base de datos y retorna la ruta del archivo."""
        import shutil
        from modules.config import BACKUP_DIR, BACKUP_MAX
        if backup_dir is None:
            backup_dir = os.path.join(get_base_dir(), BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"backup_{timestamp}.db"
        ruta_backup = os.path.join(backup_dir, nombre)
        shutil.copy2(self.ruta, ruta_backup)
        # Limpiar respaldos antiguos
        try:
            archivos = sorted(
                [f for f in os.listdir(backup_dir) if f.endswith(".db")],
                reverse=True
            )
            for arch in archivos[BACKUP_MAX:]:
                os.remove(os.path.join(backup_dir, arch))
        except Exception:
            pass
        return ruta_backup

    def restore_db(self, ruta_backup):
        """Restaura la base de datos desde un respaldo y recalcula pesos."""
        import shutil
        if not os.path.exists(ruta_backup):
            raise FileNotFoundError(f"No se encontro el archivo: {ruta_backup}")
        # Cerrar conexion actual
        self.conn.close()
        # Copiar el respaldo sobre la base actual
        shutil.copy2(ruta_backup, self.ruta)
        # Reconectar
        self.conn = sqlite3.connect(self.ruta, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._apply_pragmas()
        # Recalcular pesos de todos los envios
        self.recalcular_pesos()
        return True

    def recalcular_pesos(self):
        """Recalcula el peso_total de todos los envios basado en sus articulos."""
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM envios")
        envios = cur.fetchall()
        for env in envios:
            envio_id = env["id"]
            cur.execute("SELECT peso_lb, cantidad FROM articulos WHERE envio_id = ?", (envio_id,))
            articulos = cur.fetchall()
            peso_total = 0.0
            for a in articulos:
                peso = float(a["peso_lb"] or 0)
                cant = int(a["cantidad"] or 1)
                if peso > 0:
                    peso_total += cant * peso
            cur.execute("UPDATE envios SET peso_total = ? WHERE id = ?", (peso_total, envio_id))
        self.conn.commit()
        return len(envios)

    def close(self):
        self._client_cache.clear()
        self.conn.close()

    # ── Historial mensual ────────────────────────────────────────────────────

    def obtener_resumen_mensual(self):
        """Retorna lista de dicts con resumen por mes (anio, mes, envios, totales)."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT
                CAST(strftime('%Y', fecha) AS INTEGER) AS anio,
                CAST(strftime('%m', fecha) AS INTEGER) AS mes,
                COUNT(*) AS envios,
                SUM(total) AS total_vendido,
                SUM(abono) AS total_pagado,
                SUM(restante) AS pendiente
            FROM envios
            WHERE estado != 'Cancelado'
            GROUP BY anio, mes
            ORDER BY anio DESC, mes DESC
        """)
        return [dict(r) for r in cur.fetchall()]

    def obtener_envios_por_mes(self, anio, mes):
        """Retorna lista de envios de un mes específico."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT *
            FROM envios
            WHERE CAST(strftime('%Y', fecha) AS INTEGER) = ?
              AND CAST(strftime('%m', fecha) AS INTEGER) = ?
            ORDER BY fecha DESC
        """, (anio, mes))
        return [dict(r) for r in cur.fetchall()]

    # ── Historial de clientes ────────────────────────────────────────────────

    def obtener_clientes(self, buscar="", telefono=""):
        """Retorna lista de clientes únicos (remitentes) con resumen."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT
                ent_nombre AS nombre,
                ent_tel AS telefono,
                COUNT(*) AS envios,
                SUM(total) AS total_gastado,
                MAX(fecha) AS ultimo_envio
            FROM envios
            WHERE ent_nombre IS NOT NULL AND ent_nombre != ''
            GROUP BY ent_nombre
            ORDER BY ent_nombre
        """)
        clientes = [dict(r) for r in cur.fetchall()]

        if buscar:
            buscar_lower = buscar.lower()
            clientes = [c for c in clientes
                        if buscar_lower in (c.get("nombre") or "").lower()]

        if telefono:
            tel_lower = telefono.lower()
            clientes = [c for c in clientes
                        if tel_lower in (c.get("telefono") or "").lower()]

        return clientes

    def obtener_envios_por_cliente(self, nombre):
        """Retorna todos los envios de un cliente específico."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT *
            FROM envios
            WHERE ent_nombre = ?
            ORDER BY fecha DESC
        """, (nombre,))
        return [dict(r) for r in cur.fetchall()]