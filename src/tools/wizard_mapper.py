# ══════════════════════════════════════════════════════════════════
#  DisateQ Motor CPE v5.0  —  wizard_mapper.py
#  Motor heurístico de mapeo de campos a estructura CPE
#  FIX-WIZ-03: patrones ampliados para sistemas FoxPro/farmacia
#  FIX-WIZ-04: busca fecha y total en tabla de totales
#  FIX-WIZ-05: tabla de comprobantes identificada por campo flag
#               de envio (FLAG_ENVIO, FLAG_ENV, etc.) como criterio
#               principal — evita confusion con tabla de totales
# ══════════════════════════════════════════════════════════════════

from __future__ import annotations
from pathlib import Path


# ── Patrones de campo flag de envio ──────────────────────────────
# La tabla que tiene estos campos ES la tabla de comprobantes
PATRONES_FLAG_ENVIO = [
    "flag_envi", "flag_env", "estado_env", "pendiente_env",
    "flag_cpe", "estado_cpe", "enviado",
]

# ── Patrones conocidos por campo CPE ──────────────────────────────
PATRONES_COMPROBANTE = {
    "flag_campo":  ["flag_envi", "flag_env", "estado_env", "pendiente_"],
    "numero":      ["numero_fac", "nro_movi", "num_movi", "nro_comp", "num_comp",
                    "nro_fac", "num_fac", "nro_doc", "correlat"],
    "serie":       ["serie_fac", "serie_comp", "serie_doc", "serie"],
    "tipo_doc":    ["tipo_fact", "tipo_factu", "tipo_comp", "tipo_doc",
                    "tipo_movi", "tipo_cbte"],
    "fecha":       ["fecha_docu", "fec_emi", "fecha_emi", "fecha_fact",
                    "fec_comp", "fecha_comp", "fec_doc", "fecha_doc",
                    "fec_venta", "fecha_ven"],
    "ruc_cliente": ["ruc_cli", "ruc_clien", "ruc_client", "doc_ident",
                    "nro_doc_cli", "dni_cli", "ruc_comp"],
    "nombre_cliente": ["nombre_cli", "nom_cli", "nomb_cli", "razon_cli",
                       "nombre_clie", "razon_soc", "nombres"],
    "total":       ["real_factu", "real_fact", "real_fac", "tot_pagar",
                    "tot_venta", "total_vta", "importe_tot", "monto_tot",
                    "tot_comp", "total_comp", "importe"],
    "igv":         ["igv_factur", "igv", "monto_igv", "tot_igv"],
    "subtotal":    ["monto_fact", "subtotal", "base_imp", "val_venta", "monto_base"],
}

PATRONES_ITEMS = {
    "join_campo":   ["numero_fac", "nro_movi", "num_movi", "nro_comp",
                     "nro_doc", "nro_fac", "num_fac"],
    "codigo":       ["codigo_pro", "cod_prod", "codigo_prod", "cod_art",
                     "codigo_art", "cod_item", "codigo_item", "sku"],
    "descripcion":  ["detalle_se", "nom_prod", "desc_prod", "nombre_prod",
                     "descrip", "nom_art", "nombre_art", "detalle"],
    "cantidad":     ["cantidad_p", "cant_vend", "cantidad", "cant_prod",
                     "qty", "cant_item"],
    "precio":       ["precio_uni", "pre_venta", "precio_vta", "p_unit",
                     "prec_unit", "valor_unit"],
    "precio_igv":   ["pre_igv", "precio_igv", "p_igv"],
}

# Nombres de tabla secundarios (usados solo si no se encuentra por flag)
PATRONES_TABLA_COMP_FALLBACK = [
    "enviosffee", "comprobante", "boleta", "venta",
    "cabventa", "docventa", "movimiento",
]

PATRONES_TABLA_ITEMS = [
    "detalleventa", "detalle", "items", "lineas", "detfactura",
    "detboleta", "detcomp", "detmovim",
]

PATRONES_TABLA_ANULACION = [
    "notacredito", "anulacion", "nota_cred", "devolucion",
]

# Campos que identifican la tabla de totales
CAMPOS_TOTALES = {'REAL_FACTU', 'MONTO_FACT', 'IGV_FACTUR', 'TOTAL_FACT',
                  'IMPORTE_TO', 'TOTAL_PAGO', 'MONTO_TOTA', 'REAL_FACTU'}

PATRONES_TABLA_TOTALES = [
    "factura", "cabecera", "comprobante", "venta",
    "cabventa", "cab_venta", "cpe", "documento",
]

FLAG_VALORES_PENDIENTE = ["2", "P", "PENDIENTE", "0"]


