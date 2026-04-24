"""
cpe_logger.py
=============
Log de operaciones SQLite — Motor CPE DisateQ™ v4.0

Registra cada operacion del flujo:
LEIDO | NORMALIZADO | GENERADO | ENVIADO | ERROR | IGNORADO
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


DB_PATH = "data/cpe_log.db"

ESTADOS = {
    'LEIDO':       'Comprobante leido desde fuente',
    'NORMALIZADO': 'Normalizado a estructura CPE',
    'GENERADO':    'Archivo TXT/JSON generado',
    'ENVIADO':     'Enviado al endpoint exitosamente',
    'ERROR':       'Error en el flujo',
    'IGNORADO':    'Serie/correlativo no permitido por config',
}


class CpeLogger:
    """Logger SQLite para operaciones del Motor CPE."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Crea tabla si no existe."""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS log_envios (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha             TEXT NOT NULL,
                    ruc_emisor        TEXT NOT NULL,
                    alias_cliente     TEXT,
                    tipo_doc          TEXT,
                    serie             TEXT,
                    numero            INTEGER,
                    archivo_generado  TEXT,
                    estado            TEXT NOT NULL,
                    detalle           TEXT,
                    endpoint          TEXT,
                    duracion_ms       INTEGER
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ruc_serie
                ON log_envios (ruc_emisor, serie, numero)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_estado
                ON log_envios (estado)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fecha
                ON log_envios (fecha)
            """)

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    def registrar(self,
                  ruc_emisor: str,
                  estado: str,
                  alias_cliente: str = '',
                  tipo_doc: str = '',
                  serie: str = '',
                  numero: int = 0,
                  archivo_generado: str = '',
                  detalle: str = '',
                  endpoint: str = '',
                  duracion_ms: int = 0) -> int:
        """
        Registra una operacion en el log.

        Returns:
            ID del registro insertado
        """
        with self._conn() as conn:
            cur = conn.execute("""
                INSERT INTO log_envios
                (fecha, ruc_emisor, alias_cliente, tipo_doc, serie, numero,
                 archivo_generado, estado, detalle, endpoint, duracion_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                ruc_emisor,
                alias_cliente,
                tipo_doc,
                serie,
                numero,
                archivo_generado,
                estado,
                detalle,
                endpoint,
                duracion_ms
            ))
            return cur.lastrowid

    def leido(self, ruc: str, alias: str, tipo: str, serie: str, numero: int) -> int:
        return self.registrar(ruc, 'LEIDO', alias, tipo, serie, numero)

    def generado(self, ruc: str, alias: str, tipo: str, serie: str, numero: int, archivo: str) -> int:
        return self.registrar(ruc, 'GENERADO', alias, tipo, serie, numero, archivo_generado=archivo)

    def enviado(self, ruc: str, alias: str, tipo: str, serie: str, numero: int,
                archivo: str, endpoint: str, duracion_ms: int = 0) -> int:
        return self.registrar(ruc, 'ENVIADO', alias, tipo, serie, numero,
                              archivo_generado=archivo, endpoint=endpoint, duracion_ms=duracion_ms)

    def error(self, ruc: str, alias: str, tipo: str, serie: str, numero: int,
              detalle: str, endpoint: str = '') -> int:
        return self.registrar(ruc, 'ERROR', alias, tipo, serie, numero,
                              detalle=detalle, endpoint=endpoint)

    def ignorado(self, ruc: str, alias: str, tipo: str, serie: str, numero: int, motivo: str) -> int:
        return self.registrar(ruc, 'IGNORADO', alias, tipo, serie, numero, detalle=motivo)

    # ── Consultas ─────────────────────────────────────────────────────────────

    def consultar(self,
                  ruc: str = None,
                  estado: str = None,
                  serie: str = None,
                  fecha_desde: str = None,
                  fecha_hasta: str = None,
                  limit: int = 100) -> List[Dict]:
        """Consulta el log con filtros opcionales."""
        sql = "SELECT * FROM log_envios WHERE 1=1"
        params = []

        if ruc:
            sql += " AND ruc_emisor = ?"; params.append(ruc)
        if estado:
            sql += " AND estado = ?"; params.append(estado)
        if serie:
            sql += " AND serie = ?"; params.append(serie)
        if fecha_desde:
            sql += " AND fecha >= ?"; params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND fecha <= ?"; params.append(fecha_hasta)

        sql += " ORDER BY fecha DESC LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def resumen(self, ruc: str = None) -> Dict:
        """Resumen de operaciones por estado."""
        sql = """
            SELECT estado, COUNT(*) as total
            FROM log_envios
            {}
            GROUP BY estado
        """.format("WHERE ruc_emisor = ?" if ruc else "")

        params = [ruc] if ruc else []

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return {r[0]: r[1] for r in rows}

    def pendientes_error(self, ruc: str = None) -> List[Dict]:
        """Retorna comprobantes con ERROR para reintento manual."""
        return self.consultar(ruc=ruc, estado='ERROR')
