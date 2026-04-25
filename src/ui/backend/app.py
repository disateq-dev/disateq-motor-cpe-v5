"""
app.py
======
Backend Eel — DisateQ™ Motor CPE v4.0
Ejecuta: python -m src.ui.backend.app
"""

import eel
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.client_loader import ClientLoader
from src.logger.cpe_logger import CpeLogger
from src.motor import Motor

# Inicializar Eel
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    frontend_path = os.path.join(base_path, 'frontend')
else:
    frontend_path = str(Path(__file__).parent.parent / 'frontend')

eel.init(frontend_path)

# Estado global
_motor = None
_logger = CpeLogger()
_client_config = None


def _cargar_cliente():
    global _client_config
    try:
        loader = ClientLoader()
        clientes = loader.listar()
        if clientes:
            _client_config = loader.cargar(clientes[0])
    except Exception as e:
        print(f"⚠️ No se pudo cargar cliente: {e}")


# ================================================================
# SISTEMA
# ================================================================

@eel.expose
def inicializar_sistema():
    try:
        _cargar_cliente()
        return {'success': True, 'message': 'Sistema inicializado'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def get_empresa_info():
    if _client_config:
        return {
            'nombre': _client_config.empresa.get('nombre_comercial', _client_config.razon_social),
            'ruc': _client_config.ruc,
            'alias': _client_config.alias
        }
    return {'nombre': 'Sin cliente configurado', 'ruc': '-', 'alias': ''}


# ================================================================
# DASHBOARD
# ================================================================

@eel.expose
def get_dashboard_stats():
    try:
        resumen = _logger.resumen()
        pendientes = resumen.get('LEIDO', 0) - resumen.get('ENVIADO', 0)
        pendientes = max(0, pendientes)
        return {
            'total':          pendientes,
            'enviados':       resumen.get('ENVIADO', 0),
            'fallidos':       resumen.get('ERROR', 0),
            'pendientes':     pendientes,
            'ignorados':      resumen.get('IGNORADO', 0),
            'ultimos_7_dias': _ultimos_7_dias()
        }
    except Exception as e:
        return {'total': 0, 'enviados': 0, 'fallidos': 0, 'pendientes': 0,
                'ignorados': 0, 'ultimos_7_dias': [0]*7}


def _ultimos_7_dias():
    try:
        from datetime import datetime, timedelta
        import sqlite3
        resultado = []
        for i in range(6, -1, -1):
            fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            rows = _logger.consultar(estado='ENVIADO', fecha_desde=fecha+'T00:00:00',
                                     fecha_hasta=fecha+'T23:59:59', limit=9999)
            resultado.append(len(rows))
        return resultado
    except:
        return [0]*7


@eel.expose
def get_recent_comprobantes():
    try:
        rows = _logger.consultar(estado='ENVIADO', limit=20)
        return [
            {
                'serie':   r['serie'],
                'numero':  r['numero'],
                'fecha':   r['fecha'][:10],
                'cliente': r.get('cliente_nombre') or '-',
                'total':   float(r.get('total') or 0.0),
                'estado':  r['estado'].lower()
            }
            for r in rows
        ]
    except:
        return []


# ================================================================
# LOGS
# ================================================================

@eel.expose
def get_logs(estado=None, limit=100):
    try:
        ruc = _client_config.ruc if _client_config else None
        rows = _logger.consultar(ruc=ruc, estado=estado, limit=limit)
        return {'exito': True, 'logs': rows}
    except Exception as e:
        return {'exito': False, 'error': str(e), 'logs': []}


@eel.expose
def get_logs_resumen():
    try:
        ruc = _client_config.ruc if _client_config else None
        return {'exito': True, 'resumen': _logger.resumen(ruc)}
    except Exception as e:
        return {'exito': False, 'error': str(e), 'resumen': {}}


# ================================================================
# PROCESAMIENTO
# ================================================================

@eel.expose
def conectar_fuente(tipo, archivo):
    try:
        if tipo == 'dbf':
            from src.adapters.dbf_farmacia_adapter import DbfFarmaciaAdapter
            adapter = DbfFarmaciaAdapter(archivo)
        else:
            from src.adapters.xlsx_adapter import XlsxAdapter
            adapter = XlsxAdapter(archivo)

        adapter.connect()
        pendientes = adapter.read_pending()
        adapter.disconnect()

        return {
            'exito': True, 'tipo': tipo, 'archivo': archivo,
            'pendientes': len(pendientes),
            'comprobantes': [
                {
                    'serie':   str(c.get('TIPO_FACTU','') or c.get('SERIE','')),
                    'numero':  int(str(c.get('NUMERO_FAC', c.get('NUMERO', 0))).strip() or 0),
                    'cliente': c.get('NOMBRE_CLIENTE', c.get('CLIENTE_NOMBRE', '-')),
                    'total':   float(str(c.get('TOTAL', c.get('REAL_PEDID', 0))).strip() or 0)
                }
                for c in pendientes[:50]
            ]
        }
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def procesar_motor(cliente_alias, limit=None, modo='mock'):
    """Procesa comprobantes usando el Motor completo."""
    try:
        motor = Motor(
            cliente_alias=cliente_alias,
            output_dir='output',
            modo_sender=modo
        )
        resultados = motor.procesar(limit=limit)
        return {'exito': True, 'resultados': resultados}
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def get_clientes_disponibles():
    try:
        loader = ClientLoader()
        clientes = loader.listar()
        resultado = []
        for alias in clientes:
            cfg = loader.cargar(alias)
            resultado.append({
                'alias':          alias,
                'ruc':            cfg.ruc,
                'nombre':         cfg.empresa.get('nombre_comercial', cfg.razon_social),
                'tipo_fuente':    cfg.tipo_fuente,
            })
        return {'exito': True, 'clientes': resultado}
    except Exception as e:
        return {'exito': False, 'error': str(e), 'clientes': []}


# ================================================================
# LICENCIA
# ================================================================

@eel.expose
def validar_licencia():
    try:
        from src.licenses.validator import LicenseValidator
        validator = LicenseValidator()
        result = validator.validate()
        if isinstance(result, tuple):
            is_valid = result[0]
            status   = result[1] if len(result) > 1 else 'unknown'
        else:
            is_valid = result
            status   = 'unknown'

        if is_valid:
            try:
                info = validator.get_license_info()
            except:
                info = {'license_type': 'Trial', 'client_name': 'Usuario',
                        'dias_restantes': 30, 'expires_at': '2026-05-23'}
            return {'valida': True, 'tipo': info.get('license_type','Trial'),
                    'cliente': info.get('client_name','Usuario'),
                    'dias_restantes': info.get('dias_restantes', 0),
                    'vencimiento': info.get('expires_at','')}
        else:
            return {'valida': False, 'error': status}
    except Exception as e:
        return {'valida': True, 'tipo': 'Demo', 'cliente': 'Usuario Demo',
                'dias_restantes': 999, 'vencimiento': '2099-12-31'}


# ================================================================
# UTILIDADES
# ================================================================

@eel.expose
def seleccionar_archivo():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    archivo = filedialog.askopenfilename(
        title='Seleccionar fuente de datos',
        filetypes=[('DBF', '*.dbf'), ('Excel', '*.xlsx'), ('Todos', '*.*')]
    )
    root.destroy()
    return archivo if archivo else None


@eel.expose
def seleccionar_carpeta():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    carpeta = filedialog.askdirectory(title='Seleccionar carpeta DBF')
    root.destroy()
    return carpeta if carpeta else None


# ================================================================
# CERRAR
# ================================================================

@eel.expose
def cerrar_sistema():
    """Cierra la aplicacion limpiamente"""
    import threading
    print("\n👋 Cerrando Motor CPE...\n")
    threading.Timer(0.5, lambda: __import__('os')._exit(0)).start()
    return True


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 60)
    print("  DisateQ™ Motor CPE v4.0 — Interfaz Gráfica")
    print("=" * 60)

    _cargar_cliente()

    if _client_config:
        print(f"✅ Cliente: {_client_config.razon_social} ({_client_config.ruc})")
    else:
        print("⚠️  Sin cliente configurado")

    print("\n🌐 Abriendo interfaz...\n")

    try:
        eel.start('index.html', size=(1280, 800), port=8080, mode='chrome',
                  cmdline_args=['--app=http://localhost:8080/index.html', '--disable-infobars'],
                  close_callback=lambda *a: print("\n👋 Cerrado\n"))
    except EnvironmentError:
        eel.start('index.html', size=(1280, 800), port=8080, mode=None)

    return 0


if __name__ == '__main__':
    sys.exit(main())



