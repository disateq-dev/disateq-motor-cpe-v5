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
from datetime import datetime, timedelta

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
            'ruc':    _client_config.ruc,
            'alias':  _client_config.alias
        }
    return {'nombre': 'Sin cliente configurado', 'ruc': '-', 'alias': ''}


# ================================================================
# DASHBOARD
# ================================================================

@eel.expose
def get_dashboard_stats():
    """Estadísticas rápidas desde SQLite — no conecta a fuente."""
    try:
        resumen = _logger.resumen()
        return {
            'remitidos':      resumen.get('REMITIDO',  0),
            'errores':        resumen.get('ERROR',     0),
            'ignorados':      resumen.get('IGNORADO',  0),
            'ultimos_7_dias': _ultimos_7_dias()
        }
    except Exception as e:
        return {'remitidos': 0, 'errores': 0, 'ignorados': 0, 'ultimos_7_dias': [0]*7}


@eel.expose
def get_pendientes_fuente():
    """Cuenta pendientes en fuente DBF — llamada separada (puede tardar)."""
    try:
        if _client_config and _client_config.tipo_fuente == 'dbf':
            from src.adapters.dbf_farmacia_adapter import DbfFarmaciaAdapter
            ruta = _client_config.rutas_fuente[0]
            a = DbfFarmaciaAdapter(ruta)
            a.connect()
            count = len(a.read_pending())
            a.disconnect()
            return {'count': count}
        return {'count': 0}
    except:
        return {'count': 0}


def _ultimos_7_dias():
    try:
        resultado = []
        for i in range(6, -1, -1):
            fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            rows = _logger.consultar(
                estado='REMITIDO',
                fecha_desde=fecha + 'T00:00:00',
                fecha_hasta=fecha + 'T23:59:59',
                limit=9999
            )
            resultado.append(len(rows))
        return resultado
    except:
        return [0] * 7


