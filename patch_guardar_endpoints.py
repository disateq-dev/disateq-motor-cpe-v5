content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

# Reemplazar la lectura de endpoints en guardarConfig
old = '''    var epEls = document.querySelectorAll('[id$="-nombre"][id^="ep-"]');
    var endpoints = [];
    epEls.forEach(function(el) {
        var idx = el.id.replace('ep-','').replace('-nombre','');
        var td  = ['boleta','factura','nota_credito','nota_debito','todos'];
        var tipos = td.filter(function(t) { var cb = document.getElementById('ep-'+idx+'-tipo-'+t); return cb && cb.checked; });
        var ae = document.getElementById('ep-'+idx+'-activo');
        var ue = document.getElementById('ep-'+idx+'-url');
        var us = document.getElementById('ep-'+idx+'-usuario');
        var tk = document.getElementById('ep-'+idx+'-token');
        endpoints.push({ nombre: el.value, activo: ae ? ae.checked : false, url: ue ? ue.value : '', usuario: us ? us.value : '', token: tk ? tk.value : '', tipo_comprobante: tipos });
    });'''

new = '''    var epEls = document.querySelectorAll('[id$="-nombre"][id^="ep-"]');
    var endpoints = [];
    var TIPOS_URL = ['boleta','factura','nota_credito','nota_debito','anulacion','guia'];
    epEls.forEach(function(el) {
        var idx = el.id.replace('ep-','').replace('-nombre','');
        var ae  = document.getElementById('ep-'+idx+'-activo');
        var us  = document.getElementById('ep-'+idx+'-usuario');
        var tk  = document.getElementById('ep-'+idx+'-token');
        var fmt = document.getElementById('ep-'+idx+'-formato');
        // Leer URLs por tipo
        var urls = {};
        TIPOS_URL.forEach(function(tipo) {
            var urlEl = document.getElementById('ep-'+idx+'-url-'+tipo);
            if (urlEl && urlEl.value.trim()) urls[tipo] = urlEl.value.trim();
        });
        endpoints.push({
            nombre:  el.value,
            activo:  ae ? ae.checked : false,
            formato: fmt ? fmt.value : 'txt',
            urls:    urls,
            usuario: us ? us.value : '',
            token:   tk ? tk.value : ''
        });
    });'''

if old in content:
    content = content.replace(old, new)
    open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)
    print('OK 1/2 — guardarConfig lee URLs por tipo')
else:
    print('NO ENCONTRADO 1/2')

# Actualizar guardar_config en backend para nueva estructura
content2 = open('src/ui/backend/app.py', encoding='utf-8').read()

old2 = '''        # Endpoints
        if payload.get("endpoints") is not None:
            data["envio"] = {"endpoints": [
                {
                    "nombre": ep.get("nombre",""),
                    "activo": ep.get("activo", False),
                    "tipo_comprobante": ep.get("tipo_comprobante", ["todos"]),
                    "formato": ep.get("formato","txt"),
                    "url": ep.get("url",""),
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

if old2 in content2:
    content2 = content2.replace(old2, new2)
    open('src/ui/backend/app.py', 'w', encoding='utf-8').write(content2)
    print('OK 2/2 — guardar_config backend usa urls por tipo')
else:
    print('NO ENCONTRADO 2/2')
