content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

old = """    var payload = {
        nombre_comercial: document.getElementById('cfg-nombre-comercial') ? document.getElementById('cfg-nombre-comercial').value : '',
        alias:            document.getElementById('cfg-alias')             ? document.getElementById('cfg-alias').value             : '',
        endpoints:        endpoints,
        clave_nueva:      nueva || null
    };"""

new = """    // Leer series del DOM
    var tiposSeries = ['boleta', 'factura', 'nota_credito', 'nota_debito'];
    var series = {};
    tiposSeries.forEach(function(tipo) {
        var container = document.getElementById('series-' + tipo);
        if (!container) { series[tipo] = []; return; }
        var items = [];
        var numInputs = container.querySelectorAll('input[type=number]');
        numInputs.forEach(function(inp) {
            var match = inp.id.match(/^serie-[^-]+-(\d+)-corr$/);
            if (!match) return;
            var idx    = match[1];
            var codEl  = document.getElementById('serie-' + tipo + '-' + idx + '-codigo');
            var actEl  = document.getElementById('serie-' + tipo + '-' + idx + '-activa');
            if (!codEl) return;
            items.push({
                serie:              codEl.value,
                correlativo_inicio: parseInt(inp.value) || 0,
                activa:             actEl ? actEl.checked : true
            });
        });
        series[tipo] = items;
    });

    var payload = {
        nombre_comercial: document.getElementById('cfg-nombre-comercial') ? document.getElementById('cfg-nombre-comercial').value : '',
        alias:            document.getElementById('cfg-alias')             ? document.getElementById('cfg-alias').value             : '',
        endpoints:        endpoints,
        series:           series,
        clave_nueva:      nueva || null
    };"""

if old in content:
    content = content.replace(old, new)
    open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)
    print('app.js OK')
else:
    print('BLOQUE NO ENCONTRADO')
