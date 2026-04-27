content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

# 1. Fix archivo-seleccionado — ahora es div, no input
old_input = "    if (input && rutaResult.ruta) input.value = rutaResult.ruta;"
new_input = "    var fuenteEl = document.getElementById('archivo-seleccionado');\n    if (fuenteEl && rutaResult.ruta) fuenteEl.textContent = rutaResult.ruta;"
if old_input in content:
    content = content.replace(old_input, new_input)
    print('OK 1 — archivo-seleccionado fix')
else:
    print('NO 1')

# 2. Fix mostrarTabla — total con 2 decimales y no mostrar S/0.00
old_tabla = "               '<td>S/ ' + Number(c.total || 0).toFixed(2) + '</td></tr>';"
new_tabla = "               '<td style=\"text-align:right;font-weight:600;\">' + (c.total > 0 ? 'S/ ' + Number(c.total).toFixed(2) : '<span style=\"color:var(--text-muted)\">—</span>') + '</td></tr>';"
if old_tabla in content:
    content = content.replace(old_tabla, new_tabla)
    print('OK 2 — total fix')
else:
    print('NO 2')

# 3. Agregar spinner helpers y usarlos en carga y proceso
old_spinner = "async function cargarPendientesDesdeMotor() {"
new_spinner = """function showProcSpinner(msg) {
    var sp = document.getElementById('proc-spinner');
    if (sp) { sp.style.display = 'flex'; document.getElementById('proc-spinner-msg').textContent = msg || 'Cargando...'; }
}
function hideProcSpinner() {
    var sp = document.getElementById('proc-spinner');
    if (sp) sp.style.display = 'none';
}

async function cargarPendientesDesdeMotor() {"""

if old_spinner in content:
    content = content.replace(old_spinner, new_spinner)
    print('OK 3 — spinner helpers')
else:
    print('NO 3')

# 4. Mostrar spinner al inicio de cargarPendientesDesdeMotor
old_carga = """    var status = document.getElementById('proc-status');
    if (!status) return;
    status.style.display = 'block';
    status.style.background = '#dbeafe';
    status.style.color = '#1e40af';
    status.textContent = 'Leyendo fuente configurada...';"""
new_carga = """    var status = document.getElementById('proc-status');
    if (!status) return;
    showProcSpinner('Leyendo fuente de datos...');
    status.style.display = 'block';
    status.style.background = '#dbeafe';
    status.style.color = '#1e40af';
    status.textContent = 'Leyendo fuente configurada...';"""
if old_carga in content:
    content = content.replace(old_carga, new_carga)
    print('OK 4 — spinner en carga')
else:
    print('NO 4')

# 5. Ocultar spinner cuando termina cargarPendientesDesdeMotor (éxito y error)
old_exito = """    if (result.exito) {
        status.style.background = '#dcfce7';
        status.style.color = '#166534';
        status.textContent = result.pendientes + ' comprobantes pendientes encontrados';
        mostrarTabla(result.comprobantes, result.pendientes);
    } else {
        status.style.background = '#fee2e2';
        status.style.color = '#991b1b';
        status.textContent = result.error;
    }
    feather.replace();
}"""
new_exito = """    hideProcSpinner();
    if (result.exito) {
        status.style.background = '#dcfce7';
        status.style.color = '#166534';
        status.textContent = result.pendientes + ' comprobantes pendientes encontrados';
        mostrarTabla(result.comprobantes, result.pendientes);
    } else {
        status.style.background = '#fee2e2';
        status.style.color = '#991b1b';
        status.textContent = result.error;
    }
    feather.replace();
}"""
if old_exito in content:
    content = content.replace(old_exito, new_exito)
    print('OK 5 — ocultar spinner')
else:
    print('NO 5')

# 6. Spinner en procesarConMotor
old_proc = """    var btn = document.getElementById('btn-procesar');
    btn.disabled = true;
    btn.innerHTML = 'Procesando...';
    var result = await eel.procesar_motor(appState.clienteAlias, null, 'mock')();
    btn.disabled = false;
    btn.innerHTML = '<i data-feather="play-circle"></i> Procesar con Motor';"""
new_proc = """    var btn = document.getElementById('btn-procesar');
    btn.disabled = true;
    btn.innerHTML = 'Procesando...';
    showProcSpinner('Enviando comprobantes...');
    var result = await eel.procesar_motor(appState.clienteAlias, null, 'mock')();
    hideProcSpinner();
    btn.disabled = false;
    btn.innerHTML = '<i data-feather="play-circle"></i> Procesar con Motor';"""
if old_proc in content:
    content = content.replace(old_proc, new_proc)
    print('OK 6 — spinner en procesar')
else:
    print('NO 6')

open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)

# 7. Fix CSS spinner animation en variables o layout
css = open('src/ui/frontend/css/components.css', encoding='utf-8').read()
if '@keyframes spin' not in css:
    css += '\n@keyframes spin { to { transform: rotate(360deg); } }\n'
    open('src/ui/frontend/css/components.css', 'w', encoding='utf-8').write(css)
    print('OK 7 — @keyframes spin agregado')
else:
    print('OK 7 — spin ya existe')
