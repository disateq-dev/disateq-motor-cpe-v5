# ══════════════════════════════════════════════════════════════════
#  DisateQ Motor CPE v5.0  —  contract_validator.py
#  TASK-007: Valida contrato YAML contra la fuente de datos real
#  Retorna score 0-1 + errores/advertencias por severidad
# ══════════════════════════════════════════════════════════════════

from __future__ import annotations
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)


# ── Campos criticos — si fallan, score cae drasticamente ──────────
CAMPOS_CRITICOS = [
    ("comprobantes", "tabla"),
    ("comprobantes", "flag_lectura.campo"),
    ("comprobantes", "flag_lectura.valor"),
]

# ── Campos de comprobante que deben existir en el DBF ─────────────
CAMPOS_COMPROBANTE_CONOCIDOS = [
    "TIPO_FACTU", "SERIE_FACT", "NUMERO_FAC", "FECHA_DOCU",
    "FLAG_ENVIO", "FACTURA_EX",
]


# ══════════════════════════════════════════════════════════════════
#  RESULTADO
# ══════════════════════════════════════════════════════════════════

class ValidacionResultado:
    """
    Resultado de una validacion de contrato.

    score:       float 0-1 — 1.0 = perfecto, < 0.5 = contrato roto
    errores:     lista de str — problemas que impiden el procesamiento
    advertencias: lista de str — problemas que pueden causar resultados parciales
    info:        lista de str — observaciones sin impacto
    ok:          bool — True si score >= 0.60 y no hay errores criticos
    """
    def __init__(self):
        self.score:        float      = 0.0
        self.errores:      list[str]  = []
        self.advertencias: list[str]  = []
        self.info:         list[str]  = []

    @property
    def ok(self) -> bool:
        return self.score >= 0.60 and len(self.errores) == 0

    def to_dict(self) -> dict:
        return {
            "ok":           self.ok,
            "score":        round(self.score, 3),
            "errores":      self.errores,
            "advertencias": self.advertencias,
            "info":         self.info,
        }


# ══════════════════════════════════════════════════════════════════
#  VALIDADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def validar_contrato(contrato: dict, fuente: dict | None = None) -> ValidacionResultado:
    """
    Valida un contrato YAML contra la fuente de datos real.

    contrato: dict con estructura GenericAdapter v5
    fuente:   dict opcional con {tipo, ruta} — si None, se lee desde contrato['source']

    Retorna ValidacionResultado.
    """
    r = ValidacionResultado()

    # ── Resolver fuente ───────────────────────────────────────────
    if fuente is None:
        src = contrato.get("source", {})
        tipo = src.get("type", "dbf").lower()
        ruta = src.get("path", "")
    else:
        tipo = fuente.get("tipo", "dbf").lower()
        ruta = fuente.get("ruta", "")

    # ── Validaciones por tipo ─────────────────────────────────────
    if tipo == "dbf":
        _validar_dbf(contrato, ruta, r)
    else:
        r.info.append(f"Validacion detallada no disponible para tipo '{tipo}'. Verificacion estructural solamente.")
        _validar_estructura(contrato, r)

    return r


def validar_contrato_desde_alias(alias: str) -> ValidacionResultado:
    """
    Carga el contrato del cliente por alias y lo valida.
    Usado desde api.py → validar_contrato(alias).
    """
    import yaml
    from src.config.client_loader import ClientLoader

    r = ValidacionResultado()
    try:
        loader = ClientLoader()
        cfg    = loader.cargar(alias)
    except Exception as exc:
        r.errores.append(f"No se pudo cargar el cliente '{alias}': {exc}")
        return r

    contrato_path_str = cfg.fuente.get("contrato_path", "")
    if not contrato_path_str:
        r.errores.append("El YAML del cliente no tiene 'contrato_path' definido.")
        return r

    contrato_path = Path(contrato_path_str)
    if not contrato_path.exists():
        r.errores.append(f"Contrato no encontrado: {contrato_path}")
        return r

    try:
        with open(contrato_path, encoding="utf-8") as f:
            contrato = yaml.safe_load(f)
    except Exception as exc:
        r.errores.append(f"Error leyendo contrato YAML: {exc}")
        return r

    fuente = {
        "tipo": cfg.tipo_fuente,
        "ruta": cfg.rutas_fuente[0] if cfg.rutas_fuente else "",
    }
    return validar_contrato(contrato, fuente)


# ══════════════════════════════════════════════════════════════════
#  VALIDACION DBF
# ══════════════════════════════════════════════════════════════════