# ══════════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def mapear_dbf(carpeta: str) -> dict:
    """
    Analiza todos los DBFs de la carpeta y retorna un contrato
    pre-llenado con scores de confianza por campo.
    """
    try:
        from dbfread import DBF as DbfReader
    except ImportError:
        return {"ok": False, "error": "dbfread no instalado"}

    carpeta_path = Path(carpeta)
    if not carpeta_path.exists():
        return {"ok": False, "error": f"Carpeta no existe: {carpeta}"}

    dbfs = sorted(list(carpeta_path.glob("*.dbf")) +
                  list(carpeta_path.glob("*.DBF")))
    if not dbfs:
        return {"ok": False, "error": "No hay archivos DBF"}

    # 1. Leer estructura de cada DBF
    tablas: dict[str, list[str]] = {}
    for dbf_path in dbfs:
        try:
            t = DbfReader(str(dbf_path), encoding="latin-1", load=False)
            nombre = dbf_path.stem.lower()
            tablas[nombre] = [f.name.upper() for f in t.fields]
        except Exception:
            pass

    if not tablas:
        return {"ok": False, "error": "No se pudo leer ningun DBF"}

    # 2. FIX-WIZ-05: Identificar tabla de comprobantes por campo flag
    tabla_comp = _identificar_tabla_por_flag(tablas)

    # Si no se encontro por flag, usar patrones de nombre como fallback
    if not tabla_comp:
        tabla_comp, _ = _identificar_tabla_por_nombre(
            tablas, PATRONES_TABLA_COMP_FALLBACK)

    # 3. Identificar tabla de items
    tabla_items, _ = _identificar_tabla_por_nombre(
        tablas, PATRONES_TABLA_ITEMS)

    # 4. Identificar tabla de anulaciones
    tabla_anul, _ = _identificar_tabla_por_nombre(
        tablas, PATRONES_TABLA_ANULACION)

    # 5. Identificar tabla de totales (distinta a la de comprobantes)
    tabla_totales = _identificar_tabla_totales(tablas, tabla_comp)

    # 6. Mapear campos de la tabla de comprobantes
    campos_comp = tablas.get(tabla_comp, []) if tabla_comp else []
    mapeo_comp  = {}
    scores_comp = {}

    for campo_cpe, patrones in PATRONES_COMPROBANTE.items():
        match, score = _buscar_campo(campos_comp, patrones)
        mapeo_comp[campo_cpe]  = match or ""
        scores_comp[campo_cpe] = score

    # 7. FIX-WIZ-04: Para campos no encontrados en tabla de comprobantes,
    #    buscar en tabla de totales
    if tabla_totales and tabla_totales != tabla_comp:
        campos_tot = tablas.get(tabla_totales, [])
        campos_secundarios = ["fecha", "total", "igv", "subtotal",
                               "ruc_cliente", "nombre_cliente"]
        for campo_cpe in campos_secundarios:
            if scores_comp.get(campo_cpe, 0) < 0.5:
                patrones = PATRONES_COMPROBANTE.get(campo_cpe, [])
                match, score = _buscar_campo(campos_tot, patrones)
                if score >= 0.5:
                    mapeo_comp[campo_cpe]  = match
                    scores_comp[campo_cpe] = score

    # 8. Detectar flag_campo y flag_valor
    flag_campo = mapeo_comp.get("flag_campo", "")
    flag_score = scores_comp.get("flag_campo", 0)
    flag_valor = ""
    flag_tipo  = "integer"

    if not flag_campo:
        # Buscar flag directamente en los campos de la tabla de comprobantes
        flag_campo, flag_score = _buscar_campo(campos_comp,
                                               PATRONES_COMPROBANTE["flag_campo"])
        mapeo_comp["flag_campo"]  = flag_campo or ""
        scores_comp["flag_campo"] = flag_score

    if flag_campo and tabla_comp:
        dbf_path_str = str(carpeta_path / (tabla_comp + ".dbf"))
        if not Path(dbf_path_str).exists():
            dbf_path_str = str(carpeta_path / (tabla_comp + ".DBF"))
        flag_valor, flag_tipo = _detectar_flag_valor(dbf_path_str, flag_campo)

    # 9. Mapear campos de items
    campos_items = tablas.get(tabla_items, []) if tabla_items else []
    mapeo_items  = {}
    scores_items = {}

    for campo_cpe, patrones in PATRONES_ITEMS.items():
        match, score = _buscar_campo(campos_items, patrones)
        mapeo_items[campo_cpe]  = match or ""
        scores_items[campo_cpe] = score

    # 10. Score global
    campos_criticos = ["numero", "serie", "tipo_doc", "fecha", "total", "flag_campo"]
    scores_todos    = {**scores_comp, **scores_items}
    score_criticos  = sum(scores_todos.get(c, 0) for c in campos_criticos)
    score_global    = round(score_criticos / len(campos_criticos), 3)

    # 11. Campos sin resolver
    sin_resolver = [c for c in campos_criticos if scores_todos.get(c, 0) < 0.5]

    return {
        "ok":               True,
        "score_global":     score_global,
        "tablas_analizadas": len(tablas),
        "contrato": {
            "tabla":      tabla_comp or "",
            "flag_campo": flag_campo or "",
            "flag_valor": flag_valor,
            "flag_tipo":  flag_tipo,
            "campos":     {k: v for k, v in mapeo_comp.items()
                           if k != "flag_campo" and v},
            "items": {
                "tabla":       tabla_items or "",
                "join_campo":  mapeo_items.get("join_campo", ""),
                "codigo":      mapeo_items.get("codigo", ""),
                "descripcion": mapeo_items.get("descripcion", ""),
                "cantidad":    mapeo_items.get("cantidad", ""),
                "precio":      mapeo_items.get("precio", ""),
            },
        },
        "scores":          scores_todos,
        "sin_resolver":    sin_resolver,
        "tabla_anulacion": tabla_anul or "",
        "tabla_totales":   tabla_totales or tabla_comp or "",
    }


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def _identificar_tabla_por_flag(
    tablas: dict[str, list[str]]
) -> str | None:
    """
    FIX-WIZ-05: Identifica la tabla de comprobantes buscando la que
    tiene un campo de flag de envio (FLAG_ENVIO, FLAG_ENV, etc.).
    Esta es la señal mas confiable — la tabla de pendientes SIEMPRE
    tiene un campo flag para marcar enviados/errores.
    """
    for nombre, campos in tablas.items():
        campos_lower = [c.lower() for c in campos]
        for patron in PATRONES_FLAG_ENVIO:
            if any(patron in c for c in campos_lower):
                return nombre
    return None


