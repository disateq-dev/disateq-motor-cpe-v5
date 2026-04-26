"""
adapter_factory.py
==================
Factory de adaptadores — DisateQ CPE™ v4.0

Instancia el adaptador correcto segun la config del cliente.
El Motor no necesita saber que tipo de fuente es.

Logica de seleccion:
    1. Si cliente tiene adaptador.contrato_path → GenericAdapter
    2. Si tipo_fuente == 'dbf'                 → DbfFarmaciaAdapter (legacy)
    3. Si tipo_fuente == 'xlsx'                → XlsxAdapter
    4. Cualquier otro tipo                     → Error claro
"""

from pathlib import Path


def get_adapter(config):
    """
    Instancia el adaptador correcto para un cliente.

    Args:
        config: ClientConfig (del client_loader)

    Returns:
        Instancia de BaseAdapter (sin conectar)

    Raises:
        ValueError: tipo de fuente no soportado
        FileNotFoundError: contrato_path no existe
    """
    # Prioridad 1: contrato YAML explicito → GenericAdapter
    contrato_path = config.data.get('adaptador', {}).get('contrato_path')
    if contrato_path:
        ruta_full = Path(config.config_path).parent.parent.parent / contrato_path
        if not ruta_full.exists():
            raise FileNotFoundError(
                f"Contrato no encontrado: {ruta_full}\n"
                f"Verifica adaptador.contrato_path en {config.config_path}"
            )
        from src.adapters.generic_adapter import GenericAdapter
        return GenericAdapter(str(ruta_full))

    # Prioridad 2: tipo explicito en fuente
    tipo  = config.tipo_fuente.lower()
    rutas = config.rutas_fuente

    if not rutas:
        raise ValueError(
            f"Cliente {config.alias}: fuente.rutas esta vacia en {config.config_path}"
        )

    ruta = rutas[0]

    if tipo == 'dbf':
        from src.adapters.dbf_farmacia_adapter import DbfFarmaciaAdapter
        return DbfFarmaciaAdapter(ruta)

    elif tipo == 'xlsx':
        from src.adapters.xlsx_adapter import XlsxAdapter
        return XlsxAdapter(ruta)

    elif tipo == 'generic':
        # Alternativa: tipo=generic + contrato_path en fuente
        contrato = config.fuente.get('contrato_path')
        if not contrato:
            raise ValueError(
                f"tipo=generic requiere fuente.contrato_path en {config.config_path}"
            )
        ruta_full = Path(config.config_path).parent.parent.parent / contrato
        from src.adapters.generic_adapter import GenericAdapter
        return GenericAdapter(str(ruta_full))

    else:
        raise ValueError(
            f"Tipo de fuente no soportado: '{tipo}'\n"
            f"Valores validos: dbf, xlsx, generic\n"
            f"Cliente: {config.config_path}"
        )
