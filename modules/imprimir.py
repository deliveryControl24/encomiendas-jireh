"""
==============================================
  modules/imprimir.py
  Generacion de PDFs para:
    - Recibo de encomienda (cliente)
    - Detalle del historial
    - Reporte del dia / general
    - Recibo térmico (80mm)
    - Cotización / Presupuesto
    - Arqueo de Caja
    - Cuentas por Cobrar
    - Factura / IVA
    - Calendario Mensual
==============================================
  Requiere: pip install reportlab
  Opcional: pip install qrcode[pil]
==============================================
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas as rl_canvas

try:
    import qrcode
    QR_DISPONIBLE = True
except ImportError:
    QR_DISPONIBLE = False

try:
    from modules.config import get_base_dir
except ImportError:
    def get_base_dir():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(get_base_dir(), "encomiendas.db")

# ── Datos de la empresa ───────────────────────────────────────────────────────
EMPRESA_NOMBRE   = "Encomienda Jireh"
EMPRESA_SLOGAN   = "Envíos rápidos y seguros"
EMPRESA_TELEFONO = ""   # Ej: "+505 8888-8888"
EMPRESA_EMAIL    = ""   # Ej: "info@encomiendas.com"
EMPRESA_WEB      = ""   # Ej: "www.encomiendas.com"

# ── Paleta de colores del sistema ─────────────────────────────────────────────
VERDE       = colors.HexColor("#0f6e56")
VERDE_DARK  = colors.HexColor("#085041")
VERDE_LIGHT = colors.HexColor("#e1f5ee")
GRIS_LIGHT  = colors.HexColor("#f1efe8")
GRIS_TEXT   = colors.HexColor("#888780")
GRIS_DARK   = colors.HexColor("#2c2c2a")
AZUL        = colors.HexColor("#0c447c")
AZUL_LIGHT  = colors.HexColor("#e6f1fb")
NARANJA     = colors.HexColor("#633806")
NARANJA_LIGHT = colors.HexColor("#faeeda")
ROJO        = colors.HexColor("#791f1f")
ROJO_LIGHT  = colors.HexColor("#fcebeb")
MORADO      = colors.HexColor("#6b2fa0")
MORADO_LIGHT = colors.HexColor("#f0e6f9")
BLANCO      = colors.white

try:
    from modules.config import PRECIO_LB
except ImportError:
    PRECIO_LB = 10

ESTADO_COLORES = {
    "Pagado":    (VERDE_LIGHT,  VERDE_DARK),
    "Abono":     (AZUL_LIGHT,   AZUL),
    "Pendiente": (NARANJA_LIGHT, NARANJA),
    "Cancelado": (ROJO_LIGHT,   ROJO),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _abrir_pdf(ruta):
    """Abre el PDF con el visor predeterminado del sistema."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except Exception as e:
        print(f"No se pudo abrir el PDF automáticamente: {e}")


