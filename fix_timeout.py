content = open('src/ui/backend/app.py', encoding='utf-8').read()
content = content.replace(
    't.join(timeout=30)  # Max 30 segundos',
    't.join(timeout=120)  # Max 120 segundos'
)
content = content.replace(
    "return {'exito': False, 'error': 'Timeout al analizar la fuente (>30s)'}",
    "return {'exito': False, 'error': 'Timeout al analizar la fuente (>120s). La fuente tiene muchos archivos.'}"
)
open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
print('OK — timeout aumentado a 120s')
