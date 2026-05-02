# ══════════════════════════════════════════════════════════════════
#  DisateQ Motor CPE v5.0  —  wizard_mapper.py
#  Motor heurístico de mapeo de campos a estructura CPE
#  IA (Claude API) solo como fallback cuando heurística falla
#  2026-05-01
# ══════════════════════════════════════════════════════════════════

from __future__ import annotations
from pathlib import Path
from typing import Any


# ── Patrones conocidos por campo CPE ──────────────────────────────
# Cada entrada: campo_cpe → lista de patrones (substring case-insensitive)
# Orden importa: primero el más específico

PATRONES_COMPROBANTE = {
    "flag_campo":  ["flag_envi", "flag_env", "estado_env", "pendiente_"],
    "numero":      ["nro_movi", "num_movi", "nro_comp", "num_comp", "numero_fac",
                    "nro_fac", "num_fac", "nro_doc", "correlat"],
    "serie":       ["serie_fac", "serie_comp", "serie_doc", "serie"],
    "tipo_doc":    ["tipo_fact", "tipo_comp", "tipo_doc", "tipo_movi", "tipo_cbte"],
    "fecha":       ["fec_emi", "fecha_emi", "fec_comp", "fecha_comp", "fec_doc",
                    "fecha_doc", "fec_venta", "fecha_ven"],
    "ruc_cliente": ["ruc_cli", "ruc_clien", "doc_ident", "nro_doc_cli",
                    "dni_cli", "ruc_comp"],
    "nombre_cliente": ["nom_cli", "nomb_cli", "razon_cli", "nombre_cli",
                       "razon_soc", "nombres"],
    "total":       ["tot_pagar", "tot_venta", "total_vta", "importe_tot",
                    "monto_tot", "tot_comp", "total_comp", "importe"],
    "igv":         ["igv", "monto_igv", "tot_igv"],
    "subtotal":    ["subtotal", "base_imp", "val_venta", "monto_base"],
}

PATRONES_ITEMS = {
    "join_campo":   ["nro_movi", "num_movi", "nro_comp", "nro_doc", "nro_fac"],
    "codigo":       ["cod_prod", "codigo_prod", "cod_art", "codigo_art",
                     "cod_item", "codigo_item", "sku"],
    "descripcion":  ["nom_prod", "desc_prod", "nombre_prod", "descrip",
                     "nom_art", "nombre_art", "detalle"],
    "cantidad":     ["cant_vend", "cantidad", "cant_prod", "qty", "cant_item"],
    "precio":       ["pre_venta", "precio_uni", "precio_vta", "p_unit",
                     "prec_unit", "valor_unit"],
    "precio_igv":   ["pre_igv", "precio_igv", "p_igv"],
}

PATRONES_TABLA_COMP = [
    "enviosffee", "comprobante", "factura", "boleta", "venta",
    "cabecera", "cabventa", "docventa", "movimiento",
]

PATRONES_TABLA_ITEMS = [
    "detalleventa", "detalle", "items", "lineas", "detfactura",
    "detboleta", "detcomp", "detmovim",
]

PATRONES_TABLA_ANULACION = [
    "notacredito", "anulacion", "nota_cred", "devolucion",
]

# ── Valores de flag conocidos ─────────────────────────────────────
FLAG_VALORES_PENDIENTE = ["2", "P", "PENDIENTE", "0"]


