content = open('src/ui/backend/app.py', encoding='utf-8').read()

old = '''def get_historial(limit=200):
    """Una fila por comprobante con su ultimo estado."""
    try:
        ruc  = _client_config.ruc if _client_config else None
        rows = _logger.consultar(ruc=ruc, limit=9999)'''

new = '''def get_historial(limit=200, tipo_doc=None, estado=None):
    """Una fila por comprobante con su ultimo estado."""
    try:
        ruc  = _client_config.ruc if _client_config else None
        rows = _logger.consultar(ruc=ruc, tipo_doc=tipo_doc, estado=estado, limit=9999)'''

if old in content:
    content = content.replace(old, new)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK backend')
else:
    print('NO ENCONTRADO')
