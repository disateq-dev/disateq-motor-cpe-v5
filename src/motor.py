"""
motor.py
========
Motor CPE DisateQ™ v4.0 — Orquestador principal

Flujo:
    ClientConfig → Adapter → Normalize → Validar Serie → TxtGenerator → Sender → Log
"""

import time
from pathlib import Path
from typing import Dict, List, Tuple

from src.config.client_loader import ClientLoader, ClientConfig
from src.generators.txt_generator import TxtGenerator
from src.sender.universal_sender import UniversalSender
from src.logger.cpe_logger import CpeLogger


# Mapa tipo_doc CPE → tipo config cliente
TIPO_DOC_MAP = {
    '01': 'factura',
    '03': 'boleta',
    '07': 'nota_credito',
    '08': 'nota_debito',
}


class Motor:
    """Orquestador principal del Motor CPE."""

    def __init__(self,
                 cliente_alias: str,
                 output_dir: str = "output",
                 db_path: str = "data/cpe_log.db",
                 modo_sender: str = None):
        """
        Args:
            cliente_alias: Alias del cliente (farmacia_central)
            output_dir: Directorio de salida para TXT
            db_path: Ruta a SQLite
            modo_sender: None=real, 'mock'=simulacion
        """
        self.output_dir  = output_dir
        self.modo_sender = modo_sender

        # Cargar config cliente
        loader = ClientLoader()
        self.config = loader.cargar(cliente_alias)
        print(f"✅ Cliente: {self.config.razon_social} ({self.config.ruc})")

        # Logger
        self.log = CpeLogger(db_path)

        # Sender
        self.sender = UniversalSender(mode=modo_sender) if modo_sender == 'mock' else None

    def _get_adapter(self):
        """Instancia el adaptador segun tipo de fuente."""
        tipo  = self.config.tipo_fuente
        rutas = self.config.rutas_fuente

        if not rutas:
            raise ValueError("No hay rutas de fuente configuradas")

        ruta = rutas[0]  # Principal

        if tipo == 'dbf':
            from src.adapters.dbf_farmacia_adapter import DbfFarmaciaAdapter
            return DbfFarmaciaAdapter(ruta)
        elif tipo == 'xlsx':
            from src.adapters.xlsx_adapter import XlsxAdapter
            return XlsxAdapter(ruta)
        else:
            raise ValueError(f"Tipo de fuente no soportado: {tipo}")

    def _get_sender(self):
        """Instancia el sender segun modo."""
        if self.modo_sender == 'mock':
            return UniversalSender(mode='mock')

        modo   = self.config.modo_envio
        config = self.config.config_envio
        url    = config.get('url', '')
        creds  = config.get('credenciales', {})

        # Inyectar credenciales del cliente al endpoints.yaml temporal
        # Por ahora usar config directo
        return UniversalSender(mode=self.modo_sender)

    def procesar(self, limit: int = None) -> Dict:
        """
        Ejecuta el flujo completo.

        Args:
            limit: Limite de comprobantes a procesar (None = todos)

        Returns:
            Resumen de resultados
        """
        ruc   = self.config.ruc
        alias = self.config.alias

        adapter = self._get_adapter()
        adapter.connect()

        pendientes = adapter.read_pending()
        if limit:
            pendientes = pendientes[:limit]

        print(f"📋 Pendientes: {len(pendientes)}")

        sender  = self._get_sender()
        results = {'procesados': 0, 'enviados': 0, 'errores': 0, 'ignorados': 0}

        for comp in pendientes:
            try:
                # Leer items
                items = adapter.read_items(comp)

                # Normalizar
                cpe = adapter.normalize(comp, items)
                cab = cpe.get('comprobante', cpe)

                tipo_doc = cab.get('tipo_doc', '')
                serie_raw = cab.get('serie', '')
                prefijo   = {'01':'F','03':'B','07':'BC','08':'BD'}.get(tipo_doc, '')
                serie     = prefijo + serie_raw
                numero   = int(cab.get('numero', 0))
                tipo_str = TIPO_DOC_MAP.get(tipo_doc, 'boleta')

                # Validar serie
                if not self.config.serie_permitida(serie, numero):
                    self.log.ignorado(ruc, alias, tipo_str, serie, numero,
                                      f"Serie {serie}/{numero} no permitida por config")
                    results['ignorados'] += 1
                    continue

                cli_nombre = cpe.get('cliente', {}).get('denominacion', '-')
                total_cpe  = cpe.get('totales', {}).get('total', 0.0)
                self.log.leido(ruc, alias, tipo_str, serie, numero)

                # Generar TXT
                t0   = time.time()
                path = TxtGenerator.generate(cpe, self.output_dir)
                self.log.generado(ruc, alias, tipo_str, serie, numero, path)

                # Enviar
                endpoint_nombre = self.config.config_envio.get('nombre', 'mock')
                exito, respuesta = sender.enviar(path)
                duracion = int((time.time() - t0) * 1000)

                if exito:
                    self.log.enviado(ruc, alias, tipo_str, serie, numero,
                                     path, endpoint_nombre, duracion,
                                     cli_nombre, total_cpe)
                    results['enviados'] += 1
                    print(f"   ✅ {serie}-{numero:08d} ({duracion}ms)")
                else:
                    detalle = respuesta.get('error', str(respuesta))
                    self.log.error(ruc, alias, tipo_str, serie, numero,
                                   detalle, endpoint_nombre)
                    results['errores'] += 1
                    print(f"   ❌ {serie}-{numero:08d} — {detalle}")

                results['procesados'] += 1

            except Exception as e:
                serie  = comp.get('SERIE_FACT', '?')
                numero = comp.get('NUMERO_FAC', '?')
                self.log.error(ruc, alias, '', str(serie), 0, str(e))
                results['errores'] += 1
                print(f"   ❌ Error inesperado {serie}-{numero}: {e}")

        adapter.disconnect()

        print(f"\n📊 Resumen: {results}")
        return results

