"""
json_generator.py
=================
Generador JSON estándar DisateQ — Motor CPE v4.0

Genera JSON normalizado para envío a:
- PSE/OSE (APIFAS, Nubefact, etc.)
- SEE-Contribuyente (SUNAT directo vía API)
- DisateQ Platform (futuro)
"""

import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import Dict


class JsonGenerator:
    """
    Genera archivos JSON estándar DisateQ.
    Formato universal compatible con cualquier endpoint REST.
    """
    
    @staticmethod
    def generate(cpe: Dict, output_dir: str = "output/json") -> str:
        """
        Genera JSON normalizado desde CPE interno.
        
        Args:
            cpe: Comprobante normalizado (desde XlsxAdapter.normalize)
            output_dir: Directorio donde guardar
        
        Returns:
            Ruta del archivo generado
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Nombre archivo: SERIE-NUMERO.json
        filename = f"{cpe['serie']}-{cpe['numero']:08d}.json"
        filepath = output_path / filename
        
        # Construir payload JSON
        payload = {
            "version": "1.0",
            "formato": "disateq_standard",
            "timestamp": datetime.now().isoformat(),
            
            "emisor": {
                "ruc": cpe.get('emisor_ruc', ''),
                "razon_social": cpe.get('emisor_razon_social', ''),
                "nombre_comercial": cpe.get('emisor_nombre_comercial', ''),
                "direccion": cpe.get('emisor_direccion', ''),
                "ubigeo": cpe.get('emisor_ubigeo', '150101'),
            },
            
            "receptor": {
                "tipo_documento": cpe['cliente']['tipo_doc'],
                "numero_documento": cpe['cliente']['numero_doc'],
                "denominacion": cpe['cliente']['denominacion'],
                "direccion": cpe['cliente'].get('direccion', '-'),
                "email": cpe['cliente'].get('email', ''),
            },
            
            "comprobante": {
                "tipo": cpe['tipo_doc'],
                "serie": cpe['serie'],
                "numero": cpe['numero'],
                "fecha_emision": cpe['fecha_iso'],
                "hora_emision": cpe.get('hora_emision', '00:00:00'),
                "moneda": cpe['moneda'],
                "tipo_operacion": cpe.get('tipo_operacion', '0101'),
            },
            
            "items": [
                {
                    "codigo": item['codigo'],
                    "descripcion": item['descripcion'],
                    "unidad": item['unidad'],
                    "cantidad": float(item['cantidad']),
                    "precio_unitario": JsonGenerator._to_float(item['precio_con_igv']),
                    "valor_unitario": JsonGenerator._to_float(item['precio_sin_igv']),
                    "subtotal": JsonGenerator._to_float(item['subtotal_sin_igv']),
                    "igv": JsonGenerator._to_float(item['igv']),
                    "total": JsonGenerator._to_float(item['total']),
                    "afectacion_igv": item.get('afectacion_igv', '10'),
                    "codigo_tributo": "1000",
                    "unspsc": item.get('unspsc', '10000000'),
                }
                for item in cpe['items']
            ],
            
            "totales": {
                "gravada": JsonGenerator._to_float(cpe['totales']['gravada']),
                "exonerada": JsonGenerator._to_float(cpe['totales']['exonerada']),
                "inafecta": JsonGenerator._to_float(cpe['totales']['inafecta']),
                "igv": JsonGenerator._to_float(cpe['totales']['igv']),
                "icbper": JsonGenerator._to_float(cpe['totales'].get('icbper', 0)),
                "total": JsonGenerator._to_float(cpe['totales']['total']),
            },
            
            "forma_pago": cpe.get('forma_pago', 'Contado'),
            "observaciones": cpe.get('observaciones', ''),
        }
        
        # Guardar JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    @staticmethod
    def _to_float(value) -> float:
        """Convierte Decimal/str a float"""
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            try:
                return float(value)
            except:
                return 0.0
        return 0.0


if __name__ == '__main__':
    print("JsonGenerator v4.0 - DisateQ™")
    print("Use: from json_generator import JsonGenerator")
