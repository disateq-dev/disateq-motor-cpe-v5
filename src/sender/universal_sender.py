"""
universal_sender.py — Motor CPE DisateQ™ v5.0
TASK-008 FIX: parseo correcto del body APIFAS.

APIFAS siempre retorna HTTP 200 — el exito se determina por el body.
Formato de envio: multipart/form-data con field 'file'.

URLs confirmadas (produccion):
    comprobantes: https://apifas.disateq.com/produccion_text.php
    anulaciones:  https://apifas.disateq.com/anulacion_text.php

Respuestas de exito (cualquier otra = ERROR):
    'Procesando OSE'   — OSE
    'Anulando OSE'     — OSE anulaciones
    'Proceso-Aceptado' — SEE
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

# Respuestas que indican exito — cualquier otra es ERROR
RESPUESTAS_EXITO = {
    'procesando ose',
    'anulando ose',
    'proceso-aceptado',
    'por anular',
}


def _es_exito(body: str) -> bool:
    """
    APIFAS siempre retorna HTTP 200.
    El exito se determina por el contenido del body.
    Cualquier respuesta no reconocida = ERROR.
    """
    return body.strip().lower() in RESPUESTAS_EXITO


class UniversalSender:
    """Envia archivo CPE al endpoint correcto segun tipo de comprobante."""

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
        Envia archivo TXT a APIFAS via multipart/form-data.

        Returns:
            Lista de (exito, respuesta_dict, nombre_endpoint)
            exito=True solo si el body confirma aceptacion.
        """
        if self.mode == 'mock':
            print(f"   [MOCK] {Path(archivo_path).name}")
            return [(True, {
                'mock':        True,
                'codigo':      '0',
                'descripcion': 'MOCK OK',
                'archivo':     Path(archivo_path).name,
            }, 'MOCK')]

        resultados = []

        for ep in self.endpoints:
            if not ep.get('activo', True):
                continue

            nombre_ep = ep.get('nombre', 'APIFAS')
            url       = self._get_url(ep, tipo_comprobante)
            timeout   = ep.get('timeout', 30)
            creds     = ep.get('credenciales', {})
            fmt       = ep.get('formato', 'txt')

            if not url:
                print(f"   ⚠️  {nombre_ep}: sin URL para '{tipo_comprobante}' — omitido")
                continue

            try:
                if fmt == 'txt':
                    with open(archivo_path, 'rb') as f:
                        files = {'file': (Path(archivo_path).name, f, 'text/plain')}
                        data  = {}
                        if creds.get('usuario'): data['usuario'] = creds['usuario']
                        if creds.get('token'):   data['token']   = creds['token']
                        resp = requests.post(url, files=files, data=data, timeout=timeout)

                elif fmt == 'json':
                    import json
                    with open(archivo_path, 'r', encoding='utf-8') as f:
                        payload = json.load(f)
                    headers = {'Content-Type': 'application/json'}
                    if creds.get('token'):
                        headers['Authorization'] = f"Bearer {creds['token']}"
                    if creds.get('usuario'):
                        headers['X-User'] = creds['usuario']
                    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)

                else:
                    with open(archivo_path, 'rb') as f:
                        headers = {'Content-Type': 'application/octet-stream'}
                        if creds.get('token'):
                            headers['Authorization'] = f"Bearer {creds['token']}"
                        resp = requests.post(url, data=f.read(), headers=headers, timeout=timeout)

                # APIFAS siempre HTTP 200 — parsear body para exito real
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
