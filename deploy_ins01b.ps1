# =============================================================================
# deploy_ins01b.ps1 — TASK-INS-01 Cierre (motor.py + app.py)
# Reescritura completa de motor.py y app.py
# integrando paths_resolver para rutas C:/D:
# =============================================================================

$ErrorActionPreference = "Stop"
$Root = "D:\DisateQ\Proyectos\disateq-motor-cpe-v5"

Write-Host "=== TASK-INS-01b — motor.py + app.py ===" -ForegroundColor Cyan

# =============================================================================
# 1. src\motor.py
# =============================================================================
$motor = @'
# src/motor.py
# DisateQ Motor CPE v5.0
# TASK-008 FIX: sender.enviar() recibe ruc_emisor, serie, numero para APIFAS
# TASK-INS-01: rutas data\ y output\ via paths_resolver (C:/D: separados)
# ─────────────────────────────────────────────────────────────────────────────

"""
motor.py
========
Motor CPE DisateQ™ v5.0 — Orquestador principal
"""

import time
import logging
from pathlib import Path
from typing import Dict, Optional

from src.config.client_loader import ClientLoader
from src.config.paths_resolver import get_data_dir, get_output_dir
from src.generators.txt_generator import TxtGenerator
from src.generators.anulacion_generator import AnulacionGenerator
from src.sender.universal_sender import UniversalSender
from src.database.schema import init_db
from src.database.cpe_logger import CpeLogger
from src.adapters.adapter_factory import AdapterFactory

logger = logging.getLogger(__name__)


