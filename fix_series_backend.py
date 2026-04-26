content = open('src/ui/backend/app.py', encoding='utf-8').read()

old = """        # Clave instalador
        if payload.get("clave_nueva"):
            data.setdefault("instalador", {})["clave"] = payload["clave_nueva"]"""

new = """        # Series y correlativos
        if payload.get("series") is not None:
            data["series"] = {}
            for tipo, lista in payload["series"].items():
                data["series"][tipo] = [
                    {
                        "serie":              s.get("serie", ""),
                        "correlativo_inicio": int(s.get("correlativo_inicio", 0)),
                        "activa":             bool(s.get("activa", True))
                    }
                    for s in lista
                ]

        # Clave instalador
        if payload.get("clave_nueva"):
            data.setdefault("instalador", {})["clave"] = payload["clave_nueva"]"""

if old in content:
    content = content.replace(old, new)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content)
    print('app.py OK')
else:
    print('BLOQUE NO ENCONTRADO')
