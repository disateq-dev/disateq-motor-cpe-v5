content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

# Fix th Estado en historial
old1 = "'<th>Comprobante</th><th>Tipo</th><th>Fecha</th><th>Cliente</th><th>Total</th><th>Estado</th><th>Endpoint</th>'"
new1 = "'<th>Comprobante</th><th>Tipo</th><th>Fecha</th><th>Cliente</th><th>Total</th><th style=\"text-align:right;\">Estado</th><th>Endpoint</th>'"

# Fix td Estado en renderHistorialTabla
old2 = "            '<td><span class=\"badge badge-' + getBadgeClass(c.estado) + '\">' + c.estado + '</span></td>' +"
new2 = "            '<td style=\"text-align:right;\"><span class=\"badge badge-' + getBadgeClass(c.estado) + '\">' + c.estado + '</span></td>' +"

n = 0
if old1 in content:
    content = content.replace(old1, new1); n += 1; print('OK th')
else:
    print('NO th')
if old2 in content:
    content = content.replace(old2, new2); n += 1; print('OK td')
else:
    print('NO td')

if n:
    open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)