def _carpeta_salida():
    """Devuelve (y crea si no existe) la carpeta 'recibos' junto al script."""
    base = get_base_dir()
    carpeta = os.path.join(base, "recibos")
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def _estilos():
    """Retorna un dict con estilos reutilizables."""
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"],
            fontSize=18, textColor=VERDE, spaceAfter=2,
            fontName="Helvetica-Bold"),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"],
            fontSize=9, textColor=GRIS_TEXT, spaceAfter=6,
            fontName="Helvetica"),
        "seccion": ParagraphStyle(
            "seccion", parent=base["Normal"],
            fontSize=8, textColor=GRIS_TEXT, spaceBefore=10, spaceAfter=4,
            fontName="Helvetica-Bold"),
        "seccion_verde": ParagraphStyle(
            "seccion_verde", parent=base["Normal"],
            fontSize=8, textColor=VERDE_DARK, spaceBefore=8, spaceAfter=3,
            fontName="Helvetica-Bold"),
        "normal": ParagraphStyle(
            "normal", parent=base["Normal"],
            fontSize=10, textColor=GRIS_DARK,
            fontName="Helvetica"),
        "normal_small": ParagraphStyle(
            "normal_small", parent=base["Normal"],
            fontSize=8.5, textColor=GRIS_DARK,
            fontName="Helvetica"),
        "bold": ParagraphStyle(
            "bold", parent=base["Normal"],
            fontSize=10, textColor=GRIS_DARK,
            fontName="Helvetica-Bold"),
        "bold_verde": ParagraphStyle(
            "bold_verde", parent=base["Normal"],
            fontSize=10, textColor=VERDE_DARK,
            fontName="Helvetica-Bold"),
        "centro": ParagraphStyle(
            "centro", parent=base["Normal"],
            fontSize=9, alignment=TA_CENTER,
            textColor=GRIS_TEXT, fontName="Helvetica"),
        "codigo": ParagraphStyle(
            "codigo", parent=base["Normal"],
            fontSize=22, textColor=VERDE_DARK,
            fontName="Helvetica-Bold", spaceAfter=4),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"],
            fontSize=8, alignment=TA_CENTER,
            textColor=GRIS_TEXT, fontName="Helvetica"),
        "etiqueta": ParagraphStyle(
            "etiqueta", parent=base["Normal"],
            fontSize=7.5, textColor=GRIS_TEXT,
            fontName="Helvetica-Bold"),
        "valor": ParagraphStyle(
            "valor", parent=base["Normal"],
            fontSize=10, textColor=GRIS_DARK,
            fontName="Helvetica"),
        "monto_total": ParagraphStyle(
            "monto_total", parent=base["Normal"],
            fontSize=13, textColor=VERDE_DARK,
            fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "monto_rojo": ParagraphStyle(
            "monto_rojo", parent=base["Normal"],
            fontSize=13, textColor=ROJO,
            fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "tag_producto": ParagraphStyle(
            "tag_producto", parent=base["Normal"],
            fontSize=8, textColor=AZUL,
            fontName="Helvetica-Bold", alignment=TA_CENTER),
        "tag_documento": ParagraphStyle(
            "tag_documento", parent=base["Normal"],
            fontSize=8, textColor=NARANJA,
            fontName="Helvetica-Bold", alignment=TA_CENTER),
    }


def _tabla_info(pares, col_w=None):
    """
    Genera una tabla de dos columnas (etiqueta: valor).
    pares = [(label, valor), ...]
    """
    col_w = col_w or [5*cm, 10*cm]
    estilos = _estilos()
    data = [
        [Paragraph(f"<b>{lbl}</b>", estilos["normal"]),
         Paragraph(str(val), estilos["normal"])]
        for lbl, val in pares
    ]
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _encabezado_empresa(st, ancho_util, codigo=None, estado=None, fecha=None):
    """
    Genera el bloque de encabezado con nombre, slogan, datos de contacto
    y opcionalmente código, estado y fecha a la derecha.
    Retorna una lista de elementos para agregar al story.
    """
    elementos = []

    # Construir líneas de contacto
    contacto_parts = []
    if EMPRESA_TELEFONO:
        contacto_parts.append(f"📞 {EMPRESA_TELEFONO}")
    if EMPRESA_EMAIL:
        contacto_parts.append(f"✉ {EMPRESA_EMAIL}")
    if EMPRESA_WEB:
        contacto_parts.append(f"🌐 {EMPRESA_WEB}")
    contacto_str = "  ·  ".join(contacto_parts) if contacto_parts else ""

    # Columna izquierda: nombre y slogan
    col_izq = [
        Paragraph(f"📦 {EMPRESA_NOMBRE}", st["titulo"]),
        Paragraph(EMPRESA_SLOGAN, st["subtitulo"]),
    ]
    if contacto_str:
        col_izq.append(Paragraph(contacto_str,
                                  ParagraphStyle("ct", fontName="Helvetica",
                                                 fontSize=8, textColor=GRIS_TEXT)))

    izq_cell = [e for e in col_izq]

    if codigo and estado and fecha:
        est_bg, est_fg = ESTADO_COLORES.get(estado, (GRIS_LIGHT, GRIS_DARK))
        der_cell = [
            Paragraph(codigo,
                       ParagraphStyle("cod", fontName="Helvetica-Bold",
                                      fontSize=20, textColor=VERDE_DARK,
                                      alignment=TA_RIGHT)),
            Paragraph(f'<font color="#{est_fg.hexval()[2:]}"><b> {estado} </b></font>',
                       ParagraphStyle("est", fontName="Helvetica-Bold", fontSize=10,
                                      backColor=est_bg, borderPadding=4,
                                      alignment=TA_RIGHT)),
            Paragraph(fecha,
                       ParagraphStyle("fch", fontName="Helvetica", fontSize=9,
                                      textColor=GRIS_TEXT, alignment=TA_RIGHT)),
        ]
        hdr_data = [[izq_cell, der_cell]]
        hdr_t = Table(hdr_data, colWidths=[ancho_util * 0.58, ancho_util * 0.42])
        hdr_t.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        elementos.append(hdr_t)
    else:
        for e in col_izq:
            elementos.append(e)

    elementos.append(HRFlowable(width="100%", thickness=2, color=VERDE, spaceAfter=10))
    return elementos


def _badge_tipo(tipo_txt, st):
    """Retorna un Paragraph con estilo de badge para Producto, Documento o Medicamento."""
    if tipo_txt == "Medicamento":
        return Paragraph(
            f'<font color="#{MORADO.hexval()[2:]}">💊 Med.</font>',
            ParagraphStyle("bm", fontName="Helvetica-Bold", fontSize=8,
                           backColor=MORADO_LIGHT, borderPadding=3, alignment=TA_CENTER))
    elif tipo_txt == "Producto":
        return Paragraph(
            f'<font color="#{AZUL.hexval()[2:]}">⬜ Producto</font>',
            ParagraphStyle("bp", fontName="Helvetica-Bold", fontSize=8,
                           backColor=AZUL_LIGHT, borderPadding=3, alignment=TA_CENTER))
    else:
        return Paragraph(
            f'<font color="#{NARANJA.hexval()[2:]}">📄 Doc.</font>',
            ParagraphStyle("bd", fontName="Helvetica-Bold", fontSize=8,
                           backColor=NARANJA_LIGHT, borderPadding=3, alignment=TA_CENTER))


# ══════════════════════════════════════════════════════════════════════════════
#  1. RECIBO DE ENCOMIENDA
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_recibo(db, envio_id, abrir=True):
    """
    Genera el recibo PDF de una encomienda y lo abre automáticamente.

    db        : instancia de Database
    envio_id  : int
    abrir     : bool - si True abre el PDF tras generarlo
    Retorna   : ruta del archivo generado
    """
    env  = db.obtener_envio(envio_id)
    arts = db.obtener_articulos(envio_id)
    pags = db.obtener_pagos(envio_id)

    if not env:
        raise ValueError(f"No se encontró el envío con id={envio_id}")

    nombre_archivo = f"recibo_{env['codigo']}.pdf"
    ruta = os.path.join(_carpeta_salida(), nombre_archivo)

    doc = SimpleDocTemplate(
        ruta, pagesize=A4,
        leftMargin=1.2*cm, rightMargin=1.2*cm,
        topMargin=1*cm, bottomMargin=1*cm,
        title=f"Recibo {env['codigo']}",
        author=EMPRESA_NOMBRE
    )

    # Obtener diseño seleccionado desde configuración
    try:
        from modules.configuracion import ConfigManager
        config = ConfigManager()
        diseno = config.get("recibo_diseno", "clasico")
    except:
        diseno = "clasico"

    st         = _estilos_diseno(diseno)
    mon        = env.get("moneda", "$")
    ancho_util = A4[0] - 2.4*cm
    story      = []

    # ── Encabezado según diseño ────────────────────────────────────────────────
    story += _encabezado_diseno(st, ancho_util, diseno)

    story.append(HRFlowable(width="100%", thickness=2, color=VERDE, spaceAfter=6))

    # ── Código + Estado + Fecha ───────────────────────────────────────────────
    est_bg, est_fg = ESTADO_COLORES.get(env["estado"], (GRIS_LIGHT, GRIS_DARK))
    estado_p = Paragraph(
        f'<font color="#{est_fg.hexval()[2:]}"><b>  {env["estado"]}  </b></font>',
        ParagraphStyle("e", fontName="Helvetica-Bold", fontSize=11,
                       backColor=est_bg, borderPadding=5))

    hdr_data = [[
        Paragraph(env["codigo"], st["codigo"]),
        estado_p,
        Paragraph(env["fecha"],
                  ParagraphStyle("f", fontName="Helvetica", fontSize=9,
                                 textColor=GRIS_TEXT, alignment=TA_RIGHT))
    ]]
    hdr_t = Table(hdr_data, colWidths=[7*cm, 4*cm, None])
    hdr_t.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(hdr_t)
    story.append(Spacer(1, 6))

    # ── Remitente + Destinatario ──────────────────────────────────────────────
    def _celda_persona(titulo, nombre, tel, dir_):
        """Genera el contenido de celda para remitente o destinatario."""
        items = [Paragraph(titulo, st["seccion_verde"])]
        items.append(Paragraph(f"<b>{nombre or '—'}</b>", st["bold"]))
        if tel:
            items.append(Paragraph(f"📞 {tel}", st["normal_small"]))
        if dir_:
            items.append(Paragraph(f"📍 {dir_}", st["normal_small"]))
        return items

    personas_data = [[
        _celda_persona("QUIEN ENTREGA",
                       env.get("ent_nombre"), env.get("ent_tel"), env.get("ent_dir")),
        _celda_persona("QUIEN RECIBE",
                       env.get("rec_nombre"), env.get("rec_tel"), env.get("rec_dir")),
    ]]
    personas_t = Table(personas_data, colWidths=[ancho_util / 2, ancho_util / 2])
    personas_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), VERDE_LIGHT),
        ("BACKGROUND",    (1, 0), (1, -1), AZUL_LIGHT),
        ("BOX",           (0, 0), (0, -1), 0.5, VERDE),
        ("BOX",           (1, 0), (1, -1), 0.5, AZUL),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(personas_t)

    # ── Destino USA ───────────────────────────────────────────────────────────
    destino = env.get("destino_usa", "")
    if destino and destino != "Sin asignar":
        story.append(Spacer(1, 4))
        dest_t = Table(
            [[Paragraph(f"🗺️  <b>Destino USA:</b>  {destino}", st["normal"])]],
            colWidths=[ancho_util]
        )
        dest_t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), VERDE_LIGHT),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BOX",           (0, 0), (-1, -1), 1, VERDE),
        ]))
        story.append(dest_t)

    story.append(Spacer(1, 8))

    # ── Artículos — tablas separadas por tipo (igual que la UI) ──────────────

    # Paleta por tipo
    R_PESO_HDR   = colors.HexColor("#4a2000")
    R_PESO_COLS  = colors.HexColor("#6b3a0f")
    R_PESO_FILA2 = colors.HexColor("#fff3e6")
    R_PESO_FG    = colors.HexColor("#633806")
    R_MED_HDR    = colors.HexColor("#6b2fa0")
    R_MED_COLS   = colors.HexColor("#8e44c4")
    R_MED_FILA2  = colors.HexColor("#f8f2fd")
    R_MED_FG     = colors.HexColor("#6b2fa0")
    R_DOC_HDR    = colors.HexColor("#791f1f")
    R_DOC_COLS   = colors.HexColor("#9e2a2a")
    R_DOC_FILA2  = colors.HexColor("#fff3f3")
    R_DOC_FG     = colors.HexColor("#791f1f")
    AW = ancho_util

    def _rbg(i, c2): return BLANCO if i % 2 == 1 else c2
    def _rimp(val, fg):
        return Paragraph(f"<b>{mon}{val:,.2f}</b>",
            ParagraphStyle("ri",fontName="Helvetica-Bold",fontSize=9,
                           alignment=TA_RIGHT,textColor=fg))

    def _sec_hdr(txt, hdr_color, txt_color):
        t = Table([[Paragraph(txt, ParagraphStyle("sh",fontName="Helvetica-Bold",
                    fontSize=9,textColor=txt_color))]], colWidths=[AW])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),hdr_color),
            ("LEFTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4)]))
        return t

    def _col_hdr(cols, widths, bg):
        cells = [Paragraph(f"<b>{c}</b>",ParagraphStyle("ch",fontName="Helvetica-Bold",
                    fontSize=8,textColor=colors.white,
                    alignment=TA_RIGHT if c=="Importe" else TA_CENTER if c in ("#","Cant.","Precio unit.","Peso (lb)") else TA_LEFT))
                 for c in cols]
        t = Table([cells], colWidths=widths)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),
            ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        return t

    # Separar por tipo
    items_peso = [a for a in arts if (a.get("tipo") or "").lower() not in ("medicamento","documento") and float(a.get("peso_lb",0) or 0) > 0]
    items_med  = [a for a in arts if (a.get("tipo") or "").lower() == "medicamento"]
    items_doc  = [a for a in arts if (a.get("tipo") or "").lower() == "documento" or
                  ((a.get("tipo") or "").lower() not in ("medicamento",) and
                   float(a.get("peso_lb",0) or 0) == 0 and float(a.get("valor",0) or 0) > 0)]

    total_peso   = 0.0
    total_valor  = 0.0
    importe_calc = 0.0
    w_num, w_desc_p, w_peso_col, w_imp = 1*cm, AW-1*cm-2.5*cm-2.8*cm, 2.5*cm, 2.8*cm
    w_desc_m = AW-1*cm-1.8*cm-2.2*cm-2.8*cm

    # ── 1. POR PESO ───────────────────────────────────────────────────────────
    if items_peso:
        story.append(_sec_hdr("⚖️  ENVÍOS POR PESO", R_PESO_HDR, colors.HexColor("#f5c97a")))
        story.append(_col_hdr(["#","Descripción","Peso (lb)","Importe"],
                               [w_num, w_desc_p, w_peso_col, w_imp], R_PESO_COLS))
        for i, a in enumerate(items_peso, 1):
            peso = float(a.get("peso_lb",0) or 0)
            cant = int(a.get("cantidad",1) or 1)
            imp  = cant * peso * PRECIO_LB
            importe_calc += imp; total_peso += cant * peso
            bg = _rbg(i, R_PESO_FILA2)
            row = Table([[
                Paragraph(str(i),ParagraphStyle("",fontName="Helvetica",fontSize=9,alignment=TA_CENTER,textColor=GRIS_TEXT)),
                Paragraph(a["descripcion"],ParagraphStyle("",fontName="Helvetica",fontSize=9,textColor=colors.HexColor("#1a1a1a"))),
                Paragraph(f"{peso:.1f} lb",ParagraphStyle("",fontName="Helvetica",fontSize=9,alignment=TA_CENTER,textColor=colors.HexColor("#4a2000"))),
                _rimp(imp, R_PESO_FG),
            ]], colWidths=[w_num, w_desc_p, w_peso_col, w_imp])
            row.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),
                ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
                ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("LINEBELOW",(0,0),(-1,-1),0.3,colors.HexColor("#e8d5b0"))]))
            story.append(row)
        story.append(Spacer(1, 4))

    # ── 2. MEDICAMENTOS ───────────────────────────────────────────────────────
    if items_med:
        story.append(_sec_hdr("💊  MEDICAMENTOS", R_MED_HDR, colors.HexColor("#e8d5f5")))
        story.append(_col_hdr(["#","Medicamento","Cant.","Precio unit.","Importe"],
                               [w_num, w_desc_m, 1.8*cm, 2.2*cm, w_imp], R_MED_COLS))
        for i, a in enumerate(items_med, 1):
            valor = float(a.get("valor",0) or 0)
            cant  = int(a.get("cantidad",1) or 1)
            imp   = cant * valor
            importe_calc += imp; total_valor += imp
            bg = _rbg(i, R_MED_FILA2)
            row = Table([[
                Paragraph(str(i),ParagraphStyle("",fontName="Helvetica",fontSize=9,alignment=TA_CENTER,textColor=GRIS_TEXT)),
                Paragraph(a["descripcion"],ParagraphStyle("",fontName="Helvetica",fontSize=9,textColor=colors.HexColor("#2c1a40"))),
                Paragraph(f"×{cant}",ParagraphStyle("",fontName="Helvetica-Bold",fontSize=9,alignment=TA_CENTER,textColor=R_MED_FG)),
                Paragraph(f"{mon}{valor:.0f}",ParagraphStyle("",fontName="Helvetica-Bold",fontSize=9,alignment=TA_CENTER,textColor=R_MED_COLS)),
                _rimp(imp, R_MED_FG),
            ]], colWidths=[w_num, w_desc_m, 1.8*cm, 2.2*cm, w_imp])
            row.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),
                ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
                ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("LINEBELOW",(0,0),(-1,-1),0.3,colors.HexColor("#e0d0f5"))]))
            story.append(row)
        story.append(Spacer(1, 4))

    # ── 3. DOCUMENTOS ─────────────────────────────────────────────────────────
    if items_doc:
        story.append(_sec_hdr("📄  DOCUMENTOS", R_DOC_HDR, colors.HexColor("#fce8e8")))
        story.append(_col_hdr(["#","Documento","Cant.","Precio unit.","Importe"],
                               [w_num, w_desc_m, 1.8*cm, 2.2*cm, w_imp], R_DOC_COLS))
        for i, a in enumerate(items_doc, 1):
            valor = float(a.get("valor",0) or 0)
            cant  = int(a.get("cantidad",1) or 1)
            imp   = cant * valor
            importe_calc += imp; total_valor += imp
            bg = _rbg(i, R_DOC_FILA2)
            row = Table([[
                Paragraph(str(i),ParagraphStyle("",fontName="Helvetica",fontSize=9,alignment=TA_CENTER,textColor=GRIS_TEXT)),
                Paragraph(a["descripcion"],ParagraphStyle("",fontName="Helvetica",fontSize=9,textColor=colors.HexColor("#3a0a0a"))),
                Paragraph(f"×{cant}",ParagraphStyle("",fontName="Helvetica-Bold",fontSize=9,alignment=TA_CENTER,textColor=R_DOC_FG)),
                Paragraph(f"{mon}{valor:.0f}",ParagraphStyle("",fontName="Helvetica-Bold",fontSize=9,alignment=TA_CENTER,textColor=R_DOC_COLS)),
                _rimp(imp, R_DOC_FG),
            ]], colWidths=[w_num, w_desc_m, 1.8*cm, 2.2*cm, w_imp])
            row.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),
                ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
                ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("LINEBELOW",(0,0),(-1,-1),0.3,colors.HexColor("#f5d5d5"))]))
            story.append(row)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))

    # ── Totales financieros ───────────────────────────────────────────────────
    restante = float(env.get("restante", 0))
    tot_data = [
        [Paragraph("Subtotal artículos", st["normal"]),
         Paragraph(f"{mon} {importe_calc:,.2f}",
                   ParagraphStyle("t", fontName="Helvetica", fontSize=10,
                                  alignment=TA_RIGHT, textColor=GRIS_DARK))],
        [Paragraph("<b>Total encomienda</b>", st["bold"]),
         Paragraph(f"<b>{mon} {env['total']:,.2f}</b>",
                   ParagraphStyle("t2", fontName="Helvetica-Bold", fontSize=11,
                                  alignment=TA_RIGHT, textColor=GRIS_DARK))],
        [Paragraph("Abono recibido", st["normal"]),
         Paragraph(f"{mon} {env['abono']:,.2f}",
                   ParagraphStyle("t3", fontName="Helvetica", fontSize=10,
                                  alignment=TA_RIGHT, textColor=VERDE_DARK))],
        [Paragraph("<b>Saldo pendiente</b>", st["bold"]),
         Paragraph(f"<b>{mon} {restante:,.2f}</b>",
                   ParagraphStyle("t4", fontName="Helvetica-Bold", fontSize=13,
                                  alignment=TA_RIGHT,
                                  textColor=ROJO if restante > 0 else VERDE_DARK))],
    ]
    tot_t = Table(tot_data, colWidths=[ancho_util - 6*cm, 6*cm], hAlign="RIGHT")
    tot_t.setStyle(TableStyle([
        ("LINEBELOW",     (0, 1), (-1, 1), 1, colors.HexColor("#d0d0c8")),
        ("LINEABOVE",     (0, 3), (-1, 3), 1.5,
         ROJO if restante > 0 else VERDE),
        ("BACKGROUND",    (0, 3), (-1, 3),
         ROJO_LIGHT if restante > 0 else VERDE_LIGHT),
        ("BACKGROUND",    (0, 2), (-1, 2), GRIS_LIGHT),
        ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tot_t)
    story.append(Spacer(1, 8))

    # ── Info de pago y notas ──────────────────────────────────────────────────
    info_pago = []
    if env.get("cajero"):
        info_pago.append(("Cajero", env["cajero"]))
    if env.get("tipo_pago"):
        info_pago.append(("Forma de pago", env["tipo_pago"]))
    if env.get("nota"):
        info_pago.append(("Nota del envío", env["nota"]))
    if env.get("nota_interna"):
        info_pago.append(("Nota interna", env["nota_interna"]))

    if info_pago:
        story.append(KeepTogether([
            Paragraph("💳  INFORMACIÓN DE PAGO", st["seccion_verde"]),
            _tabla_info(info_pago, col_w=[4.5*cm, ancho_util - 4.5*cm]),
            Spacer(1, 4),
        ]))

    # ── Historial de pagos ────────────────────────────────────────────────────
    if pags:
        story.append(KeepTogether([
            Paragraph("🗓  HISTORIAL DE PAGOS", st["seccion_verde"]),
            _tabla_pagos(pags, ancho_util),
            Spacer(1, 4),
        ]))

    # ── Pie de página ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1,
                              color=colors.HexColor("#e0e0d8"), spaceAfter=4))
    pie_txt = f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  {EMPRESA_NOMBRE}"
    story.append(Paragraph(pie_txt, st["pie"]))
    story.append(Paragraph("Conserve este recibo como comprobante de su envío.", st["pie"]))

    doc.build(story)

    if abrir:
        _abrir_pdf(ruta)

    logger.info("Recibo generado: %s", ruta)
    return ruta


