/**
 * app.js - Motor CPE DisateQ v4.0
 */

var appState = {
    initialized: false,
    currentPage: 'dashboard',
    clienteAlias: null,
    archivoSeleccionado: null
};

document.addEventListener('DOMContentLoaded', async function() {
    await inicializarSistema();
    configurarNavegacion();
    configurarReloj();
    feather.replace();
});

async function inicializarSistema() {
    var result = await eel.inicializar_sistema()();
    if (!result.success) { showToast(result.error || 'Error al inicializar', 'error'); return; }
    var clientes = await eel.get_clientes_disponibles()();
    if (clientes.exito && clientes.clientes.length > 0) appState.clienteAlias = clientes.clientes[0].alias;
    appState.initialized = true;
    cargarDashboard();
}

function configurarNavegacion() {
    document.querySelectorAll('.tab-item').forEach(function(tab) {
        tab.addEventListener('click', function() { navegarA(tab.dataset.page); });
    });
}

function navegarA(page) {
    document.querySelectorAll('.tab-item').forEach(function(t) { t.classList.remove('active'); });
    document.querySelector('[data-page="' + page + '"]').classList.add('active');
    document.querySelectorAll('.content-page').forEach(function(p) { p.classList.remove('active'); });
    document.getElementById('page-' + page).classList.add('active');
    appState.currentPage = page;
    if (page === 'dashboard') cargarDashboard();
    if (page === 'procesar')  initProcesar();
    if (page === 'logs')      cargarLogs();
    if (page === 'historial') cargarHistorial();
    if (page === 'config')    initConfig();
}

function configurarReloj() {
    setInterval(function() {
        var now = new Date();
        document.getElementById('fecha-hora').textContent =
            now.toLocaleDateString('es-PE') + ' ' +
            now.toLocaleTimeString('es-PE', {hour:'2-digit', minute:'2-digit'});
    }, 1000);
}

function showToast(message, type) {
    type = type || 'info';
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(function() { toast.style.opacity = '0'; setTimeout(function() { toast.remove(); }, 300); }, 3000);
}

function showLoader(msg) {
    var loader = document.getElementById('loader-overlay');
    if (!loader) {
        loader = document.createElement('div');
        loader.id = 'loader-overlay';
        loader.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;z-index:9999;color:#fff;font-size:1.2rem;';
        document.body.appendChild(loader);
    }
    loader.textContent = msg || 'Procesando...';
    loader.style.display = 'flex';
}

function hideLoader() {
    var loader = document.getElementById('loader-overlay');
    if (loader) loader.style.display = 'none';
}

async function procesarPendientes() { navegarA('procesar'); }
function abrirConfig() { navegarA('config'); }

async function sincronizar() {
    showToast('Sincronizando...', 'info');
    await cargarDashboard();
    document.getElementById('ultima-sync').textContent =
        new Date().toLocaleTimeString('es-PE', {hour:'2-digit', minute:'2-digit'});
    showToast('Sincronizacion completada', 'success');
}

async function cerrarApp() {
    if (confirm('Cerrar Motor CPE DisateQ?')) {
        try { await eel.cerrar_sistema()(); } catch(e) {}
        window.close();
    }
}

// ================================================================
// PROCESAR
// ================================================================

async function initProcesar() {
    var empresa = await eel.get_empresa_info()();
    var info = document.getElementById('proc-cliente-info');
    if (info && empresa) info.textContent = empresa.nombre + ' - RUC: ' + empresa.ruc;
    await cargarPendientesDesdeMotor();
}

async function seleccionarArchivo() {
    var carpeta = await eel.seleccionar_carpeta()();
    if (carpeta) {
        document.getElementById('archivo-seleccionado').value = carpeta;
        appState.archivoSeleccionado = carpeta;
        await conectarYPreview(carpeta);
    }
}

async function cargarPendientes() {
    var archivo = document.getElementById('archivo-seleccionado').value;
    if (!archivo || archivo === 'Configurado en cliente YAML') await cargarPendientesDesdeMotor();
    else await conectarYPreview(archivo);
}

async function conectarYPreview(archivo) {
    var status  = document.getElementById('proc-status');
    var preview = document.getElementById('preview-container');
    status.style.display = 'block';
    status.style.background = '#dbeafe';
    status.style.color = '#1e40af';
    status.textContent = 'Conectando a fuente de datos...';
    preview.style.display = 'none';
    var result = await eel.conectar_fuente('dbf', archivo)();
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
}

