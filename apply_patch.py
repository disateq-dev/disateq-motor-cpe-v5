patch = open('D:/DATA/Downloads/wizard_backend_patch.py', encoding='utf-8').read()
content = open('src/ui/backend/app.py', encoding='utf-8').read()

# Insertar antes del bloque MAIN
marker = '# ================================================================\n# MAIN\n# ================================================================'
if marker in content:
    content = content.replace(marker, patch + '\n\n' + marker)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK — patch agregado')
else:
    print('NO ENCONTRADO — buscando alternativa...')
    idx = content.find('def main():')
    print(repr(content[idx-80:idx]))
