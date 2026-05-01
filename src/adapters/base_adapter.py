# src/adapters/base_adapter.py
# DisateQ Motor CPE v5.0
# ─────────────────────────────────────────────────────────────────────────────

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseAdapter(ABC):
    """
    Clase base para todos los adaptadores de fuente de datos.

    Cada fuente (DBF, Excel, SQL, CSV) implementa esta interfaz.
    El Motor solo conoce esta interfaz — no sabe nada del tipo de fuente.

    Flujo obligatorio:
        read_pending() → read_items() → normalize() → [write_flag()]

    write_flag() es opcional: si la fuente no permite escritura,
    el metodo base retorna silenciosamente. SQLite es siempre la
    fuente de verdad de envios, con o sin write_flag().
    """

    def __init__(self, contrato: dict, config_cliente: dict):
        """
        contrato:       dict cargado desde config/contratos/{cliente_id}.yaml
        config_cliente: dict cargado desde config/clientes/{cliente_id}.yaml
                        Contiene ruc, razon_social, series permitidas, endpoints.
        """
        self.contrato = contrato
        self.config_cliente = config_cliente

    @abstractmethod
    def read_pending(self) -> List[Dict[str, Any]]:
        """
        Lee todos los comprobantes pendientes desde la fuente.
        Incluye comprobantes normales Y notas/anulaciones pendientes.

        Cada registro retornado debe incluir:
            '_tipo_registro': 'comprobante' | 'nota'
            '_tabla_origen':  nombre de la tabla/archivo fuente

        No normaliza — retorna los datos raw de la fuente.
        """

    @abstractmethod
    def read_items(self, comprobante: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Lee los items (lineas de detalle) de un comprobante especifico.

        comprobante: registro raw retornado por read_pending()
        Retorna lista de dicts raw con los items — sin normalizar.
        """

    @abstractmethod
    def normalize(
        self,
        comprobante: Dict[str, Any],
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Convierte comprobante + items raw a la estructura CPE interna estandar.

        La estructura normalizada es independiente del tipo de fuente.
        Los generadores (txt_generator, json_generator) consumen esta estructura.

        Campos obligatorios en el resultado:
            tipo_comprobante, serie, numero, es_nota, es_anulacion,
            ruc_emisor, cliente_tipo_doc, cliente_num_doc, cliente_nombre,
            fecha_emision, total_gravada, total_igv, total, items
        """

    def write_flag(self, comprobante: Dict[str, Any], estado: str) -> None:
        """
        Escribe el resultado del envio de vuelta a la fuente original.

        estado: 'enviado' | 'error'

        Implementacion por defecto: no hace nada (retorno silencioso).
        Cada adaptador la sobreescribe si su fuente permite escritura.

        El Motor NO falla si write_flag() no hace nada —
        SQLite es la fuente de verdad y ya registro el estado antes
        de llamar a este metodo.

        NOTA farmacias_fas DBF:
            Verificar bloqueo de archivo durante escritura simultanea
            con el sistema legacy. Si hay bloqueo → dejar esta
            implementacion base activa (solo SQLite controla).
        """
