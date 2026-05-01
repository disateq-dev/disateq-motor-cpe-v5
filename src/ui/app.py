# src/ui/app.py
# DisateQ Motor CPE v5.0 — TASK-004
# ─────────────────────────────────────────────────────────────────────────────

"""
app.py
======
Arranque PyWebView — DisateQ™ Motor CPE v5.0

Reemplaza Eel (Chrome) con PyWebView (WebView2 nativo Windows 10/11).
Sin dependencia de Chrome — empaquetado limpio con PyInstaller.

Uso:
    from src.ui.app import start_app
    start_app()
"""

import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def start_app(db_path: str = 'data/disateq_cpe.db') -> int:
    """
    Inicializa y arranca la ventana PyWebView.
    Llamado desde main.py en modo UI.

    Retorna 0 si cierra normalmente.
    """
    try:
        import webview
    except ImportError:
        print("[ERROR] pywebview no instalado. Ejecuta: pip install pywebview")
        return 1

    from src.ui.api import DisateQAPI

    # ── Instanciar API (init SQLite + cargar cliente) ─────────────────────
    api = DisateQAPI(db_path=db_path)

    # ── Detectar pagina inicial (wizard o dashboard) ──────────────────────
    modo   = api.wz_detectar_modo()
    pagina = 'wizard.html' if modo.get('wizard') else 'index.html'

    # ── Ruta al frontend ──────────────────────────────────────────────────
    if getattr(sys, 'frozen', False):
        # Ejecutable PyInstaller
        import os
        frontend_path = Path(sys._MEIPASS) / 'frontend'
    else:
        frontend_path = Path(__file__).parent / 'frontend'

    html_path = str(frontend_path / pagina)

    logger.info(f"[App] Frontend: {html_path}")
    logger.info(f"[App] Pagina inicial: {pagina}")

    # ── Icono ─────────────────────────────────────────────────────────────
    icono_path = str(frontend_path / 'assets' / 'icons' / 'cpe_disateq.ico')

    # ── Crear ventana ─────────────────────────────────────────────────────
    window = webview.create_window(
        title    = 'DisateQ™ Motor CPE v5.0',
        url      = html_path,
        js_api   = api,
        width    = 1280,
        height   = 800,
        min_size = (1024, 600),
        resizable= True,
    )

    # Pasar referencia de ventana a la API (para callbacks JS)
    api.set_window(window)

    # ── Callback on_loaded — iniciar scheduler tras cargar la UI ─────────
    def on_loaded():
        try:
            api.iniciar_scheduler()
            if api._client_config:
                logger.info(
                    f"[App] Cliente: {api._client_config.razon_social} "
                    f"({api._client_config.ruc})"
                )
        except Exception as e:
            logger.warning(f"[App] on_loaded error: {e}")

    window.events.loaded += on_loaded

    # ── Arrancar WebView2 ─────────────────────────────────────────────────
    print("=" * 60)
    print("  DisateQ™ Motor CPE v5.0")
    print("=" * 60)
    print(f"  Pagina: {pagina}")
    print(f"  Frontend: {frontend_path}")
    print("\n  Abriendo interfaz...\n")

    webview.start(
        debug   = _is_debug(),
        icon    = icono_path if Path(icono_path).exists() else None,
    )

    return 0


def _is_debug() -> bool:
    """Activa devtools solo en desarrollo (no en ejecutable)."""
    return not getattr(sys, 'frozen', False)