def _tabla_pagos(pags, ancho_util):
    """Tabla de historial de pagos reutilizable."""
    pag_data = [["Fecha", "Tipo de pago", "Cajero", "Monto"]]
    for p in pags:
        pag_data.append([
            p["fecha"],
            p.get("tipo", "—"),
            p.get("cajero", "—"),
            f"{p['moneda']}{p['monto']:,.2f}",
        ])
    pag_t = Table(pag_data,
                   colWidths=[3*cm, 4*cm, 5*cm, ancho_util - 12*cm])
    pag_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), VERDE_LIGHT),
        ("TEXTCOLOR",     (0, 0), (-1, 0), VERDE_DARK),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e8e0")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [BLANCO, GRIS_LIGHT]),
        ("ALIGN",         (3, 0), (3, -1), "RIGHT"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return pag_t


# ══════════════════════════════════════════════════════════════════════════════
#  2. REPORTE GENERAL / DEL DÍA
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_reporte(db, abrir=True):
    """
    Genera un PDF con el reporte general: resumen, tabla por estado
    y tabla por mes.

    db    : instancia de Database
    abrir : bool
    Retorna: ruta del archivo generado
    """
    resumen = db.resumen_general()
    estados = db.envios_por_estado()
    meses   = db.envios_por_mes()
    hoy     = datetime.now().strftime("%d/%m/%Y")

    nombre_archivo = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    ruta = os.path.join(_carpeta_salida(), nombre_archivo)

    doc = SimpleDocTemplate(
        ruta, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Reporte {hoy}",
        author=EMPRESA_NOMBRE
    )

    st    = _estilos()
    ancho = A4[0] - 4*cm
    story = []

    # ── Encabezado ────────────────────────────────────────────────────────────
    story.append(Paragraph("📊 Reporte General", st["titulo"]))
    story.append(Paragraph(f"Generado el {hoy}", st["subtitulo"]))
    story.append(HRFlowable(width="100%", thickness=2,
                              color=VERDE, spaceAfter=14))

    # ── Tarjetas de resumen ───────────────────────────────────────────────────
    story.append(Paragraph("RESUMEN GENERAL", st["seccion"]))

    card_data = [[
        Paragraph("<b>Total envíos</b><br/>"
                  f"<font size='18'><b>{int(resumen['total_envios'])}</b></font>",
                  ParagraphStyle("c", fontName="Helvetica", fontSize=10,
                                  textColor=VERDE_DARK, alignment=TA_CENTER,
                                  leading=20)),
        Paragraph("<b>Facturado</b><br/>"
                  f"<font size='14'><b>C${resumen['total_facturado']:,.2f}</b></font>",
                  ParagraphStyle("c", fontName="Helvetica", fontSize=10,
                                  textColor=AZUL, alignment=TA_CENTER,
                                  leading=18)),
        Paragraph("<b>Cobrado</b><br/>"
                  f"<font size='14'><b>C${resumen['total_cobrado']:,.2f}</b></font>",
                  ParagraphStyle("c", fontName="Helvetica", fontSize=10,
                                  textColor=colors.HexColor("#27500a"),
                                  alignment=TA_CENTER, leading=18)),
        Paragraph("<b>Pendiente</b><br/>"
                  f"<font size='14'><b>C${resumen['total_pendiente']:,.2f}</b></font>",
                  ParagraphStyle("c", fontName="Helvetica", fontSize=10,
                                  textColor=NARANJA, alignment=TA_CENTER,
                                  leading=18)),
    ]]
    card_t = Table(card_data,
                    colWidths=[ancho / 4] * 4)
    card_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), VERDE_LIGHT),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#e6f1fb")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#eaf3de")),
        ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#faeeda")),
        ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0d8")),
        ("INNERGRID",  (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0d8")),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(card_t)
    story.append(Spacer(1, 16))

    # ── Por estado ────────────────────────────────────────────────────────────
    story.append(Paragraph("DETALLE POR ESTADO", st["seccion"]))
    est_data = [["Estado", "Cantidad", "Monto total"]]
    for e in estados:
        est_data.append([
            e["estado"],
            str(e["cantidad"]),
            f"C${e['monto']:,.2f}",
        ])
    est_t = Table(est_data, colWidths=[6*cm, 4*cm, 7*cm])
    est_colores = {
        "Pagado":    VERDE_LIGHT,
        "Abono":     colors.HexColor("#e6f1fb"),
        "Pendiente": colors.HexColor("#faeeda"),
        "Cancelado": ROJO_LIGHT,
    }
    row_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 10),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0d8")),
        ("ALIGN",      (1, 0), (2, -1), "CENTER"),
        ("ALIGN",      (2, 0), (2, -1), "RIGHT"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]
    for i, e in enumerate(estados, start=1):
        bg = est_colores.get(e["estado"], colors.white)
        row_styles.append(("BACKGROUND", (0, i), (-1, i), bg))
    est_t.setStyle(TableStyle(row_styles))
    story.append(est_t)
    story.append(Spacer(1, 16))

    # ── Por mes ───────────────────────────────────────────────────────────────
    story.append(Paragraph("RESUMEN POR MES (últimos 6)", st["seccion"]))
    if meses:
        mes_data = [["Mes", "Envíos", "Monto facturado"]]
        for m in meses:
            mes_data.append([
                m["mes"] if m["mes"] else "Sin fecha",
                str(m["cantidad"]),
                f"C${(m['monto'] or 0):,.2f}",
            ])
        mes_t = Table(mes_data, colWidths=[5*cm, 4*cm, 8*cm])
        mes_t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), VERDE),
            ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, GRIS_LIGHT]),
            ("GRID",         (0, 0), (-1, -1), 0.5,
             colors.HexColor("#e0e0d8")),
            ("ALIGN",        (1, 0), (2, -1), "CENTER"),
            ("ALIGN",        (2, 0), (2, -1), "RIGHT"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ]))
        story.append(mes_t)
    else:
        story.append(Paragraph("Sin datos aún.", st["normal"]))

    story.append(Spacer(1, 16))

    # ── Peso total ────────────────────────────────────────────────────────────
    peso_total = resumen.get('total_peso', None)
    if peso_total is not None:
        story.append(Paragraph(
            f"Peso total transportado: <b>{peso_total:.2f} lb</b>",
            st["normal"]))

    # ── Pie ───────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1,
                              color=colors.HexColor("#e0e0d8"), spaceAfter=8))
    story.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        + EMPRESA_NOMBRE,
        st["pie"]))

    doc.build(story)

    if abrir:
        _abrir_pdf(ruta)

    return ruta


# ══════════════════════════════════════════════════════════════════════════════
#  3. LISTADO DEL HISTORIAL (envios filtrados)
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_historial(db, buscar="", estado="", mes="", abrir=True):
    """
    Genera un PDF con la lista de envíos según los filtros activos
    (los mismos que usa HistorialFrame).

    db     : instancia de Database
    buscar : str
    estado : str  ("" = todos)
    mes    : str  ("" = todos)
    abrir  : bool
    Retorna: ruta del archivo generado
    """
    envios = db.listar_envios(buscar, estado, mes)
    hoy    = datetime.now().strftime("%d/%m/%Y")

    nombre_archivo = f"historial_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    ruta = os.path.join(_carpeta_salida(), nombre_archivo)

    doc = SimpleDocTemplate(
        ruta, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Historial {hoy}",
        author=EMPRESA_NOMBRE
    )

    st    = _estilos()
    story = []

    # ── Encabezado ────────────────────────────────────────────────────────────
    story.append(Paragraph("Historial de Envios", st["titulo"]))

    filtros = []
    if buscar: filtros.append(f"Búsqueda: {buscar}")
    if estado: filtros.append(f"Estado: {estado}")
    if mes:    filtros.append(f"Mes: {mes}")
    desc = " · ".join(filtros) if filtros else "Todos los registros"
    story.append(Paragraph(f"{desc}  —  {hoy}", st["subtitulo"]))
    story.append(HRFlowable(width="100%", thickness=2,
                              color=VERDE, spaceAfter=10))

    if not envios:
        story.append(Paragraph("No hay envíos que coincidan con los filtros.",
                                st["normal"]))
    else:
        # Tabla principal
        hdrs = ["Código", "Fecha", "Entrega", "Recibe",
                "Peso", "Total", "Estado"]
        data = [hdrs]
        for e in envios:
            mon = e.get("moneda", "C$")
            data.append([
                e["codigo"],
                e["fecha"],
                e["ent_nombre"],
                e["rec_nombre"],
                f"{e['peso_total']:.1f} lb",
                f"{mon}{e['total']:,.0f}",
                e["estado"],
            ])

        col_w = [2.5*cm, 2.2*cm, 4*cm, 4*cm, 2*cm, 2.8*cm, 2.5*cm]
        t = Table(data, colWidths=col_w, repeatRows=1)

        est_bg_map = {
            "Pagado":    VERDE_LIGHT,
            "Abono":     colors.HexColor("#e6f1fb"),
            "Pendiente": colors.HexColor("#faeeda"),
            "Cancelado": ROJO_LIGHT,
        }
        est_fg_map = {
            "Pagado":    VERDE_DARK,
            "Abono":     AZUL,
            "Pendiente": NARANJA,
            "Cancelado": ROJO,
        }

        base_style = [
            ("BACKGROUND",   (0, 0), (-1, 0), VERDE),
            ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("GRID",         (0, 0), (-1, -1), 0.4,
             colors.HexColor("#e0e0d8")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, GRIS_LIGHT]),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ]

        # Color de fondo por estado en columna "Estado"
        for i, e in enumerate(envios, start=1):
            bg = est_bg_map.get(e["estado"], colors.white)
            fg = est_fg_map.get(e["estado"], GRIS_DARK)
            base_style += [
                ("BACKGROUND", (6, i), (6, i), bg),
                ("TEXTCOLOR",  (6, i), (6, i), fg),
                ("FONTNAME",   (6, i), (6, i), "Helvetica-Bold"),
            ]

        t.setStyle(TableStyle(base_style))
        story.append(t)

        # Totales rápidos al final
        story.append(Spacer(1, 12))
        total_monto = sum(e["total"] for e in envios)
        total_cobrado = sum(e["abono"] for e in envios)
        total_rest = sum(e["restante"] for e in envios)
        story.append(Paragraph(
            f"<b>Total registros:</b> {len(envios)}  ·  "
            f"<b>Facturado:</b> C${total_monto:,.2f}  ·  "
            f"<b>Cobrado:</b> C${total_cobrado:,.2f}  ·  "
            f"<b>Pendiente:</b> C${total_rest:,.2f}",
            ParagraphStyle("res", fontName="Helvetica", fontSize=9,
                            textColor=GRIS_DARK, backColor=VERDE_LIGHT,
                            borderPadding=(6, 10, 6, 10))
        ))

    # ── Pie ───────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1,
                              color=colors.HexColor("#e0e0d8"), spaceAfter=8))
    story.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        + EMPRESA_NOMBRE,
        st["pie"]))

    doc.build(story)

    if abrir:
        _abrir_pdf(ruta)

    return ruta

