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


# ══════════════════════════════════════════════════════════════════
#  RESULTADO
# ══════════════════════════════════════════════════════════════════

class ValidacionResultado:
    """
    Resultado de una validacion de contrato.

    score:        float 0-1 — 1.0 = perfecto, < 0.5 = contrato roto
    errores:      problemas que impiden el procesamiento
    advertencias: problemas que pueden causar resultados parciales
    info:         observaciones sin impacto
    ok:           True si score >= 0.60 y sin errores
    """
    def __init__(self):
        self.score:        float     = 0.0
        self.errores:      list[str] = []
        self.advertencias: list[str] = []
        self.info:         list[str] = []

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
#  HELPERS DE PATH
# ══════════════════════════════════════════════════════════════════

def _raiz_proyecto() -> Path:
    """
    Sube desde este archivo hasta encontrar la carpeta 'config/'.
    Funciona independientemente del cwd de Python.
    """
    aqui = Path(__file__).resolve()
    for p in [aqui.parent.parent.parent, aqui.parent.parent]:
        if (p / "config").is_dir():
            return p
    return aqui.parent.parent.parent


def _resolver_contrato_path(contrato_path_str: str, alias: str) -> Path | None:
    """
    Resuelve el path del contrato con estos intentos en orden:
    1. Si es absoluto y existe → usarlo directamente
    2. Si es relativo → raiz/config/{contrato_path_str}
    3. Convencion → raiz/config/contratos/{alias}.yaml
    """
    raiz = _raiz_proyecto()

    if contrato_path_str:
        p = Path(contrato_path_str)
        if p.is_absolute():
            return p
        # relativo — intentar desde raiz/config/
        p2 = raiz / "config" / p
        if p2.exists():
            return p2
        # relativo — intentar desde raiz/
        p3 = raiz / p
        if p3.exists():
            return p3

    # Fallback por convencion
    return raiz / "config" / "contratos" / f"{alias}.yaml"


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
        src  = contrato.get("source", {})
        tipo = src.get("type", "dbf").lower()
        ruta = src.get("path", "")
    else:
        tipo = fuente.get("tipo", "dbf").lower()
        ruta = fuente.get("ruta", "")

    # ── Validaciones por tipo ─────────────────────────────────────
    if tipo == "dbf":
        _validar_dbf(contrato, ruta, r)
    else:
        r.info.append(
            f"Validacion detallada no disponible para tipo '{tipo}'. "
            f"Verificacion estructural solamente."
        )
        _validar_estructura(contrato, r)

    return r


def validar_contrato_desde_alias(alias: str) -> ValidacionResultado:
    """
    Carga el contrato del cliente por alias (file stem) y lo valida.
    Usado desde api.py → validar_contrato(alias).
    """
    import yaml
    from src.config.client_loader import ClientLoader

    r = ValidacionResultado()

    # ── Cargar config del cliente ─────────────────────────────────
    try:
        loader = ClientLoader()
        cfg    = loader.cargar(alias)
    except Exception as exc:
        r.errores.append(f"No se pudo cargar el cliente '{alias}': {exc}")
        return r

    # ── Resolver path del contrato ────────────────────────────────
    contrato_path_str = cfg.fuente.get("contrato_path", "")
    contrato_path     = _resolver_contrato_path(contrato_path_str, alias)

    if not contrato_path or not contrato_path.exists():
        r.errores.append(
            f"Contrato no encontrado: '{contrato_path}'. "
            f"Verifica 'contrato_path' en el YAML del cliente."
        )
        return r

    # ── Leer contrato ─────────────────────────────────────────────
    try:
        with open(contrato_path, encoding="utf-8") as f:
            contrato = yaml.safe_load(f)
    except Exception as exc:
        r.errores.append(f"Error leyendo contrato YAML: {exc}")
        return r

    r.info.append(f"Contrato cargado: {contrato_path.name}")

    # ── Validar ───────────────────────────────────────────────────
    fuente = {
        "tipo": cfg.tipo_fuente,
        "ruta": cfg.rutas_fuente[0] if cfg.rutas_fuente else "",
    }
    return validar_contrato(contrato, fuente)


# ══════════════════════════════════════════════════════════════════
#  VALIDACION DBF
# ══════════════════════════════════════════════════════════════════

