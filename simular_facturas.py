"""
simular_facturas.py
===================
Simulacion de facturas — Motor CPE DisateQ™ v4.0

Genera 3 facturas de prueba con datos hardcoded y las procesa
con el Motor completo (normalize → TxtGenerator → Sender mock → Log).

Uso:
    python simular_facturas.py
    python simular_facturas.py --real   # Envia a APIFAS real
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

from src.generators.txt_generator import TxtGenerator
from src.logger.cpe_logger import CpeLogger
from src.config.client_loader import ClientLoader

# ================================================================
# FACTURAS DE PRUEBA
# ================================================================

FACTURAS = [
    {
        'comprobante': {
            'tipo_doc':      '01',
            'serie':         'F001',
            'numero':        1,
            'fecha_emision': datetime.now().strftime('%Y-%m-%d'),
            'fecha_str':     datetime.now().strftime('%d-%m-%Y'),
            'moneda':        'PEN',
        },
        'cliente': {
            'tipo_doc':    '6',
            'numero_doc':  '20100070970',
            'denominacion':'BOTICAS Y SALUD S.A.C.',
            'direccion':   'AV. AREQUIPA 1234, LIMA',
        },
        'totales': {
            'gravada':   500.00,
            'exonerada': 0.00,
            'inafecta':  0.00,
            'igv':       90.00,
            'icbper':    0.00,
            'total':     590.00,
        },
        'items': [
            {
                'codigo':             'MED001',
                'descripcion':        'Paracetamol 500mg x 100 tab',
                'cantidad':           50,
                'unidad':             'BX',
                'precio_unitario':    11.80,
                'valor_unitario':     10.00,
                'subtotal_sin_igv':   500.00,
                'igv':                90.00,
                'total':              590.00,
                'afectacion_igv':     '10',
                'unspsc':             '51102700',
            }
        ]
    },
    {
        'comprobante': {
            'tipo_doc':      '01',
            'serie':         'F001',
            'numero':        2,
            'fecha_emision': datetime.now().strftime('%Y-%m-%d'),
            'fecha_str':     datetime.now().strftime('%d-%m-%Y'),
            'moneda':        'PEN',
        },
        'cliente': {
            'tipo_doc':    '6',
            'numero_doc':  '20512448539',
            'denominacion':'INKAFARMA S.A.',
            'direccion':   'AV. JAVIER PRADO 4200, SAN BORJA',
        },
        'totales': {
            'gravada':   1200.00,
            'exonerada': 0.00,
            'inafecta':  0.00,
            'igv':       216.00,
            'icbper':    0.00,
            'total':     1416.00,
        },
        'items': [
            {
                'codigo':             'MED002',
                'descripcion':        'Ibuprofeno 400mg x 100 tab',
                'cantidad':           100,
                'unidad':             'BX',
                'precio_unitario':    8.26,
                'valor_unitario':     7.00,
                'subtotal_sin_igv':   700.00,
                'igv':                126.00,
                'total':              826.00,
                'afectacion_igv':     '10',
                'unspsc':             '51142100',
            },
            {
                'codigo':             'MED003',
                'descripcion':        'Amoxicilina 500mg x 100 cap',
                'cantidad':           50,
                'unidad':             'BX',
                'precio_unitario':    11.80,
                'valor_unitario':     10.00,
                'subtotal_sin_igv':   500.00,
                'igv':                90.00,
                'total':              590.00,
                'afectacion_igv':     '10',
                'unspsc':             '51103200',
            }
        ]
    },
    {
        'comprobante': {
            'tipo_doc':      '01',
            'serie':         'F001',
            'numero':        3,
            'fecha_emision': datetime.now().strftime('%Y-%m-%d'),
            'fecha_str':     datetime.now().strftime('%d-%m-%Y'),
            'moneda':        'PEN',
        },
        'cliente': {
            'tipo_doc':    '6',
            'numero_doc':  '20601234567',
            'denominacion':'CLINICA SAN PABLO S.A.C.',
            'direccion':   'AV. GUARDIA CIVIL 571, SAN BORJA',
        },
        'totales': {
            'gravada':   0.00,
            'exonerada': 850.00,
            'inafecta':  0.00,
            'igv':       0.00,
            'icbper':    0.00,
            'total':     850.00,
        },
        'items': [
            {
                'codigo':             'MED004',
                'descripcion':        'Insulina Glargina 100UI/mL x 5 viales',
                'cantidad':           10,
                'unidad':             'KIT',
                'precio_unitario':    85.00,
                'valor_unitario':     85.00,
                'subtotal_sin_igv':   850.00,
                'igv':                0.00,
                'total':              850.00,
                'afectacion_igv':     '20',  # Exonerada
                'unspsc':             '51181500',
            }
        ]
    }
]

# ================================================================
# MAIN
# ================================================================

def main():
    parser = argparse.ArgumentParser(description='Simulacion de facturas Motor CPE')
    parser.add_argument('--real', action='store_true', help='Enviar a APIFAS real (sin mock)')
    args = parser.parse_args()

    modo = 'REAL' if args.real else 'MOCK'
    print("=" * 60)
    print(f"  Simulacion de Facturas — Motor CPE DisateQ™ v4.0")
    print(f"  Modo: {modo}")
    print("=" * 60)

    # Cargar cliente
    loader = ClientLoader()
    alias  = loader.listar()[0]
    config = loader.cargar(alias)
    ruc    = config.ruc
    print(f"\n Cliente: {config.razon_social} ({ruc})\n")

    # Logger
    log = CpeLogger()

    # Sender
    if args.real:
        from src.sender.universal_sender import UniversalSender
        endpoints = config.get_endpoints_para('factura')
        if not endpoints:
            print("ERROR: No hay endpoints configurados para facturas")
            sys.exit(1)
        sender = UniversalSender(endpoints=endpoints)
    else:
        from src.sender.universal_sender import UniversalSender
        sender = UniversalSender(mode='mock')

    results = {'procesadas': 0, 'enviadas': 0, 'errores': 0}

    for factura in FACTURAS:
        cab    = factura['comprobante']
        serie  = cab['serie']
        numero = cab['numero']
        tipo   = 'factura'

        print(f"\n  Procesando F{serie}-{numero:08d}...")
        print(f"    Cliente: {factura['cliente']['denominacion']}")
        print(f"    RUC:     {factura['cliente']['numero_doc']}")
        print(f"    Total:   S/ {factura['totales']['total']:.2f}")

        try:
            # Log LEIDO
            log.leido(ruc, alias, tipo, serie, numero)

            # Generar TXT
            path = TxtGenerator.generate(factura, output_dir='output/facturas_prueba')
            log.generado(ruc, alias, tipo, serie, numero, path)
            print(f"    TXT:     {path}")

            # Enviar
            import time
            t0 = time.time()
            resultados_envio = sender.enviar(path, tipo)
            duracion = int((time.time() - t0) * 1000)

            exito    = all(r[0] for r in resultados_envio)
            respuesta = resultados_envio[0][1] if resultados_envio else {}
            endpoint_nombre = 'mock' if not args.real else ','.join(
                [ep.get('nombre','') for ep in config.get_endpoints_para('factura')]
            )

            if exito:
                log.enviado(ruc, alias, tipo, serie, numero, path,
                           endpoint_nombre, duracion,
                           factura['cliente']['denominacion'],
                           factura['totales']['total'])
                results['enviadas'] += 1
                print(f"    Estado:  REMITIDO ({duracion}ms) via {endpoint_nombre}")
            else:
                detalle = respuesta.get('error', str(respuesta))
                log.error(ruc, alias, tipo, serie, numero, detalle, endpoint_nombre)
                results['errores'] += 1
                print(f"    Estado:  ERROR — {detalle}")

            results['procesadas'] += 1

        except Exception as e:
            log.error(ruc, alias, tipo, serie, str(numero), str(e))
            results['errores'] += 1
            print(f"    ERROR: {e}")

    print(f"\n{'='*60}")
    print(f"  Resumen: {results}")
    print(f"  TXT generados en: output/facturas_prueba/")
    print(f"  Ver en UI: Historial → filtro Factura")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
