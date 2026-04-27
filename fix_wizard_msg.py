content = open('src/ui/frontend/js/wizard.js', encoding='utf-8').read()
old = "status.innerHTML = '<span class=\"spinner\"></span> Analizando fuente de datos...';"
new = "status.innerHTML = '<span class=\"spinner\"></span> Analizando fuente de datos... (puede tardar hasta 2 minutos en fuentes grandes)';"
if old in content:
    content = content.replace(old, new)
    open('src/ui/frontend/js/wizard.js', 'w', encoding='utf-8').write(content)
    print('OK — mensaje actualizado')
else:
    print('NO ENCONTRADO')
