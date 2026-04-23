"""
sender.py
=========
Envío universal de comprobantes — Motor CPE DisateQ™ v4.0

Soporta múltiples endpoints:
- PSE/OSE (APIFAS, Nubefact, etc.)
- SEE-Contribuyente (SUNAT directo)
- DisateQ Platform (futuro)
- MOCK (simulación local)
"""

import json
import requests
import yaml
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime


class UniversalSender:
    """
    Sender universal que se adapta a múltiples endpoints.
    Lee configuración desde endpoints.yaml.
    """
    
    def __init__(self, config_path: str = "config/endpoints.yaml", mode: str = None):
        """
        Args:
            config_path: Ruta al archivo de configuración
            mode: 'mock' para simulación, None para usar endpoint configurado
        """
        self.mode = mode
        
        if mode != 'mock':
            self.config = self._load_config(config_path)
            self.active_endpoint = self.config.get('active', 'apifas_pse')
        else:
            self.config = None
            self.active_endpoint = 'mock'
    
    def _load_config(self, config_path: str) -> Dict:
        """Carga configuración desde YAML"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config no encontrado: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parseando config: {e}")
    
    def enviar(self, archivo_path: str, cpe_data: Dict = None) -> Tuple[bool, Dict]:
        """
        Envía archivo al endpoint configurado.
        
        Args:
            archivo_path: Ruta al TXT o JSON generado
            cpe_data: Dict con datos del CPE (opcional)
        
        Returns:
            (exito, respuesta_dict)
        """
        if self.mode == 'mock':
            return self._enviar_mock(archivo_path)
        
        endpoint_config = self.config.get(self.active_endpoint)
        
        if not endpoint_config:
            return False, {'error': f'Endpoint no configurado: {self.active_endpoint}'}
        
        if not self._validar_credenciales(endpoint_config):
            return False, {'error': 'Credenciales incompletas'}
        
        tipo = endpoint_config.get('tipo')
        
        if tipo == 'pse_ose':
            return self._enviar_pse_ose(archivo_path, endpoint_config)
        elif tipo == 'see_contribuyente':
            return self._enviar_see(archivo_path, endpoint_config)
        else:
            return False, {'error': f'Tipo endpoint desconocido: {tipo}'}
    
    def _validar_credenciales(self, config: Dict) -> bool:
        """Valida que las credenciales estén configuradas"""
        creds = config.get('credenciales', {})
        
        if config['tipo'] == 'pse_ose':
            if config.get('formato_salida') == 'txt':
                return bool(creds.get('usuario') and creds.get('token'))
            else:
                return bool(creds.get('token'))
        
        elif config['tipo'] == 'see_contribuyente':
            required = ['ruc_emisor', 'usuario_sol', 'clave_sol']
            return all(creds.get(k) for k in required)
        
        return False
    
    def _enviar_pse_ose(self, archivo: str, config: Dict) -> Tuple[bool, Dict]:
        """Envío a PSE/OSE"""
        ambiente = self.config.get('configuracion', {}).get('ambiente', 'produccion')
        url = config[ambiente]['url']
        
        print(f"   📤 Enviando a {config['nombre']} ({ambiente})")
        
        try:
            if config['formato_salida'] == 'txt':
                return self._enviar_txt_multipart(archivo, url, config)
            else:
                return self._enviar_json(archivo, url, config)
        
        except requests.Timeout:
            return False, {'error': 'Timeout'}
        except requests.ConnectionError:
            return False, {'error': 'No se pudo conectar'}
        except Exception as e:
            return False, {'error': str(e)}
    
    def _enviar_txt_multipart(self, archivo: str, url: str, config: Dict) -> Tuple[bool, Dict]:
        """Envío TXT vía multipart/form-data"""
        with open(archivo, 'rb') as f:
            files = {'file': (Path(archivo).name, f, 'text/plain')}
            data = {
                'usuario': config['credenciales']['usuario'],
                'token': config['credenciales']['token']
            }
            
            timeout = config.get('timeout', 30)
            response = requests.post(url, files=files, data=data, timeout=timeout)
        
        return self._procesar_respuesta(response, config)
    
    def _enviar_json(self, archivo: str, url: str, config: Dict) -> Tuple[bool, Dict]:
        """Envío JSON vía application/json"""
        with open(archivo, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        
        headers = {'Content-Type': 'application/json'}
        timeout = config.get('timeout', 30)
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        
        return self._procesar_respuesta(response, config)
    
    def _enviar_see(self, archivo: str, config: Dict) -> Tuple[bool, Dict]:
        """Envío SEE-Contribuyente"""
        ambiente = self.config.get('configuracion', {}).get('ambiente', 'produccion')
        url = config[ambiente]['url']
        
        print(f"   📤 Enviando a SUNAT SEE via {config['nombre']}")
        
        with open(archivo, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        
        payload['credenciales_sunat'] = {
            'ruc': config['credenciales']['ruc_emisor'],
            'usuario_sol': config['credenciales']['usuario_sol'],
            'clave_sol': config['credenciales']['clave_sol'],
        }
        
        timeout = config.get('timeout', 45)
        response = requests.post(url, json=payload, timeout=timeout)
        
        return self._procesar_respuesta(response, config)
    
    def _procesar_respuesta(self, response, config: Dict) -> Tuple[bool, Dict]:
        """Procesa respuesta HTTP"""
        if response.status_code == 200:
            try:
                data = response.json()
                codigo_sunat = self._extraer_codigo_sunat(data, config)
                exito = codigo_sunat == '0' or codigo_sunat == 0
                
                if exito:
                    print(f"   ✅ Aceptado por SUNAT (código: {codigo_sunat})")
                else:
                    print(f"   ❌ Rechazado por SUNAT (código: {codigo_sunat})")
                
                return exito, data
            
            except json.JSONDecodeError:
                return False, {
                    'error': 'Respuesta no es JSON válido',
                    'status': response.status_code
                }
        else:
            return False, {
                'error': f'HTTP {response.status_code}',
                'mensaje': response.text[:500]
            }
    
    def _extraer_codigo_sunat(self, data: Dict, config: Dict) -> str:
        """Extrae código SUNAT de respuesta"""
        if self.active_endpoint.startswith('apifas'):
            return str(data.get('cdr', {}).get('codigo_sunat', ''))
        
        return str(data.get('codigo_sunat', data.get('codigo', '')))
    
    def _enviar_mock(self, archivo: str) -> Tuple[bool, Dict]:
        """Simula envío (sin conexión real)"""
        print(f"   📤 [MOCK] Enviando: {Path(archivo).name}")
        
        respuesta = {
            "estado": "OK",
            "codigo_respuesta": "0",
            "mensaje": "Comprobante aceptado por SUNAT (MOCK)",
            "comprobante": Path(archivo).stem,
            "fecha_proceso": datetime.now().isoformat(),
            "hash_cpe": "mock_hash_" + Path(archivo).stem,
            "cdr": {
                "codigo_sunat": "0",
                "descripcion_sunat": "Aceptado (simulación)",
                "notas": []
            },
            "modo": "MOCK"
        }
        
        print(f"   ✅ [MOCK] {respuesta['mensaje']}")
        
        return True, respuesta


class CDRProcessor:
    """Procesa CDR de respuesta SUNAT"""
    
    @staticmethod
    def procesar(respuesta: Dict, cpe: Dict) -> Dict:
        """Extrae información del CDR"""
        return {
            'comprobante': f"{cpe['serie']}-{cpe['numero']:08d}",
            'fecha_proceso': datetime.now().isoformat(),
            'estado_apifas': respuesta.get('estado', 'DESCONOCIDO'),
            'mensaje_apifas': respuesta.get('mensaje', ''),
            'hash_cpe': respuesta.get('hash_cpe', ''),
            'codigo_sunat': respuesta.get('cdr', {}).get('codigo_sunat', ''),
            'descripcion_sunat': respuesta.get('cdr', {}).get('descripcion_sunat', ''),
            'notas_sunat': respuesta.get('cdr', {}).get('notas', []),
            'aceptado_sunat': respuesta.get('cdr', {}).get('codigo_sunat') == '0'
        }
    
    @staticmethod
    def guardar_cdr(cdr_info: Dict, output_dir: str = "output/cdr") -> str:
        """Guarda CDR en archivo JSON"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{cdr_info['comprobante']}_CDR.json"
        filepath = output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cdr_info, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