def _validar_dbf(contrato: dict, ruta: str, r: ValidacionResultado) -> None:
    """Valida contrato DBF en 5 pasos."""

    # Paso 1 — Estructura minima del contrato
    _validar_estructura(contrato, r)
    if r.errores:
        # Sin estructura no hay nada que validar contra la fuente
        _calcular_score(r, pasos_ok=0, pasos_total=5)
        return

    # Paso 2 — Carpeta fuente existe
    carpeta = Path(ruta)
    if not carpeta.exists():
        r.errores.append(f"Carpeta fuente no existe: {ruta}")
        _calcular_score(r, pasos_ok=1, pasos_total=5)
        return
    r.info.append(f"Carpeta fuente accesible: {ruta}")

    # Paso 3 — Tablas referenciadas existen como .dbf
    tablas_ok = _validar_tablas_dbf(contrato, carpeta, r)

    # Paso 4 — Campos referenciados existen en sus tablas
    campos_ok = _validar_campos_dbf(contrato, carpeta, r)

    # Paso 5 — Leer registros reales con el flag configurado
    lectura_ok = _validar_lectura_dbf(contrato, carpeta, r)

    pasos_ok = 1 + int(tablas_ok) + int(campos_ok) + int(lectura_ok)
    _calcular_score(r, pasos_ok=pasos_ok, pasos_total=4)


def _validar_estructura(contrato: dict, r: ValidacionResultado) -> None:
    """Verifica que el contrato tiene las secciones y campos minimos."""
    if not contrato.get("cliente_id"):
        r.errores.append("Falta 'cliente_id' en el contrato.")

    comp = contrato.get("comprobantes", {})
    if not comp:
        r.errores.append("Falta seccion 'comprobantes' en el contrato.")
        return

    if not comp.get("tabla"):
        r.errores.append("Falta 'comprobantes.tabla'.")

    fl = comp.get("flag_lectura", {})
    if not fl:
        r.errores.append("Falta 'comprobantes.flag_lectura'.")
    else:
        if not fl.get("campo"):
            r.errores.append("Falta 'comprobantes.flag_lectura.campo'.")
        if fl.get("valor") is None:
            r.errores.append("Falta 'comprobantes.flag_lectura.valor'.")

    fe = comp.get("flag_escritura", {})
    if not fe:
        r.advertencias.append("Sin 'flag_escritura' — el motor no podrá marcar registros procesados.")

    if not contrato.get("items", {}).get("tabla"):
        r.advertencias.append("Sin 'items.tabla' — los comprobantes se procesarán sin líneas de detalle.")

    if not contrato.get("totales", {}).get("tabla"):
        r.advertencias.append("Sin 'totales.tabla' — los montos se tomarán del registro principal.")

    if not contrato.get("productos", {}).get("tabla"):
        r.advertencias.append("Sin 'productos.tabla' — sin catalogo de productos (cod_sunat, descripcion).")

    if not contrato.get("cliente_varios"):
        r.info.append("Sin 'cliente_varios' — se usarán valores por defecto para clientes sin RUC.")


def _validar_tablas_dbf(contrato: dict, carpeta: Path, r: ValidacionResultado) -> bool:
    """Verifica que cada tabla referenciada existe como .dbf en la carpeta."""
    tablas_referenciadas = {
        "comprobantes": contrato.get("comprobantes", {}).get("tabla", ""),
        "items":        contrato.get("items", {}).get("tabla", ""),
        "totales":      contrato.get("totales", {}).get("tabla", ""),
        "productos":    contrato.get("productos", {}).get("tabla", ""),
    }
    if notas := contrato.get("notas", {}).get("tabla"):
        tablas_referenciadas["notas"] = notas
    if motivos := contrato.get("motivos", {}).get("tabla"):
        tablas_referenciadas["motivos"] = motivos

    todas_ok = True
    for seccion, nombre in tablas_referenciadas.items():
        if not nombre:
            continue
        path = _dbf_path(carpeta, nombre)
        if path and path.exists():
            r.info.append(f"Tabla '{nombre}' ({seccion}): encontrada.")
        else:
            msg = f"Tabla '{nombre}' ({seccion}): NO encontrada en {carpeta}."
            if seccion == "comprobantes":
                r.errores.append(msg)
                todas_ok = False
            else:
                r.advertencias.append(msg)

    return todas_ok


