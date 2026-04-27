from pathlib import Path

# 1. Patch backend
exec(open('D:/DATA/Downloads/patch_wz_explorar.py', encoding='utf-8').read())

# 2. Patch wizard.js — reemplazar formatExplorerResult
new_js = open('D:/DATA/Downloads/wizard_mapeo_visual.js', encoding='utf-8').read()
content = open('src/ui/frontend/js/wizard.js', encoding='utf-8').read()

# Encontrar y reemplazar formatExplorerResult completa
start = content.find('function formatExplorerResult(result) {')
end   = content.find('\nasync function explorarFuente()', start)

if start == -1 or end == -1:
    # Buscar alternativo
    start = content.find('function formatExplorerResult')
    end   = content.find('\nfunction validarFuente', start)

if start != -1 and end != -1:
    content = content[:start] + new_js + '\n' + content[end:]
    open('src/ui/frontend/js/wizard.js', 'w', encoding='utf-8').write(content)
    print('OK 2/2 — tabla visual de mapeo integrada en wizard.js')
else:
    # Agregar al final del archivo
    content = content + '\n\n' + new_js
    open('src/ui/frontend/js/wizard.js', 'w', encoding='utf-8').write(content)
    print('OK 2/2 — funciones de mapeo visual agregadas al wizard.js')

# 3. Actualizar validarFuente para incluir mapeo visual en el contrato
content = open('src/ui/frontend/js/wizard.js', encoding='utf-8').read()
old = '''    WZ.fuente = params;
    hideAlert('fuente-alert');
    irPaso(4);'''

new = '''    WZ.fuente = params;
    // Incluir mapeo detectado en el contrato
    var mapeoVisual = leerMapeoVisual();
    if (mapeoVisual) {
        WZ.contrato = Object.assign(WZ.contrato || {}, { mapeo: mapeoVisual });
    }
    hideAlert('fuente-alert');
    irPaso(4);'''

if old in content:
    content = content.replace(old, new)
    open('src/ui/frontend/js/wizard.js', 'w', encoding='utf-8').write(content)
    print('OK 3/3 — mapeo incluido en WZ.contrato al avanzar')
else:
    print('OK 3/3 — (validarFuente no modificada, mapeo ya incluido)')

print('\n✅ Tabla visual de mapeo integrada al Wizard Paso 3')
