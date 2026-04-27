content = open('src/ui/backend/app.py', encoding='utf-8').read()

old = """                  {
                      'serie':   str(c.get('TIPO_FACTU', '')).strip() + str(c.get('SERIE_FACT', '')).strip(),
                      'numero':  int(str(c.get('NUMERO_FAC', c.get('NUMERO', 0))).strip() or 0),
                      'cliente': c.get('NOMBRE_CLIENTE', c.get('RAZON_SOCI', 'CLIENTES VARIOS')),
                      'total':   float(str(c.get('TOTAL_FACT', c.get('TOTAL', 0))).strip() or 0)
                  }"""

new = """                  {
                      'serie':   str(c.get('TIPO_FACTU', '')).strip() + str(c.get('SERIE_FACT', '')).strip(),
                      'numero':  int(str(c.get('NUMERO_FAC', c.get('NUMERO', 0))).strip() or 0),
                      'cliente': (
                          c.get('NOMBRE_CLIENTE') or c.get('RAZON_SOCI') or
                          c.get('NOMBRE') or c.get('CLIENTE') or 'CLIENTES VARIOS'
                      ),
                      'total': float(str(
                          c.get('TOTAL_FACT') or c.get('TOTAL') or c.get('IMPORTE') or
                          c.get('MONTO_TOTAL') or c.get('TOT_VENTA') or c.get('IMPTOTAL') or
                          c.get('IMP_TOTAL') or c.get('TOTAL_PAGO') or 0
                      ).strip() or 0)
                  }"""

if old in content:
    content = content.replace(old, new)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK — total real con múltiples campos candidatos')
else:
    print('NO ENCONTRADO')
    idx = content.find("'total'")
    print(repr(content[idx:idx+120]))
