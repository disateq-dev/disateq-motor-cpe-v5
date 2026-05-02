# src/ui/api.py
# DisateQ Motor CPE v5.0 — TASK-004 + TASK-005 + TASK-006
# ─────────────────────────────────────────────────────────────────────────────

"""
DisateQAPI
==========
Clase que expone metodos Python al frontend via PyWebView (js_api).

En el frontend JS:
    // Antes (Eel):
    eel.metodo(params)(callback)

    // Ahora (PyWebView):
    window.pywebview.api.metodo(params).then(callback)

Los metodos son identicos en firma y retorno — solo cambia el mecanismo
de llamada. El frontend requiere actualizacion de llamadas (TASK-004 JS).
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.database.schema import init_db
from src.database.cpe_logger import CpeLogger
from src.motor import Motor
from src.config.client_loader import ClientLoader
from src.tools.wizard_service import test_fuente, guardar_wizard

logger = logging.getLogger(__name__)


class DisateQAPI:
    """
    API publica expuesta al frontend via PyWebView js_api.
    Se instancia una vez en app.py y se pasa a webview.create_window().
    """

    def __init__(self, db_path: str = 'data/disateq_cpe.db'):
        self._db_path      = db_path
        self._conn         = init_db(db_path)
        self._log          = CpeLogger(self._conn)
        self._client_config = None
        self._scheduler    = None
        self._window       = None   # se asigna desde app.py tras crear la ventana

        self._cargar_cliente()

    def set_window(self, window) -> None:
        """Recibe referencia a la ventana PyWebView para callbacks JS."""
        self._window = window

    def _js_call(self, fn: str, data) -> None:
        """Llama una funcion JS desde Python (reemplaza eel.fn(data))."""
        if self._window:
            try:
                payload = json.dumps(data)
                self._window.evaluate_js(f'{fn}({payload})')
            except Exception as e:
                logger.warning(f"[API] js_call {fn} error: {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # SISTEMA
    # ═════════════════════════════════════════════════════════════════════════

    def inicializar_sistema(self):
        try:
            self._cargar_cliente()
            return {'success': True, 'message': 'Sistema inicializado'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_empresa_info(self):
        if self._client_config:
            return {
                'nombre': self._client_config.empresa.get(
                    'nombre_comercial', self._client_config.razon_social),
                'ruc':    self._client_config.ruc,
                'alias':  self._client_config.alias,
            }
        return {'nombre': 'Sin cliente configurado', 'ruc': '-', 'alias': ''}

    # ═════════════════════════════════════════════════════════════════════════
    # DASHBOARD
    # ═════════════════════════════════════════════════════════════════════════

    def get_dashboard_stats(self):
        try:
            cliente_id = getattr(self, '_cliente_stem', None)
            resumen    = self._log.conteo_por_estado(cliente_id)
            return {
                'remitidos':      resumen.get('REMITIDO',  0),
                'errores':        resumen.get('ERROR',     0),
                'ignorados':      resumen.get('IGNORADO',  0),
                'ultimos_7_dias': self._ultimos_7_dias(),
            }
        except Exception as e:
            logger.exception(f"[API] get_dashboard_stats: {e}")
            return {'remitidos': 0, 'errores': 0, 'ignorados': 0, 'ultimos_7_dias': [0]*7}

    def get_pendientes_fuente(self):
        """Cuenta pendientes en la fuente usando AdapterFactory."""
        try:
            if self._client_config:
                from src.adapters.adapter_factory import AdapterFactory
                adapter    = AdapterFactory.create_from_cliente_id(getattr(self, "_cliente_stem", self._client_config.alias))
                pendientes = adapter.read_pending()
                return {'count': len(pendientes)}
            return {'count': 0}
        except Exception as e:
            logger.warning(f"[API] get_pendientes_fuente: {e}")
            return {'count': 0}

    def get_recent_comprobantes(self):
        try:
            cliente_id = getattr(self, '_cliente_stem', None)
            rows = self._log.historial(cliente_id=cliente_id, estado='REMITIDO', limit=20)
            return [
                {
                    'serie':   r['serie'],
                    'numero':  r['numero'],
                    'fecha':   r['fecha_creacion'][:10],
                    'cliente': '-',
                    'total':   0.0,
                    'estado':  r['estado'].lower(),
                }
                for r in rows
            ]
        except Exception as e:
            logger.exception(f"[API] get_recent_comprobantes: {e}")
            return []

    # ═════════════════════════════════════════════════════════════════════════
    # LOGS / HISTORIAL
    # ═════════════════════════════════════════════════════════════════════════

    def get_logs(self, estado=None, limit=100):
        try:
            cliente_id = getattr(self, '_cliente_stem', None)
            rows = self._log.historial(cliente_id=cliente_id, estado=estado, limit=limit)
            return {'exito': True, 'logs': rows}
        except Exception as e:
            return {'exito': False, 'error': str(e), 'logs': []}

    def get_logs_resumen(self):
        try:
            cliente_id = getattr(self, '_cliente_stem', None)
            return {'exito': True, 'resumen': self._log.conteo_por_estado(cliente_id)}
        except Exception as e:
            return {'exito': False, 'error': str(e), 'resumen': {}}

    def get_historial(self, limit=200, tipo_doc=None, estado=None):
        """Una fila por comprobante con su ultimo estado."""
        try:
            cliente_id = getattr(self, '_cliente_stem', None)
            rows = self._log.historial(
                cliente_id=cliente_id, estado=estado, limit=9999)

            prioridad  = {'REMITIDO':5,'ERROR':4,'GENERADO':3,'LEIDO':2,'IGNORADO':1}
            unicos: dict = {}
            for r in rows:
                key = (r['serie'], r['numero'])
                if key not in unicos:
                    unicos[key] = r
                else:
                    if prioridad.get(r['estado'],0) > prioridad.get(unicos[key]['estado'],0):
                        unicos[key] = r

            result = sorted(
                unicos.values(),
                key=lambda x: x['fecha_creacion'],
                reverse=True
            )[:limit]

            return {
                'exito': True,
                'total': len(unicos),
                'comprobantes': [
                    {
                        'serie':    r['serie'],
                        'numero':   r['numero'],
                        'tipo_doc': r.get('tipo_comprobante', ''),
                        'fecha':    r['fecha_creacion'][:10],
                        'cliente':  '-',
                        'total':    0.0,
                        'estado':   r['estado'].lower(),
                        'endpoint': r.get('endpoint') or '-',
                        'detalle':  r.get('descripcion_sunat') or '',
                    }
                    for r in result
                ],
            }
        except Exception as e:
            return {'exito': False, 'error': str(e), 'total': 0, 'comprobantes': []}

    # ═════════════════════════════════════════════════════════════════════════
    # PROCESAMIENTO
    # ═════════════════════════════════════════════════════════════════════════

    def conectar_fuente(self, tipo: str, archivo: str):
        try:
            from src.adapters.adapter_factory import AdapterFactory
            if not self._client_config:
                return {'exito': False, 'error': 'Sin cliente configurado'}

            adapter    = AdapterFactory.create_from_cliente_id(getattr(self, "_cliente_stem", self._client_config.alias))
            pendientes = adapter.read_pending()

            return {
                'exito':      True,
                'tipo':       tipo,
                'archivo':    archivo,
                'pendientes': len(pendientes),
                'comprobantes': [
                    {
                        'serie':  (
                            str(c.get('TIPO_FACTU', '')).strip() +
                            str(c.get('SERIE_FACT', '')).strip()
                        ),
                        'numero': str(c.get('NUMERO_FAC', '')).strip().lstrip('0') or '0',
                        'cliente': 'CLIENTES VARIOS',
                        'total':   0.0,
                    }
                    for c in pendientes[:50]
                ],
            }
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    def procesar_motor(self, cliente_alias: str, limit=None, modo: str = 'mock'):
        try:
            motor = Motor(
                cliente_alias=cliente_alias,
                output_dir='output',
                db_path=self._db_path,
                modo_sender=modo,
            )
            resultados = motor.procesar(limit=limit)
            return {'exito': True, 'resultados': resultados}
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    def get_ruta_fuente(self, alias: str):
        try:
            cfg   = ClientLoader().cargar(alias)
            rutas = cfg.rutas_fuente
            return {'exito': True, 'ruta': rutas[0] if rutas else ''}
        except Exception as e:
            return {'exito': False, 'ruta': '', 'error': str(e)}

    def get_clientes_disponibles(self):
        try:
            loader    = ClientLoader()
            clientes  = loader.listar()
            resultado = []
            for alias in clientes:
                cfg = loader.cargar(alias)
                resultado.append({
                    'alias':       alias,
                    'id':          alias,
                    'ruc':         cfg.ruc,
                    'nombre':      cfg.empresa.get('nombre_comercial', cfg.razon_social),
                    'tipo_fuente': cfg.tipo_fuente,
                })
            return {'exito': True, 'clientes': resultado}
        except Exception as e:
            return {'exito': False, 'error': str(e), 'clientes': []}

    # ═════════════════════════════════════════════════════════════════════════
    # LICENCIA
    # ═════════════════════════════════════════════════════════════════════════

    def validar_licencia(self):
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
                except Exception:
                    info = {'license_type': 'Trial', 'client_name': 'Usuario',
                            'dias_restantes': 30, 'expires_at': '2026-05-23'}
                return {
                    'valida':         True,
                    'tipo':           info.get('license_type', 'Trial'),
                    'cliente':        info.get('client_name', 'Usuario'),
                    'dias_restantes': info.get('dias_restantes', 0),
                    'vencimiento':    info.get('expires_at', ''),
                }
            return {'valida': False, 'error': status}
        except Exception:
            return {'valida': True, 'tipo': 'Demo', 'cliente': 'Usuario Demo',
                    'dias_restantes': 999, 'vencimiento': '2099-12-31'}

    # ═════════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ═════════════════════════════════════════════════════════════════════════

    def seleccionar_archivo(self):
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

    def seleccionar_carpeta(self):
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        carpeta = filedialog.askdirectory(title='Seleccionar carpeta DBF')
        root.destroy()
        return carpeta if carpeta else None

    def verificar_conexion_api(self):
        try:
            import requests
            if self._client_config:
                eps = self._client_config.endpoints_activos
                if eps:
                    url    = eps[0].get('url_comprobantes', eps[0].get('url', ''))
                    nombre = ', '.join([e.get('nombre', '') for e in eps])
                    if url:
                        resp = requests.head(url, timeout=5)
                        return {'conectado': resp.status_code < 500, 'nombre': nombre}
            return {'conectado': False, 'nombre': 'Sin configurar'}
        except Exception:
            return {'conectado': False, 'nombre': 'Sin conexion'}

    def cerrar_sistema(self):
        import os
        logger.info("[API] Cerrando sistema...")
        threading.Timer(0.5, lambda: os._exit(0)).start()
        return True

    # ═════════════════════════════════════════════════════════════════════════
    # CONFIGURACION
    # ═════════════════════════════════════════════════════════════════════════

    def verificar_clave_instalador(self, clave: str):
        try:
            if self._client_config:
                return {'valida': clave == self._client_config.clave_instalador}
            return {'valida': False}
        except Exception:
            return {'valida': False}

    def get_config_cliente(self):
        try:
            if not self._client_config:
                return {'exito': False, 'error': 'Sin cliente'}
            return {
                'exito':     True,
                'empresa':   self._client_config.empresa,
                'fuente': {
                    'tipo':  self._client_config.tipo_fuente,
                    'rutas': self._client_config.rutas_fuente,
                },
                'series':    self._client_config.series,
                'endpoints': self._client_config.endpoints,
                'envio':     self._client_config.envio,
            }
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    def guardar_config(self, payload: dict):
        """
        TASK-006:
        - sort_keys=False para preservar orden del YAML (BUG-1)
        - Filtra series vacias antes de escribir (BUG-2)
        - Dispara actualizacion de stat-pendientes en JS (GAP)
        """
        try:
            import yaml
            loader   = ClientLoader()
            cfg_path = None
            for alias in loader.listar():
                cfg_path = loader.clientes_dir / f"{alias}.yaml"
                break
            if not cfg_path:
                return {'exito': False, 'error': 'No hay cliente configurado'}

            with open(cfg_path, encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if payload.get('nombre_comercial'):
                data['empresa']['nombre_comercial'] = payload['nombre_comercial']
            if payload.get('alias'):
                data['empresa']['alias'] = payload['alias']

            if payload.get('endpoints') is not None:
                data['envio'] = {'endpoints': [
                    {
                        'nombre':           ep.get('nombre', ''),
                        'activo':           ep.get('activo', False),
                        'formato':          ep.get('formato', 'txt'),
                        'url_comprobantes': ep.get('url_comprobantes', ''),
                        'url_anulaciones':  ep.get('url_anulaciones', ''),
                        'credenciales': {
                            'usuario': ep.get('usuario', ''),
                            'token':   ep.get('token', ''),
                        },
                        'timeout': ep.get('timeout', 30),
                    }
                    for ep in payload['endpoints']
                ]}

            # BUG-2: filtrar series vacías antes de escribir al YAML
            if payload.get('series') is not None:
                series_limpias = {}
                for tipo, lista in payload['series'].items():
                    items_validos = [
                        {
                            'serie':              s.get('serie', ''),
                            'correlativo_inicio': int(s.get('correlativo_inicio', 0)),
                            'activa':             bool(s.get('activa', True)),
                        }
                        for s in lista
                        if s.get('serie', '').strip()   # solo series con código
                    ]
                    if items_validos:
                        series_limpias[tipo] = items_validos
                data['series'] = series_limpias

            if payload.get('clave_nueva'):
                data.setdefault('instalador', {})['clave'] = payload['clave_nueva']

            # BUG-1: sort_keys=False para preservar orden del YAML
            with open(cfg_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True,
                          default_flow_style=False, sort_keys=False)

            self._cargar_cliente()

            # GAP: refrescar stat-pendientes en dashboard tras guardar series
            try:
                pendientes = self.get_pendientes_fuente()
                self._js_call('actualizarStatPendientes', pendientes.get('count', 0))
            except Exception:
                pass

            return {'exito': True}
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    # ═════════════════════════════════════════════════════════════════════════
    # SCHEDULER
    # ═════════════════════════════════════════════════════════════════════════

    def get_scheduler_status(self):
        if self._scheduler:
            return {'exito': True, 'status': self._scheduler.get_status()}
        return {
            'exito': True,
            'status': {
                'modo': 'manual', 'activo': False, 'procesando': False,
                'intervalo_minutos': 10, 'ciclos_ejecutados': 0,
                'ultimo_ciclo': None, 'proximo_ciclo': None, 'ultimo_resultado': {},
            },
        }

    def scheduler_iniciar(self):
        try:
            if self._scheduler:
                ok = self._scheduler.iniciar()
                return {'exito': ok, 'mensaje': 'Iniciado' if ok else 'Modo manual'}
            return {'exito': False, 'error': 'Scheduler no inicializado'}
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    def scheduler_detener(self):
        try:
            if self._scheduler:
                self._scheduler.detener()
                return {'exito': True}
            return {'exito': False, 'error': 'Scheduler no inicializado'}
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    def scheduler_ejecutar_ahora(self):
        try:
            if self._scheduler:
                result = self._scheduler.ejecutar_ahora()
                return {'exito': True, 'resultado': result}
            if self._client_config:
                motor = Motor(
                    cliente_alias=getattr(self, "_cliente_stem", self._client_config.alias),
                    output_dir='output',
                    db_path=self._db_path,
                )
                resultados = motor.procesar()
                return {'exito': True, 'resultado': resultados}
            return {'exito': False, 'error': 'Sin cliente configurado'}
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    def guardar_config_scheduler(self, payload: dict):
        try:
            import yaml
            loader   = ClientLoader()
            clientes = loader.listar()
            if not clientes:
                return {'exito': False, 'error': 'Sin cliente configurado'}

            cfg_path = loader.clientes_dir / f"{clientes[0]}.yaml"
            with open(cfg_path, encoding='utf-8') as f:
                data = yaml.safe_load(f)

            data['scheduler'] = {
                'modo':              payload.get('modo', 'manual'),
                'intervalo_boletas': int(payload.get('intervalo_boletas', 10)),
                'activo':            True,
            }

            with open(cfg_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True,
                          default_flow_style=False, sort_keys=False)

            self._cargar_cliente()
            if self._scheduler:
                self._scheduler.recargar_config()
                if payload.get('modo') == 'automatico' and not self._scheduler.esta_activo:
                    self._scheduler.iniciar()
                elif payload.get('modo') == 'manual' and self._scheduler.esta_activo:
                    self._scheduler.detener()

            return {'exito': True}
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    # ═════════════════════════════════════════════════════════════════════════
    # WIZARD (legacy — TASK-004)
    # ═════════════════════════════════════════════════════════════════════════

    def wz_validar_licencia(self, codigo: str):
        try:
            from src.licenses.validator import LicenseValidator
            v          = LicenseValidator()
            ok, status = v.validate_code(codigo)
            if ok:
                info = v.get_license_info()
                return {'valida': True, 'tipo': info.get('license_type', 'Full')}
            return {'valida': False, 'error': status}
        except Exception as e:
            return {'valida': False, 'error': str(e)}

    def wz_explorar_fuente(self, params: dict):
        resultado_q: list = []

        def _explorar():
            try:
                from src.tools.source_explorer import SourceExplorer
                from src.tools.smart_mapper import SmartMapper

                explorer = SourceExplorer()
                tipo     = params.get('tipo', 'dbf')

                if tipo in ('dbf', 'xlsx', 'csv'):
                    reporte = explorer.explorar_rapido(
                        tipo=tipo, ruta=params.get('ruta', ''))
                else:
                    reporte = explorer.explorar(
                        tipo=tipo,
                        servidor=params.get('servidor', ''),
                        base_datos=params.get('base_datos', ''),
                        usuario=params.get('usuario', ''),
                        clave=params.get('clave', ''),
                        puerto=params.get('puerto', 1433),
                    )

                mapper         = SmartMapper()
                mapeo          = mapper.mapear(reporte)
                contrato_motor = mapper.generar_contrato_motor(mapeo, {
                    'tipo':     tipo,
                    'ruta':     params.get('ruta', ''),
                    'servidor': params.get('servidor', ''),
                })

                tablas      = reporte.get('tablas', {})
                tablas_info = [
                    {
                        'nombre':    t,
                        'campos':    len(tablas[t].get('campos', [])),
                        'registros': tablas[t].get('total_registros', 0),
                    }
                    for t in tablas
                ]

                resultado_q.append({
                    'exito':              True,
                    'tablas':             len(tablas),
                    'tablas_encontradas': tablas_info,
                    'metodo_mapeo':       mapeo.get('metodo', 'heuristica'),
                    'confianza':          mapeo.get('confianza', 0),
                    'mapeo_comprobantes': mapeo.get('comprobantes', {}),
                    'mapeo_items':        mapeo.get('items', {}),
                    'mapeo_anulaciones':  mapeo.get('anulaciones', {}),
                    'transformaciones':   mapeo.get('transformaciones', {}),
                    'tabla_comp':         mapeo.get('tablas', {}).get('comprobantes', ''),
                    'tabla_items':        mapeo.get('tablas', {}).get('items', ''),
                    'tabla_anulaciones':  mapeo.get('tablas', {}).get('anulaciones', ''),
                    'advertencias':       mapeo.get('advertencias', []),
                    'contrato':           contrato_motor,
                })
            except Exception as e:
                resultado_q.append({'exito': False, 'error': str(e)})

        t = threading.Thread(target=_explorar, daemon=True)
        t.start()
        t.join(timeout=120)

        if not resultado_q:
            return {'exito': False, 'error': 'Timeout al analizar la fuente (>120s).'}
        return resultado_q[0]

    def wz_guardar_config(self, payload: dict):
        try:
            import yaml

            empresa  = payload.get('empresa', {})
            fuente   = payload.get('fuente', {})
            series   = payload.get('series', {})
            endpoint = payload.get('endpoint', {})
            licencia = payload.get('licencia', {})
            contrato = payload.get('contrato')

            alias = empresa.get('alias', '').lower().replace(' ', '_')
            if not alias:
                return {'exito': False, 'error': 'Alias de empresa vacio'}

            data = {
                'empresa': {
                    'ruc':              empresa.get('ruc', ''),
                    'razon_social':     empresa.get('razon_social', ''),
                    'nombre_comercial': empresa.get(
                        'nombre_comercial', empresa.get('razon_social', '')),
                    'alias': empresa.get('alias', alias),
                },
                'fuente': {
                    'tipo':  fuente.get('tipo', 'dbf'),
                    'rutas': [fuente.get('ruta', '')] if fuente.get('ruta') else [],
                },
                'series': {
                    'boleta':       self._normalizar_series(series.get('boleta', [])),
                    'factura':      self._normalizar_series(series.get('factura', [])),
                    'nota_credito': self._normalizar_series(series.get('nota_credito', [])),
                    'nota_debito':  self._normalizar_series(series.get('nota_debito', [])),
                },
                'envio': {
                    'endpoints': [
                        {
                            'nombre':           endpoint.get('nombre', 'APIFAS'),
                            'activo':           True,
                            'formato':          'txt',
                            'url_comprobantes': endpoint.get(
                                'url_comprobantes', endpoint.get('url', '')),
                            'url_anulaciones':  endpoint.get('url_anulaciones', ''),
                            'credenciales': {
                                'usuario': endpoint.get('usuario', ''),
                                'token':   endpoint.get('token', ''),
                            },
                            'timeout': 30,
                        }
                    ]
                },
                'licencia': {
                    'tipo':   licencia.get('tipo', 'Trial'),
                    'codigo': licencia.get('codigo', ''),
                    'endpoint_validacion': 'https://licenses.disateq.com/v1/validate',
                },
                'instalador': {'clave': '1234'},
                'scheduler':  {'modo': 'manual', 'intervalo_boletas': 10, 'activo': True},
            }

            if fuente.get('servidor'):
                data['fuente']['servidor']   = fuente.get('servidor', '')
                data['fuente']['base_datos'] = fuente.get('base_datos', '')
                data['fuente']['usuario']    = fuente.get('usuario', '')
                data['fuente']['puerto']     = fuente.get('puerto', 1433)

            if contrato:
                contrato_path = Path('config/contratos') / f'{alias}.yaml'
                contrato_path.parent.mkdir(parents=True, exist_ok=True)
                with open(contrato_path, 'w', encoding='utf-8') as f:
                    yaml.dump(contrato, f, allow_unicode=True,
                              default_flow_style=False, sort_keys=False)
                data['fuente']['contrato_path'] = str(contrato_path)

            cliente_path = Path('config/clientes') / f'{alias}.yaml'
            cliente_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cliente_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True,
                          default_flow_style=False, sort_keys=False)

            self._cargar_cliente()
            return {'exito': True, 'path': str(cliente_path)}
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    def wz_ejecutar_prueba(self, cliente_alias: str):
        try:
            motor = Motor(
                cliente_alias=cliente_alias,
                output_dir='output',
                db_path=self._db_path,
                modo_sender='mock',
            )
            resultados = motor.procesar(limit=3)
            return {'exito': True, 'resultados': resultados}
        except Exception as e:
            return {'exito': False, 'error': str(e)}

    def wz_detectar_modo(self):
        try:
            loader   = ClientLoader()
            clientes = loader.listar()
            return {'wizard': len(clientes) == 0}
        except Exception:
            return {'wizard': True}

    # ═════════════════════════════════════════════════════════════════════════
    # WIZARD TASK-005 — 6 pasos
    # ═════════════════════════════════════════════════════════════════════════

    def explorar_ruta(self, es_carpeta: bool = True):
        """Dialogo nativo PyWebView para seleccionar carpeta o archivo."""
        import webview
        try:
            if es_carpeta:
                resultado = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            else:
                resultado = self._window.create_file_dialog(
                    webview.OPEN_DIALOG,
                    file_types=(
                        "Archivos de datos (*.dbf;*.xlsx;*.xls;*.csv;*.mdb;*.accdb)",
                        "Todos los archivos (*.*)",
                    ),
                )
            if resultado and len(resultado) > 0:
                return resultado[0]
        except Exception as exc:
            logger.warning(f"[WIZARD] explorar_ruta error: {exc}")
        return None

    def wizard_test_fuente(self, fuente: dict) -> dict:
        """Paso 3 — lee primeros registros de la fuente para verificar acceso."""
        try:
            return test_fuente(fuente)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def wizard_generar_contrato_auto(self, fuente: dict) -> dict:
        """Paso 4 — genera contrato via smart_mapper (stub hasta TASK-009)."""
        try:
            from src.tools.smart_mapper import SmartMapper
            mapper = SmartMapper()
            result = mapper.generar(fuente)
            if result.get("score", 0) >= 0.80:
                return {"ok": True, "contrato": result["contrato"], "score": result["score"]}
            return {
                "ok":    False,
                "error": f"Score insuficiente ({result.get('score', 0):.0%}). Completa manualmente.",
            }
        except ImportError:
            return {"ok": False, "error": "smart_mapper no disponible aun (TASK-009). Completa manualmente."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def wizard_analizar_fuente(self, fuente: dict) -> dict:
        """Paso 3->4: corre heuristica de mapeo sobre la fuente."""
        try:
            from src.tools.wizard_service import analizar_fuente
            return analizar_fuente(fuente)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "score_global": 0,
                    "contrato": {}, "scores": {}, "sin_resolver": []}

    def wizard_probar_mapeo(self, fuente: dict, contrato: dict) -> dict:
        """
        Paso 4 — lee 5 registros reales usando el contrato actual
        y retorna los valores extraídos para que el técnico valide.
        """
        try:
            from src.tools.wizard_service import probar_mapeo
            return probar_mapeo(fuente, contrato)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "filas": []}

    def wizard_guardar(self, payload: dict) -> dict:
        """Paso 6 final — guarda config/clientes y config/contratos YAML."""
        try:
            return guardar_wizard(payload)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ═════════════════════════════════════════════════════════════════════════
    # INTERNOS
    # ═════════════════════════════════════════════════════════════════════════

    def cargar_motor(self) -> dict:
        """Navega la ventana PyWebView al dashboard (index.html)."""
        try:
            if self._window:
                self._window.load_url(
                    self._window.get_current_url().replace("wizard.html", "index.html")
                )
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _cargar_cliente(self) -> None:
        try:
            loader   = ClientLoader()
            clientes = loader.listar()
            if clientes:
                self._client_config = loader.cargar(clientes[0])
            self._cliente_stem = clientes[0]
        except Exception as e:
            logger.warning(f"[API] No se pudo cargar cliente: {e}")

    def iniciar_scheduler(self) -> None:
        """Llamado desde app.py tras arrancar la ventana."""
        try:
            if not self._client_config:
                return
            from src.scheduler import CpeScheduler

            def _on_ciclo(resultados):
                self._js_call('schedulerCicloCompletado', resultados)

            loader        = ClientLoader()
            alias_archivo = loader.listar()[0] if loader.listar() else self._client_config.alias
            self._scheduler = CpeScheduler(
                cliente_alias=alias_archivo,
                on_ciclo=_on_ciclo,
            )
            self._scheduler.iniciar()
        except Exception as e:
            logger.warning(f"[API] No se pudo iniciar scheduler: {e}")

    def _ultimos_7_dias(self) -> list:
        try:
            cliente_id = getattr(self, '_cliente_stem', None)
            resultado  = []
            for i in range(6, -1, -1):
                fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                rows  = self._log.historial(
                    cliente_id=cliente_id, estado='REMITIDO', limit=9999)
                dia   = sum(1 for r in rows if r['fecha_creacion'][:10] == fecha)
                resultado.append(dia)
            return resultado
        except Exception:
            return [0] * 7

    @staticmethod
    def _normalizar_series(lista: list) -> list:
        return [
            {
                'serie':              s.get('serie', ''),
                'correlativo_inicio': int(s.get('correlativo_inicio', 0)),
                'activa':             bool(s.get('activa', True)),
            }
            for s in lista if s.get('serie')
        ]
