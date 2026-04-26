new_section = open('D:/DATA/Downloads/historial_section.js', encoding='utf-8').read()
content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

# Encontrar inicio y fin de la seccion HISTORIAL
start = content.find('// HISTORIAL\n// ================================================================')
end   = content.find('\nfunction getBadgeClass')

if start == -1 or end == -1:
    print('NO ENCONTRADO — start:', start, 'end:', end)
else:
    content = content[:start] + new_section + content[end:]
    open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)
    print('OK — seccion historial reemplazada')
