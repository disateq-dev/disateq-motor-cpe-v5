"""
client_loader.py
================
Carga y valida configuracion de cliente — Motor CPE DisateQ™ v4.0
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional


class ClientConfig:
    """Configuracion de un cliente/local."""

    def __init__(self, data: Dict, config_path: str):
        self.data        = data
        self.config_path = config_path
        self.empresa     = data.get('empresa', {})
        self.fuente      = data.get('fuente', {})
        self.series      = data.get('series', {})
        self.envio       = data.get('envio', {})
        self.licencia    = data.get('licencia', {})

    @property
    def ruc(self) -> str:
        return self.empresa.get('ruc', '')

    @property
    def razon_social(self) -> str:
        return self.empresa.get('razon_social', '')

    @property
    def alias(self) -> str:
        return self.empresa.get('alias', '')

    @property
    def tipo_fuente(self) -> str:
        return self.fuente.get('tipo', '')

    @property
    def rutas_fuente(self) -> List[str]:
        return self.fuente.get('rutas', [])

    @property
    def modo_envio(self) -> str:
        return self.envio.get('modo', 'api_tercero')

    @property
    def config_envio(self) -> Dict:
        return self.envio.get(self.modo_envio, {})

    def get_series_activas(self, tipo: str) -> List[Dict]:
        """
        Retorna series activas para un tipo de comprobante.
        tipo: 'boleta' | 'factura' | 'nota_credito' | 'nota_debito'
        """
        return [s for s in self.series.get(tipo, []) if s.get('activa', False)]

    def serie_permitida(self, serie: str, numero: int) -> bool:
        """
        Valida si una serie+numero esta permitida segun config.
        - Serie debe estar configurada y activa
        - Numero debe ser >= correlativo_inicio
        """
        for tipo in ('boleta', 'factura', 'nota_credito', 'nota_debito'):
            for s in self.get_series_activas(tipo):
                if s['serie'] == serie:
                    return numero >= s.get('correlativo_inicio', 0)
        return False

    def __repr__(self):
        return f"ClientConfig(ruc={self.ruc}, alias={self.alias})"


class ClientLoader:
    """Carga configuraciones de clientes desde archivos YAML."""

    def __init__(self, clientes_dir: str = "config/clientes"):
        self.clientes_dir = Path(clientes_dir)

    def cargar(self, alias_o_ruc: str) -> ClientConfig:
        """
        Carga config de un cliente por alias o RUC.

        Args:
            alias_o_ruc: alias (farmacia_central) o RUC (10715460632)

        Returns:
            ClientConfig

        Raises:
            FileNotFoundError si no se encuentra el cliente
        """
        # Buscar por alias (nombre de archivo)
        path = self.clientes_dir / f"{alias_o_ruc}.yaml"
        if path.exists():
            return self._load(path)

        # Buscar por RUC dentro de todos los archivos
        for yaml_file in self.clientes_dir.glob("*.yaml"):
            data = self._read(yaml_file)
            if data.get('empresa', {}).get('ruc') == alias_o_ruc:
                return ClientConfig(data, str(yaml_file))

        raise FileNotFoundError(f"Cliente no encontrado: {alias_o_ruc}")

    def listar(self) -> List[str]:
        """Lista aliases de todos los clientes configurados."""
        return [f.stem for f in self.clientes_dir.glob("*.yaml")]

    def _load(self, path: Path) -> ClientConfig:
        data = self._read(path)
        return ClientConfig(data, str(path))

    def _read(self, path: Path) -> Dict:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
