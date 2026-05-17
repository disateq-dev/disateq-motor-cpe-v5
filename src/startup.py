"""
startup.py — DisateQ Integrador CPE™ v5.0
Registro en Windows startup para arranque automatico con el sistema.
"""

import sys
import logging
import winreg
from pathlib import Path

logger = logging.getLogger(__name__)

STARTUP_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME     = "DisateQIntegradorCPE"


def _get_exe_path() -> str:
    """Retorna la ruta del ejecutable actual."""
    if getattr(sys, 'frozen', False):
        return str(Path(sys.executable))
    return str(Path(sys.executable)) + f' "{Path(__file__).parent.parent / "main.py"}"'


def registrar_startup(silencioso: bool = False) -> bool:
    """
    Registra el Motor en Windows startup.
    Arranca minimizado en tray al iniciar Windows.

    Args:
        silencioso: si True, arranca sin mostrar UI (solo tray)

    Returns:
        True si se registró correctamente
    """
    try:
        exe = _get_exe_path()
        valor = f'"{exe}" --tray' if silencioso else f'"{exe}"'

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, valor)

        logger.info(f'[Startup] Registrado en startup: {valor}')
        return True

    except Exception as e:
        logger.error(f'[Startup] Error registrando startup: {e}')
        return False


def desregistrar_startup() -> bool:
    """
    Elimina el Motor del Windows startup.

    Returns:
        True si se eliminó correctamente
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)

        logger.info('[Startup] Eliminado del startup')
        return True

    except FileNotFoundError:
        logger.info('[Startup] No estaba registrado')
        return True
    except Exception as e:
        logger.error(f'[Startup] Error eliminando startup: {e}')
        return False


def esta_registrado() -> bool:
    """Verifica si el Motor está registrado en startup."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