# ══════════════════════════════════════════════════════════════════════════════
#  4. RECIBO TERMICO (80mm / texto plano para impresora de tickets)
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_recibo_termico(db, envio_id, ruta=None):
    """
    Genera un archivo de texto plano formateado para impresora termica 80mm.
    Si ruta es None, guarda en recibos/termico_NOMBRE.txt
    Retorna la ruta del archivo generado.
    """
    env  = db.obtener_envio(envio_id)
    arts = db.obtener_articulos(envio_id)
    if not env:
        raise ValueError(f"No se encontró el envío con id={envio_id}")

    if ruta is None:
        base = os.path.join(os.path.dirname(DB_PATH), "recibos")
        os.makedirs(base, exist_ok=True)
        ruta = os.path.join(base, f"termico_{env['codigo']}.txt")

    mon = env.get("moneda", "C$")

    # Ancho 42 caracteres para papel termico 80mm
    W = 42
    sep = "=" * W
    thin = "-" * W

    lines = []
    def p(line=""):
        lines.append(line)

    p(sep)
    p("         SISTEMA DE ENCOMIENDAS")
    p("         Recibo de Envio")
    p(sep)
    p(f"  Codigo:  {env['codigo']}")
    p(f"  Fecha:   {env['fecha']}")
    p(f"  Estado:  {env['estado']}")
    p(thin)

    p("  QUIEN ENTREGA:")
    p(f"  {env['ent_nombre']}")
    if env.get("ent_tel"):
        p(f"  Tel: {env['ent_tel']}")
    p("")
    p("  QUIEN RECIBE:")
    p(f"  {env['rec_nombre']}")
    if env.get("rec_tel"):
        p(f"  Tel: {env['rec_tel']}")
    p(thin)

    p("  ARTICULOS:")
    items_peso_t = [a for a in arts if (a.get("tipo") or "").lower() not in ("medicamento","documento") and float(a.get("peso_lb",0) or 0) > 0]
    items_med_t  = [a for a in arts if (a.get("tipo") or "").lower() == "medicamento"]
    items_doc_t  = [a for a in arts if (a.get("tipo") or "").lower() == "documento" or
                    ((a.get("tipo") or "").lower() not in ("medicamento",) and
                     float(a.get("peso_lb",0) or 0) == 0 and float(a.get("valor",0) or 0) > 0)]

    if items_peso_t:
        p(f"  {'-- Por peso ':{'<'}{W-4}}")
    for a in items_peso_t:
        peso     = float(a.get("peso_lb", 0) or 0)
        cantidad = int(a.get("cantidad", 1))
        imp      = cantidad * peso * PRECIO_LB
        linea    = f"  {cantidad}x {a['descripcion']}"
        p(linea[:W])
        p(f"     {peso:.2f} lb x ${PRECIO_LB}/lb  =>  {mon}{imp:,.2f}")

    if items_med_t:
        p(f"  {'-- Medicamentos ':{'<'}{W-4}}")
    for a in items_med_t:
        valor    = float(a.get("valor", 0) or 0)
        cantidad = int(a.get("cantidad", 1))
        imp      = cantidad * valor
        linea    = f"  {cantidad}x {a['descripcion']}"
        p(linea[:W])
        p(f"     {cantidad} x {mon}{valor:,.2f}  =>  {mon}{imp:,.2f}")

    if items_doc_t:
        p(f"  {'-- Documentos ':{'<'}{W-4}}")
    for a in items_doc_t:
        valor    = float(a.get("valor", 0) or 0)
        cantidad = int(a.get("cantidad", 1))
        imp      = cantidad * valor
        linea    = f"  {cantidad}x {a['descripcion']}"
        p(linea[:W])
        p(f"     {cantidad} x {mon}{valor:,.2f}  =>  {mon}{imp:,.2f}")
    p(thin)

    p(f"  Total:        $ {env['total']:,.2f}")
    p(f"  Abono:        $ {env['abono']:,.2f}")
    p(f"  Pendiente:    $ {env['restante']:,.2f}")
    p(thin)

    if env.get("cajero"):
        p(f"  Cajero: {env['cajero']}")
    if env.get("tipo_pago"):
        p(f"  Pago:   {env['tipo_pago']}")
    if env.get("nota"):
        p(f"  Nota:   {env['nota']}")
    p(sep)
    from datetime import datetime
    p(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    p(sep)
    p("")
    p("  ¡Gracias por su preferencia!")
    p("")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("Recibo termico generado: %s", ruta)

    # Intentar imprimir directamente (solo macOS/Unix)
    try:
        import subprocess
        subprocess.Popen(["lp", ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    return ruta


# ══════════════════════════════════════════════════════════════════════════════
#  5. COTIZACION / PRESUPUESTO
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_cotizacion(db, cot_id, abrir=True):
    import json
    cot = db.obtener_cotizacion(cot_id)
    if not cot:
        raise ValueError(f"No se encontró cotización id={cot_id}")
    arts = json.loads(cot["items_json"]) if cot["items_json"] else []
    s = _estilos()
    ruta = os.path.join(_carpeta_salida(), f"cotizacion_{cot['codigo']}.pdf")
    doc = SimpleDocTemplate(ruta, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    story = []
    story.append(Paragraph("COTIZACIÓN / PRESUPUESTO", s["titulo"]))
    story.append(Paragraph(cot["codigo"], s["codigo"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=VERDE))
    story.append(Spacer(1, 8))
    story.append(_tabla_info([
        ("Fecha", cot["fecha"]),
        ("Válida hasta", cot.get("valida_hasta","") or "—"),
        ("Moneda", cot["moneda"]),
    ]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Quién entrega:</b>", s["seccion"]))
    story.append(Paragraph(f"{cot['ent_nombre']} — {cot.get('ent_tel','') or '—'}", s["normal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Quién recibe:</b>", s["seccion"]))
    story.append(Paragraph(f"{cot['rec_nombre']} — {cot.get('rec_tel','') or '—'}", s["normal"]))
    story.append(Spacer(1, 4))
    story.append(_tabla_info([
        ("Destino USA", cot.get("destino_usa","Sin asignar")),
    ]))
    story.append(Spacer(1, 8))

    if arts:
        data = [["#", "Descripción", "Cant", "Peso lb", "Valor unit.", "Total"]]
        for i, a in enumerate(arts, 1):
            tot = float(a.get("valor",0)) * int(a.get("cantidad",1))
            data.append([str(i), a.get("descripcion",""),
                        str(a.get("cantidad",1)), f"{float(a.get('peso_lb',0)):.2f}",
                        f"{float(a.get('valor',0)):.2f}", f"{tot:.2f}"])
        t = Table(data, colWidths=[20, 180, 30, 50, 60, 60])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), VERDE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("ALIGN", (2,0), (-1,-1), "CENTER"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, GRIS_LIGHT]),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    incluye_iva = cot.get("incluye_iva", 0)
    iva_pct = cot.get("iva", 0)
    subtotal = cot["subtotal"]
    total = cot["total"]
    data_tot = [["Subtotal", f"{cot['moneda']} {subtotal:,.2f}"]]
    if incluye_iva:
        data_tot.append(["IVA", f"{cot['moneda']} {subtotal*iva_pct/100:,.2f}"])
    data_tot.append(["TOTAL", f"{cot['moneda']} {total:,.2f}"])
    t2 = Table(data_tot, colWidths=[120, 100])
    t2.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("LINEABOVE", (0,-1), (-1,-1), 2, VERDE),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,-1), (-1,-1), 12),
    ]))
    story.append(t2)

    if cot.get("notas"):
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"<b>Notas:</b> {cot['notas']}", s["normal"]))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %I:%M %p')}", s["pie"]))
    doc.build(story)
    if abrir:
        _abrir_pdf(ruta)
    return ruta


# ══════════════════════════════════════════════════════════════════════════════
#  6. ARQUEO DE CAJA
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_arqueo(db, fecha, abrir=True):
    arqueos = db.listar_arqueos(por_pagina=100)
    arqueo = None
    for a in arqueos:
        if a["fecha"] == fecha:
            arqueo = a
            break
    if not arqueo:
        raise ValueError(f"No se encontró arqueo para fecha {fecha}")
    s = _estilos()
    ruta = os.path.join(_carpeta_salida(), f"arqueo_{fecha.replace('/','-')}.pdf")
    doc = SimpleDocTemplate(ruta, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    story = []
    story.append(Paragraph("ARQUEO DE CAJA", s["titulo"]))
    story.append(Paragraph(fecha, s["subtitulo"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=VERDE))
    story.append(Spacer(1, 10))

    data = [
        ["", "Córdobas (C$)", "Dólares ($)"],
        ["Apertura", f"{arqueo['apertura_cordobas']:,.2f}", f"{arqueo['apertura_dolares']:,.2f}"],
        ["+ Ingresos", f"{arqueo['ingresos_cordobas']:,.2f}", f"{arqueo['ingresos_dolares']:,.2f}"],
        ["- Egresos", f"{arqueo['egresos_cordobas']:,.2f}", f"{arqueo['egresos_dolares']:,.2f}"],
        ["= Cierre esperado",
         f"{arqueo['apertura_cordobas']+arqueo['ingresos_cordobas']-arqueo['egresos_cordobas']:,.2f}",
         f"{arqueo['apertura_dolares']+arqueo['ingresos_dolares']-arqueo['egresos_dolares']:,.2f}"],
        ["Cierre real", f"{arqueo['cierre_cordobas']:,.2f}", f"{arqueo['cierre_dolares']:,.2f}"],
    ]
    diff_cs = arqueo["diferencia_cordobas"]
    diff_us = arqueo["diferencia_dolares"]
    data.append(["DIFERENCIA",
                 f"{diff_cs:+,.2f}",
                 f"{diff_us:+,.2f}"])
    t = Table(data, colWidths=[140, 100, 100])
    style_cmds = [
        ("BACKGROUND", (0,0), (-1,0), VERDE),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, GRIS_LIGHT]),
    ]
    if abs(diff_cs) > 0.01 or abs(diff_us) > 0.01:
        style_cmds.append(("BACKGROUND", (0,-1), (-1,-1), ROJO_LIGHT))
        style_cmds.append(("TEXTCOLOR", (0,-1), (-1,-1), ROJO))
    else:
        style_cmds.append(("BACKGROUND", (0,-1), (-1,-1), VERDE_LIGHT))
        style_cmds.append(("TEXTCOLOR", (0,-1), (-1,-1), VERDE))
    style_cmds.append(("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"))
    style_cmds.append(("FONTSIZE", (0,-1), (-1,-1), 12))
    t.setStyle(TableStyle(style_cmds))
    story.append(t)

    estado = "🔒 CERRADO" if arqueo.get("cerrado") else "📂 ABIERTO"
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Estado:</b> {estado}", s["normal"]))
    if arqueo.get("nota"):
        story.append(Paragraph(f"<b>Nota:</b> {arqueo['nota']}", s["normal"]))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %I:%M %p')}", s["pie"]))
    doc.build(story)
    if abrir:
        _abrir_pdf(ruta)
    return ruta


