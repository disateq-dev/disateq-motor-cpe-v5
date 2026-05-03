# src/motor.py
# DisateQ Motor CPE v5.0
# TASK-008 FIX: sender.enviar() recibe ruc_emisor, serie, numero para APIFAS
# ─────────────────────────────────────────────────────────────────────────────

"""
motor.py
========
Motor CPE DisateQ™ v5.0 — Orquestador principal
"""

import time
import logging
from typing import Dict, Optional

from src.config.client_loader import ClientLoader
from src.generators.txt_generator import TxtGenerator
from src.generators.anulacion_generator import AnulacionGenerator
from src.sender.universal_sender import UniversalSender
from src.database.schema import init_db
from src.database.cpe_logger import CpeLogger
from src.adapters.adapter_factory import AdapterFactory

logger = logging.getLogger(__name__)


class Motor:
    """Orquestador principal del Motor CPE v5.0."""

    def __init__(
        self,
        cliente_alias: str,
        output_dir:    str = "output",
        db_path:       str = "data/disateq_cpe.db",
        modo_sender:   str = None,
    ):
        self.output_dir   = output_dir
        self.modo_sender  = modo_sender

        loader      = ClientLoader()
        self.config = loader.cargar(cliente_alias)
        self.ruc    = self.config.ruc
        self.alias  = cliente_alias
        logger.info(f"[Motor] Cliente: {self.config.razon_social} ({self.ruc})")

        self.conn = init_db(db_path)
        self.log  = CpeLogger(self.conn)
        logger.info(f"[Motor] SQLite listo: {db_path}")

        self._modo_sender = modo_sender

    # ═════════════════════════════════════════════════════════════════════════
    # PROCESAMIENTO PRINCIPAL
    # ═════════════════════════════════════════════════════════════════════════

    def procesar(self, limit: Optional[int] = None) -> Dict:
        results = {'procesados': 0, 'enviados': 0, 'errores': 0, 'ignorados': 0}

        adapter    = AdapterFactory.create_from_cliente_id(self.alias)
        pendientes = adapter.read_pending()

        if limit:
            pendientes = pendientes[:limit]

        logger.info(f"[Motor] Pendientes: {len(pendientes)}")
        print(f"📋 Pendientes: {len(pendientes)}")

        for raw in pendientes:
            try:
                items = adapter.read_items(raw)
                cpe   = adapter.normalize(raw, items)

                serie  = cpe['serie']
                numero = cpe['numero']

                # ── Anti-duplicado ────────────────────────────────────────
                if self.log.ya_remitido(self.ruc, serie, numero):
                    self.log.registrar_ignorado(cpe, self.alias, 'Duplicado — ya REMITIDO')
                    results['ignorados'] += 1
                    logger.debug(f"[Motor] IGNORADO duplicado: {serie}-{numero}")
                    continue

                # ── Validar serie ─────────────────────────────────────────
                if not self.config.serie_permitida(serie, int(numero)):
                    self.log.registrar_ignorado(
                        cpe, self.alias,
                        f"Serie {serie}/{numero} no permitida por config"
                    )
                    results['ignorados'] += 1
                    logger.info(f"[Motor] IGNORADO serie: {serie}-{numero}")
                    continue

                self.log.registrar(cpe, 'LEIDO', self.alias)

                # ── Generar TXT ───────────────────────────────────────────
                t0 = time.time()

                if cpe.get('es_anulacion'):
                    ruta_txt = AnulacionGenerator.generate(
                        cpe, self.ruc,
                        output_dir=f"{self.output_dir}/anulaciones"
                    )
                else:
                    ruta_txt = TxtGenerator.generate(cpe, self.output_dir)

                self.log.registrar(cpe, 'GENERADO', self.alias)

                # ── Enviar ────────────────────────────────────────────────
                tipo_str = self._tipo_str(cpe)
                sender   = self._get_sender(tipo_str)
                endpoint = self._nombre_endpoint(tipo_str)

                self.log.registrar(cpe, 'GENERADO', self.alias, endpoint=endpoint)

                # TASK-008 FIX: pasar ruc_emisor, serie, numero al sender
                # para que APIFAS pueda construir el header Nombre correcto
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
                    print(f"   ✅ {serie}-{numero} ({duracion}ms)")

                else:
                    detalle = respuesta.get('error', str(respuesta))
                    self.log.registrar(
                        cpe, 'ERROR', self.alias,
                        endpoint          = endpoint,
                        descripcion_sunat = detalle,
                    )
                    adapter.write_flag(raw, 'error')
                    results['errores'] += 1
                    print(f"   ❌ {serie}-{numero} — {detalle}")

                results['procesados'] += 1

            except Exception as e:
                serie  = raw.get('SERIE_FACT', '?')
                numero = raw.get('NUMERO_FAC', '?')
                logger.exception(f"[Motor] Error inesperado {serie}-{numero}: {e}")
                results['errores'] += 1
                print(f"   ❌ Error inesperado {serie}-{numero}: {e}")

        print(f"\n📊 Resumen: {results}")
        logger.info(f"[Motor] Resumen: {results}")
        return results

    def procesar_anulaciones(self, limit: Optional[int] = None) -> Dict:
        logger.info("[Motor] procesar_anulaciones() → delegando a procesar()")
        return self.procesar(limit=limit)

    # ═════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═════════════════════════════════════════════════════════════════════════

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
