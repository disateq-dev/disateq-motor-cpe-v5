# src/adapters/adapter_factory.py
# DisateQ Motor CPE v5.0
# FIX: config_cliente normalizado — ruc en raiz para que GenericAdapter lo encuentre
# ─────────────────────────────────────────────────────────────────────────────

import yaml
import logging
from pathlib import Path
from src.adapters.base_adapter import BaseAdapter
from src.adapters.generic_adapter import GenericAdapter

logger = logging.getLogger(__name__)

TIPOS_SOPORTADOS = {
    'dbf',
    'excel', 'xlsx',
    'csv',
    'sqlserver', 'sql_server', 'mssql',
    'mysql', 'mariadb',
    'postgresql', 'postgres',
}


def _normalizar_config_cliente(data: dict) -> dict:
    """
    Normaliza el dict raw del YAML de cliente para que GenericAdapter
    encuentre los campos en la raiz.

    El YAML v5 tiene estructura anidada:
        empresa:
          ruc: '10715460632'
          razon_social: ...

    GenericAdapter espera acceso plano:
        config_cliente.get('ruc', '')
        config_cliente.get('razon_social', '')

    Esta funcion agrega los campos planos sin destruir la estructura original.
    """
    empresa = data.get('empresa', {})

    # Campos que GenericAdapter lee directamente
    if 'ruc' not in data and empresa.get('ruc'):
        data['ruc'] = empresa['ruc']
    if 'razon_social' not in data and empresa.get('razon_social'):
        data['razon_social'] = empresa['razon_social']
    if 'nombre_comercial' not in data and empresa.get('nombre_comercial'):
        data['nombre_comercial'] = empresa['nombre_comercial']

    return data


class AdapterFactory:
    """
    Lee el contrato YAML de un cliente y retorna el adaptador correcto.
    """

    @staticmethod
    def create(contrato_path: str, config_cliente: dict) -> BaseAdapter:
        ruta = Path(contrato_path)
        if not ruta.exists():
            raise FileNotFoundError(f"Contrato no encontrado: {contrato_path}")

        with open(ruta, 'r', encoding='utf-8') as f:
            contrato = yaml.safe_load(f)

        cliente_id  = contrato.get('cliente_id', ruta.stem)
        source_type = contrato.get('source', {}).get('type', '').lower()

        if not source_type:
            raise ValueError(
                f"[{cliente_id}] Contrato sin source.type: {contrato_path}"
            )
        if source_type not in TIPOS_SOPORTADOS:
            raise ValueError(
                f"[{cliente_id}] Tipo de fuente no soportado: '{source_type}'. "
                f"Soportados: {sorted(TIPOS_SOPORTADOS)}"
            )

        logger.info(
            f"[AdapterFactory] cliente={cliente_id} "
            f"fuente={source_type} "
            f"contrato={ruta.name}"
        )

        # Normalizar config_cliente para que GenericAdapter encuentre ruc en raiz
        config_cliente = _normalizar_config_cliente(config_cliente)

        return GenericAdapter(contrato, config_cliente)

    @staticmethod
    def create_from_cliente_id(
        cliente_id: str,
        base_path: str = 'config'
    ) -> BaseAdapter:
        contrato_path = Path(base_path) / 'contratos' / f'{cliente_id}.yaml'
        config_path   = Path(base_path) / 'clientes'  / f'{cliente_id}.yaml'

        if not config_path.exists():
            raise FileNotFoundError(f"Config cliente no encontrada: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config_cliente = yaml.safe_load(f)

        return AdapterFactory.create(str(contrato_path), config_cliente)