# ══════════════════════════════════════════════════════════════════════════════
#  7. CUENTAS POR COBRAR
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_cuentas_cobrar(db, abrir=True):
    deudores = db.obtener_clientes_con_deuda()
    s = _estilos()
    ruta = os.path.join(_carpeta_salida(), "cuentas_por_cobrar.pdf")
    doc = SimpleDocTemplate(ruta, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    story = []
    story.append(Paragraph("CUENTAS POR COBRAR", s["titulo"]))
    story.append(Paragraph(f"Al {datetime.now().strftime('%d/%m/%Y')}", s["subtitulo"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=VERDE))
    story.append(Spacer(1, 8))

    total_gral = sum(d["total_deuda"] for d in deudores)
    story.append(_tabla_info([
        ("Total clientes con deuda", str(len(deudores))),
        ("Monto total pendiente", f"C$ {total_gral:,.2f}"),
    ]))
    story.append(Spacer(1, 8))

    if not deudores:
        story.append(Paragraph("No hay cuentas pendientes.", s["normal"]))
    else:
        data = [["#", "Cliente", "Envíos", "Total deuda", "Desde"]]
        for i, d in enumerate(deudores, 1):
            data.append([str(i), d["ent_nombre"], str(d["cantidad_deudas"]),
                        f"C$ {d['total_deuda']:,.2f}",
                        d.get("deuda_desde","") or ""])
        t = Table(data, colWidths=[20, 160, 50, 80, 80])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), VERDE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ALIGN", (1,1), (-1,-1), "LEFT"),
            ("ALIGN", (0,0), (0,-1), "CENTER"),
            ("ALIGN", (2,0), (-1,-1), "RIGHT"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, GRIS_LIGHT]),
        ]))
        story.append(t)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %I:%M %p')}", s["pie"]))
    doc.build(story)
    if abrir:
        _abrir_pdf(ruta)
    return ruta


