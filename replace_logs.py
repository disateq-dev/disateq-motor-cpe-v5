new_section = open('D:/DATA/Downloads/logs_section.js', encoding='utf-8').read()
content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

start = content.find('// LOGS\n// ================================================================')
end   = content.find('\n// ================================================================\n// HISTORIAL')

if start == -1 or end == -1:
    print('NO ENCONTRADO — start:', start, 'end:', end)
    # Debug
    for marker in ['// LOGS', '// HISTORIAL', '// CONFIGURACION']:
        idx = content.find(marker)
        print(f'  {marker}: {idx}')
else:
    content = content[:start] + new_section + content[end:]
    open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)
    print('OK — seccion LOGS reemplazada')
