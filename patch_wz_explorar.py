content = open('src/ui/backend/app.py', encoding='utf-8').read()

# Buscar el bloque completo de _explorar() dentro de wz_explorar_fuente
start = content.find('    def _explorar():\n        try:\n            from src.tools.source_explorer import SourceExplorer')
end   = content.find('\n    t = threading.Thread(target=_explorar', start)

if start == -1 or end == -1:
    print('NO ENCONTRADO — start:', start, 'end:', end)
else:
    nuevo_explorar = '''    def _explorar():
        try:
            from src.tools.source_explorer import SourceExplorer
            from src.tools.smart_mapper import SmartMapper

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

            # SmartMapper: detectar tablas y generar mapeo
            mapper  = SmartMapper()
            mapeo   = mapper.mapear(reporte)
            contrato_motor = mapper.generar_contrato_motor(mapeo, {
                'tipo': tipo,
                'ruta': params.get('ruta', ''),
                'servidor': params.get('servidor', '')
            })

            tablas = reporte.get('tablas', {})
            tablas_info = [
                {
                    'nombre':    t,
                    'campos':    len(tablas[t].get('campos', [])),
                    'registros': tablas[t].get('total_registros', 0)
                }
                for t in tablas
            ]

            resultado_q.put({
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
            resultado_q.put({'exito': False, 'error': str(e)})'''

    content = content[:start] + nuevo_explorar + content[end:]
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK — wz_explorar_fuente actualizado con SmartMapper')