# ══════════════════════════════════════════════════════════════════════════════
#  8. FACTURA / IVA  ── versión profesional completa
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_factura(db, factura_id, abrir=True):
    """
    Genera una factura PDF profesional a partir de los datos de la DB.

    Campos esperados en la factura (listar_facturas):
        id, codigo, fecha, tipo, numero_fiscal, moneda,
        cliente_nombre, cliente_tel, cliente_direccion, cliente_ruc,
        monto_neto, iva_porcentaje, iva_monto, total, nota,
        -- campos opcionales vinculados al envío --
        envio_id  (si existe, se enriquece con datos del envío)
    """
    # ── Buscar factura ─────────────────────────────────────────────────────────
    facturas = db.listar_facturas(por_pagina=500)
    fac = next((f for f in facturas if f["id"] == factura_id), None)
    if not fac:
        raise ValueError(f"No se encontró factura id={factura_id}")

    # ── Intentar enriquecer con datos del envío vinculado ─────────────────────
    env  = None
    arts = []
    pags = []
    if fac.get("envio_id"):
        try:
            env  = db.obtener_envio(fac["envio_id"])
            arts = db.obtener_articulos(fac["envio_id"])
            pags = db.obtener_pagos(fac["envio_id"])
        except Exception:
            pass

    st         = _estilos()
    mon        = fac.get("moneda", "$")
    ancho_util = A4[0] - 4 * cm
    ruta       = os.path.join(_carpeta_salida(), f"factura_{fac['codigo']}.pdf")

    doc = SimpleDocTemplate(
        ruta, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
        title=f"Factura {fac['codigo']}",
        author=EMPRESA_NOMBRE,
    )
    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # ENCABEZADO: logo empresa + datos de factura + QR
    # ══════════════════════════════════════════════════════════════════════════
    tipo_fac = fac.get("tipo", "B")
    num_fiscal = fac.get("numero_fiscal", "") or "—"

    # Columna izquierda: empresa
    col_empresa = [
        Paragraph(f"📦 {EMPRESA_NOMBRE}", st["titulo"]),
        Paragraph(EMPRESA_SLOGAN, st["subtitulo"]),
    ]
    ct_parts = list(filter(None, [EMPRESA_TELEFONO, EMPRESA_EMAIL, EMPRESA_WEB]))
    if ct_parts:
        col_empresa.append(Paragraph(
            "  ·  ".join(ct_parts),
            ParagraphStyle("ct", fontName="Helvetica", fontSize=8, textColor=GRIS_TEXT)))

    # Columna derecha: datos de factura + QR
    est_fac = env.get("estado", "Pagado") if env else "Pagado"
    est_bg_f, est_fg_f = ESTADO_COLORES.get(est_fac, (GRIS_LIGHT, GRIS_DARK))

    col_derecha = [
        Paragraph(
            f'<font color="#{AZUL.hexval()[2:]}"><b>FACTURA  {tipo_fac}</b></font>',
            ParagraphStyle("tit_fac", fontName="Helvetica-Bold", fontSize=14,
                           textColor=AZUL, alignment=TA_RIGHT)),
        Paragraph(fac["codigo"],
            ParagraphStyle("cod_fac", fontName="Helvetica-Bold", fontSize=20,
                           textColor=VERDE_DARK, alignment=TA_RIGHT)),
        Paragraph(f'<font color="#{est_fg_f.hexval()[2:]}"><b>  {est_fac}  </b></font>',
            ParagraphStyle("est_fac", fontName="Helvetica-Bold", fontSize=10,
                           backColor=est_bg_f, borderPadding=4, alignment=TA_RIGHT)),
        Paragraph(fac.get("fecha", ""),
            ParagraphStyle("fecha_fac", fontName="Helvetica", fontSize=9,
                           textColor=GRIS_TEXT, alignment=TA_RIGHT)),
    ]

    # QR si está disponible
    qr_cell = None
    if QR_DISPONIBLE:
        try:
            from reportlab.platypus import Image as RLImage
            qr = qrcode.make(f"FACTURA:{fac['codigo']}")
            buf = BytesIO(); qr.save(buf, format="PNG"); buf.seek(0)
            qr_img = RLImage(buf, width=2.2*cm, height=2.2*cm)
            qr_label = Paragraph("Verificar",
                ParagraphStyle("qrl", fontName="Helvetica", fontSize=6,
                               textColor=GRIS_TEXT, alignment=TA_CENTER))
            qr_cell = [qr_img, qr_label]
        except Exception:
            pass

    if qr_cell:
        hdr_data = [[col_empresa, col_derecha, qr_cell]]
        hdr_t = Table(hdr_data, colWidths=[ancho_util*0.46, ancho_util*0.36, 2.5*cm])
    else:
        hdr_data = [[col_empresa, col_derecha]]
        hdr_t = Table(hdr_data, colWidths=[ancho_util*0.55, ancho_util*0.45])

    hdr_t.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",(0, 0), (-1, -1), 0),
        ("ALIGN",       (-1, 0), (-1, 0), "CENTER"),
    ]))
    story.append(hdr_t)
    story.append(HRFlowable(width="100%", thickness=2.5, color=AZUL, spaceAfter=10))

    # ══════════════════════════════════════════════════════════════════════════
    # METADATOS DE LA FACTURA  (número fiscal · tipo · moneda)
    # ══════════════════════════════════════════════════════════════════════════
    meta_data = [[
        Paragraph(f"<b>N° Fiscal:</b>  {num_fiscal}",
            ParagraphStyle("m", fontName="Helvetica", fontSize=9, textColor=GRIS_DARK)),
        Paragraph(f"<b>Tipo:</b>  Factura {tipo_fac}",
            ParagraphStyle("m2", fontName="Helvetica", fontSize=9, textColor=GRIS_DARK,
                           alignment=TA_CENTER)),
        Paragraph(f"<b>Moneda:</b>  {mon}",
            ParagraphStyle("m3", fontName="Helvetica", fontSize=9, textColor=GRIS_DARK,
                           alignment=TA_RIGHT)),
    ]]
    meta_t = Table(meta_data, colWidths=[ancho_util/3]*3)
    meta_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AZUL_LIGHT),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BOX",           (0, 0), (-1, -1), 0.5, AZUL),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.HexColor("#c8dff5")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 14))

    # ══════════════════════════════════════════════════════════════════════════
    # CLIENTE  /  DATOS DEL ENVÍO (si existe)
    # ══════════════════════════════════════════════════════════════════════════
    def _celda_cliente():
        items = [Paragraph("👤  FACTURADO A", st["seccion_verde"])]
        items.append(Paragraph(f"<b>{fac.get('cliente_nombre', '—')}</b>", st["bold"]))
        if fac.get("cliente_ruc"):
            items.append(Paragraph(f"RUC/Cédula: {fac['cliente_ruc']}", st["normal_small"]))
        if fac.get("cliente_tel"):
            items.append(Paragraph(f"📞 {fac['cliente_tel']}", st["normal_small"]))
        if fac.get("cliente_direccion"):
            items.append(Paragraph(f"📍 {fac['cliente_direccion']}", st["normal_small"]))
        return items

    def _celda_envio():
        if not env:
            return [Paragraph("Sin envío vinculado", st["normal_small"])]
        items = [Paragraph("📦  DATOS DEL ENVÍO", st["seccion_verde"])]
        items.append(Paragraph(f"Código: <b>{env.get('codigo','—')}</b>", st["normal_small"]))
        if env.get("ent_nombre"):
            items.append(Paragraph(f"Remitente: {env['ent_nombre']}", st["normal_small"]))
        if env.get("rec_nombre"):
            items.append(Paragraph(f"Destinatario: {env['rec_nombre']}", st["normal_small"]))
        if env.get("destino_usa") and env["destino_usa"] != "Sin asignar":
            items.append(Paragraph(f"🗺️ {env['destino_usa']}", st["normal_small"]))
        return items

    partes_data = [[_celda_cliente(), _celda_envio()]]
    partes_t = Table(partes_data, colWidths=[ancho_util/2, ancho_util/2])
    partes_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), AZUL_LIGHT),
        ("BACKGROUND",    (1, 0), (1, -1), VERDE_LIGHT),
        ("BOX",           (0, 0), (0, -1), 0.5, AZUL),
        ("BOX",           (1, 0), (1, -1), 0.5, VERDE),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(partes_t)
    story.append(Spacer(1, 14))

    # ══════════════════════════════════════════════════════════════════════════
    # ARTÍCULOS DEL ENVÍO — tablas separadas por tipo (igual que la UI)
    # ══════════════════════════════════════════════════════════════════════════

    # Paleta por tipo (igual que nueva_encomienda.py)
    PESO_HDR    = colors.HexColor("#4a2000")
    PESO_COLS   = colors.HexColor("#6b3a0f")
    PESO_FILA1  = colors.white
    PESO_FILA2  = colors.HexColor("#fff3e6")
    PESO_FG     = colors.HexColor("#633806")

    MED_HDR     = colors.HexColor("#6b2fa0")
    MED_COLS    = colors.HexColor("#8e44c4")
    MED_FILA1   = colors.white
    MED_FILA2   = colors.HexColor("#f8f2fd")
    MED_FG      = colors.HexColor("#6b2fa0")

    DOC_HDR     = colors.HexColor("#791f1f")
    DOC_COLS    = colors.HexColor("#9e2a2a")
    DOC_FILA1   = colors.white
    DOC_FILA2   = colors.HexColor("#fff3f3")
    DOC_FG      = colors.HexColor("#791f1f")

    def _fila_bg(i, c1, c2):
        return c1 if i % 2 == 1 else c2

    def _num_p(n, bg):
        return Paragraph(str(n), ParagraphStyle(
            "fn", fontName="Helvetica", fontSize=9,
            alignment=TA_CENTER, textColor=GRIS_TEXT, backColor=bg))

    def _imp_p(val, fg):
        return Paragraph(f"<b>{mon}{val:,.2f}</b>", ParagraphStyle(
            "fi", fontName="Helvetica-Bold", fontSize=9,
            alignment=TA_RIGHT, textColor=fg))

    subtotal_arts = 0.0

    if arts:
        # ── Separar artículos por tipo ───────────────────────────────────────
        items_peso = []
        items_med  = []
        items_doc  = []
        for a in arts:
            tipo_art = (a.get("tipo") or "").lower()
            peso  = float(a.get("peso_lb", 0) or 0)
            valor = float(a.get("valor",   0) or 0)
            cant  = int(a.get("cantidad",  1) or 1)
            if tipo_art == "medicamento":
                items_med.append(a)
            elif tipo_art == "documento" or (peso == 0 and valor > 0):
                items_doc.append(a)
            else:
                items_peso.append(a)

        AW = ancho_util  # alias

        # ── 1. TABLA ENVÍOS POR PESO ─────────────────────────────────────────
        if items_peso:
            # Encabezado de sección
            sec_hdr = Table([[
                Paragraph("⚖️  ENVÍOS POR PESO",
                    ParagraphStyle("ph", fontName="Helvetica-Bold", fontSize=9,
                                   textColor=colors.HexColor("#f5c97a")))
            ]], colWidths=[AW])
            sec_hdr.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), PESO_HDR),
                ("LEFTPADDING",   (0,0),(-1,-1), 14),
                ("TOPPADDING",    (0,0),(-1,-1), 7),
                ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ]))
            story.append(sec_hdr)

            # Cabecera de columnas
            col_hdr = Table([[
                Paragraph("<b>#</b>",           ParagraphStyle("ph2",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#f5dab5"),alignment=TA_CENTER)),
                Paragraph("<b>Descripción</b>", ParagraphStyle("ph3",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#f5dab5"))),
                Paragraph("<b>Peso (lb)</b>",   ParagraphStyle("ph4",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#f5dab5"),alignment=TA_CENTER)),
                Paragraph("<b>Importe</b>",     ParagraphStyle("ph5",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#f5dab5"),alignment=TA_RIGHT)),
            ]], colWidths=[1*cm, AW-1*cm-2.5*cm-2.8*cm, 2.5*cm, 2.8*cm])
            col_hdr.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), PESO_COLS),
                ("LEFTPADDING",   (0,0),(-1,-1), 8),
                ("RIGHTPADDING",  (0,0),(-1,-1), 8),
                ("TOPPADDING",    (0,0),(-1,-1), 5),
                ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ]))
            story.append(col_hdr)

            # Filas
            for i, a in enumerate(items_peso, 1):
                peso  = float(a.get("peso_lb", 0) or 0)
                cant  = int(a.get("cantidad", 1) or 1)
                imp   = cant * peso * PRECIO_LB
                subtotal_arts += imp
                bg = _fila_bg(i, PESO_FILA1, PESO_FILA2)
                fila = Table([[
                    Paragraph(str(i), ParagraphStyle("n",fontName="Helvetica",fontSize=9,alignment=TA_CENTER,textColor=GRIS_TEXT)),
                    Paragraph(a["descripcion"], ParagraphStyle("d",fontName="Helvetica",fontSize=9,textColor=colors.HexColor("#1a1a1a"))),
                    Paragraph(f"{peso:.1f} lb", ParagraphStyle("p",fontName="Helvetica",fontSize=9,alignment=TA_CENTER,textColor=colors.HexColor("#4a2000"))),
                    _imp_p(imp, PESO_FG),
                ]], colWidths=[1*cm, AW-1*cm-2.5*cm-2.8*cm, 2.5*cm, 2.8*cm])
                fila.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0),(-1,-1), bg),
                    ("LEFTPADDING",   (0,0),(-1,-1), 8),
                    ("RIGHTPADDING",  (0,0),(-1,-1), 8),
                    ("TOPPADDING",    (0,0),(-1,-1), 5),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                    ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                    ("LINEBELOW",     (0,0),(-1,-1), 0.3, colors.HexColor("#e8d5b0")),
                ]))
                story.append(fila)
            story.append(Spacer(1, 6))

        # ── 2. TABLA MEDICAMENTOS ─────────────────────────────────────────────
        if items_med:
            sec_hdr = Table([[
                Paragraph("💊  MEDICAMENTOS",
                    ParagraphStyle("mh", fontName="Helvetica-Bold", fontSize=9,
                                   textColor=colors.HexColor("#e8d5f5")))
            ]], colWidths=[AW])
            sec_hdr.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), MED_HDR),
                ("LEFTPADDING",   (0,0),(-1,-1), 14),
                ("TOPPADDING",    (0,0),(-1,-1), 7),
                ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ]))
            story.append(sec_hdr)

            col_hdr = Table([[
                Paragraph("<b>#</b>",              ParagraphStyle("mh2",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#e8d5f5"),alignment=TA_CENTER)),
                Paragraph("<b>Medicamento</b>",    ParagraphStyle("mh3",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#e8d5f5"))),
                Paragraph("<b>Cant.</b>",          ParagraphStyle("mh4",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#e8d5f5"),alignment=TA_CENTER)),
                Paragraph("<b>Precio unit.</b>",   ParagraphStyle("mh5",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#e8d5f5"),alignment=TA_CENTER)),
                Paragraph("<b>Importe</b>",        ParagraphStyle("mh6",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#e8d5f5"),alignment=TA_RIGHT)),
            ]], colWidths=[1*cm, AW-1*cm-1.8*cm-2.2*cm-2.8*cm, 1.8*cm, 2.2*cm, 2.8*cm])
            col_hdr.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), MED_COLS),
                ("LEFTPADDING",   (0,0),(-1,-1), 8),
                ("RIGHTPADDING",  (0,0),(-1,-1), 8),
                ("TOPPADDING",    (0,0),(-1,-1), 5),
                ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ]))
            story.append(col_hdr)

            for i, a in enumerate(items_med, 1):
                valor = float(a.get("valor", 0) or 0)
                cant  = int(a.get("cantidad", 1) or 1)
                imp   = cant * valor
                subtotal_arts += imp
                bg = _fila_bg(i, MED_FILA1, MED_FILA2)
                fila = Table([[
                    Paragraph(str(i), ParagraphStyle("n",fontName="Helvetica",fontSize=9,alignment=TA_CENTER,textColor=GRIS_TEXT)),
                    Paragraph(a["descripcion"], ParagraphStyle("d",fontName="Helvetica",fontSize=9,textColor=colors.HexColor("#2c1a40"))),
                    Paragraph(f"×{cant}", ParagraphStyle("c",fontName="Helvetica-Bold",fontSize=9,alignment=TA_CENTER,textColor=MED_FG)),
                    Paragraph(f"{mon}{valor:.0f}", ParagraphStyle("v",fontName="Helvetica-Bold",fontSize=9,alignment=TA_CENTER,textColor=MED_COLS)),
                    _imp_p(imp, MED_FG),
                ]], colWidths=[1*cm, AW-1*cm-1.8*cm-2.2*cm-2.8*cm, 1.8*cm, 2.2*cm, 2.8*cm])
                fila.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0),(-1,-1), bg),
                    ("LEFTPADDING",   (0,0),(-1,-1), 8),
                    ("RIGHTPADDING",  (0,0),(-1,-1), 8),
                    ("TOPPADDING",    (0,0),(-1,-1), 5),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                    ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                    ("LINEBELOW",     (0,0),(-1,-1), 0.3, colors.HexColor("#e0d0f5")),
                ]))
                story.append(fila)
            story.append(Spacer(1, 6))

        # ── 3. TABLA DOCUMENTOS ───────────────────────────────────────────────
        if items_doc:
            sec_hdr = Table([[
                Paragraph("📄  DOCUMENTOS",
                    ParagraphStyle("dh", fontName="Helvetica-Bold", fontSize=9,
                                   textColor=colors.HexColor("#fce8e8")))
            ]], colWidths=[AW])
            sec_hdr.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), DOC_HDR),
                ("LEFTPADDING",   (0,0),(-1,-1), 14),
                ("TOPPADDING",    (0,0),(-1,-1), 7),
                ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ]))
            story.append(sec_hdr)

            col_hdr = Table([[
                Paragraph("<b>#</b>",            ParagraphStyle("dh2",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#fce8e8"),alignment=TA_CENTER)),
                Paragraph("<b>Documento</b>",    ParagraphStyle("dh3",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#fce8e8"))),
                Paragraph("<b>Cant.</b>",        ParagraphStyle("dh4",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#fce8e8"),alignment=TA_CENTER)),
                Paragraph("<b>Precio unit.</b>", ParagraphStyle("dh5",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#fce8e8"),alignment=TA_CENTER)),
                Paragraph("<b>Importe</b>",      ParagraphStyle("dh6",fontName="Helvetica-Bold",fontSize=8,textColor=colors.HexColor("#fce8e8"),alignment=TA_RIGHT)),
            ]], colWidths=[1*cm, AW-1*cm-1.8*cm-2.2*cm-2.8*cm, 1.8*cm, 2.2*cm, 2.8*cm])
            col_hdr.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), DOC_COLS),
                ("LEFTPADDING",   (0,0),(-1,-1), 8),
                ("RIGHTPADDING",  (0,0),(-1,-1), 8),
                ("TOPPADDING",    (0,0),(-1,-1), 5),
                ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ]))
            story.append(col_hdr)

            for i, a in enumerate(items_doc, 1):
                valor = float(a.get("valor", 0) or 0)
                cant  = int(a.get("cantidad", 1) or 1)
                imp   = cant * valor
                subtotal_arts += imp
                bg = _fila_bg(i, DOC_FILA1, DOC_FILA2)
                fila = Table([[
                    Paragraph(str(i), ParagraphStyle("n",fontName="Helvetica",fontSize=9,alignment=TA_CENTER,textColor=GRIS_TEXT)),
                    Paragraph(a["descripcion"], ParagraphStyle("d",fontName="Helvetica",fontSize=9,textColor=colors.HexColor("#3a0a0a"))),
                    Paragraph(f"×{cant}", ParagraphStyle("c",fontName="Helvetica-Bold",fontSize=9,alignment=TA_CENTER,textColor=DOC_FG)),
                    Paragraph(f"{mon}{valor:.0f}", ParagraphStyle("v",fontName="Helvetica-Bold",fontSize=9,alignment=TA_CENTER,textColor=DOC_COLS)),
                    _imp_p(imp, DOC_FG),
                ]], colWidths=[1*cm, AW-1*cm-1.8*cm-2.2*cm-2.8*cm, 1.8*cm, 2.2*cm, 2.8*cm])
                fila.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0),(-1,-1), bg),
                    ("LEFTPADDING",   (0,0),(-1,-1), 8),
                    ("RIGHTPADDING",  (0,0),(-1,-1), 8),
                    ("TOPPADDING",    (0,0),(-1,-1), 5),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                    ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                    ("LINEBELOW",     (0,0),(-1,-1), 0.3, colors.HexColor("#f5d5d5")),
                ]))
                story.append(fila)
            story.append(Spacer(1, 6))

    else:
        subtotal_arts = float(fac.get("monto_neto", 0))

    # ══════════════════════════════════════════════════════════════════════════
    # TOTALES FINANCIEROS  (Subtotal · IVA · TOTAL · Abono · Restante)
    # ══════════════════════════════════════════════════════════════════════════
    monto_neto  = float(fac.get("monto_neto",      subtotal_arts))
    iva_pct     = float(fac.get("iva_porcentaje",  0))
    iva_monto   = float(fac.get("iva_monto",       0))
    total_fac   = float(fac.get("total",           monto_neto + iva_monto))

    # Si hay envío vinculado, añadir desglose de pago
    abono_env    = float(env.get("abono",    0)) if env else total_fac
    restante_env = float(env.get("restante", 0)) if env else 0.0

    filas_tot = [
        [Paragraph("Subtotal", st["normal"]),
         Paragraph(f"{mon} {monto_neto:,.2f}",
             ParagraphStyle("tv", fontName="Helvetica", fontSize=10,
                            alignment=TA_RIGHT, textColor=GRIS_DARK))],
    ]
    if iva_pct:
        filas_tot.append([
            Paragraph(f"IVA ({iva_pct:.0f}%)", st["normal"]),
            Paragraph(f"{mon} {iva_monto:,.2f}",
                ParagraphStyle("tv2", fontName="Helvetica", fontSize=10,
                               alignment=TA_RIGHT, textColor=GRIS_DARK))
        ])
    filas_tot += [
        [Paragraph("<b>TOTAL FACTURA</b>", st["bold"]),
         Paragraph(f"<b>{mon} {total_fac:,.2f}</b>",
             ParagraphStyle("tv3", fontName="Helvetica-Bold", fontSize=13,
                            alignment=TA_RIGHT, textColor=AZUL))],
    ]
    if env:
        filas_tot += [
            [Paragraph("Abono recibido", st["normal"]),
             Paragraph(f"{mon} {abono_env:,.2f}",
                 ParagraphStyle("tv4", fontName="Helvetica", fontSize=10,
                                alignment=TA_RIGHT, textColor=VERDE_DARK))],
            [Paragraph("<b>Saldo pendiente</b>", st["bold"]),
             Paragraph(f"<b>{mon} {restante_env:,.2f}</b>",
                 ParagraphStyle("tv5", fontName="Helvetica-Bold", fontSize=13,
                                alignment=TA_RIGHT,
                                textColor=ROJO if restante_env > 0 else VERDE_DARK))],
        ]

    tot_t = Table(filas_tot, colWidths=[ancho_util - 6*cm, 6*cm], hAlign="RIGHT")
    tot_style = [
        ("LINEBELOW",     (0, 1 if not iva_pct else 2), (-1, 1 if not iva_pct else 2),
         1.5, AZUL),
        ("BACKGROUND",    (0, 1 if not iva_pct else 2), (-1, 1 if not iva_pct else 2),
         AZUL_LIGHT),
        ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    if env and restante_env > 0:
        tot_style.append(("BACKGROUND", (0, -1), (-1, -1), ROJO_LIGHT))
        tot_style.append(("LINEABOVE",  (0, -1), (-1, -1), 1.5, ROJO))
    elif env:
        tot_style.append(("BACKGROUND", (0, -1), (-1, -1), VERDE_LIGHT))
        tot_style.append(("LINEABOVE",  (0, -1), (-1, -1), 1.5, VERDE))
    tot_t.setStyle(TableStyle(tot_style))
    story.append(tot_t)
    story.append(Spacer(1, 14))

    # ══════════════════════════════════════════════════════════════════════════
    # INFORMACIÓN DE PAGO  (cajero, tipo_pago, historial de pagos)
    # ══════════════════════════════════════════════════════════════════════════
    info_bloques = []
    if env:
        pago_info = []
        if env.get("cajero"):     pago_info.append(("Cajero",        env["cajero"]))
        if env.get("tipo_pago"):  pago_info.append(("Forma de pago", env["tipo_pago"]))
        if env.get("nota"):       pago_info.append(("Nota del envío", env["nota"]))
        if pago_info:
            info_bloques.append(KeepTogether([
                Paragraph("💳  INFORMACIÓN DE PAGO", st["seccion_verde"]),
                _tabla_info(pago_info, col_w=[4.5*cm, ancho_util - 4.5*cm]),
                Spacer(1, 8),
            ]))
        if pags:
            info_bloques.append(KeepTogether([
                Paragraph("🗓  HISTORIAL DE PAGOS", st["seccion_verde"]),
                _tabla_pagos(pags, ancho_util),
                Spacer(1, 8),
            ]))

    # Nota de factura
    if fac.get("nota"):
        info_bloques.append(KeepTogether([
            Paragraph("📝  NOTAS", st["seccion_verde"]),
            Paragraph(fac["nota"], st["normal"]),
            Spacer(1, 8),
        ]))

    for bloque in info_bloques:
        story.append(bloque)

    # ══════════════════════════════════════════════════════════════════════════
    # BARRA DE PROGRESO DE PAGO
    # ══════════════════════════════════════════════════════════════════════════
    if total_fac > 0:
        pct = min(abono_env / total_fac, 1.0)
        barra_ancho = ancho_util
        barra_relleno = barra_ancho * pct
        barra_color = VERDE if pct >= 1.0 else AZUL if pct >= 0.5 else NARANJA

        barra_data = [[
            Paragraph(
                f"{'✅ PAGADO' if pct >= 1 else f'{pct*100:.0f}% pagado'}  —  "
                f"{mon} {abono_env:,.2f} de {mon} {total_fac:,.2f}",
                ParagraphStyle("barra_txt", fontName="Helvetica-Bold", fontSize=9,
                               textColor=BLANCO, alignment=TA_CENTER))
        ]]
        barra_t = Table(barra_data, colWidths=[barra_ancho])
        barra_t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), barra_color),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ]))
        story.append(barra_t)
        story.append(Spacer(1, 14))

    # ══════════════════════════════════════════════════════════════════════════
    # PIE DE PÁGINA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(HRFlowable(width="100%", thickness=1,
                              color=colors.HexColor("#e0e0d8"), spaceAfter=8))
    pie_izq = Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  {EMPRESA_NOMBRE}",
        st["pie"])
    pie_der = Paragraph(
        "Esta factura es un comprobante oficial de pago.",
        ParagraphStyle("pie_d", fontName="Helvetica", fontSize=8,
                       alignment=TA_RIGHT, textColor=GRIS_TEXT))
    pie_t = Table([[pie_izq, pie_der]], colWidths=[ancho_util/2, ancho_util/2])
    pie_t.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",(0, 0), (-1, -1), 0),
    ]))
    story.append(pie_t)

    doc.build(story)
    if abrir:
        _abrir_pdf(ruta)

    logger.info("Factura generada: %s", ruta)
    return ruta


