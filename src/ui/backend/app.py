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
def get_historial(limit=200, tipo_doc=None, estado=None):
    """Una fila por comprobante con su ultimo estado."""
    try:
        ruc  = _client_config.ruc if _client_config else None
        rows = _logger.consultar(ruc=ruc, tipo_doc=tipo_doc, estado=estado, limit=9999)

        # Consolidar por (serie, numero) — quedarse con el ultimo estado
        comprobantes = {}
        for r in rows:
            key = (r['serie'], r['numero'])
            if key not in comprobantes:
                comprobantes[key] = r
            else:
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
                    'tipo_doc': r.get('tipo_doc', ''),
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

        # Endpoints
        if payload.get("endpoints") is not None:
            data["envio"] = {"endpoints": [
                {
                    "nombre": ep.get("nombre",""),
                    "activo": ep.get("activo", False),
                    "tipo_comprobante": ep.get("tipo_comprobante", ["todos"]),
                    "formato": ep.get("formato","txt"),
                    "url": ep.get("url",""),
                    "credenciales": {
                        "usuario": ep.get("usuario",""),
                        "token":   ep.get("token","")
                    },
                    "timeout": ep.get("timeout", 30)
                }
                for ep in payload["endpoints"]
            ]}

        # Series y correlativos
        if payload.get("series") is not None:
            data["series"] = {}
            for tipo, lista in payload["series"].items():
                data["series"][tipo] = [
                    {
                        "serie":              s.get("serie", ""),
                        "correlativo_inicio": int(s.get("correlativo_inicio", 0)),
                        "activa":             bool(s.get("activa", True))
                    }
                    for s in lista
                ]

        # Series y correlativos
        if payload.get("series") is not None:
            data["series"] = {}
            for tipo, lista in payload["series"].items():
                data["series"][tipo] = [
                    {
                        "serie":              s.get("serie", ""),
                        "correlativo_inicio": int(s.get("correlativo_inicio", 0)),
                        "activa":             bool(s.get("activa", True))
                    }
                    for s in lista
                ]

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

"""
PATCH: agregar al final de src/ui/backend/app.py (antes del bloque MAIN)

Endpoints Eel para el wizard de instalacion — DisateQ CPE™ v4.0
"""

"""
PATCH: agregar al final de src/ui/backend/app.py (antes del bloque MAIN)

Endpoints Eel para el scheduler — DisateQ CPE™ v4.0
También reemplazar _cargar_cliente() y cerrar_sistema() para integrar scheduler.
"""

# ================================================================
# SCHEDULER
# ================================================================

_scheduler = None


def _iniciar_scheduler():
    """Inicia el scheduler si el cliente está configurado y modo=automatico."""
    global _scheduler
    try:
        if not _client_config:
            return
        from src.scheduler import CpeScheduler

        def _on_ciclo(resultados):
            """Notifica a la UI cuando termina un ciclo."""
            try:
                eel.scheduler_ciclo_completado(resultados)
            except Exception:
                pass

        # Usar nombre del archivo YAML, no el alias interno
        from src.config.client_loader import ClientLoader
        loader = ClientLoader()
        alias_archivo = loader.listar()[0] if loader.listar() else _client_config.alias
        _scheduler = CpeScheduler(
            cliente_alias=alias_archivo,
            on_ciclo=_on_ciclo
        )
        _scheduler.iniciar()
    except Exception as e:
        print(f"⚠️  No se pudo iniciar scheduler: {e}")


@eel.expose
def get_scheduler_status():
    """Retorna estado actual del scheduler para la UI."""
    if _scheduler:
        return {'exito': True, 'status': _scheduler.get_status()}
    return {
        'exito': True,
        'status': {
            'modo': 'manual',
            'activo': False,
            'procesando': False,
            'intervalo_minutos': 10,
            'ciclos_ejecutados': 0,
            'ultimo_ciclo': None,
            'proximo_ciclo': None,
            'ultimo_resultado': {}
        }
    }