@eel.expose
def get_recent_comprobantes():
    try:
        rows = _logger.consultar(estado='REMITIDO', limit=20)
        return [
            {
                'serie':   r['serie'],
                'numero':  r['numero'],
                'fecha':   r['fecha'][:10],
                'cliente': r.get('cliente_nombre') or 'CLIENTES VARIOS',
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
        ruc  = _client_config.ruc if _client_config else None
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
            'exito':      True,
            'tipo':       tipo,
            'archivo':    archivo,
            'pendientes': len(pendientes),
            'comprobantes': [
                {
                    'serie':   str(c.get('TIPO_FACTU', '')).strip() + str(c.get('SERIE_FACT', '')).strip(),
                    'numero':  int(str(c.get('NUMERO_FAC', c.get('NUMERO', 0))).strip() or 0),
                    'cliente': c.get('NOMBRE_CLIENTE', c.get('RAZON_SOCI', 'CLIENTES VARIOS')),
                    'total':   float(str(c.get('TOTAL_FACT', c.get('TOTAL', 0))).strip() or 0)
                }
                for c in pendientes[:50]
            ]
        }
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def procesar_motor(cliente_alias, limit=None, modo='mock'):
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
def get_ruta_fuente(alias: str):
    try:
        cfg   = ClientLoader().cargar(alias)
        rutas = cfg.rutas_fuente
        return {'exito': True, 'ruta': rutas[0] if rutas else ''}
    except Exception as e:
        return {'exito': False, 'ruta': '', 'error': str(e)}


@eel.expose
def get_clientes_disponibles():
    try:
        loader    = ClientLoader()
        clientes  = loader.listar()
        resultado = []
        for alias in clientes:
            cfg = loader.cargar(alias)
            resultado.append({
                'alias':       alias,
                'ruc':         cfg.ruc,
                'nombre':      cfg.empresa.get('nombre_comercial', cfg.razon_social),
                'tipo_fuente': cfg.tipo_fuente,
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
        result    = validator.validate()

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
            return {
                'valida':          True,
                'tipo':            info.get('license_type', 'Trial'),
                'cliente':         info.get('client_name', 'Usuario'),
                'dias_restantes':  info.get('dias_restantes', 0),
                'vencimiento':     info.get('expires_at', '')
            }
        else:
            return {'valida': False, 'error': status}
    except:
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
# VERIFICAR CONEXION API
# ================================================================

@eel.expose
def verificar_conexion_api():
    try:
        import requests
        if _client_config:
            eps = _client_config.endpoints_activos
            if eps:
                url    = eps[0].get('url', '')
                nombre = ', '.join([e.get('nombre','') for e in eps])
                if url:
                    resp = requests.head(url, timeout=5)
                    return {'conectado': resp.status_code < 500, 'nombre': nombre}
        return {'conectado': False, 'nombre': 'Sin configurar'}
    except:
        return {'conectado': False, 'nombre': 'Sin conexion'}


# ================================================================
# CERRAR
# ================================================================

@eel.expose
def cerrar_sistema():
    import threading
    print("\n👋 Cerrando Motor CPE...\n")
    threading.Timer(0.5, lambda: __import__('os')._exit(0)).start()
    return True



# ================================================================
# HISTORIAL CONSOLIDADO
# ================================================================

@eel.expose
def get_historial(limit=200):
    """Una fila por comprobante con su ultimo estado."""
    try:
        ruc  = _client_config.ruc if _client_config else None
        rows = _logger.consultar(ruc=ruc, limit=9999)

        # Consolidar por (serie, numero) — quedarse con el ultimo estado
        comprobantes = {}
        for r in rows:
            key = (r['serie'], r['numero'])
            if key not in comprobantes:
                comprobantes[key] = r
            else:
                # Prioridad de estado: REMITIDO > ERROR > GENERADO > LEIDO > IGNORADO
                prioridad = {'REMITIDO':5,'ERROR':4,'GENERADO':3,'LEIDO':2,'IGNORADO':1}
                if prioridad.get(r['estado'],0) > prioridad.get(comprobantes[key]['estado'],0):
                    comprobantes[key] = r

        result = sorted(comprobantes.values(), key=lambda x: x['fecha'], reverse=True)[:limit]

        return {
            'exito': True,
            'total': len(comprobantes),
            'comprobantes': [
                {
                    'serie':    r['serie'],
                    'numero':   r['numero'],
                    'fecha':    r['fecha'][:10],
                    'cliente':  r.get('cliente_nombre') or 'CLIENTES VARIOS',
                    'total':    float(r.get('total') or 0.0),
                    'estado':   r['estado'].lower(),
                    'endpoint': r.get('endpoint') or '-',
                    'detalle':  r.get('detalle') or ''
                }
                for r in result
            ]
        }
    except Exception as e:
        return {'exito': False, 'error': str(e), 'total': 0, 'comprobantes': []}


# ================================================================
# CONFIGURACION
# ================================================================

@eel.expose
def verificar_clave_instalador(clave: str):
    try:
        if _client_config:
            return {'valida': clave == _client_config.clave_instalador}
        return {'valida': False}
    except:
        return {'valida': False}


@eel.expose
def get_config_cliente():
    try:
        if not _client_config:
            return {'exito': False, 'error': 'Sin cliente'}
        return {
            'exito':     True,
            'empresa':   _client_config.empresa,
            'fuente': {
                'tipo':  _client_config.tipo_fuente,
                'rutas': _client_config.rutas_fuente
            },
            'series':    _client_config.series,
            'endpoints': _client_config.endpoints,
            'envio':     _client_config.envio
        }
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def guardar_config(payload):
    try:
        import yaml
        cfg_path = None
        loader = ClientLoader()
        for alias in loader.listar():
            cfg_path = loader.clientes_dir / f"{alias}.yaml"
            break
        if not cfg_path:
            return {"exito": False, "error": "No hay cliente configurado"}

        with open(cfg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Campos editables empresa
        if payload.get("nombre_comercial"):
            data["empresa"]["nombre_comercial"] = payload["nombre_comercial"]
        if payload.get("alias"):
            data["empresa"]["alias"] = payload["alias"]

        # Credenciales API
        if "api_tercero" not in data.get("envio", {}):
            data.setdefault("envio", {})["api_tercero"] = {}
        if payload.get("url"):
            data["envio"]["api_tercero"]["url"] = payload["url"]
        data["envio"]["api_tercero"].setdefault("credenciales", {})
        if payload.get("usuario") is not None:
            data["envio"]["api_tercero"]["credenciales"]["usuario"] = payload["usuario"]
        if payload.get("token"):
            data["envio"]["api_tercero"]["credenciales"]["token"] = payload["token"]

        # Clave instalador
        if payload.get("clave_nueva"):
            data.setdefault("instalador", {})["clave"] = payload["clave_nueva"]

        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        # Recargar cliente
        _cargar_cliente()
        return {"exito": True}
    except Exception as e:
        return {"exito": False, "error": str(e)}

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
        eel.start(
            'index.html',
            size=(1280, 800),
            port=8080,
            mode='chrome',
            cmdline_args=['--app=http://localhost:8080/index.html', '--disable-infobars'],
            close_callback=lambda *a: print("\n👋 Cerrado\n")
        )
    except EnvironmentError:
        eel.start('index.html', size=(1280, 800), port=8080, mode=None)

    return 0


if __name__ == '__main__':
    sys.exit(main())
