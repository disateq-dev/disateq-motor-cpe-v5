"""
base_adapter.py
===============
Clase base para adaptadores — Motor CPE DisateQ™ v3.0

Define interfaz común para todos los adaptadores.
Todos los adaptadores heredan de BaseAdapter.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseAdapter(ABC):
    """
    Clase base abstracta para adaptadores de fuentes de datos.
    
    Todos los adaptadores (DBF, XLSX, SQL, etc.) deben heredar de esta clase
    e implementar los métodos abstractos.
    
    Flujo típico:
        1. connect() — Establecer conexión con fuente
        2. read_pending() — Leer comprobantes pendientes
        3. read_items(comprobante) — Leer items de un comprobante
        4. normalize(data, items) — Normalizar al formato CPE
        5. disconnect() — Cerrar conexión
    """
    
    def __init__(self):
        """Inicializa el adaptador."""
        pass
    
    @abstractmethod
    def connect(self):
        """
        Establece conexión con la fuente de datos.
        
        Debe implementarse en cada adaptador específico.
        Puede lanzar excepciones si la conexión falla.
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """
        Cierra conexión con la fuente de datos.
        
        Debe implementarse en cada adaptador específico.
        """
        pass
    
    @abstractmethod
    def read_pending(self) -> List[Dict]:
        """
        Lee comprobantes pendientes de envío.
        
        Returns:
            Lista de dicts con datos de cabecera de comprobantes pendientes.
            Cada dict representa un comprobante.
        
        Example:
            [
                {
                    'TIPO_DOCUMENTO': 'F',
                    'SERIE': '001',
                    'NUMERO': 1234,
                    'FECHA': '2026-04-19',
                    ...
                },
                ...
            ]
        """
        pass
    
    @abstractmethod
    def read_items(self, comprobante: Dict) -> List[Dict]:
        """
        Lee items/detalle de un comprobante específico.
        
        Args:
            comprobante: Dict con datos de cabecera del comprobante
        
        Returns:
            Lista de dicts con items del comprobante.
        
        Example:
            [
                {
                    'CODIGO': 'PROD001',
                    'DESCRIPCION': 'Producto de prueba',
                    'CANTIDAD': 2,
                    'PRECIO': 10.50,
                    ...
                },
                ...
            ]
        """
        pass
    
    @abstractmethod
    def normalize(self, source_data: Dict, source_items: List[Dict]) -> Dict:
        """
        Normaliza datos de la fuente al formato estándar del Motor CPE.
        
        Args:
            source_data: Datos de cabecera del comprobante (origen)
            source_items: Lista de items del comprobante (origen)
        
        Returns:
            Dict normalizado con estructura estándar del Motor CPE:
            {
                'comprobante': {
                    'tipo_doc': '01',  # 01=Factura, 03=Boleta
                    'serie': 'F001',
                    'numero': 1234,
                    'fecha_emision': '2026-04-19',
                    'moneda': 'PEN',
                    ...
                },
                'cliente': {
                    'tipo_doc': '6',
                    'numero_doc': '20123456789',
                    'denominacion': 'CLIENTE S.A.C.',
                    ...
                },
                'totales': {
                    'gravada': 100.00,
                    'exonerada': 0.00,
                    'inafecta': 0.00,
                    'igv': 18.00,
                    'total': 118.00,
                },
                'items': [
                    {
                        'codigo': 'PROD001',
                        'descripcion': 'Producto',
                        'cantidad': 2,
                        'unidad': 'NIU',
                        'precio_unitario': 10.00,
                        'valor_unitario': 8.47,
                        'subtotal_sin_igv': 16.94,
                        'igv': 3.05,
                        'total': 20.00,
                        'afectacion_igv': '10',
                        'unspsc': '10000000',
                    },
                    ...
                ]
            }
        """
        pass
    
    # Métodos opcionales (pueden sobrescribirse si es necesario)
    
    def validate_source(self) -> tuple[bool, str]:
        """
        Valida que la fuente de datos esté disponible y sea accesible.
        
        Returns:
            (es_valida, mensaje)
        
        Este método es opcional. Los adaptadores pueden sobrescribirlo
        para realizar validaciones específicas.
        """
        return True, "OK"
    
    def get_source_info(self) -> Dict:
        """
        Retorna información sobre la fuente de datos.
        
        Returns:
            Dict con información de la fuente (tipo, ubicación, estado, etc.)
        
        Este método es opcional.
        """
        return {
            'type': self.__class__.__name__,
            'status': 'connected' if hasattr(self, 'conn') and self.conn else 'disconnected',
        }


class AdapterError(Exception):
    """Excepción base para errores de adaptadores."""
    pass


class ConnectionError(AdapterError):
    """Error de conexión con la fuente de datos."""
    pass


class DataError(AdapterError):
    """Error en la estructura o contenido de los datos."""
    pass


class MappingError(AdapterError):
    """Error en el mapeo de campos."""
    pass
