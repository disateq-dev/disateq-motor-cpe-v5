"""
tray.py — DisateQ Integrador CPE™ v5.0
Tray icon PySide6 — Motor corre en background independiente de la UI.
"""

import sys
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_icon_path() -> str:
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
        candidatos = [
            base / 'frontend' / 'assets' / 'icons' / 'cpe_disateq.ico',
            base.parent / '_internal' / 'frontend' / 'assets' / 'icons' / 'cpe_disateq.ico',
        ]
        for c in candidatos:
            if c.exists():
                return str(c)
    return str(Path(__file__).parent / 'ui' / 'frontend' / 'assets' / 'icons' / 'cpe_disateq.ico')


class DisateQTray:
    """
    Tray icon para DisateQ Integrador CPE.
    - Click simple  -> mostrar/ocultar UI
    - Click derecho -> menu contextual
    - Double click  -> ejecutar ciclo ahora
    """

    def __init__(self, on_abrir_ui=None, on_ejecutar=None, on_salir=None):
        self.on_abrir_ui = on_abrir_ui
        self.on_ejecutar = on_ejecutar
        self.on_salir    = on_salir
        self._tray       = None
        self._app        = None
        self._estado     = 'ok'  # ok | warn | error

    def iniciar(self):
        """Inicia el tray en el thread principal (requerido por Qt)."""
        try:
            from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
            from PySide6.QtGui     import QIcon, QAction
            from PySide6.QtCore    import Qt

            if not QApplication.instance():
                self._app = QApplication(sys.argv)

            icon_path = _get_icon_path()
            icon      = QIcon(icon_path) if Path(icon_path).exists() else QIcon()

            self._tray = QSystemTrayIcon(icon)
            self._tray.setToolTip('DisateQ Integrador CPE — Flujo estable')

            menu = QMenu()

            accion_abrir = QAction('Abrir panel')
            accion_abrir.triggered.connect(self._abrir_ui)
            menu.addAction(accion_abrir)

            accion_ejecutar = QAction('Ejecutar ciclo ahora')
            accion_ejecutar.triggered.connect(self._ejecutar)
            menu.addAction(accion_ejecutar)

            menu.addSeparator()

            self._accion_estado = QAction('Estado: Flujo estable')
            self._accion_estado.setEnabled(False)
            menu.addAction(self._accion_estado)

            menu.addSeparator()

            accion_salir = QAction('Cerrar DisateQ')
            accion_salir.triggered.connect(self._salir)
            menu.addAction(accion_salir)

            self._tray.setContextMenu(menu)
            self._tray.activated.connect(self._on_activated)
            self._tray.show()

            logger.info('[Tray] Tray icon iniciado')
            return True

        except Exception as e:
            logger.error(f'[Tray] Error iniciando tray: {e}')
            return False

    def actualizar_estado(self, estado: str, mensaje: str = ''):
        """
        Actualiza icono y tooltip segun estado.
        estado: 'ok' | 'warn' | 'error' | 'procesando'
        """
        if not self._tray:
            return
        self._estado = estado
        labels = {
            'ok':          'Flujo estable',
            'warn':        'Con observaciones',
            'error':       'Atencion requerida',
            'procesando':  'Procesando...',
            'offline':     'Sin conexion',
        }
        label = labels.get(estado, estado)
        texto = f'DisateQ Integrador CPE — {label}'
        if mensaje:
            texto += f'\n{mensaje}'
        self._tray.setToolTip(texto)
        if hasattr(self, '_accion_estado'):
            self._accion_estado.setText(f'Estado: {label}')

    def mostrar_notificacion(self, titulo: str, mensaje: str, tipo: str = 'info'):
        """Muestra notificacion del sistema desde el tray."""
        if not self._tray:
            return
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            iconos = {
                'info':    QSystemTrayIcon.MessageIcon.Information,
                'warn':    QSystemTrayIcon.MessageIcon.Warning,
                'error':   QSystemTrayIcon.MessageIcon.Critical,
            }
            self._tray.showMessage(titulo, mensaje, iconos.get(tipo, QSystemTrayIcon.MessageIcon.Information), 4000)
        except Exception as e:
            logger.error(f'[Tray] Error notificacion: {e}')

    def _on_activated(self, reason):
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                self._ejecutar()
            elif reason == QSystemTrayIcon.ActivationReason.Trigger:
                self._abrir_ui()
        except Exception:
            pass

    def _abrir_ui(self):
        if self.on_abrir_ui:
            threading.Thread(target=self.on_abrir_ui, daemon=True).start()

    def _ejecutar(self):
        if self.on_ejecutar:
            threading.Thread(target=self.on_ejecutar, daemon=True).start()
            self.mostrar_notificacion('DisateQ', 'Ejecutando ciclo...', 'info')

    def _salir(self):
        if self.on_salir:
            self.on_salir()
        if self._tray:
            self._tray.hide()
        if self._app:
            self._app.quit()