@eel.expose
def scheduler_iniciar():
    """Inicia el scheduler desde la UI."""
    global _scheduler
    try:
        if _scheduler:
            ok = _scheduler.iniciar()
            return {'exito': ok, 'mensaje': 'Scheduler iniciado' if ok else 'Modo manual — no aplica'}
        return {'exito': False, 'error': 'Scheduler no inicializado'}
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def scheduler_detener():
    """Detiene el scheduler desde la UI."""
    try:
        if _scheduler:
            _scheduler.detener()
            return {'exito': True}
        return {'exito': False, 'error': 'Scheduler no inicializado'}
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def scheduler_ejecutar_ahora():
    """Fuerza un ciclo inmediato desde la UI."""
    try:
        if _scheduler:
            result = _scheduler.ejecutar_ahora()
            return {'exito': True, 'resultado': result}
        # Si no hay scheduler, procesar directamente
        if _client_config:
            alias = _client_config.alias.lower().replace(' ', '_')
            motor = Motor(cliente_alias=alias, output_dir='output', modo_sender=None)
            resultados = motor.procesar()
            return {'exito': True, 'resultado': resultados}
        return {'exito': False, 'error': 'Sin cliente configurado'}
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def guardar_config_scheduler(payload: dict):
    """
    Guarda configuración del scheduler en el YAML del cliente.
    payload: {modo, intervalo_boletas}
    """
    try:
        import yaml
        from pathlib import Path

        loader = ClientLoader()
        clientes = loader.listar()
        if not clientes:
            return {'exito': False, 'error': 'Sin cliente configurado'}

        cfg_path = loader.clientes_dir / f"{clientes[0]}.yaml"
        with open(cfg_path, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        data['scheduler'] = {
            'modo':              payload.get('modo', 'manual'),
            'intervalo_boletas': int(payload.get('intervalo_boletas', 10)),
            'activo':            True
        }

        with open(cfg_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # Recargar cliente y scheduler
        _cargar_cliente()
        if _scheduler:
            _scheduler.recargar_config()
            # Si cambió a automático, iniciar
            if payload.get('modo') == 'automatico' and not _scheduler.esta_activo:
                _scheduler.iniciar()
            # Si cambió a manual, detener
            elif payload.get('modo') == 'manual' and _scheduler.esta_activo:
                _scheduler.detener()

        return {'exito': True}
    except Exception as e:
        return {'exito': False, 'error': str(e)}


# ================================================================
# WIZARD DE INSTALACION
# ================================================================

@eel.expose
def wz_validar_licencia(codigo: str):
    """Valida un codigo de licencia contra el servidor DisateQ."""
    try:
        from src.licenses.validator import LicenseValidator
        v = LicenseValidator()
        ok, status = v.validate_code(codigo)
        if ok:
            info = v.get_license_info()
            return {'valida': True, 'tipo': info.get('license_type', 'Full')}
        return {'valida': False, 'error': status}
    except Exception as e:
        # Si el servidor no responde, no bloqueamos
        return {'valida': False, 'error': str(e)}


@eel.expose
def wz_explorar_fuente(params: dict):
    """
    Ejecuta source_explorer en un thread separado (no bloquea UI).
    params: {tipo, ruta} o {tipo, servidor, base_datos, usuario, clave, puerto}
    """
    import threading
    import queue

    resultado_q = queue.Queue()

    def _explorar():
        try:
            from src.tools.source_explorer import SourceExplorer
            explorer = SourceExplorer()

            tipo = params.get('tipo', 'dbf')
            if tipo in ('dbf', 'xlsx', 'csv'):
                reporte = explorer.explorar(tipo=tipo, ruta=params.get('ruta', ''))
            else:
                reporte = explorer.explorar(
                    tipo=tipo,
                    servidor=params.get('servidor', ''),
                    base_datos=params.get('base_datos', ''),
                    usuario=params.get('usuario', ''),
                    clave=params.get('clave', ''),
                    puerto=params.get('puerto', 1433)
                )

            # Extraer info resumida para el frontend
            tablas = reporte.get('tablas', [])
            tablas_info = [
                {
                    'nombre':    t.get('nombre', ''),
                    'campos':    len(t.get('campos', [])),
                    'registros': t.get('total_registros', 0)
                }
                for t in tablas
            ]

            resultado_q.put({
                'exito':             True,
                'tablas':            len(tablas),
                'tablas_encontradas': tablas_info,
                'campos_detectados': reporte.get('campos_cpe_detectados', {}),
                'advertencias':      reporte.get('advertencias', []),
                'contrato':          reporte.get('contrato_sugerido', None)
            })
        except Exception as e:
            resultado_q.put({'exito': False, 'error': str(e)})

    t = threading.Thread(target=_explorar, daemon=True)
    t.start()
    t.join(timeout=30)  # Max 30 segundos

    if resultado_q.empty():
        return {'exito': False, 'error': 'Timeout al analizar la fuente (>30s)'}
    return resultado_q.get()


@eel.expose
def wz_guardar_config(payload: dict):
    """
    Guarda la configuracion completa generada por el wizard.
    Crea o sobreescribe config/clientes/{alias}.yaml
    """
    try:
        import yaml
        from pathlib import Path

        empresa  = payload.get('empresa', {})
        fuente   = payload.get('fuente', {})
        series   = payload.get('series', {})
        endpoint = payload.get('endpoint', {})
        licencia = payload.get('licencia', {})
        contrato = payload.get('contrato')
        modo     = payload.get('modo', 'nuevo')

        alias = empresa.get('alias', '').lower().replace(' ', '_')
        if not alias:
            return {'exito': False, 'error': 'Alias de empresa vacío'}

        # Estructura del YAML cliente
        data = {
            'empresa': {
                'ruc':              empresa.get('ruc', ''),
                'razon_social':     empresa.get('razon_social', ''),
                'nombre_comercial': empresa.get('nombre_comercial', empresa.get('razon_social', '')),
                'alias':            empresa.get('alias', alias)
            },
            'fuente': {
                'tipo':  fuente.get('tipo', 'dbf'),
                'rutas': [fuente.get('ruta', '')] if fuente.get('ruta') else []
            },
            'series': {
                'boleta':       _normalizar_series(series.get('boleta', [])),
                'factura':      _normalizar_series(series.get('factura', [])),
                'nota_credito': _normalizar_series(series.get('nota_credito', [])),
                'nota_debito':  _normalizar_series(series.get('nota_debito', []))
            },
            'envio': {
                'endpoints': [
                    {
                        'nombre':  endpoint.get('nombre', 'APIFAS'),
                        'activo':  True,
                        'tipo_comprobante': ['boleta', 'factura', 'nota_credito', 'nota_debito'],
                        'formato': 'txt',
                        'url':     endpoint.get('url', ''),
                        'credenciales': {
                            'usuario': endpoint.get('usuario', ''),
                            'token':   endpoint.get('token', '')
                        },
                        'timeout': 30
                    }
                ]
            },
            'licencia': {
                'tipo':   licencia.get('tipo', 'Trial'),
                'codigo': licencia.get('codigo', ''),
                'endpoint_validacion': 'https://licenses.disateq.com/v1/validate'
            },
            'instalador': {
                'clave': '1234'
            }
        }

        # Si hay fuente SQL, guardar datos de conexion
        if fuente.get('servidor'):
            data['fuente']['servidor']   = fuente.get('servidor', '')
            data['fuente']['base_datos'] = fuente.get('base_datos', '')
            data['fuente']['usuario']    = fuente.get('usuario', '')
            data['fuente']['puerto']     = fuente.get('puerto', 1433)

        # Si hay contrato generado por source_explorer, guardarlo
        if contrato:
            contrato_path = Path('config/contratos') / (alias + '.yaml')
            contrato_path.parent.mkdir(parents=True, exist_ok=True)
            with open(contrato_path, 'w', encoding='utf-8') as f:
                yaml.dump(contrato, f, allow_unicode=True, default_flow_style=False)
            data['fuente']['contrato_path'] = str(contrato_path)

        # Guardar YAML del cliente
        cliente_path = Path('config/clientes') / (alias + '.yaml')
        cliente_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cliente_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # Recargar cliente en memoria
        _cargar_cliente()
        return {'exito': True, 'path': str(cliente_path)}

    except Exception as e:
        return {'exito': False, 'error': str(e)}


def _normalizar_series(lista):
    return [
        {
            'serie':              s.get('serie', ''),
            'correlativo_inicio': int(s.get('correlativo_inicio', 0)),
            'activa':             bool(s.get('activa', True))
        }
        for s in lista if s.get('serie')
    ]


@eel.expose
def wz_ejecutar_prueba(cliente_alias: str):
    """Ejecuta Motor en modo mock con limit=3 para prueba del wizard."""
    try:
        motor = Motor(
            cliente_alias=cliente_alias,
            output_dir='output',
            modo_sender='mock'
        )
        resultados = motor.procesar(limit=3)
        return {'exito': True, 'resultados': resultados}
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def wz_enviar_real(cliente_alias: str):
    """Envía 1 comprobante real a SUNAT (con confirmación previa en frontend)."""
    try:
        motor = Motor(
            cliente_alias=cliente_alias,
            output_dir='output',
            modo_sender=None  # Envío real
        )
        resultados = motor.procesar(limit=1)
        exito = resultados.get('enviados', 0) > 0
        return {'exito': exito, 'resultados': resultados}
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def wz_abrir_motor():
    """Cierra el wizard y abre la UI principal."""
    import threading
    def _reabrir():
        import time
        time.sleep(0.5)
        # Re-lanzar con index.html
        try:
            eel.start('index.html', size=(1280, 800), port=8080, mode='chrome',
                      cmdline_args=[f'--app={url}', '--disable-infobars'])
        except Exception:
            pass
    threading.Thread(target=_reabrir, daemon=True).start()
    return True


@eel.expose
def wz_detectar_modo():
    """
    Retorna si debe mostrar wizard o UI principal.
    Llamado desde main() al iniciar.
    """
    try:
        loader = ClientLoader()
        clientes = loader.listar()
        return {'wizard': len(clientes) == 0}
    except Exception:
        return {'wizard': True}


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 60)
    print("  DisateQ™ Motor CPE v4.0 — Interfaz Gráfica")
    print("=" * 60)

    _cargar_cliente()
    _iniciar_scheduler()

    if _client_config:
        print(f"✅ Cliente: {_client_config.razon_social} ({_client_config.ruc})")
    else:
        print("⚠️  Sin cliente configurado")

    print("\n🌐 Abriendo interfaz...\n")

    try:
        modo = wz_detectar_modo()
        pagina = 'wizard.html' if modo['wizard'] else 'index.html'
        print(f'Pagina: {pagina}')
        url = f'http://localhost:8080/{pagina}'
        eel.start(
            pagina,
            size=(1280, 800),
            port=8080,
            mode='chrome',
            cmdline_args=[f'--app={url}', '--disable-infobars'],
            close_callback=lambda *a: print("\n👋 Cerrado\n")
        )
    except EnvironmentError:
        eel.start('index.html', size=(1280, 800), port=8080, mode=None)

    return 0


if __name__ == '__main__':
    sys.exit(main())
