content = open('src/ui/backend/app.py', encoding='utf-8').read()

old = """def get_historial(limit=200, tipo_doc=None, estado=None):
    \"\"\"Una fila por comprobante con su ultimo estado.\"\"\"
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
                    'fecha':"""

# Encontrar fin del bloque
start = content.find('@eel.expose\ndef get_historial')
end   = content.find('\n@eel.expose\n', start + 10)

if start == -1:
    print('NO ENCONTRADO')
else:
    new_block = '''@eel.expose
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

'''
    content = content[:start] + new_block + content[end+1:]
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK — get_historial reemplazado')
