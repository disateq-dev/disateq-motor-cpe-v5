"""
main.py — DisateQ Integrador CPE™ v5.0
Entry point — soporta 3 modos:
  python main.py              # UI + tray (modo normal)
  python main.py --tray       # Solo tray, sin UI (background)
  python main.py --cli <alias> # CLI sin UI ni tray
"""

import sys
import argparse
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


def _verificar_instancia_unica() -> object:
    try:
        import ctypes
        kernel32  = ctypes.windll.kernel32
        mutex     = kernel32.CreateMutexW(None, False, "DisateQIntegradorCPE_v5_SingleInstance")
        last_error= kernel32.GetLastError()
        if last_error == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.user32.MessageBoxW(
                0,
                "DisateQ Integrador CPE ya esta en ejecucion.\n\nRevisa la barra de tareas.",
                "DisateQ Integrador CPE",
                0x30
            )
            sys.exit(0)
        return mutex
    except Exception:
        return None


def _iniciar_scheduler(cliente_alias: str, tray=None) -> object:
    """Inicia el scheduler en background y retorna la instancia."""
    try:
        from src.scheduler import CpeScheduler

        def on_ciclo(resultados: dict):
            if tray:
                enviados  = resultados.get('enviados', 0)
                errores   = resultados.get('errores', 0)
                if errores > 0:
                    tray.actualizar_estado('warn', f'{enviados} entregados - {errores} con problema')
                    tray.mostrar_notificacion(
                        'DisateQ — Ciclo completado',
                        f'{enviados} entregados · {errores} con problema',
                        'warn'
                    )
                else:
                    tray.actualizar_estado('ok', f'{enviados} entregados')

        scheduler = CpeScheduler(cliente_alias, on_ciclo=on_ciclo)
        scheduler.iniciar()
        return scheduler

    except Exception as e:
        logger.error(f'[Main] Error iniciando scheduler: {e}')
        return None


def _get_cliente_alias() -> str:
    """Obtiene el alias del primer cliente configurado."""
    try:
        from src.config.client_loader import ClientLoader
        loader   = ClientLoader()
        clientes = loader.listar()
        if clientes:
            return clientes[0]
    except Exception:
        pass
    return None


def modo_tray_only() -> int:
    """
    Modo background — solo tray icon, sin UI.
    El scheduler corre automaticamente.
    """
    from src.tray import DisateQTray

    cliente_alias = _get_cliente_alias()
    tray = DisateQTray()

    scheduler = None
    _ui_abierta = threading.Event()

    def abrir_ui():
        if _ui_abierta.is_set():
            return
        _ui_abierta.set()
        try:
            from src.ui.app import start_app
            start_app()
        finally:
            _ui_abierta.clear()

    def ejecutar_ahora():
        if scheduler:
            scheduler.ejecutar_ahora()

    def salir():
        if scheduler:
            scheduler.detener()
        sys.exit(0)

    tray.on_abrir_ui = abrir_ui
    tray.on_ejecutar = ejecutar_ahora
    tray.on_salir    = salir

    if tray.iniciar():
        if cliente_alias:
            scheduler = _iniciar_scheduler(cliente_alias, tray)
            if scheduler:
                tray.actualizar_estado('ok', 'Scheduler activo')
            else:
                tray.actualizar_estado('warn', 'Sin cliente configurado')
        else:
            tray.actualizar_estado('warn', 'Sin cliente configurado')

        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                return app.exec()
        except Exception as e:
            logger.error(f'[Main] Error Qt loop: {e}')

    return 0


def modo_ui() -> int:
    """
    Modo normal — UI + tray.
    Cerrar la ventana NO detiene el Motor — minimiza al tray.
    """
    from src.tray  import DisateQTray
    from src.ui.app import start_app

    cliente_alias = _get_cliente_alias()
    tray = DisateQTray()

    scheduler = None
    _ui_abierta = threading.Event()

    def abrir_ui():
        if _ui_abierta.is_set():
            return
        _ui_abierta.set()
        try:
            start_app()
        finally:
            _ui_abierta.clear()

    def ejecutar_ahora():
        if scheduler:
            scheduler.ejecutar_ahora()

    def salir():
        if scheduler:
            scheduler.detener()
        sys.exit(0)

    tray.on_abrir_ui = abrir_ui
    tray.on_ejecutar = ejecutar_ahora
    tray.on_salir    = salir

    if tray.iniciar():
        if cliente_alias:
            scheduler = _iniciar_scheduler(cliente_alias, tray)

        # Abrir UI inmediatamente en thread separado
        threading.Thread(target=abrir_ui, daemon=True).start()

        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                return app.exec()
        except Exception as e:
            logger.error(f'[Main] Error Qt loop: {e}')

    else:
        # Si tray falla, arrancar UI directamente
        if cliente_alias:
            scheduler = _iniciar_scheduler(cliente_alias)
        return start_app()

    return 0


def modo_cli(alias: str, limit: int = None, mock: bool = False) -> int:
    """Modo CLI sin UI ni tray."""
    from src.motor import Motor
    motor    = Motor(cliente_alias=alias, modo_sender='mock' if mock else None)
    results  = motor.procesar(limit=limit)
    return 0 if results.get('errores', 0) == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description='DisateQ Integrador CPE v5.0')
    parser.add_argument('--tray',  action='store_true', help='Solo tray, sin UI')
    parser.add_argument('--cli',   metavar='CLIENTE',   help='Modo CLI')
    parser.add_argument('--limit', type=int,            help='Limite comprobantes')
    parser.add_argument('--mock',  action='store_true', help='Sin envio real')
    args = parser.parse_args()

    if args.cli:
        return modo_cli(args.cli, args.limit, args.mock)

    # UI o tray — verificar instancia unica
    _mutex = _verificar_instancia_unica()

    if args.tray:
        return modo_tray_only()
    else:
        return modo_ui()


if __name__ == '__main__':
    sys.exit(main())
