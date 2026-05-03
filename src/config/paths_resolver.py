# src/config/paths_resolver.py -- DisateQ Motor CPE v5.0
# Resuelve las rutas de data y output segun el entorno:
#
#   Produccion (instalado):
#     Lee disateq_paths.cfg generado por el instalador.
#     data_dir   -> D:\{elegido por cliente}\data
#     output_dir -> D:\{elegido por cliente}\output
#
#   Desarrollo (local):
#     Sin disateq_paths.cfg -> rutas relativas al proyecto.
#     data_dir   -> {raiz_proyecto}\data
#     output_dir -> {raiz_proyecto}\output
#
# Uso:
#     from src.config.paths_resolver import get_data_dir, get_output_dir

import configparser
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CFG_FILENAME = "disateq_paths.cfg"


def _buscar_cfg() -> Path | None:
    """
    Busca disateq_paths.cfg en:
      1. exe dir produccion -- 4 niveles arriba de _internal/src/config/
         C:/Program Files/DisateQ/Motor CPE/disateq_paths.cfg
      2. Raiz proyecto desarrollo -- 3 niveles arriba de src/config/
    """
    candidatos = [
        Path(__file__).resolve().parent.parent.parent.parent / _CFG_FILENAME,
        Path(__file__).resolve().parent.parent.parent / _CFG_FILENAME,
    ]
    for candidato in candidatos:
        if candidato.is_file():
            logger.debug(f"paths_resolver: cfg en {candidato}")
            return candidato
    return None


def _rutas_desarrollo() -> dict:
    """Rutas relativas para entorno de desarrollo -- sin cfg.
    paths_resolver.py esta en src/config/ -> subir 3 niveles = raiz proyecto.
    """
    raiz = Path(__file__).resolve().parent.parent.parent
    return {
        "data_dir":   raiz / "data",
        "output_dir": raiz / "output",
    }


def resolver_rutas() -> dict:
    """
    Retorna dict con:
        data_dir   : Path absoluta a la carpeta data
        output_dir : Path absoluta a la carpeta output

    Nunca lanza excepcion -- cfg malformado cae a rutas de desarrollo.
    """
    cfg_path = _buscar_cfg()

    if cfg_path is None:
        logger.info("paths_resolver: sin cfg -- modo desarrollo")
        return _rutas_desarrollo()

    cfg = configparser.ConfigParser()
    try:
        cfg.read(cfg_path, encoding="utf-8")
        data_dir   = Path(cfg["paths"]["data_dir"])
        output_dir = Path(cfg["paths"]["output_dir"])
        logger.info(f"paths_resolver: produccion -- data={data_dir} output={output_dir}")
        return {"data_dir": data_dir, "output_dir": output_dir}
    except (KeyError, configparser.Error, ValueError) as exc:
        logger.warning(f"paths_resolver: cfg malformado ({exc}) -- fallback dev")
        return _rutas_desarrollo()


# Singleton: se resuelve una sola vez al importar
_rutas_cache: dict | None = None


def _get_rutas() -> dict:
    global _rutas_cache
    if _rutas_cache is None:
        _rutas_cache = resolver_rutas()
    return _rutas_cache


def get_data_dir() -> Path:
    """Retorna Path absoluta a la carpeta data (crea si no existe)."""
    d = _get_rutas()["data_dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_output_dir() -> Path:
    """Retorna Path absoluta a la carpeta output (crea si no existe)."""
    d = _get_rutas()["output_dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d
