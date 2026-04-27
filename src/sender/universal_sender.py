"""
universal_sender.py — Motor CPE DisateQ™ v4.0
Responsabilidad: enviar TXT/JSON a uno o multiples endpoints segun tipo de comprobante.

Soporta estructura de URLs por tipo:
    urls:
        boleta:    https://...
        factura:   https://...
        anulacion: https://...

Compatible con estructura legacy (url: unica para todos).
"""
import requests
from pathlib import Path
from typing import Dict, List, Tuple


class UniversalSender:
    """Envia archivo CPE a los endpoints configurados para el tipo de comprobante."""

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

        Soporta dos estructuras:
        1. Nueva: urls.{tipo} -> URL especifica por tipo
        2. Legacy: url -> URL unica para todos
        """
        # Nueva estructura: urls por tipo
        urls = ep.get('urls', {})
        if urls:
            # Buscar URL exacta para el tipo
            url = urls.get(tipo_comprobante)
            if url:
                return url
            # Fallback: boleta/factura usan misma URL en muchos servicios
            if tipo_comprobante in ('nota_credito', 'nota_debito'):
                url = urls.get('factura') or urls.get('boleta')
                if url:
                    return url
            # Ultimo fallback: cualquier URL disponible
            return next(iter(urls.values()), '')

        # Legacy: url unica
        return ep.get('url', '')

    def enviar(self, archivo_path: str, tipo_comprobante: str = 'boleta') -> List[Tuple[bool, Dict, str]]:
        """
        Envia archivo a todos los endpoints activos para el tipo de comprobante.

        Args:
            archivo_path:     Ruta al archivo TXT/JSON generado
            tipo_comprobante: boleta | factura | nota_credito | nota_debito | anulacion | guia

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
                resultados.append((False, {'error': f'Sin URL para tipo {tipo_comprobante}'}, nombre))
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
                    # Otros formatos (XML, etc) — enviar como binario
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

        return resultados if resultados else [(False, {'error': 'Sin endpoints configurados'}, '')]

    def enviar_primero(self, archivo_path: str, tipo_comprobante: str = 'boleta') -> Tuple[bool, Dict]:
        """Compatibilidad — retorna solo el primer resultado."""
        resultados = self.enviar(archivo_path, tipo_comprobante)
        if resultados:
            exito, respuesta, nombre = resultados[0]
            return exito, respuesta
        return False, {'error': 'Sin resultados'}
