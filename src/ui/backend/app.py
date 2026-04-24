"""
app.py
======
Backend Eel — DisateQ™ Motor CPE v4.0

Entry point de la interfaz gráfica.
Ejecuta: python -m src.ui.backend.app
"""

import eel
import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.licenses.validator import LicenseValidator
from src.adapters.xlsx_adapter import XlsxAdapter
from src.adapters.dbf_farmacia_adapter import DbfFarmaciaAdapter
from src.generators.json_generator import JsonGenerator
from src.generators.txt_generator import TxtGenerator
from src.sender.universal_sender import UniversalSender, CDRProcessor


# Inicializar Eel
import sys
if getattr(sys, 'frozen', False):
    # Ejecutable PyInstaller
    base_path = sys._MEIPASS
    frontend_path = os.path.join(base_path, 'frontend')
else:
    # Desarrollo
    frontend_path = str(Path(__file__).parent.parent / 'frontend')

eel.init(frontend_path)


# ================================================================
# FUNCIONES EXPUESTAS A JAVASCRIPT
# ================================================================

@eel.expose
def inicializar_sistema():
    """Inicializa el sistema y valida todo"""
    try:
        return {
            'success': True,
            'message': 'Sistema inicializado'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@eel.expose
def get_dashboard_stats():
    """Obtiene estadísticas del dashboard"""
    return {
        'total': 12,
        'enviados': 45,
        'fallidos': 2,
        'pendientes': 3,
        'ultimos_7_dias': [12, 18, 25, 32, 28, 35, 42]
    }


@eel.expose
def get_recent_comprobantes():
    """Obtiene comprobantes recientes"""
    # TODO: Conectar con SQLite
    return [
        {
            'id': 1,
            'serie': 'F001',
            'numero': 12345,
            'cliente': 'ACME SAC',
            'total': 118.00,
            'estado': 'enviado',
            'fecha': '2026-04-23'
        },
        {
            'id': 2,
            'serie': 'B001',
            'numero': 567,
            'cliente': 'Juan Pérez',
            'total': 59.00,
            'estado': 'pendiente',
            'fecha': '2026-04-23'
        },
        {
            'id': 3,
            'serie': 'F001',
            'numero': 12344,
            'cliente': 'TECH SA',
            'total': 590.00,
            'estado': 'error',
            'fecha': '2026-04-23'
        }
    ]


@eel.expose
def validar_licencia():
    """Valida licencia RSA-2048"""
    try:
        validator = LicenseValidator()
        result = validator.validate()
        
        # Manejar diferentes retornos del validador
        if isinstance(result, tuple):
            if len(result) == 2:
                is_valid, status = result
                info = None
            elif len(result) == 3:
                is_valid, status, info = result
            else:
                return {'valida': False, 'error': 'Formato de respuesta inválido'}
        else:
            is_valid = result
            status = 'unknown'
            info = None
        
        if is_valid:
            # Obtener info de licencia
            if info is None:
                try:
                    info = validator.get_license_info()
                except:
                    info = {
                        'license_type': 'Trial',
                        'client_name': 'Usuario',
                        'dias_restantes': 30,
                        'expires_at': '2026-05-23'
                    }
            
            return {
                'valida': True,
                'tipo': info.get('license_type', 'Trial'),
                'cliente': info.get('client_name', 'Usuario'),
                'dias_restantes': info.get('dias_restantes', 0),
                'vencimiento': info.get('expires_at', '')
            }
        else:
            return {
                'valida': False,
                'error': status
            }
    except Exception as e:
        print(f"Error validando licencia: {e}")
        # Modo fallback - permitir ejecución
        return {
            'valida': True,
            'tipo': 'Demo',
            'cliente': 'Usuario Demo',
            'dias_restantes': 999,
            'vencimiento': '2099-12-31'
        }


@eel.expose
def conectar_fuente(tipo, archivo):
    """Conecta a fuente de datos"""
    try:
        if tipo == 'xlsx':
            adapter = XlsxAdapter(archivo)
            adapter.connect()
            pendientes = adapter.read_pending()
            adapter.disconnect()
            
            return {
                'exito': True,
                'tipo': tipo,
                'archivo': archivo,
                'pendientes': len(pendientes),
                'comprobantes': [
                    {
                        'serie': c.get('TIPO_DOCUMENTO', '') + c.get('SERIE', ''),
                        'numero': c.get('NUMERO', 0),
                        'cliente': c.get('CLIENTE_NOMBRE', ''),
                        'total': float(c.get('TOTAL', 0))
                    }
                    for c in pendientes[:10]  # Primeros 10
                ]
            }
        elif tipo == 'dbf':
            adapter = DbfFarmaciaAdapter(archivo)
            adapter.connect()
            pendientes = adapter.read_pending()
            adapter.disconnect()
            return {
                'exito': True, 'tipo': tipo, 'archivo': archivo,
                'pendientes': len(pendientes),
                'comprobantes': [
                    {'serie': str(c.get('TIPO_DOC',''))+str(c.get('SERIE','')),
                     'numero': c.get('NUMERO',0),
                     'cliente': c.get('NOMBRE_CLIENTE',''),
                     'total': float(c.get('TOTAL',0))}
                    for c in pendientes[:10]
                ]
            }
        else:
            return {'exito': False, 'error': f'Tipo no soportado: {tipo}'}
    
    except Exception as e:
        return {'exito': False, 'error': str(e)}


@eel.expose
def procesar_comprobantes(archivo, endpoint, indices_seleccionados):
    """Procesa comprobantes seleccionados"""
    try:
        # Conectar a fuente (detectar tipo)
        import os as _os
        if _os.path.isdir(archivo):
            adapter = DbfFarmaciaAdapter(archivo)
        else:
            adapter = XlsxAdapter(archivo)
        adapter.connect()
        pendientes = adapter.read_pending()
        
        # Filtrar seleccionados
        if indices_seleccionados:
            comprobantes = [pendientes[i] for i in indices_seleccionados]
        else:
            comprobantes = pendientes
        
        # Sender
        if endpoint == 'mock':
            sender = UniversalSender(mode='mock')
        else:
            sender = UniversalSender(config_path='config/endpoints.yaml')
        
        resultados = []
        
        for idx, comp in enumerate(comprobantes):
            # Notificar progreso a JS
            eel.update_progress(idx + 1, len(comprobantes))
            
            # Leer y normalizar
            items = adapter.read_items(comp)
            cpe = adapter.normalize(comp, items)
            
            # Generar archivo
            if endpoint in ['apifas_pse', 'mock']:
                output_file = TxtGenerator.generate(cpe, 'output')
            else:
                output_file = JsonGenerator.generate(cpe, 'output/json')
            
            # Enviar
            exito, respuesta = sender.enviar(output_file, cpe)
            
            # Guardar CDR
            if exito:
                cdr_info = CDRProcessor.procesar(respuesta, cpe)
                cdr_file = CDRProcessor.guardar_cdr(cdr_info, 'output/cdr')
            
            resultados.append({
                'comprobante': f"{cpe['serie']}-{cpe['numero']:08d}",
                'exito': exito,
                'mensaje': respuesta.get('mensaje', '') if exito else respuesta.get('error', '')
            })
        
        adapter.disconnect()
        
        return {
            'exito': True,
            'procesados': len(resultados),
            'exitosos': sum(1 for r in resultados if r['exito']),
            'fallidos': sum(1 for r in resultados if not r['exito']),
            'resultados': resultados
        }
    
    except Exception as e:
        return {
            'exito': False,
            'error': str(e)
        }


@eel.expose
def get_config():
    """Obtiene configuración actual"""
    # TODO: Leer desde YAML
    return {
        'fuente': {
            'tipo': 'xlsx',
            'archivo': 'ventas_pos.xlsx',
            'auto_procesar': False
        },
        'endpoint': {
            'activo': 'apifas_pse',
            'ambiente': 'produccion'
        },
        'salida': {
            'formato': 'txt',
            'guardar_txt': True,
            'guardar_json': True,
            'guardar_cdr': True,
            'directorio': 'output'
        }
    }


@eel.expose
def save_config(config):
    """Guarda configuración"""
    # TODO: Escribir a YAML
    return {'exito': True}


@eel.expose
def seleccionar_archivo():
    """Abre diálogo para seleccionar archivo"""
    import tkinter as tk
    from tkinter import filedialog
    
    root = tk.Tk()
    root.withdraw()
    
    archivo = filedialog.askopenfilename(
        title='Seleccionar archivo de datos',
        filetypes=[
            ('Excel', '*.xlsx'),
            ('DBF', '*.dbf'),
            ('Todos', '*.*')
        ]
    )
    
    root.destroy()
    
    return archivo if archivo else None


# ================================================================
# MAIN
# ================================================================

def main():
    """Inicia la aplicación"""
    print("=" * 60)
    print("  DisateQ™ Motor CPE v4.0 — Interfaz Gráfica")
    print("=" * 60)
    print("\n🚀 Iniciando aplicación...\n")
    
    # Validar licencia (sin bloqueo)
    try:
        validator = LicenseValidator()
        result = validator.validate()
        
        # Manejar diferentes retornos
        if isinstance(result, tuple):
            is_valid = result[0] if len(result) > 0 else False
            status = result[1] if len(result) > 1 else 'unknown'
        else:
            is_valid = result
            status = 'unknown'
        
        if is_valid:
            try:
                info = validator.get_license_info()
                print(f"✅ Licencia válida")
                print(f"   Cliente: {info.get('client_name', 'Usuario')}")
                print(f"   Tipo: {info.get('license_type', 'Trial')}")
                print(f"   Días restantes: {info.get('dias_restantes', 0)}\n")
            except:
                print(f"✅ Licencia válida (modo demo)\n")
        else:
            print(f"⚠️  Advertencia: {status}")
            print(f"   Ejecutando en modo demo\n")
    except Exception as e:
        print(f"⚠️  Error validando licencia: {e}")
        print(f"   Ejecutando en modo demo\n")
    
    # Iniciar Eel
    print("🌐 Abriendo interfaz gráfica...\n")
    
    try:
        eel.start(
            'index.html',
            size=(1280, 800),
            port=8080,
            mode='chrome',  # o 'edge' en Windows
            close_callback=lambda *args: print("\n👋 Aplicación cerrada\n")
        )
    except EnvironmentError:
        # Si no encuentra Chrome, usar navegador por defecto
        eel.start(
            'index.html',
            size=(1280, 800),
            port=8080,
            mode=None
        )
    
    return 0


if __name__ == '__main__':
    sys.exit(main())