# ══════════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def mapear_dbf(carpeta: str) -> dict:
    """
    Analiza todos los DBFs de la carpeta y retorna un contrato
    pre-llenado con scores de confianza por campo.

    Retorna:
    {
      ok: bool,
      score_global: float (0-1),
      contrato: { tabla, flag_campo, flag_valor, flag_tipo, campos, items },
      scores: { campo: float },   # confianza por campo
      sin_resolver: [ campo ],    # campos que necesitan input manual
      tablas_analizadas: int,
    }
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

    # ── 1. Leer estructura de cada DBF (sin datos) ────────────────
    tablas: dict[str, list[str]] = {}
    for dbf_path in dbfs:
        try:
            t = DbfReader(str(dbf_path), encoding="latin-1", load=False)
            nombre = dbf_path.stem.lower()
            tablas[nombre] = [f.name.upper() for f in t.fields]
        except Exception:
            pass

    if not tablas:
        return {"ok": False, "error": "No se pudo leer ningún DBF"}

    # ── 2. Identificar tabla de comprobantes ──────────────────────
    tabla_comp, score_tc = _identificar_tabla(tablas, PATRONES_TABLA_COMP,
                                               list(PATRONES_COMPROBANTE.keys()))

    # ── 3. Identificar tabla de ítems ─────────────────────────────
    tabla_items, score_ti = _identificar_tabla(tablas, PATRONES_TABLA_ITEMS,
                                                list(PATRONES_ITEMS.keys()))

    # ── 4. Identificar tabla de anulaciones ──────────────────────
    tabla_anul, _ = _identificar_tabla(tablas, PATRONES_TABLA_ANULACION, [])

    # ── 5. Mapear campos de la tabla de comprobantes ──────────────
    campos_comp  = tablas.get(tabla_comp, []) if tabla_comp else []
    mapeo_comp   = {}
    scores_comp  = {}

    for campo_cpe, patrones in PATRONES_COMPROBANTE.items():
        match, score = _buscar_campo(campos_comp, patrones)
        mapeo_comp[campo_cpe]  = match or ""
        scores_comp[campo_cpe] = score

    # ── 6. Detectar flag_campo y flag_valor ───────────────────────
    flag_campo, flag_score = _buscar_campo(campos_comp,
                                            PATRONES_COMPROBANTE["flag_campo"])
    flag_valor = ""
    flag_tipo  = "integer"

    if flag_campo and tabla_comp:
        flag_valor, flag_tipo = _detectar_flag_valor(
            str(carpeta_path / (tabla_comp + ".dbf")), flag_campo)

    mapeo_comp["flag_campo"] = flag_campo or ""
    scores_comp["flag_campo"] = flag_score

    # ── 7. Mapear campos de ítems ─────────────────────────────────
    campos_items = tablas.get(tabla_items, []) if tabla_items else []
    mapeo_items  = {}
    scores_items = {}

    for campo_cpe, patrones in PATRONES_ITEMS.items():
        match, score = _buscar_campo(campos_items, patrones)
        mapeo_items[campo_cpe]  = match or ""
        scores_items[campo_cpe] = score

    # ── 8. Score global ───────────────────────────────────────────
    campos_criticos = ["numero", "serie", "tipo_doc", "fecha", "total",
                       "flag_campo"]
    scores_todos    = {**scores_comp, **scores_items}
    score_criticos  = sum(scores_todos.get(c, 0) for c in campos_criticos)
    score_global    = round(score_criticos / len(campos_criticos), 3)

    # ── 9. Campos sin resolver ────────────────────────────────────
    sin_resolver = [c for c in campos_criticos
                    if scores_todos.get(c, 0) < 0.5]

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
                "tabla":      tabla_items or "",
                "join_campo": mapeo_items.get("join_campo", ""),
                "codigo":     mapeo_items.get("codigo", ""),
                "descripcion":mapeo_items.get("descripcion", ""),
                "cantidad":   mapeo_items.get("cantidad", ""),
                "precio":     mapeo_items.get("precio", ""),
            },
        },
        "scores":      scores_todos,
        "sin_resolver": sin_resolver,
        "tabla_anulacion": tabla_anul or "",
    }


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def _identificar_tabla(
    tablas: dict[str, list[str]],
    patrones_nombre: list[str],
    campos_esperados: list[str],
) -> tuple[str | None, float]:
    """
    Identifica la tabla más probable por:
    1. Match de nombre con patrones_nombre
    2. Cantidad de campos esperados que contiene
    """
    mejor_tabla  = None
    mejor_score  = 0.0

    for nombre, campos in tablas.items():
        score = 0.0
        campos_lower = [c.lower() for c in campos]

        # Score por nombre de tabla
        for i, patron in enumerate(patrones_nombre):
            if patron in nombre:
                score += 1.0 - (i * 0.05)  # más score al primer patron
                break

        # Score por campos que contiene
        if campos_esperados:
            hits = 0
            for campo_cpe in campos_esperados[:8]:
                patrones = (PATRONES_COMPROBANTE.get(campo_cpe) or
                            PATRONES_ITEMS.get(campo_cpe) or [])
                for p in patrones:
                    if any(p in c for c in campos_lower):
                        hits += 1
                        break
            score += hits / len(campos_esperados[:8])

        if score > mejor_score:
            mejor_score = score
            mejor_tabla = nombre

    return mejor_tabla, round(mejor_score, 3)


def _buscar_campo(
    campos: list[str],
    patrones: list[str],
) -> tuple[str | None, float]:
    """
    Busca el campo más probable en la lista de campos del DBF.
    Retorna (nombre_campo_real, score 0-1).
    """
    campos_lower = [(c, c.lower()) for c in campos]

    for i, patron in enumerate(patrones):
        # Match exacto
        for nombre, lower in campos_lower:
            if lower == patron:
                return nombre, 1.0

        # Match parcial — el patrón es substring del campo
        for nombre, lower in campos_lower:
            if patron in lower:
                score = 0.95 - (i * 0.05)
                return nombre, max(score, 0.5)

    return None, 0.0


def _detectar_flag_valor(
    dbf_path: str,
    flag_campo: str,
) -> tuple[str, str]:
    """
    Lee los primeros 20 registros del DBF para detectar
    el valor del flag de pendiente y su tipo.
    """
    try:
        from dbfread import DBF as DbfReader
        t = DbfReader(dbf_path, encoding="latin-1", load=False)
        valores = set()
        for i, rec in enumerate(t):
            if i >= 20:
                break
            v = rec.get(flag_campo)
            if v is not None:
                valores.add(v)

        # Detectar tipo
        tipos = {type(v).__name__ for v in valores}
        if "int" in tipos or all(
            str(v).strip().lstrip("-").isdigit() for v in valores if v is not None
        ):
            flag_tipo = "integer"
            # Buscar valor que coincida con pendiente conocido
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
