content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

# Encontrar inicio y fin de _renderEndpoints
start = content.find('_renderEndpoints(eps) {')
# Encontrar el fin buscando la siguiente funcion
end = content.find('\nfunction _renderSL', start)
if end == -1:
    end = content.find('\nfunction agregarSerie', start)

if start == -1 or end == -1:
    print('NO ENCONTRADO — start:', start, 'end:', end)
else:
    nueva_funcion = '''_renderEndpoints(eps) {
    var TIPOS = ['boleta','factura','nota_credito','nota_debito','anulacion','guia'];
    var TIPO_LABEL = {
        'boleta': 'Boleta',
        'factura': 'Factura',
        'nota_credito': 'N.Crédito',
        'nota_debito': 'N.Débito',
        'anulacion': 'Anulación',
        'guia': 'Guía'
    };
    var html = '';

    for (var i = 0; i < eps.length; i++) {
        var ep = eps[i];
        var u  = ep.credenciales && ep.credenciales.usuario ? ep.credenciales.usuario : '';
        var t  = ep.credenciales && ep.credenciales.token   ? ep.credenciales.token   : '';

        // URLs por tipo — soporta nueva estructura (urls) y legacy (url)
        var urls = ep.urls || {};
        // Si es legacy, rellenar urls con el valor de url
        if (!Object.keys(urls).length && ep.url) {
            TIPOS.forEach(function(tipo) { urls[tipo] = ep.url; });
        }

        // Filas de URLs por tipo
        var urlRows = '';
        TIPOS.forEach(function(tipo) {
            urlRows +=
                '<tr style="border-bottom:1px solid #f3f4f6;">' +
                '<td style="padding:0.3rem 0.5rem;font-size:0.75rem;color:#6b7280;white-space:nowrap;min-width:90px;">' + (TIPO_LABEL[tipo] || tipo) + '</td>' +
                '<td style="padding:0.3rem 0.5rem;width:100%;">' +
                '<input type="text" id="ep-' + i + '-url-' + tipo + '" value="' + (urls[tipo] || '') + '" ' +
                'placeholder="https://... (dejar vacío si no aplica)" ' +
                'style="width:100%;padding:0.25rem 0.5rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.78rem;font-family:monospace;">' +
                '</td></tr>';
        });

        html +=
            '<div style="border:1px solid #d1d5db;border-radius:8px;padding:1rem;margin-bottom:0.75rem;background:' + (ep.activo ? '#fafffe' : '#f9fafb') + ';">' +

            // Header: nombre + activo + eliminar
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">' +
            '<div style="display:flex;align-items:center;gap:0.75rem;">' +
            '<input type="text" id="ep-' + i + '-nombre" value="' + (ep.nombre||'') + '" ' +
            'style="font-weight:600;border:1px solid #d1d5db;border-radius:4px;padding:0.25rem 0.5rem;font-size:0.875rem;width:150px;">' +
            '<label style="display:flex;align-items:center;gap:0.3rem;font-size:0.82rem;cursor:pointer;">' +
            '<input type="checkbox" id="ep-' + i + '-activo" ' + (ep.activo ? 'checked' : '') + '> Activo</label>' +
            '<select id="ep-' + i + '-formato" style="padding:0.25rem 0.5rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.78rem;">' +
            '<option value="txt" ' + (ep.formato === 'txt' || !ep.formato ? 'selected' : '') + '>TXT</option>' +
            '<option value="json" ' + (ep.formato === 'json' ? 'selected' : '') + '>JSON</option>' +
            '<option value="xml" ' + (ep.formato === 'xml' ? 'selected' : '') + '>XML</option>' +
            '</select>' +
            '</div>' +
            '<button onclick="this.closest(\'div\').parentElement.remove()" ' +
            'style="background:none;border:none;cursor:pointer;color:#ef4444;font-size:1rem;">&#10005;</button>' +
            '</div>' +

            // Credenciales
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:0.75rem;">' +
            '<div><label style="font-size:0.72rem;color:#6b7280;">Usuario API <span style="color:#9ca3af">(opcional)</span></label>' +
            '<input type="text" id="ep-' + i + '-usuario" value="' + u + '" placeholder="Dejar vacío" ' +
            'style="width:100%;padding:0.3rem 0.5rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;"></div>' +
            '<div><label style="font-size:0.72rem;color:#6b7280;">Token <span style="color:#9ca3af">(opcional)</span></label>' +
            '<input type="password" id="ep-' + i + '-token" value="' + t + '" placeholder="Dejar vacío" ' +
            'style="width:100%;padding:0.3rem 0.5rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;"></div>' +
            '</div>' +

            // URLs por tipo
            '<div><label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.35rem;">URLs por tipo de comprobante</label>' +
            '<table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;">' +
            urlRows +
            '</table></div>' +

            '</div>';
    }

    return html + '<button onclick="agregarEndpoint()" ' +
        'style="font-size:0.78rem;color:#2563eb;background:none;border:1px dashed #60a5fa;border-radius:6px;padding:0.35rem 1rem;cursor:pointer;">+ Agregar servicio</button>';
}'''

    content = content[:start] + nueva_funcion + content[end:]
    open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)
    print('OK — _renderEndpoints actualizado con URLs por tipo')