async function cargarPendientesDesdeMotor() {
    var status = document.getElementById('proc-status');
    if (!status) return;
    status.style.display = 'block';
    status.style.background = '#dbeafe';
    status.style.color = '#1e40af';
    status.textContent = 'Leyendo fuente configurada...';
    var clientes = await eel.get_clientes_disponibles()();
    if (!clientes.exito || !clientes.clientes.length) {
        status.style.background = '#fee2e2';
        status.style.color = '#991b1b';
        status.textContent = 'No hay cliente configurado';
        return;
    }
    var cfg = clientes.clientes[0];
    var rutaResult = await eel.get_ruta_fuente(cfg.alias)();
    var input = document.getElementById('archivo-seleccionado');
    if (input && rutaResult.ruta) input.value = rutaResult.ruta;
    var result = await eel.conectar_fuente(cfg.tipo_fuente, rutaResult.ruta || cfg.alias)();
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
}

function mostrarTabla(comprobantes, total) {
    var tbody   = document.getElementById('preview-tbody');
    var counter = document.getElementById('proc-count');
    var preview = document.getElementById('preview-container');
    counter.textContent = 'Mostrando ' + comprobantes.length + ' de ' + total + ' pendientes';
    tbody.innerHTML = comprobantes.map(function(c, i) {
        return '<tr><td><input type="checkbox" class="comp-check" data-index="' + i + '" checked></td>' +
               '<td><strong>' + c.serie + '-' + String(c.numero).padStart(8,'0') + '</strong></td>' +
               '<td>' + (c.cliente || 'CLIENTES VARIOS') + '</td>' +
               '<td>S/ ' + Number(c.total || 0).toFixed(2) + '</td></tr>';
    }).join('');
    preview.style.display = 'block';
    feather.replace();
}

function toggleAll(cb) {
    document.querySelectorAll('.comp-check').forEach(function(c) { c.checked = cb.checked; });
}

async function procesarConMotor() {
    if (!appState.clienteAlias) { showToast('No hay cliente configurado', 'error'); return; }
    var checks = document.querySelectorAll('.comp-check:checked');
    if (checks.length === 0) { showToast('Selecciona al menos un comprobante', 'warning'); return; }
    if (!confirm('Procesar ' + checks.length + ' comprobante(s)?')) return;
    var btn = document.getElementById('btn-procesar');
    btn.disabled = true;
    btn.innerHTML = 'Procesando...';
    var result = await eel.procesar_motor(appState.clienteAlias, null, 'mock')();
    btn.disabled = false;
    btn.innerHTML = '<i data-feather="play-circle"></i> Procesar con Motor';
    feather.replace();
    if (result.exito) { mostrarResultado(result.resultados); await cargarDashboard(); }
    else showToast(result.error, 'error');
}

function mostrarResultado(r) {
    var div = document.getElementById('proc-resultado');
    div.style.display = 'block';
    document.getElementById('preview-container').style.display = 'none';
    div.innerHTML =
        '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:1.5rem;">' +
        '<h4 style="margin:0 0 1rem 0;color:#166534;">Procesamiento completado</h4>' +
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem;">' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;">' + r.procesados + '</div><div style="font-size:0.8rem;color:#6b7280;">Procesados</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:#166534;">' + r.enviados + '</div><div style="font-size:0.8rem;color:#6b7280;">Enviados</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:#991b1b;">' + r.errores + '</div><div style="font-size:0.8rem;color:#6b7280;">Errores</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:#92400e;">' + r.ignorados + '</div><div style="font-size:0.8rem;color:#6b7280;">Ignorados</div></div>' +
        '</div><div style="display:flex;gap:0.75rem;">' +
        '<button class="btn btn-primary" onclick="volverAProcesar()">Procesar mas</button>' +
        '<button class="btn btn-secondary" onclick="navegarA(\'logs\')">Ver logs</button>' +
        '<button class="btn btn-secondary" onclick="navegarA(\'dashboard\')">Dashboard</button>' +
        '</div></div>';
}