class Motor:
    """Orquestador principal del Motor CPE v5.0."""

    def __init__(
        self,
        cliente_alias: str,
        output_dir:    str = None,
        db_path:       str = None,
        modo_sender:   str = None,
    ):
        # ── Rutas via paths_resolver ──────────────────────────────────────
        # Si no se pasan explicitamente, se resuelven desde disateq_paths.cfg
        # (produccion) o desde rutas relativas al proyecto (desarrollo).
        self.output_dir  = output_dir or str(get_output_dir())
        self._db_path    = db_path    or str(get_data_dir() / "disateq_cpe.db")
        self.modo_sender = modo_sender

        loader      = ClientLoader()
        self.config = loader.cargar(cliente_alias)
        self.ruc    = self.config.ruc
        self.alias  = cliente_alias
        logger.info(f"[Motor] Cliente: {self.config.razon_social} ({self.ruc})")
        logger.info(f"[Motor] output_dir : {self.output_dir}")
        logger.info(f"[Motor] db_path    : {self._db_path}")

        self.conn = init_db(self._db_path)
        self.log  = CpeLogger(self.conn)
        logger.info(f"[Motor] SQLite listo: {self._db_path}")

        self._modo_sender = modo_sender

    # ═════════════════════════════════════════════════════════════════════════
    # PROCESAMIENTO PRINCIPAL
    # ═════════════════════════════════════════════════════════════════════════

    def procesar(self, limit: Optional[int] = None) -> Dict:
        results = {'procesados': 0, 'enviados': 0, 'errores': 0, 'ignorados': 0}

        adapter    = AdapterFactory.create_from_cliente_id(self.alias)
        pendientes = adapter.read_pending()

        if limit:
            pendientes = pendientes[:limit]

        logger.info(f"[Motor] Pendientes: {len(pendientes)}")
        print(f"📋 Pendientes: {len(pendientes)}")

        for raw in pendientes:
            try:
                items = adapter.read_items(raw)
                cpe   = adapter.normalize(raw, items)

                serie  = cpe['serie']
                numero = cpe['numero']

                # ── Anti-duplicado ────────────────────────────────────────
                if self.log.ya_remitido(self.ruc, serie, numero):
                    self.log.registrar_ignorado(cpe, self.alias, 'Duplicado — ya REMITIDO')
                    results['ignorados'] += 1
                    logger.debug(f"[Motor] IGNORADO duplicado: {serie}-{numero}")
                    continue

                # ── Validar serie ─────────────────────────────────────────
                if not self.config.serie_permitida(serie, int(numero)):
                    self.log.registrar_ignorado(
                        cpe, self.alias,
                        f"Serie {serie}/{numero} no permitida por config"
                    )
                    results['ignorados'] += 1
                    logger.info(f"[Motor] IGNORADO serie: {serie}-{numero}")
                    continue

                self.log.registrar(cpe, 'LEIDO', self.alias)

                # ── Generar TXT ───────────────────────────────────────────
                t0 = time.time()

                if cpe.get('es_anulacion'):
                    ruta_txt = AnulacionGenerator.generate(
                        cpe, self.ruc,
                        output_dir=str(Path(self.output_dir) / "anulaciones")
                    )
                else:
                    ruta_txt = TxtGenerator.generate(cpe, self.output_dir)

                self.log.registrar(cpe, 'GENERADO', self.alias)

                # ── Enviar ────────────────────────────────────────────────
                tipo_str = self._tipo_str(cpe)
                sender   = self._get_sender(tipo_str)
                endpoint = self._nombre_endpoint(tipo_str)

                self.log.registrar(cpe, 'GENERADO', self.alias, endpoint=endpoint)

                # TASK-008 FIX: pasar ruc_emisor, serie, numero al sender
                # para que APIFAS pueda construir el header Nombre correcto
                resultados_envio = sender.enviar(
                    archivo_path     = ruta_txt,
                    tipo_comprobante = tipo_str,
                    ruc_emisor       = self.ruc,
                    serie            = serie,
                    numero           = numero,
                )

                exito     = all(r[0] for r in resultados_envio)
                respuesta = resultados_envio[0][1] if resultados_envio else {}
                duracion  = int((time.time() - t0) * 1000)

                if exito:
                    self.log.registrar(
                        cpe, 'REMITIDO', self.alias,
                        endpoint          = endpoint,
                        respuesta_raw     = str(respuesta),
                        codigo_sunat      = str(respuesta.get('codigo', '')),
                        descripcion_sunat = str(respuesta.get('descripcion', '')),
                    )
                    self.log.limpiar_forzar_reenvio(self.ruc, serie, numero)
                    adapter.write_flag(raw, 'enviado')
                    results['enviados'] += 1
                    print(f"   ✅ {serie}-{numero} ({duracion}ms)")

                else:
                    detalle = respuesta.get('error', str(respuesta))
                    self.log.registrar(
                        cpe, 'ERROR', self.alias,
                        endpoint          = endpoint,
                        descripcion_sunat = detalle,
                    )
                    adapter.write_flag(raw, 'error')
                    results['errores'] += 1
                    print(f"   ❌ {serie}-{numero} — {detalle}")

                results['procesados'] += 1

            except Exception as e:
                serie  = raw.get('SERIE_FACT', '?')
                numero = raw.get('NUMERO_FAC', '?')
                logger.exception(f"[Motor] Error inesperado {serie}-{numero}: {e}")
                results['errores'] += 1
                print(f"   ❌ Error inesperado {serie}-{numero}: {e}")

        print(f"\n📊 Resumen: {results}")
        logger.info(f"[Motor] Resumen: {results}")
        return results

    def procesar_anulaciones(self, limit: Optional[int] = None) -> Dict:
        logger.info("[Motor] procesar_anulaciones() → delegando a procesar()")
        return self.procesar(limit=limit)

    # ═════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═════════════════════════════════════════════════════════════════════════

    def _get_sender(self, tipo_str: str) -> UniversalSender:
        if self._modo_sender == 'mock':
            return UniversalSender(mode='mock')
        endpoints = self.config.get_endpoints_para(tipo_str)
        return UniversalSender(endpoints=endpoints)

    def _nombre_endpoint(self, tipo_str: str) -> str:
        endpoints = self.config.get_endpoints_para(tipo_str)
        return ','.join(ep.get('nombre', '') for ep in endpoints) or 'mock'

    @staticmethod
    def _tipo_str(cpe: Dict) -> str:
        mapa = {'1': 'factura', '2': 'boleta', '3': 'nota_credito', '7': 'nota_debito'}
        if cpe.get('es_anulacion'):
            return 'anulacion'
        return mapa.get(str(cpe.get('tipo_comprobante', '2')), 'boleta')
'@

Set-Content -Path "$Root\src\motor.py" -Value $motor -Encoding UTF8
Write-Host "  [OK] src\motor.py" -ForegroundColor Green

# =============================================================================
# 2. src\ui\app.py
# =============================================================================
$app = @'
# src/ui/app.py
# DisateQ Motor CPE v5.0 — TASK-004 + TASK-014 + TASK-INS-01
# ─────────────────────────────────────────────────────────────────────────────

"""
app.py
======
Arranque PyWebView — DisateQ™ Motor CPE v5.0
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
    Ruta resuelta via paths_resolver → D:\{cliente}\data\disateq.log
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
    Las rutas de data\ y output\ las maneja paths_resolver — no dependen del cwd.
    """
    if getattr(sys, 'frozen', False):
        import os
        exe_dir = Path(sys.executable).parent
        os.chdir(str(exe_dir))
        logger.info(f"[App] cwd → {exe_dir}")
        return exe_dir
    return Path.cwd()


