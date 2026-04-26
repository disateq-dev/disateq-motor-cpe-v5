content = open('src/ui/backend/app.py', encoding='utf-8').read()

old = "        modo = wz_detectar_modo()\n        pagina = 'wizard.html' if modo['wizard'] else 'index.html'\n        print(f'Pagina: {pagina}')\n        eel.start(\n            pagina,"

new = "        modo = wz_detectar_modo()\n        pagina = 'wizard.html' if modo['wizard'] else 'index.html'\n        print(f'Pagina: {pagina}')\n        url = f'http://localhost:8080/{pagina}'\n        eel.start(\n            pagina,"

if old in content:
    # Tambien actualizar cmdline_args
    content = content.replace(old, new)
    content = content.replace(
        "cmdline_args=['--app=http://localhost:8080/index.html', '--disable-infobars']",
        "cmdline_args=[f'--app={url}', '--disable-infobars']"
    )
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('NO ENCONTRADO')