# ══════════════════════════════════════════════════════════════════════════════
#  9. CALENDARIO MENSUAL
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_calendario(db, anio, mes, abrir=True):
    import calendar as cal_mod
    s = _estilos()
    nombre_mes = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
                  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][mes]
    ruta = os.path.join(_carpeta_salida(), f"calendario_{nombre_mes}_{anio}.pdf")
    doc = SimpleDocTemplate(ruta, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    story = []
    story.append(Paragraph(f"Calendario de Envíos — {nombre_mes} {anio}", s["titulo"]))
    story.append(HRFlowable(width="100%", thickness=1, color=VERDE))
    story.append(Spacer(1, 8))

    mes_str = f"{mes:02d}"
    anio_str = str(anio)
    rows = db.conn.execute("""
        SELECT substr(fecha, 1, 2) as dia,
               COUNT(*) as cantidad,
               COALESCE(SUM(CASE WHEN moneda='C$' THEN total ELSE 0 END), 0) as monto_cs,
               COALESCE(SUM(CASE WHEN moneda='$' THEN total ELSE 0 END), 0) as monto_us
        FROM envios
        WHERE substr(fecha, 4, 2) = ? AND substr(fecha, 7, 4) = ?
          AND estado != 'Cancelado'
        GROUP BY dia ORDER BY dia
    """, (mes_str, anio_str)).fetchall()
    datos = {r["dia"]: dict(r) for r in rows}

    r = db.conn.execute("""
        SELECT COUNT(*) as total,
               COALESCE(SUM(CASE WHEN moneda='C$' THEN total ELSE 0 END), 0) as total_cs,
               COALESCE(SUM(CASE WHEN moneda='$' THEN total ELSE 0 END), 0) as total_us
        FROM envios
        WHERE substr(fecha, 4, 2) = ? AND substr(fecha, 7, 4) = ?
          AND estado != 'Cancelado'
    """, (mes_str, anio_str)).fetchone()
    story.append(_tabla_info([
        ("Total envíos", str(r["total"])),
        ("Total C$", f"C${r['total_cs']:,.0f}"),
        ("Total $", f"${r['total_us']:,.0f}"),
    ]))
    story.append(Spacer(1, 10))

    cal = cal_mod.monthcalendar(anio, mes)
    dias_sem = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    header_row = [Paragraph(f"<b>{d}</b>", s["normal"]) for d in dias_sem]
    data = [header_row]
    for semana in cal:
        row = []
        for dia_num in semana:
            if dia_num == 0:
                row.append("")
                continue
            d = f"{dia_num:02d}"
            info = datos.get(d)
            cnt = info["cantidad"] if info else 0
            cs = info["monto_cs"] if info else 0
            us = info["monto_us"] if info else 0
            txt = f"{dia_num}"
            if cnt:
                txt += f"\n{cnt} env."
                if cs:
                    txt += f"\nC${cs:,.0f}"
                if us:
                    txt += f"\n${us:,.0f}"
            row.append(Paragraph(txt.replace("\n", "<br/>"), s["normal"]))
        data.append(row)

    t = Table(data, colWidths=[75]*7)
    style_cmds = [
        ("BACKGROUND", (0,0), (-1,0), VERDE),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, GRIS_LIGHT]),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]
    t.setStyle(TableStyle(style_cmds))
    story.append(t)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %I:%M %p')}", s["pie"]))
    doc.build(story)
    if abrir:
        _abrir_pdf(ruta)
    return ruta


# ══════════════════════════════════════════════════════════════════════════════
#  DISEÑOS DE RECIBO
# ══════════════════════════════════════════════════════════════════════════════

DISENOS_DISPONIBLES = {
    "clasico": {
        "nombre": "Clásico",
        "desc": "Diseño tradicional con colores verdes",
        "color_principal": "#0f6e56",
        "color_secundario": "#0c447c",
    },
    "moderno": {
        "nombre": "Moderno",
        "desc": "Diseño con degradados y sombras",
        "color_principal": "#2c3e50",
        "color_secundario": "#3498db",
    },
    "elegante": {
        "nombre": "Elegante",
        "desc": "Diseño sobrio con tonos oscuros",
        "color_principal": "#1a1a2e",
        "color_secundario": "#16213e",
    },
    "minimalista": {
        "nombre": "Minimalista",
        "desc": "Solo texto, sin colores llamativos",
        "color_principal": "#333333",
        "color_secundario": "#666666",
    },
}


