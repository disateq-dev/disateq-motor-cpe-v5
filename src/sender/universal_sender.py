"""
universal_sender.py — Motor CPE DisateQ™ v4.0
Responsabilidad: enviar TXT/JSON al endpoint correcto segun tipo de comprobante.

Estructura de endpoints:
    url_comprobantes: facturas + boletas + notas credito/debito
    url_anulaciones:  comunicaciones de baja
    url_guias:        guias de remision
    url_retenciones:  retenciones (opcional)
    url_percepciones: percepciones (opcional)

Compatible con estructura legacy (url: unica para todos).
"""
import requests
from pathlib import Path
from typing import Dict, List, Tuple


# Mapa tipo_comprobante -> campo URL en el endpoint
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


class UniversalSender:
    """Envia archivo CPE al endpoint correcto segun tipo de comprobante."""

    def __init__(self, endpoints: list = None, mode: str = None):
        """
        Args:
            endpoints: Lista de endpoints del ClientConfig
            mode: 'mock' para simulacion
        """
        self.mode      = mode
        self.endpoints = endpoints or []

    def _get_url(self, ep: Dict, tipo_comprobante: str) -> str:
        """
        Obtiene la URL correcta para el tipo de comprobante.

        Prioridad:
        1. Nueva estructura: url_comprobantes / url_anulaciones / url_guias
        2. Legacy: urls.{tipo} (estructura intermedia)
        3. Legacy: url (URL unica para todo)
        """
        # Nueva estructura: url_comprobantes / url_anulaciones / url_guias
        campo_url = URL_MAP.get(tipo_comprobante, 'url_comprobantes')
        url = ep.get(campo_url, '').strip()
        if url:
            return url

        # Fallback legacy: urls por tipo
        urls = ep.get('urls', {})
        if urls:
            url = urls.get(tipo_comprobante, '')
            if url:
                return url
            # Fallback dentro de urls
            if tipo_comprobante in ('nota_credito', 'nota_debito'):
                return urls.get('factura') or urls.get('boleta') or ''
            return next(iter(urls.values()), '')

        # Fallback legacy final: url unica
        return ep.get('url', '').strip()

    def enviar(self, archivo_path: str, tipo_comprobante: str = 'boleta') -> List[Tuple[bool, Dict, str]]:
        """
        Envia archivo al endpoint correcto para el tipo de comprobante.

        Args:
            archivo_path:     Ruta al archivo TXT/JSON generado
            tipo_comprobante: boleta | factura | nota_credito | nota_debito |
                              anulacion | guia | retencion | percepcion

        Returns:
            Lista de (exito, respuesta_dict, nombre_endpoint)
        """
        if self.mode == 'mock':
            print(f"   [MOCK] {Path(archivo_path).name}")
            return [(True, {'mock': True, 'archivo': Path(archivo_path).name}, 'MOCK')]

        resultados = []

        for ep in self.endpoints:
            if not ep.get('activo', True):
                continue

            nombre  = ep.get('nombre', 'API')
            url     = self._get_url(ep, tipo_comprobante)
            timeout = ep.get('timeout', 30)
            creds   = ep.get('credenciales', {})
            fmt     = ep.get('formato', 'txt')

            if not url:
                print(f"   ⚠️  {nombre}: sin URL para tipo '{tipo_comprobante}' — omitido")
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

                exito = resp.status_code == 200
                try:
                    respuesta = resp.json()
                except Exception:
                    respuesta = {'raw': resp.text[:500], 'status': resp.status_code}

                resultados.append((exito, respuesta, nombre))

            except requests.Timeout:
                resultados.append((False, {'error': f'Timeout ({timeout}s)'}, nombre))
            except requests.ConnectionError:
                resultados.append((False, {'error': 'Sin conexion al servidor'}, nombre))
            except Exception as e:
                resultados.append((False, {'error': str(e)}, nombre))

        return resultados if resultados else [(False, {'error': 'Sin endpoints configurados o sin URL para este tipo'}, '')]

    def enviar_primero(self, archivo_path: str, tipo_comprobante: str = 'boleta') -> Tuple[bool, Dict]:
        """Compatibilidad — retorna solo el primer resultado."""
        resultados = self.enviar(archivo_path, tipo_comprobante)
        if resultados:
            exito, respuesta, nombre = resultados[0]
            return exito, respuesta
        return False, {'error': 'Sin resultados'}
