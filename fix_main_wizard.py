content = open('src/ui/backend/app.py', encoding='utf-8').read()

old = "        eel.start(\n            'index.html',"
new = "        modo = wz_detectar_modo()\n        pagina = 'wizard.html' if modo['wizard'] else 'index.html'\n        print(f'Pagina: {pagina}')\n        eel.start(\n            pagina,"

if old in content:
    content = content.replace(old, new)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('NO ENCONTRADO — texto real:')
    idx = content.find('eel.start')
    print(repr(content[idx:idx+60]))
