# Patch 1: client_loader.py - get_endpoints_para con nueva estructura
content = open('src/config/client_loader.py', encoding='utf-8').read()

old = '''    def get_endpoints_para(self, tipo_comprobante: str) -> list:
        """
        Retorna endpoints activos para un tipo de comprobante.

        Soporta dos estructuras:
        1. Nueva: urls.{tipo} -> endpoint tiene URL para ese tipo
        2. Legacy: tipo_comprobante lista -> endpoint cubre ese tipo

        tipo_comprobante: 'boleta', 'factura', 'nota_credito', 'nota_debito', 'anulacion', 'guia'
        """
        result = []
        for ep in self.endpoints_activos:
            # Nueva estructura: urls por tipo
            urls = ep.get('urls', {})
            if urls:
                # Tiene URL especifica para este tipo
                if tipo_comprobante in urls:
                    result.append(ep)
                    continue
                # Nota credito/debito usan URL de factura como fallback
                if tipo_comprobante in ('nota_credito', 'nota_debito'):
                    if 'factura' in urls or 'boleta' in urls:
                        result.append(ep)
                        continue
            else:
                # Legacy: lista tipo_comprobante
                tipos = ep.get('tipo_comprobante', ['todos'])
                if 'todos' in tipos or tipo_comprobante in tipos:
                    result.append(ep)
        return result'''

new = '''    # Mapa tipo_comprobante -> campo URL en endpoint
    URL_CAMPO_MAP = {
        'boleta':       'url_comprobantes',
        'factura':      'url_comprobantes',
        'nota_credito': 'url_comprobantes',
        'nota_debito':  'url_comprobantes',
        'anulacion':    'url_anulaciones',
        'guia':         'url_guias',
        'retencion':    'url_retenciones',
        'percepcion':   'url_percepciones',
    }

    def get_endpoints_para(self, tipo_comprobante: str) -> list:
        """
        Retorna endpoints activos que tienen URL configurada para el tipo de comprobante.

        tipo_comprobante: boleta | factura | nota_credito | nota_debito |
                          anulacion | guia | retencion | percepcion
        """
        result = []
        campo_url = self.URL_CAMPO_MAP.get(tipo_comprobante, 'url_comprobantes')

        for ep in self.endpoints_activos:
            # Nueva estructura: url_comprobantes / url_anulaciones / url_guias
            if ep.get(campo_url, '').strip():
                result.append(ep)
                continue

            # Fallback legacy: urls{}
            urls = ep.get('urls', {})
            if urls:
                if tipo_comprobante in urls and urls[tipo_comprobante]:
                    result.append(ep)
                    continue
                if tipo_comprobante in ('nota_credito', 'nota_debito'):
                    if urls.get('factura') or urls.get('boleta'):
                        result.append(ep)
                        continue

            # Fallback legacy: url unica para todo
            elif ep.get('url', '').strip():
                result.append(ep)

        return result'''

if old in content:
    content = content.replace(old, new)
    open('src/config/client_loader.py', 'w', encoding='utf-8').write(content)
    print('OK 1/2 — client_loader.py actualizado')
else:
    print('NO ENCONTRADO 1/2 — client_loader')

# Patch 2: app.py - guardar_config con nueva estructura
content2 = open('src/ui/backend/app.py', encoding='utf-8').read()

old2 = '''        # Endpoints
        if payload.get("endpoints") is not None:
            data["envio"] = {"endpoints": [
                {
                    "nombre":  ep.get("nombre",""),
                    "activo":  ep.get("activo", False),
                    "formato": ep.get("formato","txt"),
                    "urls":    ep.get("urls", {}),
                    "credenciales": {
                        "usuario": ep.get("usuario",""),
                        "token":   ep.get("token","")
                    },
                    "timeout": ep.get("timeout", 30)
                }
                for ep in payload["endpoints"]
            ]}'''

new2 = '''        # Endpoints
        if payload.get("endpoints") is not None:
            data["envio"] = {"endpoints": [
                {
                    "nombre":            ep.get("nombre",""),
                    "activo":            ep.get("activo", False),
                    "formato":           ep.get("formato","txt"),
                    "url_comprobantes":  ep.get("url_comprobantes",""),
                    "url_anulaciones":   ep.get("url_anulaciones",""),
                    "url_guias":         ep.get("url_guias",""),
                    "url_retenciones":   ep.get("url_retenciones",""),
                    "url_percepciones":  ep.get("url_percepciones",""),
                    "credenciales": {
                        "usuario": ep.get("usuario",""),
                        "token":   ep.get("token","")
                    },
                    "timeout": ep.get("timeout", 30)
                }
                for ep in payload["endpoints"]
            ]}'''

if old2 in content2:
    content2 = content2.replace(old2, new2)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content2)
    print('OK 2/2 — app.py guardar_config actualizado')
else:
    print('NO ENCONTRADO 2/2 — app.py')