def _estilos_diseno(diseno="clasico"):
    """Retorna estilos personalizados según el diseño seleccionado."""
    colores_diseno = DISENOS_DISPONIBLES.get(diseno, DISENOS_DISPONIBLES["clasico"])
    c1 = colors.HexColor(colores_diseno["color_principal"])
    c2 = colors.HexColor(colores_diseno["color_secundario"])
    
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"],
            fontSize=18, textColor=c1, spaceAfter=2,
            fontName="Helvetica-Bold"),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"],
            fontSize=9, textColor=GRIS_TEXT, spaceAfter=6,
            fontName="Helvetica"),
        "seccion": ParagraphStyle(
            "seccion", parent=base["Normal"],
            fontSize=8, textColor=GRIS_TEXT, spaceBefore=10, spaceAfter=4,
            fontName="Helvetica-Bold"),
        "seccion_verde": ParagraphStyle(
            "seccion_verde", parent=base["Normal"],
            fontSize=8, textColor=c1, spaceBefore=8, spaceAfter=3,
            fontName="Helvetica-Bold"),
        "normal": ParagraphStyle(
            "normal", parent=base["Normal"],
            fontSize=10, textColor=GRIS_DARK,
            fontName="Helvetica"),
        "normal_small": ParagraphStyle(
            "normal_small", parent=base["Normal"],
            fontSize=8.5, textColor=GRIS_DARK,
            fontName="Helvetica"),
        "bold": ParagraphStyle(
            "bold", parent=base["Normal"],
            fontSize=10, textColor=GRIS_DARK,
            fontName="Helvetica-Bold"),
        "bold_verde": ParagraphStyle(
            "bold_verde", parent=base["Normal"],
            fontSize=10, textColor=c1,
            fontName="Helvetica-Bold"),
        "centro": ParagraphStyle(
            "centro", parent=base["Normal"],
            fontSize=9, alignment=TA_CENTER,
            textColor=GRIS_TEXT, fontName="Helvetica"),
        "codigo": ParagraphStyle(
            "codigo", parent=base["Normal"],
            fontSize=22, textColor=c1,
            fontName="Helvetica-Bold", spaceAfter=4),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"],
            fontSize=8, alignment=TA_CENTER,
            textColor=GRIS_TEXT, fontName="Helvetica"),
        "etiqueta": ParagraphStyle(
            "etiqueta", parent=base["Normal"],
            fontSize=7.5, textColor=GRIS_TEXT,
            fontName="Helvetica-Bold"),
        "valor": ParagraphStyle(
            "valor", parent=base["Normal"],
            fontSize=10, textColor=GRIS_DARK,
            fontName="Helvetica"),
        "monto_total": ParagraphStyle(
            "monto_total", parent=base["Normal"],
            fontSize=13, textColor=c1,
            fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "monto_rojo": ParagraphStyle(
            "monto_rojo", parent=base["Normal"],
            fontSize=13, textColor=ROJO,
            fontName="Helvetica-Bold", alignment=TA_RIGHT),
    }


def _encabezado_diseno(st, ancho_util, diseno="clasico"):
    """Genera encabezado según el diseño."""
    colores = DISENOS_DISPONIBLES.get(diseno, DISENOS_DISPONIBLES["clasico"])
    c1 = colors.HexColor(colores["color_principal"])
    
    elementos = []
    
    if diseno == "minimalista":
        # Minimalista: solo texto simple
        elementos.append(Paragraph(EMPRESA_NOMBRE, st["titulo"]))
        elementos.append(HRFlowable(width="100%", thickness=1, color=GRIS_TEXT, spaceAfter=8))
    elif diseno == "elegante":
        # Elegante: fondo oscuro
        hdr_data = [[Paragraph(f"<b>{EMPRESA_NOMBRE}</b>", 
                     ParagraphStyle("hdr_e", fontName="Helvetica-Bold", fontSize=16, 
                                    textColor=colors.white, alignment=TA_CENTER))]]
        hdr_t = Table(hdr_data, colWidths=[ancho_util])
        hdr_t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), c1),
            ("TOPPADDING", (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ]))
        elementos.append(hdr_t)
        elementos.append(Spacer(1, 8))
    elif diseno == "moderno":
        # Moderno: con línea de color
        elementos.append(Paragraph(f"📦 {EMPRESA_NOMBRE}", st["titulo"]))
        elementos.append(HRFlowable(width="100%", thickness=3, color=c1, spaceAfter=8))
    else:
        # Clásico: encabezado estándar
        elementos.append(Paragraph(f"📦 {EMPRESA_NOMBRE}", st["titulo"]))
        elementos.append(Paragraph(EMPRESA_SLOGAN, st["subtitulo"]))
        elementos.append(HRFlowable(width="100%", thickness=2, color=VERDE, spaceAfter=8))
    
    return elementos


def vista_previa_recibo(db, envio_id, diseno="clasico", ancho_max=400, alto_max=500):
    """
    Genera una imagen de vista previa del recibo.
    Retorna una imagen PIL o None si hay error.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    
    env = db.obtener_envio(envio_id)
    if not env:
        return None
    
    # Colores del diseño
    colores = DISENOS_DISPONIBLES.get(diseno, DISENOS_DISPONIBLES["clasico"])
    c1 = colores["color_principal"]
    c2 = colores["color_secundario"]
    
    # Crear imagen
    img = Image.new("RGB", (ancho_max, alto_max), "#ffffff")
    draw = ImageDraw.Draw(img)
    
    y = 20
    
    # Header según diseño
    if diseno == "elegante":
        draw.rectangle([0, 0, ancho_max, 60], fill=c1)
        try:
            font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font_title = ImageFont.load_default()
        draw.text((ancho_max//2 - 80, 20), EMPRESA_NOMBRE, fill="#ffffff", font=font_title)
        y = 80
    elif diseno == "minimalista":
        try:
            font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        except:
            font_title = ImageFont.load_default()
        draw.text((20, y), EMPRESA_NOMBRE, fill="#333333", font=font_title)
        y += 35
        draw.line([(20, y), (ancho_max-20, y)], fill="#cccccc", width=1)
        y += 15
    else:
        try:
            font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        except:
            font_title = ImageFont.load_default()
        draw.text((20, y), f"📦 {EMPRESA_NOMBRE}", fill=c1, font=font_title)
        y += 35
        draw.line([(20, y), (ancho_max-20, y)], fill=c1 if diseno == "moderno" else "#0f6e56", 
                  width=3 if diseno == "moderno" else 2)
        y += 15
    
    # Código y estado
    try:
        font_code = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
    except:
        font_code = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.text((20, y), env.get("codigo", ""), fill=c1, font=font_code)
    
    # Estado con color
    estado = env.get("estado", "Pendiente")
    estado_colores = {"Pagado": "#28a745", "Abono": "#007bff", "Pendiente": "#fd7e14"}
    draw.text((200, y+2), estado, fill=estado_colores.get(estado, "#666666"), font=font_small)
    y += 30
    
    # Fecha
    draw.text((20, y), env.get("fecha", ""), fill="#888888", font=font_small)
    y += 25
    
    # Remitente y destinatario
    draw.rectangle([20, y, ancho_max//2-10, y+60], outline="#0f6e56", width=1)
    draw.rectangle([ancho_max//2+10, y, ancho_max-20, y+60], outline="#0c447c", width=1)
    
    draw.text((25, y+5), "ENTREGA:", fill="#0f6e56", font=font_small)
    draw.text((25, y+20), env.get("ent_nombre", "—")[:20], fill="#333333", font=font_small)
    draw.text((ancho_max//2+15, y+5), "RECIBE:", fill="#0c447c", font=font_small)
    draw.text((ancho_max//2+15, y+20), env.get("rec_nombre", "—")[:20], fill="#333333", font=font_small)
    y += 75
    
    # Destino
    destino = env.get("destino_usa", "")
    if destino and destino != "Sin asignar":
        draw.rectangle([20, y, ancho_max-20, y+25], fill="#e1f5ee")
        draw.text((25, y+5), f"🗺️ Destino: {destino}", fill="#0f6e56", font=font_small)
        y += 35
    
    # Artículos (resumen)
    draw.line([(20, y), (ancho_max-20, y)], fill="#cccccc", width=1)
    y += 10
    draw.text((20, y), "ARTÍCULOS:", fill="#333333", font=font_small)
    y += 20
    
    arts = db.obtener_articulos(envio_id)
    for i, art in enumerate(arts[:5]):  # Mostrar solo primeros 5
        desc = art.get("descripcion", "")[:25]
        draw.text((30, y), f"• {desc}", fill="#333333", font=font_small)
        y += 18
    if len(arts) > 5:
        draw.text((30, y), f"... y {len(arts)-5} más", fill="#888888", font=font_small)
        y += 18
    
    # Total
    y += 10
    draw.line([(20, y), (ancho_max-20, y)], fill="#cccccc", width=1)
    y += 10
    draw.text((20, y), "TOTAL:", fill="#333333", font=font_code)
    draw.text((ancho_max-100, y), f"${env.get('total', 0):,.2f}", fill=c1, font=font_code)
    
    return img


def generar_miniatura_pdf(db, envio_id, diseno="clasico", ruta_temp=None):
    """Genera un PDF pequeño para vista previa."""
    if ruta_temp is None:
        ruta_temp = os.path.join(_carpeta_salida(), f"preview_{diseno}.pdf")
    
    env = db.obtener_envio(envio_id)
    if not env:
        return None
    
    doc = SimpleDocTemplate(
        ruta_temp, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1*cm, bottomMargin=1*cm
    )
    
    st = _estilos_diseno(diseno)
    ancho_util = A4[0] - 3*cm
    story = []
    
    # Encabezado según diseño
    story += _encabezado_diseno(st, ancho_util, diseno)
    
    # Código y estado
    est_bg, est_fg = ESTADO_COLORES.get(env["estado"], (GRIS_LIGHT, GRIS_DARK))
    estado_p = Paragraph(
        f'<font color="#{est_fg.hexval()[2:]}"><b>  {env["estado"]}  </b></font>',
        ParagraphStyle("e", fontName="Helvetica-Bold", fontSize=11,
                       backColor=est_bg, borderPadding=5))
    
    hdr_data = [[
        Paragraph(env["codigo"], st["codigo"]),
        estado_p,
        Paragraph(env["fecha"],
                  ParagraphStyle("f", fontName="Helvetica", fontSize=9,
                                 textColor=GRIS_TEXT, alignment=TA_RIGHT))
    ]]
    hdr_t = Table(hdr_data, colWidths=[7*cm, 4*cm, None])
    hdr_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(hdr_t)
    story.append(Spacer(1, 8))
    
    # Remitente y destinatario
    personas_data = [[
        [Paragraph("ENTREGA", st["seccion_verde"]),
         Paragraph(f"<b>{env.get('ent_nombre', '—')}</b>", st["bold"])],
        [Paragraph("RECIBE", st["seccion_verde"]),
         Paragraph(f"<b>{env.get('rec_nombre', '—')}</b>", st["bold"])],
    ]]
    personas_t = Table(personas_data, colWidths=[ancho_util/2, ancho_util/2])
    personas_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), VERDE_LIGHT),
        ("BACKGROUND", (1, 0), (1, -1), AZUL_LIGHT),
        ("BOX", (0, 0), (0, -1), 0.5, VERDE),
        ("BOX", (1, 0), (1, -1), 0.5, AZUL),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(personas_t)
    story.append(Spacer(1, 10))
    
    # Total
    restante = float(env.get("restante", 0))
    tot_data = [
        [Paragraph("<b>Total encomienda</b>", st["bold"]),
         Paragraph(f"<b>${env['total']:,.2f}</b>", st["monto_total"])],
    ]
    tot_t = Table(tot_data, colWidths=[ancho_util-6*cm, 6*cm], hAlign="RIGHT")
    tot_t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.5, VERDE),
        ("BACKGROUND", (0, 0), (-1, 0), VERDE_LIGHT),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tot_t)
    
    # Pie
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0d8"), spaceAfter=6))
    story.append(Paragraph(f"Vista previa - Diseño: {DISENOS_DISPONIBLES.get(diseno, {}).get('nombre', diseno)}", st["pie"]))
    
    doc.build(story)
    return ruta_temp