function volverAProcesar() {
    document.getElementById('proc-resultado').style.display = 'none';
    document.getElementById('proc-status').style.display = 'none';
    document.getElementById('preview-container').style.display = 'none';
    cargarPendientesDesdeMotor();
}

eel.expose(update_progress);
function update_progress(current, total) {
    showToast('Procesando ' + current + '/' + total, 'info');
}

// ================================================================
// LOGS
// ================================================================

async function cargarLogs() {
    try {
        var result = await eel.get_logs(null, 100)();
        var page = document.getElementById('page-logs');
        if (!result.exito) { page.querySelector('.card-body').innerHTML = '<p>' + result.error + '</p>'; return; }
        var html =
            '<div style="margin-bottom:0.75rem;display:flex;gap:0.5rem;">' +
            '<button class="btn btn-sm btn-ghost" onclick="filtrarLogs(null)">Todos</button>' +
            '<button class="btn btn-sm btn-ghost" onclick="filtrarLogs(\'REMITIDO\')">Remitidos</button>' +
            '<button class="btn btn-sm btn-ghost" onclick="filtrarLogs(\'ERROR\')">Errores</button>' +
            '<button class="btn btn-sm btn-ghost" onclick="filtrarLogs(\'IGNORADO\')">Ignorados</button></div>' +
            '<table class="table" id="tabla-logs"><thead><tr>' +
            '<th>Fecha</th><th>Serie-Numero</th><th>Estado</th><th>Endpoint</th><th>Detalle</th>' +
            '</tr></thead><tbody>' +
            result.logs.map(function(r) {
                return '<tr>' +
                    '<td>' + (r.fecha ? r.fecha.substring(0,19).replace('T',' ') : '-') + '</td>' +
                    '<td>' + r.serie + '-' + String(r.numero).padStart(8,'0') + '</td>' +
                    '<td><span class="badge badge-' + getBadgeClass(r.estado.toLowerCase()) + '">' + r.estado + '</span></td>' +
                    '<td>' + (r.endpoint || '-') + '</td>' +
                    '<td>' + (r.detalle || '-') + '</td></tr>';
            }).join('') + '</tbody></table>';
        page.querySelector('.card-body').innerHTML = html;
    } catch(e) { console.error('Error logs:', e); }
}

async function filtrarLogs(estado) {
    var result = await eel.get_logs(estado, 100)();
    if (!result.exito) return;
    var tbody = document.querySelector('#tabla-logs tbody');
    if (!tbody) return;
    tbody.innerHTML = result.logs.map(function(r) {
        return '<tr>' +
            '<td>' + (r.fecha ? r.fecha.substring(0,19).replace('T',' ') : '-') + '</td>' +
            '<td>' + r.serie + '-' + String(r.numero).padStart(8,'0') + '</td>' +
            '<td><span class="badge badge-' + getBadgeClass(r.estado.toLowerCase()) + '">' + r.estado + '</span></td>' +
            '<td>' + (r.endpoint || '-') + '</td>' +
            '<td>' + (r.detalle || '-') + '</td></tr>';
    }).join('');
}

// ================================================================
// HISTORIAL
// ================================================================

async function cargarHistorial() {
    var page = document.getElementById('page-historial');
    page.querySelector('.card-body').innerHTML = '<p style="color:#6b7280">Cargando...</p>';
    var result = await eel.get_historial(200)();
    if (!result.exito) { page.querySelector('.card-body').innerHTML = '<p style="color:red">Error</p>'; return; }
    var html =
        '<div style="margin-bottom:0.75rem;display:flex;justify-content:space-between;align-items:center;">' +
        '<span style="font-size:0.85rem;color:#6b7280;">Total: <strong>' + result.total + '</strong> comprobantes</span>' +
        '<input type="text" id="hist-search" placeholder="Buscar..." ' +
        'style="padding:0.4rem 0.75rem;border:1px solid #d1d5db;border-radius:6px;font-size:0.85rem;" ' +
        'oninput="filtrarHistorial(this.value)"></div>' +
        '<div style="max-height:500px;overflow-y:auto;border:1px solid #e5e7eb;border-radius:6px;">' +
        '<table class="table" id="tabla-historial" style="margin:0;">' +
        '<thead style="position:sticky;top:0;background:#fff;z-index:1;"><tr>' +
        '<th>Comprobante</th><th>Fecha</th><th>Cliente</th><th>Total</th><th>Estado</th><th>Endpoint</th>' +
        '</tr></thead><tbody id="historial-tbody">' +
        result.comprobantes.map(function(c) {
            return '<tr>' +
                '<td><strong>' + c.serie + '-' + String(c.numero).padStart(8,'0') + '</strong></td>' +
                '<td>' + c.fecha + '</td>' +
                '<td>' + c.cliente + '</td>' +
                '<td>S/ ' + Number(c.total).toFixed(2) + '</td>' +
                '<td><span class="badge badge-' + getBadgeClass(c.estado) + '">' + c.estado + '</span></td>' +
                '<td>' + c.endpoint + '</td></tr>';
        }).join('') + '</tbody></table></div>';
    page.querySelector('.card-body').innerHTML = html;
}

