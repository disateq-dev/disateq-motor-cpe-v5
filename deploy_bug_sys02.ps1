# =============================================================================
# deploy_bug_sys02.ps1 -- BUG-SYS-02 DisateQ Motor CPE v5.0
# - cpe_logger.py: estado ABANDONADO + marcar_abandonado()
# - motor.py: limite MAX_INTENTOS=5, log informativo detallado
# - scheduler.py: output_dir via paths_resolver
# =============================================================================

$ErrorActionPreference = "Stop"
$Root = "D:\DisateQ\Proyectos\disateq-motor-cpe-v5"

Write-Host "=== BUG-SYS-02 -- Max reintentos + logs informativos ===" -ForegroundColor Cyan

# =============================================================================
# 1. src\database\cpe_logger.py
# =============================================================================
$cpeLogger = @'
# src/database/cpe_logger.py
# DisateQ Motor CPE v5.0
# BUG-SYS-02: estado ABANDONADO + marcar_abandonado() + ya_remitido bloquea ABANDONADO
# -----------------------------------------------------------------------------

import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

MAX_INTENTOS = 5  # Maximo de reintentos antes de ABANDONADO

# Estados validos del ciclo de vida de un CPE
ESTADOS = {
    'LEIDO',        # Comprobante leido desde la fuente
    'NORMALIZADO',  # Convertido a estructura CPE interna
    'GENERADO',     # Archivo .txt generado
    'REMITIDO',     # Enviado al endpoint -- SUNAT confirmo
    'ERROR',        # Fallo en algun punto -- pendiente reintento
    'IGNORADO',     # Serie no permitida o duplicado detectado
    'ABANDONADO',   # Supero MAX_INTENTOS -- requiere revision manual
}


