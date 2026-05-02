# ══════════════════════════════════════════════════════════════════
#  DisateQ Motor CPE v5.0  —  wizard_service.py
#  2026-05-01  + mapeo heurístico en analizar_fuente()
# ══════════════════════════════════════════════════════════════════

from __future__ import annotations
import traceback
from pathlib import Path
import yaml


def _ruta_config() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent.parent.parent, here.parent.parent]:
        if (p / "config").is_dir():
            return p / "config"
    return here.parent.parent.parent / "config"


# ══════════════════════════════════════════════════════════════════
#  TEST FUENTE — paso 3: lista archivos, no datos
# ══════════════════════════════════════════════════════════════════

def test_fuente(fuente: dict) -> dict:
    tipo = fuente.get("tipo", "").lower()
    try:
        if tipo == "dbf":       return _test_dbf(fuente)
        elif tipo == "excel":   return _test_excel(fuente)
        elif tipo == "csv":     return _test_csv(fuente)
        elif tipo in ("sqlserver", "mysql", "postgresql"):
            return _test_db(fuente)
        elif tipo == "access":  return _test_access(fuente)
        else:
            return {"ok": False, "error": f"Tipo no soportado: '{tipo}'"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _test_dbf(fuente: dict) -> dict:
    try:
        from dbfread import DBF as DbfReader
    except ImportError:
        return {"ok": False, "error": "dbfread no instalado. pip install dbfread"}

    ruta = fuente.get("ruta", "").strip()
    if not ruta:
        return {"ok": False, "error": "Ruta de carpeta no especificada"}

    carpeta = Path(ruta)
    if not carpeta.exists():
        return {"ok": False, "error": f"La ruta no existe: {ruta}"}

    # Sin duplicados en Windows
    dbfs = sorted({p.stem.lower(): p for p in
                   list(carpeta.glob("*.dbf")) +
                   list(carpeta.glob("*.DBF"))}.values())

    if not dbfs:
        return {"ok": False, "error": f"No se encontraron archivos .DBF en: {ruta}"}

    archivos = []
    for dbf_path in dbfs:
        try:
            t = DbfReader(str(dbf_path), encoding="latin-1", load=False)
            archivos.append({
                "archivo":      dbf_path.name,
                "campos":       len(t.fields),
                "lista_campos": ", ".join(f.name for f in t.fields[:6]) +
                                ("..." if len(t.fields) > 6 else ""),
            })
        except Exception:
            archivos.append({"archivo": dbf_path.name, "campos": 0,
                             "lista_campos": "(no se pudo leer)"})

    return {
        "ok":      True,
        "mensaje": f"{len(dbfs)} archivo(s) DBF encontrado(s) en la carpeta.",
        "columnas": ["archivo", "campos", "lista_campos"],
        "filas":    archivos,
        "total_registros": len(archivos),
    }


def _test_excel(fuente: dict) -> dict:
    try:
        import openpyxl
    except ImportError:
        return {"ok": False, "error": "openpyxl no instalado."}
    ruta = Path(fuente.get("ruta", "").strip())
    if not ruta.exists():
        return {"ok": False, "error": f"Archivo no encontrado: {ruta}"}
    wb   = openpyxl.load_workbook(str(ruta), read_only=True, data_only=True)
    ws   = wb.active
    rows = list(ws.iter_rows(values_only=True, max_row=6))
    wb.close()
    if not rows:
        return {"ok": False, "error": "Archivo Excel vacío"}
    cols  = [str(c) if c is not None else f"Col{i}" for i, c in enumerate(rows[0])]
    filas = [{cols[j]: str(v) for j, v in enumerate(r)} for r in rows[1:6]]
    return {"ok": True, "mensaje": f"Excel OK — {ws.max_row - 1} filas.",
            "columnas": cols[:12], "filas": filas,
            "total_registros": ws.max_row - 1}


def _test_csv(fuente: dict) -> dict:
    import csv as _csv
    ruta = Path(fuente.get("ruta", "").strip())
    if not ruta.exists():
        return {"ok": False, "error": f"Archivo no encontrado: {ruta}"}
    with open(ruta, newline="", encoding="latin-1", errors="replace") as f:
        reader = _csv.DictReader(f)
        cols   = reader.fieldnames or []
        filas  = [row for i, row in enumerate(reader) if i < 5]
    return {"ok": True, "mensaje": f"CSV OK — {len(cols)} columnas.",
            "columnas": list(cols)[:12], "filas": filas,
            "total_registros": len(filas)}


def _test_db(fuente: dict) -> dict:
    tipo = fuente.get("tipo"); host = fuente.get("host", "localhost")
    puerto = fuente.get("puerto", ""); database = fuente.get("database", "")
    usuario = fuente.get("usuario", ""); password = fuente.get("password", "")
    try:
        if tipo == "sqlserver":
            import pyodbc
            cs   = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={host},{puerto or 1433};DATABASE={database};UID={usuario};PWD={password}"
            conn = pyodbc.connect(cs, timeout=5)
            cur  = conn.cursor()
            cur.execute("SELECT TOP 10 TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        elif tipo == "mysql":
            import mysql.connector
            conn = mysql.connector.connect(host=host, port=int(puerto or 3306),
                database=database, user=usuario, password=password, connection_timeout=5)
            cur  = conn.cursor(); cur.execute("SHOW TABLES")
        elif tipo == "postgresql":
            import psycopg2
            conn = psycopg2.connect(host=host, port=int(puerto or 5432),
                dbname=database, user=usuario, password=password, connect_timeout=5)
            cur  = conn.cursor()
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' LIMIT 10")
        else:
            return {"ok": False, "error": f"DB tipo no soportado: {tipo}"}
        tablas = [row[0] for row in cur.fetchall()]
        cur.close(); conn.close()
        return {"ok": True, "mensaje": f"Conexión OK — {len(tablas)} tabla(s).",
                "columnas": ["tabla"], "filas": [{"tabla": t} for t in tablas],
                "total_registros": len(tablas)}
    except Exception as exc:
        return {"ok": False, "error": f"No se pudo conectar a {tipo}: {exc}"}


def _test_access(fuente: dict) -> dict:
    try:
        import pyodbc
    except ImportError:
        return {"ok": False, "error": "pyodbc no instalado."}
    ruta = fuente.get("ruta", "").strip()
    if not Path(ruta).exists():
        return {"ok": False, "error": f"Archivo no encontrado: {ruta}"}
    try:
        conn   = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ruta};")
        cur    = conn.cursor()
        tablas = [r.table_name for r in cur.tables(tableType="TABLE")]
        cur.close(); conn.close()
        return {"ok": True, "mensaje": f"Access OK — {len(tablas)} tabla(s).",
                "columnas": ["tabla"], "filas": [{"tabla": t} for t in tablas],
                "total_registros": len(tablas)}
    except Exception as exc:
        return {"ok": False, "error": f"Error Access: {exc}"}


# ══════════════════════════════════════════════════════════════════
#  ANALIZAR FUENTE — paso 3→4: mapeo heurístico
# ══════════════════════════════════════════════════════════════════

def analizar_fuente(fuente: dict) -> dict:
    """
    Corre el motor heurístico sobre la fuente y retorna
    el contrato pre-llenado con scores de confianza.

    Solo DBF por ahora — Excel/CSV/DB retornan contrato vacío
    para que el usuario lo llene manualmente.

    Retorna:
    {
      ok: bool,
      score_global: float,
      contrato: { ... },
      scores: { campo: float },
      sin_resolver: [ campo ],
      metodo: 'heuristica' | 'manual',
    }
    """
    tipo = fuente.get("tipo", "").lower()

    if tipo == "dbf":
        try:
            from src.tools.wizard_mapper import mapear_dbf
            ruta    = fuente.get("ruta", "").strip()
            result  = mapear_dbf(ruta)
            result["metodo"] = "heuristica"
            return result
        except Exception as exc:
            return {
                "ok":          False,
                "error":       str(exc),
                "metodo":      "manual",
                "score_global": 0,
                "contrato":    {},
                "scores":      {},
                "sin_resolver": [],
            }

    # Para otros tipos — contrato vacío, llenado manual
    return {
        "ok":           True,
        "score_global": 0,
        "metodo":       "manual",
        "contrato":     {},
        "scores":       {},
        "sin_resolver": [],
        "tablas_analizadas": 0,
    }


# ══════════════════════════════════════════════════════════════════
#  GUARDAR WIZARD
# ══════════════════════════════════════════════════════════════════

def guardar_wizard(payload: dict) -> dict:
    try:
        cfg_root   = _ruta_config()
        cliente    = payload["cliente"]
        fuente     = payload["fuente"]
        contrato   = payload["contrato"]
        series     = payload["series"]
        creds      = payload["credenciales"]
        cliente_id = cliente["cliente_id"]

        d = cfg_root / "clientes"
        d.mkdir(parents=True, exist_ok=True)
        _write_yaml(d / f"{cliente_id}.yaml",
                    _build_cliente_yaml(cliente, fuente, series, creds))

        d = cfg_root / "contratos"
        d.mkdir(parents=True, exist_ok=True)
        _write_yaml(d / f"{cliente_id}.yaml",
                    _build_contrato_yaml(cliente_id, fuente, contrato))

        return {"ok": True, "cliente_id": cliente_id}
    except Exception as exc:
        traceback.print_exc()
        return {"ok": False, "error": str(exc)}


def _build_cliente_yaml(cliente, fuente, series, creds):
    tipo_map    = {"01": "01", "02": "02", "07": "07", "anulacion": "AN"}
    series_list = [{"tipo": tipo_map.get(k, k), "serie": v}
                   for k, vals in series.items() for v in vals]
    proveedor = creds.get("proveedor", "apifas")
    ep = {"proveedor": proveedor, "activo": True}
    if proveedor == "apifas":
        ep["token"]    = creds.get("token", "")
        ep["url_base"] = creds.get("url_base", "https://api.apifas.com/v1")
    elif proveedor == "nubef":
        ep["token"] = creds.get("token", "")
    elif proveedor == "disateq":
        ep["api_key"]  = creds.get("api_key", "")
        ep["url_base"] = creds.get("url_base", "https://platform.disateq.com/api/v1")
    return {
        "cliente_id":        cliente["cliente_id"],
        "ruc_emisor":        cliente["ruc_emisor"],
        "razon_social":      cliente["razon_social"],
        "nombre_comercial":  cliente.get("nombre_comercial", ""),
        "alias":             cliente.get("alias", ""),
        "regimen":           cliente["regimen"],
        "contrato":          f"contratos/{cliente['cliente_id']}.yaml",
        "series":            series_list,
        "endpoints":         [ep],
    }


def _build_contrato_yaml(cliente_id, fuente, contrato):
    tipo = fuente.get("tipo", "")
    if tipo in ("dbf", "excel", "csv", "access"):
        source = {"type": tipo, "path": fuente.get("ruta", "")}
        if tipo == "dbf":
            source["encoding"] = "latin-1"
    else:
        source = {
            "type":     tipo,
            "host":     fuente.get("host", "localhost"),
            "port":     int(fuente.get("puerto") or
                           {"sqlserver":1433,"mysql":3306,"postgresql":5432}.get(tipo, 0)),
            "database": fuente.get("database", ""),
            "username": fuente.get("usuario", ""),
            "password": fuente.get("password", ""),
        }
    c = contrato; cm = c.get("campos", {}); ci = c.get("items", {})
    return {
        "cliente_id": cliente_id,
        "source":     source,
        "comprobantes": {
            "tabla":      c.get("tabla", ""),
            "flag_campo": c.get("flag_campo", ""),
            "flag_valor": c.get("flag_valor", ""),
            "flag_tipo":  c.get("flag_tipo", "integer"),
            "campos":     {k: v for k, v in cm.items() if v},
        },
        "items": {k: v for k, v in {
            "tabla":       ci.get("tabla", ""),
            "join_campo":  ci.get("join_campo", ""),
            "codigo":      ci.get("codigo", ""),
            "descripcion": ci.get("descripcion", ""),
            "cantidad":    ci.get("cantidad", ""),
            "precio":      ci.get("precio", ""),
        }.items() if v},
    }


def _write_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True,
                  default_flow_style=False, sort_keys=False)
