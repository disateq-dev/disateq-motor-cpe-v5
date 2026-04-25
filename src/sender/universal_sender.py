"""
universal_sender.py — Motor CPE DisateQ™ v4.0
Responsabilidad: enviar TXT/JSON a uno o multiples endpoints segun tipo de comprobante.
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

    def enviar(self, archivo_path: str, tipo_comprobante: str = 'boleta') -> List[Tuple[bool, Dict, str]]:
        """
        Envia archivo a todos los endpoints activos para el tipo de comprobante.

        Returns:
            Lista de (exito, respuesta_raw, nombre_endpoint)
        """
        if self.mode == 'mock':
            print(f"   [MOCK] {Path(archivo_path).name}")
            return [(True, {'mock': True, 'archivo': Path(archivo_path).name}, 'MOCK')]

        resultados = []
        for ep in self.endpoints:
            nombre  = ep.get('nombre', 'API')
            url     = ep.get('url', '')
            timeout = ep.get('timeout', 30)
            creds   = ep.get('credenciales', {})
            fmt     = ep.get('formato', 'txt')

            try:
                if fmt == 'txt':
                    with open(archivo_path, 'rb') as f:
                        files = {'file': (Path(archivo_path).name, f, 'text/plain')}
                        data  = {}
                        if creds.get('usuario'): data['usuario'] = creds['usuario']
                        if creds.get('token'):   data['token']   = creds['token']
                        resp = requests.post(url, files=files, data=data, timeout=timeout)
                else:
                    import json
                    with open(archivo_path, 'r', encoding='utf-8') as f:
                        payload = json.load(f)
                    headers = {'Content-Type': 'application/json'}
                    if creds.get('token'):
                        headers['Authorization'] = f"Bearer {creds['token']}"
                    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)

                exito = resp.status_code == 200
                try:
                    respuesta = resp.json()
                except Exception:
                    respuesta = {'raw': resp.text[:500], 'status': resp.status_code}

                resultados.append((exito, respuesta, nombre))

            except requests.Timeout:
                resultados.append((False, {'error': 'Timeout'}, nombre))
            except requests.ConnectionError:
                resultados.append((False, {'error': 'Sin conexion'}, nombre))
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
