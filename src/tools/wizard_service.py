# ══════════════════════════════════════════════════════════════════
#  DisateQ Motor CPE v5.0  —  wizard_service.py
#  Lógica de negocio para el Wizard end-to-end (TASK-005)
#  2026-05-01
# ══════════════════════════════════════════════════════════════════

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import Any

import yaml


# ── helpers ───────────────────────────────────────────────────────
def _ruta_config() -> Path:
    """Raíz del proyecto, buscando hacia arriba desde este archivo."""
    here = Path(__file__).resolve()
    for p in [here.parent.parent.parent, here.parent.parent]:
        if (p / "config").is_dir():
            return p / "config"
    return here.parent.parent.parent / "config"


# ══════════════════════════════════════════════════════════════════
#  TEST FUENTE
# ══════════════════════════════════════════════════════════════════

def test_fuente(fuente: dict) -> dict:
    """
    Intenta leer los primeros registros de la fuente indicada.
    Retorna:
        { ok: bool, mensaje: str, columnas: list, filas: list[dict], total_registros: int }
    o en error:
        { ok: false, error: str }
    """
    tipo = fuente.get("tipo", "").lower()
    try:
        if tipo == "dbf":
            return _test_dbf(fuente)
        elif tipo == "excel":
            return _test_excel(fuente)
        elif tipo == "csv":
            return _test_csv(fuente)
        elif tipo in ("sqlserver", "mysql", "postgresql"):
            return _test_db(fuente)
        elif tipo == "access":
            return _test_access(fuente)
        else:
            return {"ok": False, "error": f"Tipo de fuente no soportado: '{tipo}'"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── DBF ───────────────────────────────────────────────────────────
def _test_dbf(fuente: dict) -> dict:
    try:
        from dbfread import DBF as DbfReader, FieldNotFoundError
    except ImportError:
        return {"ok": False, "error": "dbfread no está instalado. Ejecuta: pip install dbfread"}

    ruta = fuente.get("ruta", "").strip()
    if not ruta:
        return {"ok": False, "error": "Ruta de carpeta no especificada"}

    carpeta = Path(ruta)
    if not carpeta.exists():
        return {"ok": False, "error": f"La ruta no existe: {ruta}"}

    dbfs = list(carpeta.glob("*.dbf")) + list(carpeta.glob("*.DBF"))
    if not dbfs:
        return {"ok": False, "error": f"No se encontraron archivos .DBF en: {ruta}"}

    # usa el primero como muestra
    dbf_path = dbfs[0]
    try:
        tabla = DbfReader(str(dbf_path), encoding="latin-1", load=True)
        cols  = [f.name for f in tabla.fields]
        filas = []
        total = 0
        for i, rec in enumerate(tabla):
            total += 1
            if i < 5:
                filas.append({c: str(rec.get(c, "")) for c in cols})

        archivos = [p.name for p in dbfs[:8]]
        return {
            "ok": True,
            "mensaje": (
                f"Acceso correcto. {len(dbfs)} archivo(s) DBF encontrado(s): "
                f"{', '.join(archivos)}{'...' if len(dbfs) > 8 else ''}. "
                f"Muestra de «{dbf_path.name}»."
            ),
            "columnas": cols[:12],
            "filas":    filas,
            "total_registros": total,
        }
    except Exception as exc:
        return {"ok": False, "error": f"Error leyendo {dbf_path.name}: {exc}"}


# ── Excel ─────────────────────────────────────────────────────────
def _test_excel(fuente: dict) -> dict:
    try:
        import openpyxl
    except ImportError:
        return {"ok": False, "error": "openpyxl no instalado. Ejecuta: pip install openpyxl"}

    ruta = Path(fuente.get("ruta", "").strip())
    if not ruta.exists():
        return {"ok": False, "error": f"Archivo no encontrado: {ruta}"}

    wb = openpyxl.load_workbook(str(ruta), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return {"ok": False, "error": "El archivo Excel está vacío"}

    cols  = [str(c) if c is not None else f"Col{i}" for i, c in enumerate(rows[0])]
    filas = [{cols[j]: str(v) for j, v in enumerate(r)} for r in rows[1:6]]
    return {
        "ok": True,
        "mensaje": f"Archivo Excel leído correctamente. {ws.max_row - 1} filas detectadas.",
        "columnas": cols[:12],
        "filas":    filas,
        "total_registros": ws.max_row - 1,
    }


# ── CSV ───────────────────────────────────────────────────────────
def _test_csv(fuente: dict) -> dict:
    import csv as _csv

    ruta = Path(fuente.get("ruta", "").strip())
    if not ruta.exists():
        return {"ok": False, "error": f"Archivo no encontrado: {ruta}"}

    with open(ruta, newline="", encoding="latin-1", errors="replace") as f:
        reader = _csv.DictReader(f)
        cols   = reader.fieldnames or []
        filas  = []
        total  = 0
        for row in reader:
            total += 1
            if total <= 5:
                filas.append({k: str(v) for k, v in row.items()})

    return {
        "ok": True,
        "mensaje": f"CSV leído correctamente. {total} filas, {len(cols)} columnas.",
        "columnas": list(cols)[:12],
        "filas":    filas,
        "total_registros": total,
    }


# ── SQL Server / MySQL / PostgreSQL ───────────────────────────────
def _test_db(fuente: dict) -> dict:
    tipo     = fuente.get("tipo")
    host     = fuente.get("host", "localhost")
    puerto   = fuente.get("puerto", "")
    database = fuente.get("database", "")
    usuario  = fuente.get("usuario", "")
    password = fuente.get("password", "")

    try:
        if tipo == "sqlserver":
            import pyodbc
            driver = "ODBC Driver 17 for SQL Server"
            cs = f"DRIVER={{{driver}}};SERVER={host},{puerto or 1433};DATABASE={database};UID={usuario};PWD={password}"
            conn = pyodbc.connect(cs, timeout=5)
        elif tipo == "mysql":
            import mysql.connector
            conn = mysql.connector.connect(
                host=host, port=int(puerto or 3306),
                database=database, user=usuario, password=password,
                connection_timeout=5,
            )
        elif tipo == "postgresql":
            import psycopg2
            conn = psycopg2.connect(
                host=host, port=int(puerto or 5432),
                dbname=database, user=usuario, password=password,
                connect_timeout=5,
            )
        else:
            return {"ok": False, "error": f"DB tipo no soportado: {tipo}"}

        cur = conn.cursor()
        # listar tablas como muestra
        if tipo == "sqlserver":
            cur.execute("SELECT TOP 5 TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        elif tipo == "mysql":
            cur.execute("SHOW TABLES")
        elif tipo == "postgresql":
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' LIMIT 5")

        tablas = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()

        return {
            "ok": True,
            "mensaje": f"Conexión exitosa a {tipo.upper()}. Tablas encontradas: {', '.join(tablas) or '(ninguna)'}",
            "columnas": ["tabla"],
            "filas":    [{"tabla": t} for t in tablas],
            "total_registros": len(tablas),
        }
    except Exception as exc:
        return {"ok": False, "error": f"No se pudo conectar a {tipo}: {exc}"}


# ── Access ────────────────────────────────────────────────────────
def _test_access(fuente: dict) -> dict:
    try:
        import pyodbc
    except ImportError:
        return {"ok": False, "error": "pyodbc no instalado."}

    ruta = fuente.get("ruta", "").strip()
    if not Path(ruta).exists():
        return {"ok": False, "error": f"Archivo no encontrado: {ruta}"}

    try:
        cs   = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ruta};"
        conn = pyodbc.connect(cs)
        cur  = conn.cursor()
        tablas = [row.table_name for row in cur.tables(tableType="TABLE")][:5]
        cur.close()
        conn.close()
        return {
            "ok": True,
            "mensaje": f"Access abierto. Tablas: {', '.join(tablas) or '(ninguna)'}",
            "columnas": ["tabla"],
            "filas":    [{"tabla": t} for t in tablas],
            "total_registros": len(tablas),
        }
    except Exception as exc:
        return {"ok": False, "error": f"Error abriendo Access: {exc}. ¿Está instalado el Access Engine?"}


# ══════════════════════════════════════════════════════════════════
#  GUARDAR CLIENTE + CONTRATO → YAML
# ══════════════════════════════════════════════════════════════════

def guardar_wizard(payload: dict) -> dict:
    """
    Recibe el payload completo del wizard y escribe:
      config/clientes/{cliente_id}.yaml
      config/contratos/{cliente_id}.yaml
    Retorna { ok: bool, cliente_id: str } o { ok: false, error: str }
    """
    try:
        cfg_root   = _ruta_config()
        cliente    = payload["cliente"]
        fuente     = payload["fuente"]
        contrato   = payload["contrato"]
        series     = payload["series"]
        creds      = payload["credenciales"]
        cliente_id = cliente["cliente_id"]

        # ── 1. YAML del cliente ─────────────────────────────────
        cliente_yaml = _build_cliente_yaml(cliente, fuente, series, creds)
        clientes_dir = cfg_root / "clientes"
        clientes_dir.mkdir(parents=True, exist_ok=True)
        _write_yaml(clientes_dir / f"{cliente_id}.yaml", cliente_yaml)

        # ── 2. YAML del contrato ────────────────────────────────
        contrato_yaml = _build_contrato_yaml(cliente_id, fuente, contrato)
        contratos_dir = cfg_root / "contratos"
        contratos_dir.mkdir(parents=True, exist_ok=True)
        _write_yaml(contratos_dir / f"{cliente_id}.yaml", contrato_yaml)

        return {"ok": True, "cliente_id": cliente_id}

    except Exception as exc:
        traceback.print_exc()
        return {"ok": False, "error": str(exc)}


def _build_cliente_yaml(cliente: dict, fuente: dict, series: dict, creds: dict) -> dict:
    """Arma la estructura del YAML de cliente."""
    # series → lista de dicts { tipo, serie }
    series_list = []
    tipo_map = {"01": "01", "02": "02", "07": "07", "anulacion": "AN"}
    for k, vals in series.items():
        for v in vals:
            series_list.append({"tipo": tipo_map.get(k, k), "serie": v})

    # endpoint
    proveedor = creds.get("proveedor", "apifas")
    endpoint  = {
        "proveedor": proveedor,
        "activo":    True,
    }
    if proveedor == "apifas":
        endpoint["token"]    = creds.get("token", "")
        endpoint["url_base"] = creds.get("url_base", "https://api.apifas.com/v1")
    elif proveedor == "nubef":
        endpoint["token"] = creds.get("token", "")
    elif proveedor == "disateq":
        endpoint["api_key"]  = creds.get("api_key", "")
        endpoint["url_base"] = creds.get("url_base", "https://platform.disateq.com/api/v1")

    return {
        "cliente_id":   cliente["cliente_id"],
        "ruc_emisor":   cliente["ruc_emisor"],
        "razon_social": cliente["razon_social"],
        "regimen":      cliente["regimen"],
        "contrato":     f"contratos/{cliente['cliente_id']}.yaml",
        "series":       series_list,
        "endpoints":    [endpoint],
    }


def _build_contrato_yaml(cliente_id: str, fuente: dict, contrato: dict) -> dict:
    """Arma la estructura del YAML de contrato."""
    tipo = fuente.get("tipo", "")

    # source_config según tipo
    if tipo in ("dbf", "excel", "csv", "access"):
        source = {
            "type": tipo,
            "path": fuente.get("ruta", ""),
        }
        if tipo == "dbf":
            source["encoding"] = "latin-1"
    else:
        source = {
            "type":     tipo,
            "host":     fuente.get("host", "localhost"),
            "port":     int(fuente.get("puerto") or _default_port(tipo)),
            "database": fuente.get("database", ""),
            "username": fuente.get("usuario", ""),
            "password": fuente.get("password", ""),
        }

    c  = contrato
    cm = c.get("campos", {})
    ci = c.get("items", {})

    return {
        "cliente_id": cliente_id,
        "source":     source,
        "comprobantes": {
            "tabla":      c.get("tabla", ""),
            "flag_campo": c.get("flag_campo", ""),
            "flag_valor": c.get("flag_valor", ""),
            "flag_tipo":  c.get("flag_tipo", "integer"),
            "campos": {k: v for k, v in cm.items() if v},
        },
        "items": {k: v for k, v in {
            "tabla":      ci.get("tabla", ""),
            "join_campo": ci.get("join_campo", ""),
            "codigo":     ci.get("codigo", ""),
            "descripcion":ci.get("descripcion", ""),
            "cantidad":   ci.get("cantidad", ""),
            "precio":     ci.get("precio", ""),
        }.items() if v},
    }


def _default_port(tipo: str) -> int:
    return {"sqlserver": 1433, "mysql": 3306, "postgresql": 5432}.get(tipo, 0)


def _write_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
