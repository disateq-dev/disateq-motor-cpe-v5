# src/database/schema.py
# DisateQ Motor CPE v5.0
# ─────────────────────────────────────────────────────────────────────────────

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Ruta por defecto — sobreescribible desde config del cliente o main.py
DB_DEFAULT_PATH = 'data/disateq_cpe.db'

# ─── DDL ──────────────────────────────────────────────────────────────────────

SQL_CREATE_CPE_ENVIOS = """
CREATE TABLE IF NOT EXISTS cpe_envios (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identificacion unica del comprobante
    cliente_id           TEXT NOT NULL,
    ruc_emisor           TEXT NOT NULL,
    tipo_comprobante     TEXT NOT NULL,   -- 1=Factura 2=Boleta 3=NC 7=NCB
    serie                TEXT NOT NULL,   -- B001, F013, BC001
    numero               TEXT NOT NULL,   -- sin ceros a la izquierda

    -- Estado del ciclo de vida
    -- LEIDO | NORMALIZADO | GENERADO | REMITIDO | ERROR | IGNORADO
    estado               TEXT NOT NULL DEFAULT 'LEIDO',
    motivo_ignore        TEXT,            -- razon cuando estado=IGNORADO

    -- Envio
    endpoint             TEXT,            -- APIFAS | Nubefact | DisateQ
    intentos             INTEGER NOT NULL DEFAULT 0,

    -- Respuesta SUNAT / endpoint
    respuesta_raw        TEXT,            -- CDR completo (JSON o XML)
    codigo_sunat         TEXT,            -- ej: 0, 2335
    descripcion_sunat    TEXT,

    -- Control reenvio forzado desde UI
    -- 1 = Motor ignora anti-duplicado y reprocesa
    forzar_reenvio       INTEGER NOT NULL DEFAULT 0,

    -- Timestamps ISO 8601
    fecha_creacion       TEXT NOT NULL,
    fecha_actualizacion  TEXT NOT NULL
);
"""

SQL_INDICES = [
    # Clave de unicidad anti-duplicado
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_cpe_unico
    ON cpe_envios (ruc_emisor, serie, numero);
    """,
    # Consultas por estado (Motor + UI dashboard)
    """
    CREATE INDEX IF NOT EXISTS idx_cpe_estado
    ON cpe_envios (estado);
    """,
    # Historial por cliente y fecha (UI historial)
    """
    CREATE INDEX IF NOT EXISTS idx_cpe_cliente_fecha
    ON cpe_envios (cliente_id, fecha_creacion DESC);
    """,
    # Reenvios pendientes
    """
    CREATE INDEX IF NOT EXISTS idx_cpe_forzar
    ON cpe_envios (forzar_reenvio)
    WHERE forzar_reenvio = 1;
    """,
]

# ─── INIT ─────────────────────────────────────────────────────────────────────

def init_db(db_path: str = DB_DEFAULT_PATH) -> sqlite3.Connection:
    """
    Inicializa la base de datos SQLite.
    Crea el archivo y las tablas si no existen.
    Idempotente — seguro llamar en cada arranque.

    Retorna la conexion abierta con row_factory configurado.
    El llamador es responsable de cerrarla (o usar context manager).

    Uso tipico en arranque:
        from src.database.schema import init_db
        conn = init_db()   # usa ruta por defecto
        # o
        conn = init_db('data/cliente_x.db')
    """
    ruta = Path(db_path)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(ruta), check_same_thread=False)
    conn.row_factory = sqlite3.Row          # acceso por nombre de columna
    conn.execute("PRAGMA journal_mode=WAL") # escrituras concurrentes seguras
    conn.execute("PRAGMA foreign_keys=ON")

    _crear_tablas(conn)

    logger.info(f"[SQLite] Base de datos lista: {ruta.resolve()}")
    return conn


def _crear_tablas(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(SQL_CREATE_CPE_ENVIOS)
        for sql in SQL_INDICES:
            conn.execute(sql)