def _validar_campos_dbf(contrato: dict, carpeta: Path, r: ValidacionResultado) -> bool:
    """
    Verifica que los campos mapeados en el contrato existen
    en sus respectivas tablas DBF.
    """
    try:
        from dbfread import DBF as DbfReader
    except ImportError:
        r.advertencias.append("dbfread no disponible — omitiendo validacion de campos.")
        return True

    todas_ok = True

    # Tabla comprobantes
    comp     = contrato.get("comprobantes", {})
    tbl_comp = comp.get("tabla", "")
    path_comp = _dbf_path(carpeta, tbl_comp)

    if path_comp and path_comp.exists():
        try:
            t = DbfReader(str(path_comp), encoding="latin-1", load=False)
            campos_dbf = {f.name.upper() for f in t.fields}

            # flag_lectura.campo
            flag_c = comp.get("flag_lectura", {}).get("campo", "")
            if flag_c:
                if flag_c.upper() in campos_dbf:
                    r.info.append(f"Campo flag '{flag_c}': encontrado en {tbl_comp}.")
                else:
                    r.errores.append(f"Campo flag '{flag_c}': NO existe en {tbl_comp}. Campos disponibles: {', '.join(sorted(campos_dbf)[:10])}...")
                    todas_ok = False

            r.info.append(f"Tabla '{tbl_comp}': {len(campos_dbf)} campos disponibles.")

        except Exception as exc:
            r.advertencias.append(f"No se pudo leer estructura de '{tbl_comp}': {exc}")

    # Tabla items
    items     = contrato.get("items", {})
    tbl_items = items.get("tabla", "")
    path_items = _dbf_path(carpeta, tbl_items)

    if tbl_items and path_items and path_items.exists():
        try:
            t = DbfReader(str(path_items), encoding="latin-1", load=False)
            campos_items = {f.name.upper() for f in t.fields}
            join_c = items.get("join_campo", "")
            if join_c and join_c.upper() not in campos_items:
                r.advertencias.append(f"Campo join '{join_c}': NO existe en '{tbl_items}'.")
            elif join_c:
                r.info.append(f"Campo join '{join_c}': encontrado en '{tbl_items}'.")
        except Exception as exc:
            r.advertencias.append(f"No se pudo leer estructura de '{tbl_items}': {exc}")

    return todas_ok


def _validar_lectura_dbf(contrato: dict, carpeta: Path, r: ValidacionResultado) -> bool:
    """
    Lee 3 registros reales con el flag configurado y verifica
    que el motor podria procesarlos.
    """
    try:
        from dbfread import DBF as DbfReader
    except ImportError:
        return True

    comp      = contrato.get("comprobantes", {})
    tbl_comp  = comp.get("tabla", "")
    flag_c    = comp.get("flag_lectura", {}).get("campo", "")
    flag_v    = comp.get("flag_lectura", {}).get("valor")
    path_comp = _dbf_path(carpeta, tbl_comp)

    if not path_comp or not path_comp.exists():
        return False

    try:
        t = DbfReader(str(path_comp), encoding="latin-1", load=False)

        total = 0
        pendientes = []
        muestra    = []

        for rec in t:
            total += 1
            val = rec.get(flag_c)
            # Comparar con tolerancia de tipo
            if _valores_iguales(val, flag_v):
                pendientes.append(rec)
                if len(muestra) < 3:
                    muestra.append(rec)
            if total >= 500 and len(pendientes) >= 3:
                break

        if not pendientes:
            r.advertencias.append(
                f"No se encontraron registros con {flag_c}={flag_v} "
                f"en los primeros {total} registros de '{tbl_comp}'. "
                f"Verifica el valor del flag."
            )
            return False

        r.info.append(
            f"Lectura OK — {len(pendientes)} pendiente(s) encontrado(s) "
            f"en muestra de {total} registros."
        )

        # Verificar campos clave en la muestra
        rec0     = muestra[0]
        campos0  = set(rec0.keys())
        faltantes = []
        for campo in ["TIPO_FACTU", "SERIE_FACT", "NUMERO_FAC"]:
            if campo not in campos0:
                faltantes.append(campo)

        if faltantes:
            r.advertencias.append(
                f"Campos clave no encontrados en '{tbl_comp}': "
                f"{', '.join(faltantes)}. El contrato es de otra estructura."
            )
        else:
            r.info.append("Campos clave (TIPO_FACTU, SERIE_FACT, NUMERO_FAC): presentes.")

        return True

    except Exception as exc:
        r.advertencias.append(f"Error en lectura de prueba: {exc}")
        return False


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def _dbf_path(carpeta: Path, nombre: str) -> Path | None:
    """Retorna el Path al DBF, probando mayusculas y minusculas."""
    if not nombre:
        return None
    nombre = nombre.strip()
    if not nombre.lower().endswith(".dbf"):
        nombre = nombre + ".dbf"
    p1 = carpeta / nombre
    if p1.exists():
        return p1
    p2 = carpeta / nombre.upper()
    if p2.exists():
        return p2
    p3 = carpeta / nombre.lower()
    if p3.exists():
        return p3
    return p1  # retorna el path aunque no exista (para el mensaje de error)


def _valores_iguales(val_dbf: Any, val_config: Any) -> bool:
    """
    Compara el valor del flag con tolerancia de tipo.
    DBF puede devolver int 2, config puede tener int 2 o str '2'.
    """
    if val_dbf is None:
        return False
    if val_dbf == val_config:
        return True
    try:
        return str(val_dbf).strip() == str(val_config).strip()
    except Exception:
        return False


def _calcular_score(r: ValidacionResultado, pasos_ok: int, pasos_total: int) -> None:
    """
    Calcula score final considerando pasos completados y
    penalizaciones por errores y advertencias.
    """
    base = pasos_ok / pasos_total if pasos_total else 0.0

    # Penalizacion por errores criticos
    penalizacion_err  = len(r.errores)      * 0.20
    penalizacion_warn = len(r.advertencias) * 0.05

    score = max(0.0, base - penalizacion_err - penalizacion_warn)
    r.score = round(min(score, 1.0), 3)
