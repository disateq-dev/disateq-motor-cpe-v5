# src/ui/app.py
# DisateQ Motor CPE v5.0 -- TASK-004 + TASK-014 + TASK-INS-01
# -----------------------------------------------------------------------------

"""
app.py
======
Arranque PyWebView -- DisateQ Motor CPE v5.0
TASK-014:    manejo correcto de rutas en exe PyInstaller 6.20+
             (_MEIPASS apunta a _internal\ en versiones nuevas)
TASK-INS-01: log y db apuntan a D: via paths_resolver
"""

import sys
import logging
import traceback
from pathlib import Path

from src.config.paths_resolver import get_data_dir

logger = logging.getLogger(__name__)


def _setup_logging_exe() -> None:
    """
    Configura logging a archivo cuando corre como exe.
    Ruta resuelta via paths_resolver -> D:\{cliente}\data\disateq.log
    """
    log_path = get_data_dir() / "disateq.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename = str(log_path),
        level    = logging.DEBUG,
        format   = '%(asctime)s %(levelname)s %(name)s: %(message)s',
        datefmt  = '%H:%M:%S',
        encoding = 'utf-8',
    )


def _resolver_frontend() -> Path:
    """
    Resuelve la ruta al frontend en todos los contextos:
    - Desarrollo: src/ui/frontend/
    - Exe PyInstaller 6.x: _MEIPASS/frontend/
    - Exe PyInstaller 6.20+: _MEIPASS apunta a _internal/,
      frontend en _internal/frontend/
    """
    if getattr(sys, 'frozen', False):
        meipass = Path(sys._MEIPASS)
        candidatos = [
            meipass / 'frontend',
            meipass.parent / '_internal' / 'frontend',
            meipass / '_internal' / 'frontend',
        ]
        for p in candidatos:
            if p.exists():
                logger.info(f"[App] Frontend (exe): {p}")
                return p
        logger.warning(f"[App] Frontend no encontrado en candidatos, usando _MEIPASS: {meipass}")
        return meipass / 'frontend'
    else:
        return Path(__file__).parent / 'frontend'


def _resolver_cwd_exe() -> Path:
    """
    En el exe, establece cwd a la carpeta del ejecutable
    para que rutas relativas de config\ funcionen correctamente.
    Las rutas de data\ y output\ las maneja paths_resolver -- no dependen del cwd.
    """
    if getattr(sys, 'frozen', False):
        import os
        exe_dir = Path(sys.executable).parent
        os.chdir(str(exe_dir))
        logger.info(f"[App] cwd -> {exe_dir}")
        return exe_dir
    return Path.cwd()


def start_app(db_path: str = None) -> int:
    """
    Inicializa y arranca la ventana PyWebView.
    Llamado desde main.py en modo UI.

    db_path: ruta a disateq_cpe.db. Si no se pasa, se resuelve
             via paths_resolver -> D:\{cliente}\data\disateq_cpe.db
    """
    # -- Logging en exe ------------------------------------------------------
    if getattr(sys, 'frozen', False):
        _setup_logging_exe()
        logger.info("=" * 50)
        logger.info("DisateQ Motor CPE v5.0 -- INICIO EXE")
        logger.info(f"exe      : {sys.executable}")
        logger.info(f"_MEIPASS : {sys._MEIPASS}")
        logger.info(f"data_dir : {get_data_dir()}")
        logger.info(f"Python   : {sys.version}")

    # -- Resolver db_path si no viene explicito ------------------------------
    if db_path is None:
        db_path = str(get_data_dir() / "disateq_cpe.db")

    try:
        import webview
    except ImportError as e:
        msg = f"[ERROR] pywebview no instalado: {e}"
        print(msg)
        logger.error(msg)
        return 1

    try:
        # -- Resolver cwd en exe ---------------------------------------------
        _resolver_cwd_exe()

        from src.ui.api import DisateQAPI

        # -- API -------------------------------------------------------------
        logger.info(f"[App] Inicializando DisateQAPI... db={db_path}")
        api = DisateQAPI(db_path=db_path)
        logger.info("[App] API lista.")

        # -- Pagina inicial --------------------------------------------------
        modo   = api.wz_detectar_modo()
        pagina = 'wizard.html' if modo.get('wizard') else 'index.html'

        # -- Frontend --------------------------------------------------------
        frontend_path = _resolver_frontend()
        html_path     = str(frontend_path / pagina)
        icono_path    = str(frontend_path / 'assets' / 'icons' / 'cpe_disateq.ico')

        logger.info(f"[App] Frontend : {frontend_path}")
        logger.info(f"[App] Pagina   : {pagina}")
        logger.info(f"[App] html_path existe: {Path(html_path).exists()}")
        logger.info(f"[App] icono existe    : {Path(icono_path).exists()}")

        print("=" * 60)
        print("  DisateQ Motor CPE v5.0")
        print("=" * 60)
        print(f"  Pagina  : {pagina}")
        print(f"  Frontend: {frontend_path}")
        print(f"  Data    : {get_data_dir()}")
        print("\n  Abriendo interfaz...\n")

        # -- Ventana ---------------------------------------------------------
        window = webview.create_window(
            title    = 'DisateQ Motor CPE v5.0',
            url      = html_path,
            js_api   = api,
            width    = 1280,
            height   = 800,
            min_size = (1024, 600),
            resizable= True,
        )

        api.set_window(window)

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

        # -- Arrancar --------------------------------------------------------
        webview.start(
            debug = _is_debug(),
            icon  = icono_path if Path(icono_path).exists() else None,
        )

        logger.info("[App] Ventana cerrada normalmente.")
        return 0

    except Exception as e:
        msg = f"[App] ERROR FATAL: {e}\n{traceback.format_exc()}"
        print(msg)
        logger.error(msg)
        if getattr(sys, 'frozen', False):
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Error al iniciar DisateQ Motor CPE:\n\n{e}\n\n"
                    f"Revisa el log en:\n{get_data_dir()}\\disateq.log",
                    "DisateQ Error",
                    0x10  # MB_ICONERROR
                )
            except Exception:
                pass
        return 1


def _is_debug() -> bool:
    """Activa devtools solo en desarrollo."""
    return not getattr(sys, 'frozen', False)
