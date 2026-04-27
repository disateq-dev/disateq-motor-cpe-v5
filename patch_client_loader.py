content = open('src/config/client_loader.py', encoding='utf-8').read()

old = '''    def get_endpoints_para(self, tipo_comprobante: str) -> list:
        """
        Retorna endpoints activos para un tipo de comprobante.
        tipo_comprobante: 'boleta', 'factura', 'nota_credito', 'nota_debito'
        """
        result = []
        for ep in self.endpoints_activos:
            tipos = ep.get('tipo_comprobante', ['todos'])
            if 'todos' in tipos or tipo_comprobante in tipos:
                result.append(ep)
        return result'''

new = '''    def get_endpoints_para(self, tipo_comprobante: str) -> list:
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

if old in content:
    content = content.replace(old, new)
    open('src/config/client_loader.py', 'w', encoding='utf-8').write(content)
    print('OK — get_endpoints_para actualizado')
else:
    print('NO ENCONTRADO')
    idx = content.find('def get_endpoints_para')
    print(repr(content[idx:idx+300]))
