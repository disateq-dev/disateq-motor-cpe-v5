"""
install_scheduler.py
Instala el scheduler en el proyecto DisateQ CPE v4.0
"""
from pathlib import Path
import shutil

# 1. Copiar scheduler.py
src = Path('D:/DATA/Downloads/scheduler.py')
dst = Path('src/scheduler.py')
shutil.copy(src, dst)
print(f'OK 1/4 — scheduler.py copiado a {dst}')

# 2. Copiar farmacia_central.yaml
src = Path('D:/DATA/Downloads/farmacia_central.yaml')
dst = Path('config/clientes/farmacia_central.yaml')
shutil.copy(src, dst)
print(f'OK 2/4 — farmacia_central.yaml actualizado')

# 3. Agregar patch al app.py
patch = open('D:/DATA/Downloads/scheduler_app_patch.py', encoding='utf-8').read()
content = open('src/ui/backend/app.py', encoding='utf-8').read()

marker = '# ================================================================\n# WIZARD DE INSTALACION'
if marker in content:
    content = content.replace(marker, patch + '\n\n' + marker)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK 3/4 — endpoints scheduler agregados a app.py')
else:
    print('ERROR 3/4 — marker no encontrado en app.py')

# 4. Integrar _iniciar_scheduler en main()
content = open('src/ui/backend/app.py', encoding='utf-8').read()
old = '    _cargar_cliente()\n\n    if _client_config:'
new = '    _cargar_cliente()\n    _iniciar_scheduler()\n\n    if _client_config:'

if old in content:
    content = content.replace(old, new)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK 4/4 — _iniciar_scheduler() agregado a main()')
else:
    print('ERROR 4/4 — no se pudo integrar en main() — verificar manualmente')

print('\n✅ Instalación completa')
print('   Prueba: python -m src.ui.backend.app')
