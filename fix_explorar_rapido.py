content = open('src/ui/backend/app.py', encoding='utf-8').read()

old = "                reporte = explorer.explorar(tipo=tipo, ruta=params.get('ruta', ''))"
new = "                reporte = explorer.explorar_rapido(tipo=tipo, ruta=params.get('ruta', ''))"

if old in content:
    content = content.replace(old, new)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK — usando explorar_rapido en backend')
else:
    print('NO ENCONTRADO')
    idx = content.find('explorer.explorar')
    print(repr(content[idx:idx+100]))
