content = open('src/ui/backend/app.py', encoding='utf-8').read()

old = "        _scheduler = CpeScheduler(\n            cliente_alias=_client_config.alias.lower().replace(' ', '_'),\n            on_ciclo=_on_ciclo\n        )"
new = "        # Usar nombre del archivo YAML, no el alias interno\n        from src.config.client_loader import ClientLoader\n        loader = ClientLoader()\n        alias_archivo = loader.listar()[0] if loader.listar() else _client_config.alias\n        _scheduler = CpeScheduler(\n            cliente_alias=alias_archivo,\n            on_ciclo=_on_ciclo\n        )"

if old in content:
    content = content.replace(old, new)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('NO ENCONTRADO')
