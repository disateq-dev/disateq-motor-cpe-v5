# src/database/cpe_logger.py
# DisateQ Motor CPE v5.0
# ─────────────────────────────────────────────────────────────────────────────

import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Estados validos del ciclo de vida de un CPE
ESTADOS = {
    'LEIDO',        # Comprobante leido desde la fuente
    'NORMALIZADO',  # Convertido a estructura CPE interna
    'GENERADO',     # Archivo .txt/.json generado
    'REMITIDO',     # Enviado al endpoint — SUNAT confirmo
    'ERROR',        # Fallo en algun punto — pendiente reintento
    'IGNORADO',     # Serie no permitida o duplicado detectado
}


class CpeLogger:
    """
    Fuente de verdad de todos los envios CPE.

    Responsabilidades:
        - Detectar duplicados antes de procesar (ya_remitido)
        - Registrar cada cambio de estado del ciclo de vida
        - Gestionar reenvios forzados desde la UI
        - Proveer datos para el historial y dashboard

    La conexion SQLite se pasa en el constructor —
    el Motor la crea una vez en arranque y la comparte.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ═════════════════════════════════════════════════════════════════════════
    # ANTI-DUPLICADO — consulta principal del Motor
    # ═════════════════════════════════════════════════════════════════════════

    def ya_remitido(self, ruc_emisor: str, serie: str, numero: str) -> bool:
        """
        Verifica si un comprobante ya fue enviado y confirmado por SUNAT.

        Retorna True  → Motor debe IGNORAR este comprobante.
        Retorna False → Motor puede procesar.

        Casos donde retorna False aunque exista registro:
            - estado = ERROR      → se reintenta
            - forzar_reenvio = 1  → UI pidio reenvio manual
            - No existe registro  → primer envio
        """
        sql = """
            SELECT estado, forzar_reenvio
            FROM cpe_envios
            WHERE ruc_emisor = ? AND serie = ? AND numero = ?
            LIMIT 1
        """
        row = self.conn.execute(sql, (ruc_emisor, serie, numero)).fetchone()

        if row is None:
            return False                            # nunca procesado

        if row['forzar_reenvio'] == 1:
            logger.info(
                f"[CpeLogger] Reenvio forzado: {ruc_emisor} {serie}-{numero}"
            )
            return False                            # UI pidio reenvio

        if row['estado'] == 'REMITIDO':
            logger.debug(
                f"[CpeLogger] Duplicado ignorado: {ruc_emisor} {serie}-{numero}"
            )
            return True                             # ya confirmado por SUNAT

        # ERROR, LEIDO, NORMALIZADO, GENERADO → reintenta
        return False

    # ═════════════════════════════════════════════════════════════════════════
    # REGISTRO DE ESTADOS
    # ═════════════════════════════════════════════════════════════════════════

    def registrar(
        self,
        cpe: Dict[str, Any],
        estado: str,
        cliente_id: str,
        endpoint: str = '',
        respuesta_raw: str = '',
        codigo_sunat: str = '',
        descripcion_sunat: str = '',
        motivo_ignore: str = '',
    ) -> None:
        """
        Registra o actualiza el estado de un comprobante en SQLite.

        cpe:    estructura normalizada retornada por GenericAdapter.normalize()
        estado: uno de ESTADOS

        Usa INSERT OR REPLACE para manejar tanto primer registro
        como actualizaciones de estado posteriores.
        """
        if estado not in ESTADOS:
            raise ValueError(f"Estado invalido: '{estado}'. Validos: {ESTADOS}")

        ahora = _now()
        ruc   = cpe.get('ruc_emisor', '')
        serie = cpe.get('serie', '')
        num   = cpe.get('numero', '')

        # Buscar si ya existe para preservar fecha_creacion e intentos
        existente = self._buscar(ruc, serie, num)

        if existente is None:
            self._insertar(
                cliente_id, ruc, cpe, estado,
                endpoint, respuesta_raw, codigo_sunat,
                descripcion_sunat, motivo_ignore, ahora
            )
        else:
            nuevos_intentos = existente['intentos']
            if estado in ('REMITIDO', 'ERROR'):
                nuevos_intentos += 1

            self._actualizar(
                ruc, serie, num, estado,
                endpoint, respuesta_raw, codigo_sunat,
                descripcion_sunat, motivo_ignore,
                nuevos_intentos, ahora
            )

        logger.info(
            f"[CpeLogger] {estado:12} | {cliente_id} | "
            f"{ruc} {serie}-{num}"
            + (f" | {codigo_sunat}" if codigo_sunat else '')
        )

    def registrar_ignorado(
        self,
        cpe: Dict[str, Any],
        cliente_id: str,
        motivo: str
    ) -> None:
        """Atajo para registrar IGNORADO con motivo explicito."""
        self.registrar(cpe, 'IGNORADO', cliente_id, motivo_ignore=motivo)

    # ═════════════════════════════════════════════════════════════════════════
    # REENVIO FORZADO — llamado desde UI
    # ═════════════════════════════════════════════════════════════════════════

    def marcar_forzar_reenvio(
        self,
        ruc_emisor: str,
        serie: str,
        numero: str
    ) -> bool:
        """
        Marca un comprobante para reenvio forzado.
        El Motor ignorara el anti-duplicado en el proximo ciclo.

        Retorna True si encontro y marco el registro.
        Retorna False si el comprobante no existe en SQLite.
        """
        ahora = _now()
        sql = """
            UPDATE cpe_envios
            SET forzar_reenvio      = 1,
                estado              = 'ERROR',
                fecha_actualizacion = ?
            WHERE ruc_emisor = ? AND serie = ? AND numero = ?
        """
        cursor = self.conn.execute(sql, (ahora, ruc_emisor, serie, numero))
        self.conn.commit()

        if cursor.rowcount == 0:
            logger.warning(
                f"[CpeLogger] marcar_forzar_reenvio: no encontrado "
                f"{ruc_emisor} {serie}-{numero}"
            )
            return False

        logger.info(
            f"[CpeLogger] Marcado para reenvio: {ruc_emisor} {serie}-{numero}"
        )
        return True

    def limpiar_forzar_reenvio(
        self,
        ruc_emisor: str,
        serie: str,
        numero: str
    ) -> None:
        """
        Limpia el flag forzar_reenvio despues de un reenvio exitoso.
        Llamado por el Motor tras confirmar REMITIDO.
        """
        ahora = _now()
        sql = """
            UPDATE cpe_envios
            SET forzar_reenvio      = 0,
                fecha_actualizacion = ?
            WHERE ruc_emisor = ? AND serie = ? AND numero = ?
        """
        self.conn.execute(sql, (ahora, ruc_emisor, serie, numero))
        self.conn.commit()

    # ═════════════════════════════════════════════════════════════════════════
    # CONSULTAS — UI historial y dashboard
    # ═════════════════════════════════════════════════════════════════════════

    def historial(
        self,
        cliente_id: Optional[str] = None,
        estado: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retorna historial de envios para la UI.
        Filtrable por cliente_id y/o estado.
        """
        condiciones = []
        params: List[Any] = []

        if cliente_id:
            condiciones.append("cliente_id = ?")
            params.append(cliente_id)
        if estado:
            condiciones.append("estado = ?")
            params.append(estado)

        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        sql = f"""
            SELECT *
            FROM cpe_envios
            {where}
            ORDER BY fecha_creacion DESC
            LIMIT ? OFFSET ?
        """
        params += [limit, offset]
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def conteo_por_estado(self, cliente_id: Optional[str] = None) -> Dict[str, int]:
        """
        Retorna conteo de comprobantes por estado.
        Usado en el dashboard.
        """
        params: List[Any] = []
        where = ""
        if cliente_id:
            where = "WHERE cliente_id = ?"
            params.append(cliente_id)

        sql = f"""
            SELECT estado, COUNT(*) as total
            FROM cpe_envios
            {where}
            GROUP BY estado
        """
        rows = self.conn.execute(sql, params).fetchall()
        return {r['estado']: r['total'] for r in rows}

    def pendientes_reenvio(self) -> List[Dict[str, Any]]:
        """Retorna comprobantes marcados para reenvio forzado."""
        sql = """
            SELECT * FROM cpe_envios
            WHERE forzar_reenvio = 1
            ORDER BY fecha_actualizacion ASC
        """
        return [dict(r) for r in self.conn.execute(sql).fetchall()]

    # ═════════════════════════════════════════════════════════════════════════
    # INTERNOS
    # ═════════════════════════════════════════════════════════════════════════

    def _buscar(
        self,
        ruc_emisor: str,
        serie: str,
        numero: str
    ) -> Optional[sqlite3.Row]:
        sql = """
            SELECT * FROM cpe_envios
            WHERE ruc_emisor = ? AND serie = ? AND numero = ?
            LIMIT 1
        """
        return self.conn.execute(sql, (ruc_emisor, serie, numero)).fetchone()

    def _insertar(
        self,
        cliente_id, ruc, cpe, estado,
        endpoint, respuesta_raw, codigo_sunat,
        descripcion_sunat, motivo_ignore, ahora
    ) -> None:
        sql = """
            INSERT INTO cpe_envios (
                cliente_id, ruc_emisor, tipo_comprobante, serie, numero,
                estado, motivo_ignore, endpoint, intentos,
                respuesta_raw, codigo_sunat, descripcion_sunat,
                forzar_reenvio, fecha_creacion, fecha_actualizacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 0, ?, ?)
        """
        with self.conn:
            self.conn.execute(sql, (
                cliente_id,
                ruc,
                cpe.get('tipo_comprobante', ''),
                cpe.get('serie', ''),
                cpe.get('numero', ''),
                estado,
                motivo_ignore,
                endpoint,
                respuesta_raw,
                codigo_sunat,
                descripcion_sunat,
                ahora,
                ahora,
            ))

    def _actualizar(
        self,
        ruc, serie, numero, estado,
        endpoint, respuesta_raw, codigo_sunat,
        descripcion_sunat, motivo_ignore,
        intentos, ahora
    ) -> None:
        sql = """
            UPDATE cpe_envios
            SET estado              = ?,
                motivo_ignore       = ?,
                endpoint            = ?,
                intentos            = ?,
                respuesta_raw       = ?,
                codigo_sunat        = ?,
                descripcion_sunat   = ?,
                fecha_actualizacion = ?
            WHERE ruc_emisor = ? AND serie = ? AND numero = ?
        """
        with self.conn:
            self.conn.execute(sql, (
                estado,
                motivo_ignore,
                endpoint,
                intentos,
                respuesta_raw,
                codigo_sunat,
                descripcion_sunat,
                ahora,
                ruc, serie, numero,
            ))


# ─── UTILS ────────────────────────────────────────────────────────────────────

def _now() -> str:
    """Timestamp UTC ISO 8601 para todos los registros."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
