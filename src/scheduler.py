"""
scheduler.py
============
Scheduler automático — Motor CPE DisateQ™ v4.0

Ejecuta el Motor en background según configuración del cliente:
- modo: manual     → no hace nada, el operador procesa manualmente
- modo: automatico → boletas cada X minutos, facturas inmediato

Uso:
    from src.scheduler import CpeScheduler
    scheduler = CpeScheduler('farmacia_central')
    scheduler.iniciar()
    scheduler.detener()
"""

import threading
import time
import logging
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class CpeScheduler:
    """
    Scheduler de procesamiento automático del Motor CPE.
    Corre en un thread daemon — muere al cerrar la app.
    """

    def __init__(self, cliente_alias: str, on_ciclo: Optional[Callable] = None):
        """
        Args:
            cliente_alias: alias del cliente (farmacia_central)
            on_ciclo: callback opcional llamado al terminar cada ciclo
                      recibe (resultados: dict) como argumento
        """
        self.cliente_alias = cliente_alias
        self.on_ciclo      = on_ciclo

        self._thread:   Optional[threading.Thread] = None
        self._stop_evt  = threading.Event()
        self._activo    = False
        self._procesando = False

        self.ultimo_ciclo:    Optional[datetime] = None
        self.proximo_ciclo:   Optional[datetime] = None
        self.ultimo_resultado: dict = {}
        self.ciclos_ejecutados: int = 0
        self.errores_consecutivos: int = 0

        # Cargar config del cliente
        self._config = None
        self._scheduler_config = {}
        self._cargar_config()

    # ================================================================
    # CONFIG
    # ================================================================

    def _cargar_config(self):
        """Carga configuración del cliente y scheduler."""
        try:
            from src.config.client_loader import ClientLoader
            loader = ClientLoader()
            self._config = loader.cargar(self.cliente_alias)
            self._scheduler_config = self._config.data.get('scheduler', {})
        except Exception as e:
            logger.error(f"Error cargando config scheduler: {e}")
            self._scheduler_config = {}

    def recargar_config(self):
        """Recarga config sin detener el scheduler."""
        self._cargar_config()

    @property
    def modo(self) -> str:
        return self._scheduler_config.get('modo', 'manual')

    @property
    def intervalo_boletas(self) -> int:
        """Intervalo en minutos para boletas."""
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
        """
        Inicia el scheduler si está en modo automático.

        Returns:
            True si inició, False si modo manual o ya estaba corriendo
        """
        if self.modo != 'automatico':
            logger.info(f"Scheduler {self.cliente_alias}: modo manual — no inicia")
            return False

        if self.esta_activo:
            logger.info(f"Scheduler {self.cliente_alias}: ya está corriendo")
            return True

        self._stop_evt.clear()
        self._activo = True
        self._thread = threading.Thread(
            target=self._loop,
            name=f"scheduler-{self.cliente_alias}",
            daemon=True
        )
        self._thread.start()
        logger.info(f"✅ Scheduler iniciado — {self.cliente_alias} — cada {self.intervalo_boletas} min")
        print(f"⏱️  Scheduler automático iniciado — boletas cada {self.intervalo_boletas} min")
        return True

    def detener(self):
        """Detiene el scheduler."""
        self._stop_evt.set()
        self._activo = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info(f"Scheduler {self.cliente_alias}: detenido")
        print(f"⏹️  Scheduler detenido — {self.cliente_alias}")

    def ejecutar_ahora(self) -> dict:
        """
        Fuerza un ciclo inmediato (desde UI o reintento).
        Corre en thread separado para no bloquear.
        """
        if self._procesando:
            return {'error': 'Ya hay un ciclo en ejecución'}

        t = threading.Thread(target=self._ejecutar_ciclo, daemon=True)
        t.start()
        return {'iniciado': True}

    # ================================================================
    # LOOP PRINCIPAL
    # ================================================================

    def _loop(self):
        """Loop principal del scheduler."""
        logger.info(f"Scheduler loop iniciado — {self.cliente_alias}")

        # Primer ciclo inmediato al arrancar
        self._ejecutar_ciclo()

        while not self._stop_evt.is_set():
            # Recargar config por si cambió el intervalo
            self._cargar_config()

            # Calcular próximo ciclo
            self.proximo_ciclo = datetime.now().replace(microsecond=0)
            next_ts = time.time() + self.intervalo_segundos

            # Esperar en trozos de 5s para poder parar rápido
            while time.time() < next_ts:
                if self._stop_evt.is_set():
                    return
                time.sleep(5)

            if not self._stop_evt.is_set():
                self._ejecutar_ciclo()

    def _ejecutar_ciclo(self):
        """Ejecuta un ciclo completo del Motor."""
        if self._procesando:
            logger.warning("Ciclo omitido — ya hay uno en ejecución")
            return

        self._procesando = True
        inicio = datetime.now()
        print(f"\n⏱️  [{inicio.strftime('%H:%M:%S')}] Ciclo automático — {self.cliente_alias}")

        try:
            from src.motor import Motor
            motor = Motor(
                cliente_alias=self.cliente_alias,
                output_dir='output',
                modo_sender=None  # Envío real
            )
            resultados = motor.procesar()

            self.ultimo_ciclo    = inicio
            self.ultimo_resultado = resultados
            self.ciclos_ejecutados += 1
            self.errores_consecutivos = 0

            duracion = (datetime.now() - inicio).seconds
            print(f"   ✅ Ciclo completado en {duracion}s — {resultados}")

            if self.on_ciclo:
                try:
                    self.on_ciclo(resultados)
                except Exception:
                    pass

        except Exception as e:
            self.errores_consecutivos += 1
            logger.error(f"Error en ciclo scheduler: {e}")
            print(f"   ❌ Error en ciclo: {e}")

            # Si hay muchos errores consecutivos, pausar más tiempo
            if self.errores_consecutivos >= 3:
                print(f"   ⚠️  {self.errores_consecutivos} errores consecutivos — esperando 2x intervalo")

        finally:
            self._procesando = False

    # ================================================================
    # STATUS
    # ================================================================

    def get_status(self) -> dict:
        """Retorna estado actual del scheduler para la UI."""
        return {
            'modo':              self.modo,
            'activo':            self.esta_activo,
            'procesando':        self.esta_procesando,
            'intervalo_minutos': self.intervalo_boletas,
            'ciclos_ejecutados': self.ciclos_ejecutados,
            'errores_consecutivos': self.errores_consecutivos,
            'ultimo_ciclo':      self.ultimo_ciclo.strftime('%H:%M:%S') if self.ultimo_ciclo else None,
            'proximo_ciclo':     self.proximo_ciclo.strftime('%H:%M:%S') if self.proximo_ciclo and self.esta_activo else None,
            'ultimo_resultado':  self.ultimo_resultado,
        }