def start_app(db_path: str = None) -> int:
    """
    Inicializa y arranca la ventana PyWebView.
    Llamado desde main.py en modo UI.

    db_path: ruta a disateq_cpe.db. Si no se pasa, se resuelve
             via paths_resolver → D:\{cliente}\data\disateq_cpe.db
    """
    # ── Logging en exe ────────────────────────────────────────────────────
    if getattr(sys, 'frozen', False):
        _setup_logging_exe()
        logger.info("=" * 50)
        logger.info("DisateQ Motor CPE v5.0 — INICIO EXE")
        logger.info(f"exe      : {sys.executable}")
        logger.info(f"_MEIPASS : {sys._MEIPASS}")
        logger.info(f"data_dir : {get_data_dir()}")
        logger.info(f"Python   : {sys.version}")

    # ── Resolver db_path si no viene explicito ────────────────────────────
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
        # ── Resolver cwd en exe ───────────────────────────────────────────
        _resolver_cwd_exe()

        from src.ui.api import DisateQAPI

        # ── API ───────────────────────────────────────────────────────────
        logger.info(f"[App] Inicializando DisateQAPI... db={db_path}")
        api = DisateQAPI(db_path=db_path)
        logger.info("[App] API lista.")

        # ── Pagina inicial ────────────────────────────────────────────────
        modo   = api.wz_detectar_modo()
        pagina = 'wizard.html' if modo.get('wizard') else 'index.html'

        # ── Frontend ──────────────────────────────────────────────────────
        frontend_path = _resolver_frontend()
        html_path     = str(frontend_path / pagina)
        icono_path    = str(frontend_path / 'assets' / 'icons' / 'cpe_disateq.ico')

        logger.info(f"[App] Frontend : {frontend_path}")
        logger.info(f"[App] Pagina   : {pagina}")
        logger.info(f"[App] html_path existe: {Path(html_path).exists()}")
        logger.info(f"[App] icono existe    : {Path(icono_path).exists()}")

        print("=" * 60)
        print("  DisateQ™ Motor CPE v5.0")
        print("=" * 60)
        print(f"  Pagina  : {pagina}")
        print(f"  Frontend: {frontend_path}")
        print(f"  Data    : {get_data_dir()}")
        print("\n  Abriendo interfaz...\n")

        # ── Ventana ───────────────────────────────────────────────────────
        window = webview.create_window(
            title    = 'DisateQ™ Motor CPE v5.0',
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

        # ── Arrancar ──────────────────────────────────────────────────────
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
                    "DisateQ™ Error",
                    0x10  # MB_ICONERROR
                )
            except Exception:
                pass
        return 1


def _is_debug() -> bool:
    """Activa devtools solo en desarrollo."""
    return not getattr(sys, 'frozen', False)
'@

Set-Content -Path "$Root\src\ui\app.py" -Value $app -Encoding UTF8
Write-Host "  [OK] src\ui\app.py" -ForegroundColor Green

# =============================================================================
# Resumen + git
# =============================================================================
Write-Host ""
Write-Host "=== TASK-INS-01 COMPLETO — 6/6 archivos ===" -ForegroundColor Green
Write-Host ""
Write-Host "Archivos entregados en total:" -ForegroundColor Yellow
Write-Host "  installer\disateq_setup.iss          (deploy_ins01.ps1)"
Write-Host "  installer\build_installer.ps1         (deploy_ins01.ps1)"
Write-Host "  installer\README_INSTALADOR.md        (deploy_ins01.ps1)"
Write-Host "  src\config\paths_resolver.py          (deploy_ins01.ps1)"
Write-Host "  src\motor.py                          (este script)"
Write-Host "  src\ui\app.py                         (este script)"
Write-Host ""
Write-Host "Git:" -ForegroundColor Cyan
Write-Host "  git add installer\ src\config\paths_resolver.py src\motor.py src\ui\app.py"
Write-Host "  git commit -m 'TASK-INS-01: instalador Inno Setup + paths_resolver C:/D:'"
Write-Host "  git push"
Write-Host ""
Write-Host "Probar instalador:" -ForegroundColor Cyan
Write-Host "  .\build.ps1"
Write-Host "  .\installer\build_installer.ps1 -Cliente farmacia_central"
Write-Host ""