def _validar_dbf(contrato: dict, ruta: str, r: ValidacionResultado) -> None:
    """Valida contrato DBF en 4 pasos acumulativos."""

    # Paso 1 — Estructura minima del contrato
    _validar_estructura(contrato, r)
    if r.errores:
        _calcular_score(r, pasos_ok=0, pasos_total=4)
        return

    # Paso 2 — Carpeta fuente existe
    carpeta = Path(ruta)
    if not carpeta.exists():
        r.errores.append(f"Carpeta fuente no existe: {ruta}")
        _calcular_score(r, pasos_ok=1, pasos_total=4)
        return
    r.info.append(f"Carpeta fuente accesible: {ruta}")

    # Paso 3 — Tablas referenciadas existen
    tablas_ok = _validar_tablas_dbf(contrato, carpeta, r)

    # Paso 4 — Campos y lectura real
    campos_ok  = _validar_campos_dbf(contrato, carpeta, r)
    lectura_ok = _validar_lectura_dbf(contrato, carpeta, r)

    pasos_ok = 1 + int(tablas_ok) + int(campos_ok) + int(lectura_ok)
    _calcular_score(r, pasos_ok=pasos_ok, pasos_total=4)


def _validar_estructura(contrato: dict, r: ValidacionResultado) -> None:
    """Verifica secciones y campos minimos del contrato."""
    if not contrato.get("cliente_id"):
        r.advertencias.append("Falta 'cliente_id' en el contrato.")

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

    if not comp.get("flag_escritura"):
        r.advertencias.append(
            "Sin 'flag_escritura' — el motor no marcara registros procesados."
        )

    if not contrato.get("items", {}).get("tabla"):
        r.advertencias.append(
            "Sin 'items.tabla' — comprobantes sin lineas de detalle."
        )
    if not contrato.get("totales", {}).get("tabla"):
        r.advertencias.append(
            "Sin 'totales.tabla' — montos desde registro principal."
        )
    if not contrato.get("productos", {}).get("tabla"):
        r.advertencias.append(
            "Sin 'productos.tabla' — sin catalogo (cod_sunat, descripcion)."
        )
    if not contrato.get("cliente_varios"):
        r.info.append(
            "Sin 'cliente_varios' — defaults para clientes sin RUC."
        )


def _validar_tablas_dbf(
    contrato: dict, carpeta: Path, r: ValidacionResultado
) -> bool:
    """Verifica que cada tabla referenciada existe como .dbf."""
    tablas_ref = {
        "comprobantes": contrato.get("comprobantes", {}).get("tabla", ""),
        "items":        contrato.get("items",        {}).get("tabla", ""),
        "totales":      contrato.get("totales",      {}).get("tabla", ""),
        "productos":    contrato.get("productos",    {}).get("tabla", ""),
    }
    if notas := contrato.get("notas", {}).get("tabla"):
        tablas_ref["notas"] = notas
    if motivos := contrato.get("motivos", {}).get("tabla"):
        tablas_ref["motivos"] = motivos

    todas_ok = True
    for seccion, nombre in tablas_ref.items():
        if not nombre:
            continue
        path = _dbf_path(carpeta, nombre)
        if path and path.exists():
            r.info.append(f"Tabla '{nombre}' ({seccion}): OK.")
        else:
            msg = f"Tabla '{nombre}' ({seccion}): NO encontrada en {carpeta}."
            if seccion == "comprobantes":
                r.errores.append(msg)
                todas_ok = False
            else:
                r.advertencias.append(msg)

    return todas_ok