class CpeLogger:
    """
    Fuente de verdad de todos los envios CPE.

    Responsabilidades:
        - Detectar duplicados antes de procesar (ya_remitido)
        - Registrar cada cambio de estado del ciclo de vida
        - Gestionar reenvios forzados desde la UI
        - Proveer datos para el historial y dashboard
        - Marcar ABANDONADO tras MAX_INTENTOS fallidos
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # =========================================================================
    # ANTI-DUPLICADO -- consulta principal del Motor
    # =========================================================================

    def ya_remitido(self, ruc_emisor: str, serie: str, numero: str) -> bool:
        """
        Verifica si un comprobante ya fue enviado o fue abandonado.

        Retorna True  -> Motor debe IGNORAR este comprobante.
        Retorna False -> Motor puede procesar.

        Casos donde retorna False aunque exista registro:
            - estado = ERROR      -> se reintenta (si intentos < MAX_INTENTOS)
            - forzar_reenvio = 1  -> UI pidio reenvio manual
            - No existe registro  -> primer envio

        Casos donde retorna True:
            - estado = REMITIDO   -> ya confirmado por SUNAT
            - estado = ABANDONADO -> supero MAX_INTENTOS, no reintentar
        """
        sql = """
            SELECT estado, forzar_reenvio, intentos
            FROM cpe_envios
            WHERE ruc_emisor = ? AND serie = ? AND numero = ?
            LIMIT 1
        """
        row = self.conn.execute(sql, (ruc_emisor, serie, numero)).fetchone()

        if row is None:
            return False

        if row['forzar_reenvio'] == 1:
            logger.info(f"[CpeLogger] Reenvio forzado: {ruc_emisor} {serie}-{numero}")
            return False

        if row['estado'] == 'REMITIDO':
            return True

        if row['estado'] == 'ABANDONADO':
            logger.debug(f"[CpeLogger] ABANDONADO ignorado: {ruc_emisor} {serie}-{numero}")
            return True

        # ERROR, LEIDO, NORMALIZADO, GENERADO -> reintenta
        return False

    def obtener_intentos(self, ruc_emisor: str, serie: str, numero: str) -> int:
        """Retorna el numero de intentos actuales de un comprobante."""
        sql = """
            SELECT intentos FROM cpe_envios
            WHERE ruc_emisor = ? AND serie = ? AND numero = ?
            LIMIT 1
        """
        row = self.conn.execute(sql, (ruc_emisor, serie, numero)).fetchone()
        return row['intentos'] if row else 0

    # =========================================================================
    # REGISTRO DE ESTADOS
    # =========================================================================

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
        if estado not in ESTADOS:
            raise ValueError(f"Estado invalido: '{estado}'. Validos: {ESTADOS}")

        ahora = _now()
        ruc   = cpe.get('ruc_emisor', '')
        serie = cpe.get('serie', '')
        num   = cpe.get('numero', '')

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
        self.registrar(cpe, 'IGNORADO', cliente_id, motivo_ignore=motivo)

    def marcar_abandonado(
        self,
        ruc_emisor: str,
        serie: str,
        numero: str,
        cliente_id: str,
        endpoint: str = '',
        ultimo_error: str = '',
        intentos: int = 0,
    ) -> None:
        """
        Marca un comprobante como ABANDONADO tras superar MAX_INTENTOS.
        Genera log informativo para revision del tecnico.
        """
        ahora = _now()
        sql = """
            UPDATE cpe_envios
            SET estado              = 'ABANDONADO',
                motivo_ignore       = ?,
                fecha_actualizacion = ?
            WHERE ruc_emisor = ? AND serie = ? AND numero = ?
        """
        with self.conn:
            self.conn.execute(sql, (
                f"Supero {intentos} intentos. Ultimo error: {ultimo_error}",
                ahora,
                ruc_emisor, serie, numero
            ))

        logger.error(
            f"[CpeLogger] ABANDONADO | {cliente_id} | {ruc_emisor} {serie}-{numero} | "
            f"intentos={intentos} | endpoint={endpoint} | error={ultimo_error}"
        )
        logger.error(
            f"[CpeLogger] ACCION REQUERIDA: Revisar {serie}-{numero} manualmente. "
            f"Usar 'Forzar reenvio' desde la UI una vez resuelto el problema."
        )

    # =========================================================================
    # REENVIO FORZADO -- llamado desde UI
    # =========================================================================

    def marcar_forzar_reenvio(
        self,
        ruc_emisor: str,
        serie: str,
        numero: str
    ) -> bool:
        ahora = _now()
        sql = """
            UPDATE cpe_envios
            SET forzar_reenvio      = 1,
                estado              = 'ERROR',
                intentos            = 0,
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

        logger.info(f"[CpeLogger] Marcado para reenvio: {ruc_emisor} {serie}-{numero}")
        return True

    def limpiar_forzar_reenvio(
        self,
        ruc_emisor: str,
        serie: str,
        numero: str
    ) -> None:
        ahora = _now()
        sql = """
            UPDATE cpe_envios
            SET forzar_reenvio      = 0,
                fecha_actualizacion = ?
            WHERE ruc_emisor = ? AND serie = ? AND numero = ?
        """
        self.conn.execute(sql, (ahora, ruc_emisor, serie, numero))
        self.conn.commit()

    # =========================================================================
    # CONSULTAS -- UI historial y dashboard
    # =========================================================================

    def historial(
        self,
        cliente_id: Optional[str] = None,
        estado: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
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
        sql = """
            SELECT * FROM cpe_envios
            WHERE forzar_reenvio = 1
            ORDER BY fecha_actualizacion ASC
        """
        return [dict(r) for r in self.conn.execute(sql).fetchall()]

    def abandonados(self, cliente_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna comprobantes abandonados para revision en UI."""
        params: List[Any] = []
        where = "WHERE estado = 'ABANDONADO'"
        if cliente_id:
            where += " AND cliente_id = ?"
            params.append(cliente_id)
        sql = f"""
            SELECT * FROM cpe_envios
            {where}
            ORDER BY fecha_actualizacion DESC
        """
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    # =========================================================================
    # INTERNOS
    # =========================================================================

    def _buscar(self, ruc_emisor, serie, numero):
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
                cliente_id, ruc,
                cpe.get('tipo_comprobante', ''),
                cpe.get('serie', ''),
                cpe.get('numero', ''),
                estado, motivo_ignore, endpoint,
                respuesta_raw, codigo_sunat, descripcion_sunat,
                ahora, ahora,
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
                estado, motivo_ignore, endpoint, intentos,
                respuesta_raw, codigo_sunat, descripcion_sunat,
                ahora, ruc, serie, numero,
            ))


# --- UTILS -------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
'@

Set-Content -Path "$Root\src\database\cpe_logger.py" -Value $cpeLogger -Encoding UTF8
Write-Host "  [OK] src\database\cpe_logger.py" -ForegroundColor Green

# =============================================================================
# 2. src\motor.py -- agregar check MAX_INTENTOS antes de procesar
# =============================================================================
$motor = @'
# src/motor.py
# DisateQ Motor CPE v5.0
# TASK-008 FIX: sender.enviar() recibe ruc_emisor, serie, numero para APIFAS
# TASK-INS-01: rutas data\ y output\ via paths_resolver (C:/D: separados)
# BUG-SYS-02: verifica MAX_INTENTOS antes de procesar -- marca ABANDONADO
# -----------------------------------------------------------------------------

"""
motor.py
========
Motor CPE DisateQ v5.0 -- Orquestador principal
"""

import time
import logging
from pathlib import Path
from typing import Dict, Optional

from src.config.client_loader import ClientLoader
from src.config.paths_resolver import get_data_dir, get_output_dir
from src.generators.txt_generator import TxtGenerator
from src.generators.anulacion_generator import AnulacionGenerator
from src.sender.universal_sender import UniversalSender
from src.database.schema import init_db
from src.database.cpe_logger import CpeLogger, MAX_INTENTOS
from src.adapters.adapter_factory import AdapterFactory

logger = logging.getLogger(__name__)


class Motor:
    """Orquestador principal del Motor CPE v5.0."""

    def __init__(
        self,
        cliente_alias: str,
        output_dir:    str = None,
        db_path:       str = None,
        modo_sender:   str = None,
    ):
        self.output_dir  = output_dir or str(get_output_dir())
        self._db_path    = db_path    or str(get_data_dir() / "disateq_cpe.db")
        self.modo_sender = modo_sender

        loader      = ClientLoader()
        self.config = loader.cargar(cliente_alias)
        self.ruc    = self.config.ruc
        self.alias  = cliente_alias
        logger.info(f"[Motor] Cliente: {self.config.razon_social} ({self.ruc})")
        logger.info(f"[Motor] output_dir : {self.output_dir}")
        logger.info(f"[Motor] db_path    : {self._db_path}")

        self.conn = init_db(self._db_path)
        self.log  = CpeLogger(self.conn)
        logger.info(f"[Motor] SQLite listo: {self._db_path}")

        self._modo_sender = modo_sender

    # =========================================================================
    # PROCESAMIENTO PRINCIPAL
    # =========================================================================

    def procesar(self, limit: Optional[int] = None) -> Dict:
        results = {'procesados': 0, 'enviados': 0, 'errores': 0, 'ignorados': 0, 'abandonados': 0}

        adapter    = AdapterFactory.create_from_cliente_id(self.alias)
        pendientes = adapter.read_pending()

        if limit:
            pendientes = pendientes[:limit]

        logger.info(f"[Motor] Pendientes: {len(pendientes)}")
        print(f"Pendientes: {len(pendientes)}")

        for raw in pendientes:
            try:
                items = adapter.read_items(raw)
                cpe   = adapter.normalize(raw, items)

                serie  = cpe['serie']
                numero = cpe['numero']

                # -- Anti-duplicado -------------------------------------------
                if self.log.ya_remitido(self.ruc, serie, numero):
                    self.log.registrar_ignorado(cpe, self.alias, 'Duplicado -- ya REMITIDO o ABANDONADO')
                    results['ignorados'] += 1
                    logger.debug(f"[Motor] IGNORADO: {serie}-{numero}")
                    continue

                # -- BUG-SYS-02: Verificar MAX_INTENTOS -----------------------
                intentos_actuales = self.log.obtener_intentos(self.ruc, serie, numero)
                if intentos_actuales >= MAX_INTENTOS:
                    tipo_str = self._tipo_str(cpe)
                    endpoint = self._nombre_endpoint(tipo_str)
                    self.log.marcar_abandonado(
                        ruc_emisor = self.ruc,
                        serie      = serie,
                        numero     = numero,
                        cliente_id = self.alias,
                        endpoint   = endpoint,
                        ultimo_error = f"Supero {MAX_INTENTOS} intentos sin exito",
                        intentos   = intentos_actuales,
                    )
                    adapter.write_flag(raw, 'error')
                    results['abandonados'] += 1
                    print(f"   ABANDONADO {serie}-{numero} ({intentos_actuales} intentos)")
                    continue

                # -- Validar serie --------------------------------------------
                if not self.config.serie_permitida(serie, int(numero)):
                    self.log.registrar_ignorado(
                        cpe, self.alias,
                        f"Serie {serie}/{numero} no permitida por config"
                    )
                    results['ignorados'] += 1
                    logger.info(f"[Motor] IGNORADO serie: {serie}-{numero}")
                    continue

                self.log.registrar(cpe, 'LEIDO', self.alias)

                # -- Generar TXT ----------------------------------------------
                t0 = time.time()

                if cpe.get('es_anulacion'):
                    ruta_txt = AnulacionGenerator.generate(
                        cpe, self.ruc,
                        output_dir=str(Path(self.output_dir) / "anulaciones")
                    )
                else:
                    ruta_txt = TxtGenerator.generate(cpe, self.output_dir)

                self.log.registrar(cpe, 'GENERADO', self.alias)

                # -- Enviar ---------------------------------------------------
                tipo_str = self._tipo_str(cpe)
                sender   = self._get_sender(tipo_str)
                endpoint = self._nombre_endpoint(tipo_str)

                self.log.registrar(cpe, 'GENERADO', self.alias, endpoint=endpoint)

                resultados_envio = sender.enviar(
                    archivo_path     = ruta_txt,
                    tipo_comprobante = tipo_str,
                    ruc_emisor       = self.ruc,
                    serie            = serie,
                    numero           = numero,
                )

                exito     = all(r[0] for r in resultados_envio)
                respuesta = resultados_envio[0][1] if resultados_envio else {}
                duracion  = int((time.time() - t0) * 1000)

                if exito:
                    self.log.registrar(
                        cpe, 'REMITIDO', self.alias,
                        endpoint          = endpoint,
                        respuesta_raw     = str(respuesta),
                        codigo_sunat      = str(respuesta.get('codigo', '')),
                        descripcion_sunat = str(respuesta.get('descripcion', '')),
                    )
                    self.log.limpiar_forzar_reenvio(self.ruc, serie, numero)
                    adapter.write_flag(raw, 'enviado')
                    results['enviados'] += 1
                    print(f"   OK {serie}-{numero} ({duracion}ms)")

                else:
                    detalle          = respuesta.get('error', str(respuesta))
                    intentos_nuevos  = intentos_actuales + 1
                    self.log.registrar(
                        cpe, 'ERROR', self.alias,
                        endpoint          = endpoint,
                        descripcion_sunat = detalle,
                    )
                    adapter.write_flag(raw, 'error')
                    results['errores'] += 1

                    # Log informativo con detalle completo
                    logger.error(
                        f"[Motor] ERROR {serie}-{numero} | "
                        f"intento {intentos_nuevos}/{MAX_INTENTOS} | "
                        f"endpoint={endpoint} | "
                        f"respuesta={detalle}"
                    )
                    if intentos_nuevos >= MAX_INTENTOS:
                        logger.error(
                            f"[Motor] PROXIMO CICLO: {serie}-{numero} sera ABANDONADO "
                            f"(supera {MAX_INTENTOS} intentos)"
                        )
                    print(f"   ERROR {serie}-{numero} -- intento {intentos_nuevos}/{MAX_INTENTOS} -- {detalle}")

                results['procesados'] += 1

            except Exception as e:
                serie  = raw.get('SERIE_FACT', '?')
                numero = raw.get('NUMERO_FAC', '?')
                logger.exception(f"[Motor] Error inesperado {serie}-{numero}: {e}")
                results['errores'] += 1
                print(f"   ERROR inesperado {serie}-{numero}: {e}")

        print(f"\nResumen: {results}")
        logger.info(f"[Motor] Resumen: {results}")
        return results

    def procesar_anulaciones(self, limit: Optional[int] = None) -> Dict:
        logger.info("[Motor] procesar_anulaciones() -> delegando a procesar()")
        return self.procesar(limit=limit)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_sender(self, tipo_str: str) -> UniversalSender:
        if self._modo_sender == 'mock':
            return UniversalSender(mode='mock')
        endpoints = self.config.get_endpoints_para(tipo_str)
        return UniversalSender(endpoints=endpoints)

    def _nombre_endpoint(self, tipo_str: str) -> str:
        endpoints = self.config.get_endpoints_para(tipo_str)
        return ','.join(ep.get('nombre', '') for ep in endpoints) or 'mock'

    @staticmethod
    def _tipo_str(cpe: Dict) -> str:
        mapa = {'1': 'factura', '2': 'boleta', '3': 'nota_credito', '7': 'nota_debito'}
        if cpe.get('es_anulacion'):
            return 'anulacion'
        return mapa.get(str(cpe.get('tipo_comprobante', '2')), 'boleta')
'@

Set-Content -Path "$Root\src\motor.py" -Value $motor -Encoding UTF8
Write-Host "  [OK] src\motor.py" -ForegroundColor Green

# =============================================================================
# 3. src\scheduler.py -- fix output_dir hardcodeado
# =============================================================================
$schedulerPath = "$Root\src\scheduler.py"
$content = Get-Content $schedulerPath -Raw -Encoding UTF8
$content = $content -replace "output_dir='output',\s*`r?`n\s*modo_sender=None", "output_dir=None,`r`n                modo_sender=None"
Set-Content -Path $schedulerPath -Value $content -Encoding UTF8
Write-Host "  [OK] src\scheduler.py -- output_dir corregido" -ForegroundColor Green

# =============================================================================
# Resumen
# =============================================================================
Write-Host ""
Write-Host "=== BUG-SYS-02 deploy completo ===" -ForegroundColor Green
Write-Host ""
Write-Host "Cambios:" -ForegroundColor Yellow
Write-Host "  cpe_logger.py : estado ABANDONADO + marcar_abandonado() + obtener_intentos()"
Write-Host "  motor.py      : check MAX_INTENTOS=5 antes de procesar + logs informativos"
Write-Host "  scheduler.py  : output_dir=None (via paths_resolver)"
Write-Host ""
Write-Host "Git:" -ForegroundColor Cyan
Write-Host "  git add src\database\cpe_logger.py src\motor.py src\scheduler.py"
Write-Host "  git commit -m 'BUG-SYS-02: MAX_INTENTOS=5 ABANDONADO + logs informativos'"
Write-Host "  git push"
Write-Host ""
