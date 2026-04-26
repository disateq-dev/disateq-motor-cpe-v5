content = open('src/logger/cpe_logger.py', encoding='utf-8').read()

old = '''def consultar(self,
                  ruc: str = None,
                  estado: str = None,
                  serie: str = None,
                  fecha_desde: str = None,
                  fecha_hasta: str = None,
                  limit: int = 100) -> List[Dict]:
        """Consulta el log con filtros opcionales."""
        sql = "SELECT * FROM log_envios WHERE 1=1"
        params = []
        if ruc:
            sql += " AND ruc_emisor = ?"; params.append(ruc)
        if estado:
            sql += " AND estado = ?"; params.append(estado)'''

new = '''def consultar(self,
                  ruc: str = None,
                  estado: str = None,
                  tipo_doc: str = None,
                  serie: str = None,
                  fecha_desde: str = None,
                  fecha_hasta: str = None,
                  limit: int = 100) -> List[Dict]:
        """Consulta el log con filtros opcionales."""
        sql = "SELECT * FROM log_envios WHERE 1=1"
        params = []
        if ruc:
            sql += " AND ruc_emisor = ?"; params.append(ruc)
        if estado:
            sql += " AND estado = ?"; params.append(estado)
        if tipo_doc:
            sql += " AND tipo_doc = ?"; params.append(tipo_doc)'''

if old in content:
    content = content.replace(old, new)
    open('src/logger/cpe_logger.py', 'w', encoding='utf-8').write(content)
    print('OK logger')
else:
    print('NO ENCONTRADO')