def _validar_campos_dbf(
    contrato: dict, carpeta: Path, r: ValidacionResultado
) -> bool:
    """Verifica que los campos del contrato existen en sus tablas."""
    try:
        from dbfread import DBF as DbfReader
    except ImportError:
        r.advertencias.append("dbfread no disponible — omitiendo validacion de campos.")
        return True

    todas_ok = True
    comp      = contrato.get("comprobantes", {})
    tbl_comp  = comp.get("tabla", "")
    path_comp = _dbf_path(carpeta, tbl_comp)

    if path_comp and path_comp.exists():
        try:
            t          = DbfReader(str(path_comp), encoding="latin-1", load=False)
            campos_dbf = {f.name.upper() for f in t.fields}
            r.info.append(
                f"Tabla '{tbl_comp}': {len(campos_dbf)} campos."
            )

            flag_c = comp.get("flag_lectura", {}).get("campo", "")
            if flag_c:
                if flag_c.upper() in campos_dbf:
                    r.info.append(f"Campo flag '{flag_c}': OK en '{tbl_comp}'.")
                else:
                    r.errores.append(
                        f"Campo flag '{flag_c}': NO existe en '{tbl_comp}'. "
                        f"Disponibles: {', '.join(sorted(campos_dbf)[:12])}..."
                    )
                    todas_ok = False

        except Exception as exc:
            r.advertencias.append(
                f"No se pudo leer estructura de '{tbl_comp}': {exc}"
            )

    # Tabla items — verificar join_campo
    items      = contrato.get("items", {})
    tbl_items  = items.get("tabla", "")
    path_items = _dbf_path(carpeta, tbl_items)

    if tbl_items and path_items and path_items.exists():
        try:
            t            = DbfReader(str(path_items), encoding="latin-1", load=False)
            campos_items = {f.name.upper() for f in t.fields}
            join_c       = items.get("join_campo", "")
            if join_c:
                if join_c.upper() in campos_items:
                    r.info.append(f"Campo join '{join_c}': OK en '{tbl_items}'.")
                else:
                    r.advertencias.append(
                        f"Campo join '{join_c}': NO existe en '{tbl_items}'."
                    )
        except Exception as exc:
            r.advertencias.append(
                f"No se pudo leer '{tbl_items}': {exc}"
            )

    return todas_ok


def _validar_lectura_dbf(
    contrato: dict, carpeta: Path, r: ValidacionResultado
) -> bool:
    """Lee registros reales con el flag configurado."""
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
        t          = DbfReader(str(path_comp), encoding="latin-1", load=False)
        total      = 0
        pendientes = []

        for rec in t:
            total += 1
            if _valores_iguales(rec.get(flag_c), flag_v):
                pendientes.append(rec)
            if total >= 500 and len(pendientes) >= 3:
                break

        if not pendientes:
            r.advertencias.append(
                f"No se encontraron registros con {flag_c}={flag_v} "
                f"en los primeros {total} de '{tbl_comp}'. "
                f"Verifica el valor del flag."
            )
            return False

        r.info.append(
            f"Lectura OK — {len(pendientes)} pendiente(s) en muestra de {total}."
        )

        # Verificar campos clave en primer registro
        campos0   = set(pendientes[0].keys())
        faltantes = [c for c in ("TIPO_FACTU", "SERIE_FACT", "NUMERO_FAC")
                     if c not in campos0]
        if faltantes:
            r.advertencias.append(
                f"Campos clave ausentes en '{tbl_comp}': {', '.join(faltantes)}."
            )
        else:
            r.info.append(
                "Campos clave (TIPO_FACTU, SERIE_FACT, NUMERO_FAC): presentes."
            )

        return True

    except Exception as exc:
        r.advertencias.append(f"Error en lectura de prueba: {exc}")
        return False


# ══════════════════════════════════════════════════════════════════
#  HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════

def _dbf_path(carpeta: Path, nombre: str) -> Path | None:
    """Resuelve path al DBF probando mayusculas/minusculas."""
    if not nombre:
        return None
    nombre = nombre.strip()
    if not nombre.lower().endswith(".dbf"):
        nombre += ".dbf"
    for candidate in (carpeta / nombre,
                      carpeta / nombre.upper(),
                      carpeta / nombre.lower()):
        if candidate.exists():
            return candidate
    return carpeta / nombre  # retorna aunque no exista (para mensajes de error)


def _valores_iguales(val_dbf: Any, val_config: Any) -> bool:
    """Compara con tolerancia de tipo (DBF int vs config str)."""
    if val_dbf is None:
        return False
    if val_dbf == val_config:
        return True
    try:
        return str(val_dbf).strip() == str(val_config).strip()
    except Exception:
        return False


def _calcular_score(
    r: ValidacionResultado, pasos_ok: int, pasos_total: int
) -> None:
    """Score basado en pasos completados menos penalizaciones."""
    base              = pasos_ok / pasos_total if pasos_total else 0.0
    penalizacion_err  = len(r.errores)      * 0.20
    penalizacion_warn = len(r.advertencias) * 0.05
    r.score = round(min(max(0.0, base - penalizacion_err - penalizacion_warn), 1.0), 3)