def _identificar_tabla_totales(
    tablas: dict[str, list[str]],
    tabla_comp: str | None,
) -> str | None:
    """
    Identifica la tabla que contiene los campos financieros del comprobante.
    Si la tabla de comprobantes ya los tiene, la retorna.
    Si no, busca en otras tablas.
    """
    if tabla_comp:
        campos = set(tablas.get(tabla_comp, []))
        if campos & CAMPOS_TOTALES:
            return tabla_comp

    for nombre in PATRONES_TABLA_TOTALES:
        if nombre == tabla_comp:
            continue
        campos = set(tablas.get(nombre, []))
        if campos & CAMPOS_TOTALES:
            return nombre

    for nombre, campos_lista in tablas.items():
        if nombre == tabla_comp:
            continue
        if set(campos_lista) & CAMPOS_TOTALES:
            return nombre

    return tabla_comp


def _identificar_tabla_por_nombre(
    tablas: dict[str, list[str]],
    patrones_nombre: list[str],
) -> tuple[str | None, float]:
    """Identifica tabla por nombre usando lista de patrones."""
    for patron in patrones_nombre:
        for nombre in tablas:
            if patron in nombre:
                return nombre, 1.0
    return None, 0.0


def _buscar_campo(
    campos: list[str],
    patrones: list[str],
) -> tuple[str | None, float]:
    campos_lower = [(c, c.lower()) for c in campos]

    for i, patron in enumerate(patrones):
        # Match exacto
        for nombre, lower in campos_lower:
            if lower == patron:
                return nombre, 1.0
        # Match parcial
        for nombre, lower in campos_lower:
            if patron in lower:
                score = 0.95 - (i * 0.05)
                return nombre, max(score, 0.5)

    return None, 0.0


def _detectar_flag_valor(
    dbf_path: str,
    flag_campo: str,
) -> tuple[str, str]:
    try:
        from dbfread import DBF as DbfReader
        if not Path(dbf_path).exists():
            return "2", "integer"
        t = DbfReader(dbf_path, encoding="latin-1", load=False)
        valores = set()
        for i, rec in enumerate(t):
            if i >= 20:
                break
            v = rec.get(flag_campo)
            if v is not None:
                valores.add(v)

        tipos = {type(v).__name__ for v in valores}
        if "int" in tipos or all(
            str(v).strip().lstrip("-").isdigit() for v in valores if v is not None
        ):
            flag_tipo = "integer"
            for v in valores:
                if str(v).strip() in FLAG_VALORES_PENDIENTE:
                    return str(v).strip(), "integer"
            return "2", "integer"
        else:
            flag_tipo = "string"
            for v in valores:
                if str(v).strip() in FLAG_VALORES_PENDIENTE:
                    return str(v).strip(), "string"
            return "2", "string"
    except Exception:
        return "2", "integer"
