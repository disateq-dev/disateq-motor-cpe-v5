"""
universal_sender.py — Motor CPE DisateQ™ v5.0
TASK-008 FIX: formato APIFAS correcto — headers HTTP, no multipart/form-data

Endpoints APIFAS confirmados:
    OSE comprobantes: POST ose_produccion_1.php
    OSE anulaciones:  POST ose_anular_1.php
    SEE comprobantes: POST produccion_text_1.php
    SEE anulaciones:  POST produccion_anular_1.php

Headers requeridos:
    Ruc:    RUC del emisor
    Nombre: {RUC}-{tipo_cod}-{serie}-{numero}.txt
            A-{RUC}-{tipo_cod}-{serie}-{numero}.txt  (anulaciones)
    Texto:  contenido completo del archivo TXT

Respuestas de exito (cualquier otra = ERROR):
    'Procesando OSE'   — OSE comprobantes
    'Anulando OSE'     — OSE anulaciones
    'Proceso-Aceptado' — SEE comprobantes
    'Por Anular'       — SEE anulaciones
"""

import requests
from pathlib import Path
from typing import Dict, List, Tuple


# Mapa tipo_comprobante → campo URL en el endpoint
URL_MAP = {
    'boleta':       'url_comprobantes',
    'factura':      'url_comprobantes',
    'nota_credito': 'url_comprobantes',
    'nota_debito':  'url_comprobantes',
    'anulacion':    'url_anulaciones',
    'guia':         'url_guias',
    'retencion':    'url_retenciones',
    'percepcion':   'url_percepciones',
}

# Tipo comprobante → codigo numerico SUNAT para el Nombre del archivo
TIPO_COMP_COD = {
    'boleta':       '02',
    'factura':      '01',
    'nota_credito': '07',
    'nota_debito':  '08',
    'anulacion':    '02',
    'guia':         '09',
    'retencion':    '20',
    'percepcion':   '40',
}

# Respuestas que indican exito — cualquier otra es ERROR
RESPUESTAS_EXITO = {
    'procesando ose',
    'anulando ose',
    'proceso-aceptado',
    'por anular',
}


def _es_exito(body: str) -> bool:
    return body.strip().lower() in RESPUESTAS_EXITO


def _nombre_archivo(ruc: str, tipo_comprobante: str, serie: str,
                    numero: str, es_anulacion: bool = False) -> str:
    tipo_cod = TIPO_COMP_COD.get(tipo_comprobante, '02')
    nombre   = f"{ruc}-{tipo_cod}-{serie}-{numero}.txt"
    if es_anulacion:
        nombre = f"A-{nombre}"
    return nombre


class UniversalSender:
    """Envia archivo CPE a APIFAS usando headers HTTP."""

    def __init__(self, endpoints: list = None, mode: str = None):
        self.mode      = mode
        self.endpoints = endpoints or []

    def _get_url(self, ep: Dict, tipo_comprobante: str) -> str:
        campo_url = URL_MAP.get(tipo_comprobante, 'url_comprobantes')
        url = ep.get(campo_url, '').strip()
        if url:
            return url
        urls = ep.get('urls', {})
        if urls:
            url = urls.get(tipo_comprobante, '')
            if url:
                return url
            if tipo_comprobante in ('nota_credito', 'nota_debito'):
                return urls.get('factura') or urls.get('boleta') or ''
            return next(iter(urls.values()), '')
        return ep.get('url', '').strip()

    def enviar(self, archivo_path: str, tipo_comprobante: str = 'boleta',
               ruc_emisor: str = '', serie: str = '',
               numero: str = '') -> List[Tuple[bool, Dict, str]]:
        """
        Envia archivo TXT a APIFAS usando headers HTTP.

        Args:
            archivo_path:     Ruta al archivo TXT generado
            tipo_comprobante: boleta | factura | nota_credito | anulacion | ...
            ruc_emisor:       RUC del emisor
            serie:            Serie del comprobante
            numero:           Numero del comprobante

        Returns:
            Lista de (exito, respuesta_dict, nombre_endpoint)
        """
        if self.mode == 'mock':
            print(f"   [MOCK] {Path(archivo_path).name}")
            return [(True, {
                'mock':        True,
                'codigo':      '0',
                'descripcion': 'MOCK OK',
                'archivo':     Path(archivo_path).name,
            }, 'MOCK')]

        resultados    = []
        es_anulacion  = (tipo_comprobante == 'anulacion')

        for ep in self.endpoints:
            if not ep.get('activo', True):
                continue

            nombre_ep = ep.get('nombre', 'APIFAS')
            url       = self._get_url(ep, tipo_comprobante)
            timeout   = ep.get('timeout', 30)
            creds     = ep.get('credenciales', {})

            if not url:
                print(f"   ⚠️  {nombre_ep}: sin URL para '{tipo_comprobante}' — omitido")
                continue

            try:
                with open(archivo_path, 'r', encoding='utf-8') as f:
                    texto = f.read()

                nombre_archivo = _nombre_archivo(
                    ruc              = ruc_emisor,
                    tipo_comprobante = tipo_comprobante,
                    serie            = serie,
                    numero           = numero,
                    es_anulacion     = es_anulacion,
                )

                headers = {
                    'Ruc':    ruc_emisor,
                    'Nombre': nombre_archivo,
                    'Texto':  texto,
                }
                if creds.get('usuario'):
                    headers['Usuario'] = creds['usuario']
                if creds.get('token'):
                    headers['Token'] = creds['token']

                resp  = requests.post(url, headers=headers, timeout=timeout)
                body  = resp.text.strip()
                exito = _es_exito(body)

                respuesta = {
                    'codigo':      '0' if exito else 'ERROR',
                    'descripcion': body,
                    'raw':         body[:200],
                }
                if not exito:
                    respuesta['error'] = body

                resultados.append((exito, respuesta, nombre_ep))

            except requests.Timeout:
                resultados.append((False, {
                    'error':       f'Timeout ({timeout}s)',
                    'descripcion': f'Sin respuesta en {timeout}s',
                    'codigo':      'TIMEOUT',
                }, nombre_ep))
            except requests.ConnectionError:
                resultados.append((False, {
                    'error':       'Sin conexion al servidor',
                    'descripcion': 'No se pudo conectar',
                    'codigo':      'CONNECTION_ERROR',
                }, nombre_ep))
            except Exception as e:
                resultados.append((False, {
                    'error':       str(e),
                    'descripcion': str(e),
                    'codigo':      'ERROR',
                }, nombre_ep))

        return resultados if resultados else [(False, {
            'error':       'Sin endpoints configurados',
            'descripcion': f'Sin URL para tipo {tipo_comprobante}',
            'codigo':      'NO_ENDPOINT',
        }, '')]

    def enviar_primero(self, archivo_path: str,
                       tipo_comprobante: str = 'boleta') -> Tuple[bool, Dict]:
        resultados = self.enviar(archivo_path, tipo_comprobante)
        if resultados:
            exito, respuesta, nombre = resultados[0]
            return exito, respuesta
        return False, {'error': 'Sin resultados'}
