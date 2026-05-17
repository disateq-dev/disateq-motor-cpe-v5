"""
scheduler.py — DisateQ Integrador CPE™ v5.0
Scheduler robusto con deteccion offline y fix encoding.
"""

import threading
import time
import logging
import socket
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)


def _check_internet(host: str = "8.8.8.8", port: int = 53, timeout: int = 3) -> bool:
    """Verifica conectividad a internet via socket."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False


class CpeScheduler:
    """
    Scheduler de procesamiento automatico del Motor CPE.
    - Deteccion offline: no envia si no hay internet
    - Fix encoding: sin emojis en logs
    - Cola inteligente: acumula en offline, entrega al reconectar
    """

    def __init__(self, cliente_alias: str, on_ciclo: Optional[Callable] = None):
        self.cliente_alias = cliente_alias
        self.on_ciclo      = on_ciclo

        self._thread:    Optional[threading.Thread] = None
        self._stop_evt   = threading.Event()
        self._activo     = False
        self._procesando = False

        self.ultimo_ciclo:         Optional[datetime] = None
        self.proximo_ciclo:        Optional[datetime] = None
        self.ultimo_resultado:     dict = {}
        self.ciclos_ejecutados:    int  = 0
        self.errores_consecutivos: int  = 0
        self.online:               bool = True
        self.offline_desde:        Optional[datetime] = None

        self._config           = None
        self._scheduler_config = {}
        self._cargar_config()

    # ================================================================
    # CONFIG
    # ================================================================

    def _cargar_config(self):
        try:
            from src.config.client_loader import ClientLoader
            loader = ClientLoader()
            self._config = loader.cargar(self.cliente_alias)
            self._scheduler_config = self._config.data.get('scheduler', {})
        except Exception as e:
            logger.error(f'[Scheduler] Error cargando config: {e}')
            self._scheduler_config = {}

    def recargar_config(self):
        self._cargar_config()

    @property
    def modo(self) -> str:
        return self._scheduler_config.get('modo', 'manual')

    @property
    def intervalo_boletas(self) -> int:
        return int(self._scheduler_config.get('intervalo_boletas', 10))

    @property
    def intervalo_segundos(self) -> int:
        return self.intervalo_boletas * 60

    @property
    def esta_activo(self) -> bool:
        return self._activo and self._thread is not None and self._thread.is_alive()

    @property
    def esta_procesando(self) -> bool:
        return self._procesando

    # ================================================================
    # CONTROL
    # ================================================================

    def iniciar(self) -> bool:
        if self.modo != 'automatico':
            logger.info(f'[Scheduler] {self.cliente_alias}: modo manual')
            return False

        if self.esta_activo:
            logger.info(f'[Scheduler] {self.cliente_alias}: ya esta corriendo')
            return True

        self._stop_evt.clear()
        self._activo = True
        self._thread = threading.Thread(
            target=self._loop,
            name=f'scheduler-{self.cliente_alias}',
            daemon=True
        )
        self._thread.start()
        logger.info(f'[Scheduler] Iniciado — {self.cliente_alias} — cada {self.intervalo_boletas} min')
        return True

    def detener(self):
        self._stop_evt.set()
        self._activo = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info(f'[Scheduler] Detenido — {self.cliente_alias}')

    def ejecutar_ahora(self) -> dict:
        if self._procesando:
            return {'error': 'Ya hay un ciclo en ejecucion'}
        t = threading.Thread(target=self._ejecutar_ciclo, daemon=True)
        t.start()
        return {'iniciado': True}

    # ================================================================
    # LOOP PRINCIPAL
    # ================================================================

    def _loop(self):
        logger.info(f'[Scheduler] Loop iniciado — {self.cliente_alias}')

        # Primer ciclo inmediato
        self._ejecutar_ciclo()

        while not self._stop_evt.is_set():
            self._cargar_config()
            self.proximo_ciclo = datetime.now().replace(microsecond=0)
            next_ts = time.time() + self.intervalo_segundos

            while time.time() < next_ts:
                if self._stop_evt.is_set():
                    return
                time.sleep(5)

            if not self._stop_evt.is_set():
                self._ejecutar_ciclo()

    def _verificar_conexion(self) -> bool:
        """Verifica internet y actualiza estado online/offline."""
        ahora  = datetime.now()
        online = _check_internet()

        if online and not self.online:
            # Recupero de offline
            duracion = (ahora - self.offline_desde).seconds // 60 if self.offline_desde else 0
            logger.info(f'[Scheduler] Conexion restaurada — estuvo offline {duracion} min')
            self.online        = True
            self.offline_desde = None

        elif not online and self.online:
            # Perdida de conexion
            logger.warning(f'[Scheduler] Sin conexion a internet — acumulando en cola local')
            self.online        = False
            self.offline_desde = ahora

        return online

    def _ejecutar_ciclo(self):
        if self._procesando:
            logger.warning(f'[Scheduler] Ciclo omitido — ya hay uno en ejecucion')
            return

        self._procesando = True
        inicio = datetime.now()
        logger.info(f'[Scheduler] Ciclo iniciado — {self.cliente_alias} — {inicio.strftime("%H:%M:%S")}')

        try:
            # Verificar conexion antes de procesar
            online = self._verificar_conexion()

            if not online:
                logger.warning(f'[Scheduler] Sin internet — ciclo diferido, registros en cola local')
                self.ultimo_resultado = {
                    'procesados': 0, 'enviados': 0,
                    'errores': 0, 'ignorados': 0,
                    'estado': 'offline'
                }
                if self.on_ciclo:
                    self.on_ciclo(self.ultimo_resultado)
                return

            from src.motor import Motor
            motor      = Motor(cliente_alias=self.cliente_alias, modo_sender=None)
            resultados = motor.procesar()

            self.ultimo_ciclo         = inicio
            self.ultimo_resultado     = resultados
            self.ciclos_ejecutados   += 1
            self.errores_consecutivos = 0

            duracion = (datetime.now() - inicio).seconds
            logger.info(f'[Scheduler] Ciclo completado en {duracion}s — {resultados}')

            if self.on_ciclo:
                try:
                    self.on_ciclo(resultados)
                except Exception as e:
                    logger.error(f'[Scheduler] Error en callback on_ciclo: {e}')

        except Exception as e:
            self.errores_consecutivos += 1
            logger.error(f'[Scheduler] Error en ciclo: {e}')

            if self.errores_consecutivos >= 3:
                logger.warning(
                    f'[Scheduler] {self.errores_consecutivos} errores consecutivos '
                    f'— esperando {self.intervalo_boletas * 2} min'
                )

        finally:
            self._procesando = False

    # ================================================================
    # STATUS
    # ================================================================

    def get_status(self) -> dict:
        ahora = datetime.now()
        pct   = 0
        if self.proximo_ciclo and self.esta_activo:
            transcurrido = (ahora - self.proximo_ciclo).seconds
            pct = min(100, int((transcurrido / self.intervalo_segundos) * 100))

        return {
            'modo':                self.modo,
            'activo':              self.esta_activo,
            'procesando':          self.esta_procesando,
            'intervalo_minutos':   self.intervalo_boletas,
            'ciclos_hoy':          self.ciclos_ejecutados,
            'errores_consecutivos':self.errores_consecutivos,
            'online':              self.online,
            'offline_desde':       self.offline_desde.strftime('%H:%M:%S') if self.offline_desde else None,
            'ultimo_ciclo':        self.ultimo_ciclo.strftime('%H:%M:%S') if self.ultimo_ciclo else None,
            'proximo_ciclo':       self.proximo_ciclo.strftime('%H:%M:%S') if self.proximo_ciclo and self.esta_activo else None,
            'hace':                self._hace(self.ultimo_ciclo),
            'pct_proximo':         pct,
            'ultimo_resultado':    self.ultimo_resultado,
        }

    def _hace(self, dt: Optional[datetime]) -> str:
        if not dt:
            return 'nunca'
        diff = (datetime.now() - dt).seconds
        if diff < 60:
            return f'hace {diff}s'
        return f'hace {diff // 60} min'
