"""
client_loader.py
================
Carga y valida configuracion de cliente — Motor CPE DisateQ™ v5.0
Soporta estructura legacy (empresa.ruc) y nueva (ruc_emisor).
Salta archivos YAML malformados o incompletos.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional


class ClientConfig:
    """Configuracion de un cliente/local."""

    def __init__(self, data: Dict, config_path: str):
        self.data        = data
        self.config_path = config_path

        # ── Normalizar estructura ──────────────────────────────
        # Soporta dos formatos:
        # A) Legacy: empresa: {ruc, razon_social, alias, ...}
        # B) Nuevo (wizard v5): ruc_emisor, razon_social, alias en raíz
        if 'empresa' in data:
            self.empresa = data['empresa']
        else:
            # Mapear campos raíz a estructura empresa
            self.empresa = {
                'ruc':              data.get('ruc_emisor', ''),
                'razon_social':     data.get('razon_social', ''),
                'nombre_comercial': data.get('nombre_comercial', data.get('razon_social', '')),
                'alias':            data.get('alias', ''),
                'regimen':          data.get('regimen', ''),
            }

        self.fuente   = data.get('fuente', {})
        self.series   = data.get('series', {})
        self.envio    = data.get('envio', {})
        self.licencia = data.get('licencia', {})

    # ── Propiedades básicas ────────────────────────────────────

    @property
    def ruc(self) -> str:
        return self.empresa.get('ruc', '')

    @property
    def clave_instalador(self) -> str:
        return str(self.data.get('instalador', {}).get('clave', '1234'))

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
    def endpoints(self) -> list:
        """Lista de endpoints configurados."""
        return self.envio.get('endpoints', [])

    @property
    def endpoints_activos(self) -> list:
        """Solo endpoints activos."""
        return [e for e in self.endpoints if e.get('activo', False)]

    # Mapa tipo_comprobante → campo URL en endpoint
    URL_CAMPO_MAP = {
        'boleta':       'url_comprobantes',
        'factura':      'url_comprobantes',
        'nota_credito': 'url_comprobantes',
        'nota_debito':  'url_comprobantes',
        'anulacion':    'url_anulaciones',
        'guia':         'url_guias',
        'retencion':    'url_retenciones',
        'percepcion':   'url_percepciones',
    }

    def get_endpoints_para(self, tipo_comprobante: str) -> list:
        """
        Retorna endpoints activos con URL configurada para el tipo.
        tipo: boleta | factura | nota_credito | nota_debito |
              anulacion | guia | retencion | percepcion
        """
        result    = []
        campo_url = self.URL_CAMPO_MAP.get(tipo_comprobante, 'url_comprobantes')

        for ep in self.endpoints_activos:
            if ep.get(campo_url, '').strip():
                result.append(ep)
                continue
            # Fallback legacy: urls{}
            urls = ep.get('urls', {})
            if urls:
                if tipo_comprobante in urls and urls[tipo_comprobante]:
                    result.append(ep); continue
                if tipo_comprobante in ('nota_credito', 'nota_debito'):
                    if urls.get('factura') or urls.get('boleta'):
                        result.append(ep); continue
            elif ep.get('url', '').strip():
                result.append(ep)

        return result

    # ── Compatibilidad legacy ──────────────────────────────────

    @property
    def modo_envio(self) -> str:
        eps = self.endpoints_activos
        return eps[0].get('nombre', 'api_tercero') if eps else 'sin_configurar'

    @property
    def config_envio(self) -> Dict:
        eps = self.endpoints_activos
        return eps[0] if eps else {}

    def get_series_activas(self, tipo: str) -> List[Dict]:
        """Retorna series activas para un tipo de comprobante."""
        return [s for s in self.series.get(tipo, []) if s.get('activa', False)]

    def serie_permitida(self, serie: str, numero: int) -> bool:
        """Valida si serie+numero está permitida según config."""
        for tipo in ('boleta', 'factura', 'nota_credito', 'nota_debito'):
            for s in self.get_series_activas(tipo):
                if s['serie'] == serie:
                    return numero >= s.get('correlativo_inicio', 0)
        return False

    def es_valido(self) -> bool:
        """True si el config tiene al menos RUC."""
        return bool(self.ruc)

    def __repr__(self):
        return f"ClientConfig(ruc={self.ruc}, alias={self.alias})"


class ClientLoader:
    """Carga configuraciones de clientes desde archivos YAML."""

    def __init__(self, clientes_dir: str = "config/clientes"):
        self.clientes_dir = Path(clientes_dir)

    def cargar(self, alias_o_ruc: str) -> ClientConfig:
        """
        Carga config de un cliente por stem de archivo, alias o RUC.
        Busca en este orden:
          1. Archivo {alias_o_ruc}.yaml
          2. Cualquier YAML cuyo empresa.ruc coincida
          3. Cualquier YAML cuyo empresa.alias coincida (case-insensitive)

        Raises FileNotFoundError si no encuentra nada válido.
        """
        # 1. Por nombre de archivo
        path = self.clientes_dir / f"{alias_o_ruc}.yaml"
        if path.exists():
            cfg = self._load(path)
            if cfg.es_valido():
                return cfg

        # 2. Buscar en todos los YAMLs válidos
        for yaml_file in sorted(self.clientes_dir.glob("*.yaml")):
            try:
                data = self._read(yaml_file)
                cfg  = ClientConfig(data, str(yaml_file))
                if not cfg.es_valido():
                    continue
                if (cfg.ruc == alias_o_ruc or
                        cfg.alias.upper() == alias_o_ruc.upper() or
                        yaml_file.stem == alias_o_ruc):
                    return cfg
            except Exception:
                continue

        raise FileNotFoundError(
            f"Config cliente no encontrada: {self.clientes_dir / alias_o_ruc}.yaml"
        )

    def listar(self) -> List[str]:
        """
        Lista stems de YAMLs válidos (con RUC).
        Ordena poniendo primero los que tienen series activas configuradas.
        """
        validos = []
        for f in sorted(self.clientes_dir.glob("*.yaml")):
            try:
                data = self._read(f)
                cfg  = ClientConfig(data, str(f))
                if cfg.es_valido():
                    validos.append(f.stem)
            except Exception:
                continue
        return validos

    def _load(self, path: Path) -> ClientConfig:
        data = self._read(path)
        return ClientConfig(data, str(path))

    def _read(self, path: Path) -> Dict:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
