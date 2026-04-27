content = open('src/ui/backend/app.py', encoding='utf-8').read()

old = (
    "                      'total':   float(str(c.get('TOTAL_FACT', c.get('TOTAL', 0))).strip() or 0)\n"
    "                  }"
)

new = (
    "                      'total':   float(str(c.get('TOTAL_FACT') or c.get('TOTAL') or c.get('IMPORTE') or c.get('TOT_VENTA') or c.get('IMP_TOTAL') or c.get('IMPTOTAL') or 0).strip() or 0)\n"
    "                  }"
)

if old in content:
    content = content.replace(old, new)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK — total fix aplicado')
else:
    print('NO ENCONTRADO')