function filtrarHistorial(query) {
    var rows = document.querySelectorAll('#historial-tbody tr');
    var q = query.toLowerCase();
    rows.forEach(function(row) { row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none'; });
}

function getBadgeClass(estado) {
    var map = {'remitido':'success','enviado':'success','pendiente':'warning','error':'error','ignorado':'info','leido':'info','generado':'info'};
    return map[estado] || 'info';
}

function verTodos() { navegarA('historial'); }

// ================================================================
// CONFIGURACION
// ================================================================

var _configDesbloqueada = false;
var _SL = 'opacity:0.6;background:#f3f4f6;border:1px solid #e5e7eb;border-radius:6px;padding:0.4rem 0.75rem;font-size:0.875rem;color:#374151;display:block;';

async function initConfig() {
    if (_configDesbloqueada) await mostrarConfigCompleta();
    else mostrarLockConfig();
}

function mostrarLockConfig() {
    var page = document.getElementById('page-config');
    var pins = '';
    for (var i = 0; i < 4; i++) {
        pins += '<input type="password" maxlength="1" id="pin-' + i + '" ' +
            'style="width:52px;height:52px;text-align:center;font-size:1.5rem;border:2px solid #d1d5db;border-radius:6px;outline:none;" ' +
            'oninput="onPinInput(' + i + ',this)" onkeydown="onPinKey(event,' + i + ')">';
    }
    page.querySelector('.card-body').innerHTML =
        '<div style="max-width:320px;margin:3rem auto;text-align:center;">' +
        '<div style="font-size:3rem;margin-bottom:1rem;">&#128274;</div>' +
        '<h3 style="margin-bottom:0.5rem;">Acceso Restringido</h3>' +
        '<p style="color:#6b7280;margin-bottom:1.5rem;font-size:0.875rem;">Esta seccion requiere clave del tecnico instalador.</p>' +
        '<div style="display:flex;gap:0.75rem;justify-content:center;margin-bottom:1.25rem;">' + pins + '</div>' +
        '<button class="btn btn-primary" onclick="verificarPin()" style="width:100%;display:flex;align-items:center;justify-content:center;">Acceder</button>' +
        '<div id="pin-error" style="color:#ef4444;margin-top:0.75rem;font-size:0.875rem;display:none;">Clave incorrecta</div></div>';
    setTimeout(function() { var el = document.getElementById('pin-0'); if(el) el.focus(); }, 100);
}

function onPinInput(idx, input) {
    input.value = input.value.replace(/[^0-9]/g,'');
    if (input.value && idx < 3) { var n = document.getElementById('pin-'+(idx+1)); if(n) n.focus(); }
    if (idx === 3 && input.value) verificarPin();
}

function onPinKey(e, idx) {
    if (e.key === 'Backspace' && !e.target.value && idx > 0) {
        var p = document.getElementById('pin-'+(idx-1)); if(p) p.focus();
    }
}

async function verificarPin() {
    var clave = '';
    for (var i = 0; i < 4; i++) { var el = document.getElementById('pin-'+i); clave += el ? el.value : ''; }
    if (clave.length < 4) return;
    var result = await eel.verificar_clave_instalador(clave)();
    if (result.valida) { _configDesbloqueada = true; await mostrarConfigCompleta(); }
    else {
        var err = document.getElementById('pin-error'); if(err) err.style.display = 'block';
        for (var i = 0; i < 4; i++) { var el = document.getElementById('pin-'+i); if(el){el.value='';el.style.borderColor='#ef4444';} }
        setTimeout(function() {
            var e0 = document.getElementById('pin-0'); if(e0) e0.focus();
            for (var i = 0; i < 4; i++) { var el = document.getElementById('pin-'+i); if(el) el.style.borderColor='#d1d5db'; }
        }, 1000);
    }
}

function _renderSL(val) { return '<div style="' + _SL + '">' + (val || '-') + '</div>'; }

function _renderSeries(tipo, lista) {
    if (!lista || !lista.length) return '<div style="color:#6b7280;font-size:0.85rem;padding:0.5rem;">Sin series</div>';
    var html = '';
    for (var i = 0; i < lista.length; i++) {
        var s = lista[i];
        html += '<div style="display:flex;align-items:center;gap:0.5rem;padding:0.4rem 0.6rem;' +
            'background:' + (s.activa ? '#f0fdf4' : '#f9fafb') + ';' +
            'border:1px solid ' + (s.activa ? '#86efac' : '#e5e7eb') + ';border-radius:6px;margin-bottom:0.35rem;">' +
            '<strong style="min-width:55px;font-size:0.875rem;">' + s.serie + '</strong>' +
            '<span style="color:#6b7280;font-size:0.78rem;">desde:</span>' +
            '<input type="number" value="' + s.correlativo_inicio + '" id="serie-' + tipo + '-' + i + '-corr" style="width:75px;padding:0.2rem 0.4rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;">' +
            '<input type="hidden" id="serie-' + tipo + '-' + i + '-codigo" value="' + s.serie + '">' +
            '<label style="display:flex;align-items:center;gap:0.25rem;cursor:pointer;font-size:0.82rem;">' +
            '<input type="checkbox" id="serie-' + tipo + '-' + i + '-activa" ' + (s.activa ? 'checked' : '') + '> Activa</label>' +
            '<button onclick="this.parentElement.remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:#ef4444;font-size:1rem;">&#10005;</button></div>';
    }
    return html + '<button onclick="agregarSerie(\'' + tipo + '\')" style="font-size:0.78rem;color:#2563eb;background:none;border:1px dashed #60a5fa;border-radius:6px;padding:0.25rem 0.75rem;cursor:pointer;margin-top:0.25rem;">+ Agregar serie</button>';
}

function _renderEndpoints(eps) {
    var td = ['boleta','factura','nota_credito','nota_debito','todos'];
    var html = '';
    for (var i = 0; i < eps.length; i++) {
        var ep = eps[i];
        var th = '';
        for (var j = 0; j < td.length; j++) {
            var chk = (ep.tipo_comprobante || []).indexOf(td[j]) >= 0 ? 'checked' : '';
            th += '<label style="display:flex;align-items:center;gap:0.25rem;font-size:0.8rem;cursor:pointer;"><input type="checkbox" id="ep-' + i + '-tipo-' + td[j] + '" ' + chk + '> ' + td[j] + '</label>';
        }
        var u = ep.credenciales && ep.credenciales.usuario ? ep.credenciales.usuario : '';
        var t = ep.credenciales && ep.credenciales.token   ? ep.credenciales.token   : '';
        html += '<div style="border:1px solid #d1d5db;border-radius:8px;padding:1rem;margin-bottom:0.75rem;background:' + (ep.activo ? '#fafffe' : '#f9fafb') + ';">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">' +
            '<div style="display:flex;align-items:center;gap:0.75rem;">' +
            '<input type="text" id="ep-' + i + '-nombre" value="' + (ep.nombre||'') + '" style="font-weight:600;border:1px solid #d1d5db;border-radius:4px;padding:0.25rem 0.5rem;font-size:0.875rem;width:150px;">' +
            '<label style="display:flex;align-items:center;gap:0.3rem;font-size:0.82rem;cursor:pointer;"><input type="checkbox" id="ep-' + i + '-activo" ' + (ep.activo ? 'checked' : '') + '> Activo</label></div>' +
            '<button onclick="this.closest(\'div\').remove()" style="background:none;border:none;cursor:pointer;color:#ef4444;font-size:1rem;">&#10005;</button></div>' +
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">' +
            '<div style="grid-column:span 2;"><label style="font-size:0.72rem;color:#6b7280;">URL</label>' +
            '<input type="text" id="ep-' + i + '-url" value="' + (ep.url||'') + '" style="width:100%;padding:0.35rem 0.6rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;font-family:monospace;"></div>' +
            '<div><label style="font-size:0.72rem;color:#6b7280;">Usuario API <span style="color:#9ca3af">(opcional)</span></label>' +
            '<input type="text" id="ep-' + i + '-usuario" value="' + u + '" placeholder="Dejar vacio si no aplica" style="width:100%;padding:0.35rem 0.6rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;"></div>' +
            '<div><label style="font-size:0.72rem;color:#6b7280;">Token <span style="color:#9ca3af">(opcional)</span></label>' +
            '<input type="password" id="ep-' + i + '-token" value="' + t + '" placeholder="Dejar vacio si no aplica" style="width:100%;padding:0.35rem 0.6rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;"></div>' +
            '<div style="grid-column:span 2;"><label style="font-size:0.72rem;color:#6b7280;">Tipos de comprobante</label>' +
            '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.25rem;">' + th + '</div></div></div></div>';
    }
    return html + '<button onclick="agregarEndpoint()" style="font-size:0.78rem;color:#2563eb;background:none;border:1px dashed #60a5fa;border-radius:6px;padding:0.35rem 1rem;cursor:pointer;">+ Agregar endpoint</button>';
}

async function mostrarConfigCompleta() {
    var page = document.getElementById('page-config');
    var result = await eel.get_config_cliente()();
    if (!result.exito) { page.querySelector('.card-body').innerHTML = '<p style="color:red">Error</p>'; return; }
    var d = result;
    var series    = d.series    || {};
    var endpoints = d.endpoints || [];
    var rutas = (d.fuente.rutas || []).map(function(r) {
        return '<div style="' + _SL + 'font-family:monospace;font-size:0.82rem;margin-bottom:0.25rem;">' + r + '</div>';
    }).join('');

    var html =
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">' +
        '<span style="color:#22c55e;font-size:0.875rem;">&#128275; Modo tecnico activo</span>' +
        '<button class="btn btn-secondary" onclick="bloquearConfig()" style="font-size:0.8rem;">&#128274; Bloquear</button></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header">' +
        '<h3>&#127968; Empresa</h3>' +
        '<span style="font-size:0.72rem;color:#6b7280;background:#f3f4f6;padding:2px 8px;border-radius:10px;">Parcialmente editable</span>' +
        '</div><div class="card-body"><div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">' +
        '<div><label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.25rem;">RUC</label>' + _renderSL(d.empresa.ruc) + '</div>' +
        '<div><label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.25rem;">Razon Social</label>' + _renderSL(d.empresa.razon_social) + '</div>' +
        '<div><label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.25rem;">Nombre Comercial</label>' +
        '<input type="text" id="cfg-nombre-comercial" value="' + (d.empresa.nombre_comercial||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid #d1d5db;border-radius:6px;font-size:0.875rem;"></div>' +
        '<div><label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.25rem;">Alias / Local</label>' +
        '<input type="text" id="cfg-alias" value="' + (d.empresa.alias||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid #d1d5db;border-radius:6px;font-size:0.875rem;"></div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header">' +
        '<h3>&#128451; Fuente de Datos</h3>' +
        '<span style="font-size:0.72rem;color:#6b7280;background:#f3f4f6;padding:2px 8px;border-radius:10px;">Solo lectura</span>' +
        '</div><div class="card-body"><div style="display:grid;grid-template-columns:100px 1fr;gap:1rem;align-items:start;">' +
        '<div><label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.25rem;">Tipo</label>' + _renderSL((d.fuente.tipo||'').toUpperCase()) + '</div>' +
        '<div><label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.25rem;">Ruta(s)</label>' + rutas + '</div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header">' +
        '<h3>&#128203; Series y Correlativos</h3>' +
        '<span style="font-size:0.72rem;color:#22c55e;background:#dcfce7;padding:2px 8px;border-radius:10px;">Editable</span>' +
        '</div><div class="card-body"><div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;">' +
        '<div><label style="font-size:0.72rem;font-weight:600;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:0.5rem;">Boletas</label><div id="series-boleta">' + _renderSeries('boleta', series.boleta) + '</div></div>' +
        '<div><label style="font-size:0.72rem;font-weight:600;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:0.5rem;">Facturas</label><div id="series-factura">' + _renderSeries('factura', series.factura) + '</div></div>' +
        '<div><label style="font-size:0.72rem;font-weight:600;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:0.5rem;">Notas Credito</label><div id="series-nota_credito">' + _renderSeries('nota_credito', series.nota_credito) + '</div></div>' +
        '<div><label style="font-size:0.72rem;font-weight:600;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:0.5rem;">Notas Debito</label><div id="series-nota_debito">' + _renderSeries('nota_debito', series.nota_debito) + '</div></div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header">' +
        '<h3>&#128225; Endpoints de Envio</h3>' +
        '<span style="font-size:0.72rem;color:#22c55e;background:#dcfce7;padding:2px 8px;border-radius:10px;">Editable</span>' +
        '</div><div class="card-body"><div id="endpoints-container">' + _renderEndpoints(endpoints) + '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header">' +
        '<h3>&#128273; Clave del Instalador</h3>' +
        '<span style="font-size:0.72rem;color:#22c55e;background:#dcfce7;padding:2px 8px;border-radius:10px;">Editable</span>' +
        '</div><div class="card-body"><div style="display:flex;gap:1rem;align-items:flex-end;max-width:400px;">' +
        '<div style="flex:1;"><label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.25rem;">Nueva clave (4 digitos)</label>' +
        '<input type="password" id="cfg-clave-nueva" maxlength="4" placeholder="..." style="width:100%;padding:0.4rem 0.75rem;border:1px solid #d1d5db;border-radius:6px;font-size:1rem;letter-spacing:0.5rem;"></div>' +
        '<div style="flex:1;"><label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.25rem;">Confirmar clave</label>' +
        '<input type="password" id="cfg-clave-confirma" maxlength="4" placeholder="..." style="width:100%;padding:0.4rem 0.75rem;border:1px solid #d1d5db;border-radius:6px;font-size:1rem;letter-spacing:0.5rem;"></div>' +
        '</div></div></div>' +

        '<div style="display:flex;gap:0.75rem;justify-content:flex-end;padding-top:0.5rem;">' +
        '<button class="btn btn-secondary" onclick="bloquearConfig()">Cancelar</button>' +
        '<button class="btn btn-primary" onclick="guardarConfig()">&#128190; Guardar Cambios</button></div>' +
        '<div id="cfg-mensaje" style="text-align:right;margin-top:0.5rem;font-size:0.85rem;display:none;"></div>';

    page.querySelector('.card-body').innerHTML = html;
}

function agregarSerie(tipo) {
    var serie = prompt('Codigo de serie (ej: B002):');
    if (!serie) return;
    var corr = prompt('Correlativo de inicio:', '0');
    var container = document.getElementById('series-' + tipo);
    if (!container) return;
    var idx = container.querySelectorAll('input[type=number]').length;
    var div = document.createElement('div');
    div.style.cssText = 'display:flex;align-items:center;gap:0.5rem;padding:0.4rem 0.6rem;background:#f0fdf4;border:1px solid #86efac;border-radius:6px;margin-bottom:0.35rem;';
    div.innerHTML =
        '<strong style="min-width:55px;font-size:0.875rem;">' + serie.toUpperCase() + '</strong>' +
        '<span style="color:#6b7280;font-size:0.78rem;">desde:</span>' +
        '<input type="number" value="' + (corr||0) + '" id="serie-' + tipo + '-' + idx + '-corr" style="width:75px;padding:0.2rem 0.4rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;">' +
        '<input type="hidden" id="serie-' + tipo + '-' + idx + '-codigo" value="' + serie.toUpperCase() + '">' +
        '<label style="display:flex;align-items:center;gap:0.25rem;cursor:pointer;font-size:0.82rem;"><input type="checkbox" id="serie-' + tipo + '-' + idx + '-activa" checked> Activa</label>' +
        '<button onclick="this.parentElement.remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:#ef4444;font-size:1rem;">&#10005;</button>';
    var btn = container.querySelector('button');
    if (btn) container.insertBefore(div, btn);
    else container.appendChild(div);
}

function agregarEndpoint() {
    var container = document.getElementById('endpoints-container');
    var btn = container.querySelector('button[onclick="agregarEndpoint()"]');
    var idx = container.querySelectorAll('input[id$="-nombre"]').length;
    var td = ['boleta','factura','nota_credito','nota_debito','todos'];
    var th = td.map(function(t) {
        return '<label style="display:flex;align-items:center;gap:0.25rem;font-size:0.8rem;cursor:pointer;"><input type="checkbox" id="ep-' + idx + '-tipo-' + t + '"> ' + t + '</label>';
    }).join('');
    var div = document.createElement('div');
    div.style.cssText = 'border:1px solid #d1d5db;border-radius:8px;padding:1rem;margin-bottom:0.75rem;background:#fafffe;';
    div.innerHTML =
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">' +
        '<div style="display:flex;align-items:center;gap:0.75rem;">' +
        '<input type="text" id="ep-' + idx + '-nombre" placeholder="Nombre endpoint" style="font-weight:600;border:1px solid #d1d5db;border-radius:4px;padding:0.25rem 0.5rem;font-size:0.875rem;width:150px;">' +
        '<label style="display:flex;align-items:center;gap:0.3rem;font-size:0.82rem;cursor:pointer;"><input type="checkbox" id="ep-' + idx + '-activo" checked> Activo</label></div>' +
        '<button onclick="this.closest(\'div\').remove()" style="background:none;border:none;cursor:pointer;color:#ef4444;font-size:1rem;">&#10005;</button></div>' +
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">' +
        '<div style="grid-column:span 2;"><label style="font-size:0.72rem;color:#6b7280;">URL</label>' +
        '<input type="text" id="ep-' + idx + '-url" placeholder="https://..." style="width:100%;padding:0.35rem 0.6rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;font-family:monospace;"></div>' +
        '<div><label style="font-size:0.72rem;color:#6b7280;">Usuario API (opcional)</label>' +
        '<input type="text" id="ep-' + idx + '-usuario" placeholder="Dejar vacio" style="width:100%;padding:0.35rem 0.6rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;"></div>' +
        '<div><label style="font-size:0.72rem;color:#6b7280;">Token (opcional)</label>' +
        '<input type="password" id="ep-' + idx + '-token" placeholder="Dejar vacio" style="width:100%;padding:0.35rem 0.6rem;border:1px solid #d1d5db;border-radius:4px;font-size:0.82rem;"></div>' +
        '<div style="grid-column:span 2;"><label style="font-size:0.72rem;color:#6b7280;">Tipos de comprobante</label>' +
        '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.25rem;">' + th + '</div></div></div>';
    if (btn) container.insertBefore(div, btn);
    else container.appendChild(div);
}

async function guardarConfig() {
    var nueva    = document.getElementById('cfg-clave-nueva')    ? document.getElementById('cfg-clave-nueva').value    : '';
    var confirma = document.getElementById('cfg-clave-confirma') ? document.getElementById('cfg-clave-confirma').value : '';
    var msg      = document.getElementById('cfg-mensaje');
    if (nueva && nueva !== confirma)      { msg.style.display='block'; msg.style.color='#ef4444'; msg.textContent='Las claves no coinciden'; return; }
    if (nueva && !/^\d{4}$/.test(nueva)) { msg.style.display='block'; msg.style.color='#ef4444'; msg.textContent='La clave debe ser 4 digitos'; return; }
    var epEls = document.querySelectorAll('[id$="-nombre"][id^="ep-"]');
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
    });
    var payload = {
        nombre_comercial: document.getElementById('cfg-nombre-comercial') ? document.getElementById('cfg-nombre-comercial').value : '',
        alias:            document.getElementById('cfg-alias')             ? document.getElementById('cfg-alias').value             : '',
        endpoints:        endpoints,
        clave_nueva:      nueva || null
    };
    var result = await eel.guardar_config(payload)();
    msg.style.display = 'block';
    if (result.exito) {
        msg.style.color = '#22c55e'; msg.textContent = 'Configuracion guardada correctamente';
        setTimeout(function() { mostrarConfigCompleta(); }, 1500);
    } else {
        msg.style.color = '#ef4444'; msg.textContent = 'Error: ' + result.error;
    }
}

function bloquearConfig() { _configDesbloqueada = false; mostrarLockConfig(); }
