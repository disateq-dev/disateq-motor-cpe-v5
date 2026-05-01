# src/adapters/adapter_factory.py
# DisateQ Motor CPE v5.0
# ─────────────────────────────────────────────────────────────────────────────

import yaml
import logging
from pathlib import Path

from src.adapters.base_adapter import BaseAdapter
from src.adapters.generic_adapter import GenericAdapter

logger = logging.getLogger(__name__)

# Tipos de fuente soportados → todos usan GenericAdapter
# La diferencia es como GenericAdapter los lee internamente
TIPOS_SOPORTADOS = {
    'dbf',
    'excel', 'xlsx',
    'csv',
    'sqlserver', 'sql_server', 'mssql',
    'mysql', 'mariadb',
    'postgresql', 'postgres',
}


class AdapterFactory:
    """
    Lee el contrato YAML de un cliente y retorna el adaptador correcto.

    Uso:
        adapter = AdapterFactory.create(
            contrato_path='config/contratos/farmacias_fas.yaml',
            config_cliente={...}   # cargado desde config/clientes/farmacias_fas.yaml
        )
        pendientes = adapter.read_pending()
    """

    @staticmethod
    def create(contrato_path: str, config_cliente: dict) -> BaseAdapter:
        """
        contrato_path:  ruta al YAML del contrato del cliente
        config_cliente: dict con ruc, razon_social, series, endpoints, etc.

        Retorna instancia de GenericAdapter configurada para el tipo de fuente.
        Lanza ValueError si el tipo de fuente no es soportado.
        """
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

        return GenericAdapter(contrato, config_cliente)

    @staticmethod
    def create_from_cliente_id(
        cliente_id: str,
        base_path: str = 'config'
    ) -> BaseAdapter:
        """
        Alternativa conveniente: carga contrato Y config del cliente
        por cliente_id, asumiendo estructura estandar de carpetas.

        config/contratos/{cliente_id}.yaml
        config/clientes/{cliente_id}.yaml
        """
        contrato_path  = Path(base_path) / 'contratos' / f'{cliente_id}.yaml'
        config_path    = Path(base_path) / 'clientes'  / f'{cliente_id}.yaml'

        if not config_path.exists():
            raise FileNotFoundError(f"Config cliente no encontrada: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config_cliente = yaml.safe_load(f)

        return AdapterFactory.create(str(contrato_path), config_cliente)
