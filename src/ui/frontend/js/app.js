/**
 * app.js — DisateQ Motor CPE v5.0
 * TASK-004 JS: migrado eel → window.pywebview.api
 */

'use strict';

var appState = {
    initialized:        false,
    currentPage:        'dashboard',
    clienteAlias:       null,
    archivoSeleccionado: null
};

// ── Helper: llama a pywebview.api y retorna promesa ────────────
function api(method) {
    var args = Array.prototype.slice.call(arguments, 1);
    return window.pywebview.api[method].apply(window.pywebview.api, args);
}

document.addEventListener('DOMContentLoaded', function() {
    if (window.pywebview) {
        inicializarSistema();
    } else {
        window.addEventListener('pywebviewready', function() {
            inicializarSistema();
        });
    }
    configurarNavegacion();
    configurarReloj();
    if (typeof feather !== 'undefined') feather.replace();
});

async function inicializarSistema() {
    try {
        var result = await api('inicializar_sistema');
        if (!result.success) { showToast(result.error || 'Error al inicializar', 'error'); return; }
        var clientes = await api('get_clientes_disponibles');
        if (clientes.exito && clientes.clientes.length > 0) {
            appState.clienteAlias = clientes.clientes[0].id || clientes.clientes[0].alias;
        }
        appState.initialized = true;
        cargarDashboard();
    } catch(e) {
        console.error('Error inicializando sistema:', e);
    }
}

function configurarNavegacion() {
    document.querySelectorAll('.tab-item').forEach(function(tab) {
        tab.addEventListener('click', function() { navegarA(tab.dataset.page); });
    });
}

function navegarA(page) {
    document.querySelectorAll('.tab-item').forEach(function(t) { t.classList.remove('active'); });
    var tabEl = document.querySelector('[data-page="' + page + '"]');
    if (tabEl) tabEl.classList.add('active');
    document.querySelectorAll('.content-page').forEach(function(p) { p.classList.remove('active'); });
    var pageEl = document.getElementById('page-' + page);
    if (pageEl) pageEl.classList.add('active');
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
        var el  = document.getElementById('fecha-hora');
        if (el) el.textContent =
            now.toLocaleDateString('es-PE') + ' ' +
            now.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
    }, 1000);
}

// ── Callback desde Python via evaluate_js ─────────────────────
// Python llama: window.evaluate_js('schedulerCicloCompletado({...})')
function schedulerCicloCompletado(resultados) {
    showToast('Ciclo automático: ' + resultados.enviados + ' enviados, ' + resultados.errores + ' errores', 'info');
    cargarDashboard();
}

// ── Toast ──────────────────────────────────────────────────────
function showToast(message, type) {
    type = type || 'info';
    var toast = document.createElement('div');
    toast.className  = 'toast ' + type;
    toast.textContent = message;
    var container = document.getElementById('toast-container');
    if (container) container.appendChild(toast);
    setTimeout(function() {
        toast.style.opacity = '0';
        setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
}

function showLoader(msg) {
    var loader = document.getElementById('loader-overlay');
    if (!loader) {
        loader = document.createElement('div');
        loader.id = 'loader-overlay';
        loader.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;z-index:9999;color:#fff;font-size:1.2rem;';
        document.body.appendChild(loader);
    }
    loader.textContent    = msg || 'Procesando...';
    loader.style.display  = 'flex';
}

function hideLoader() {
    var loader = document.getElementById('loader-overlay');
    if (loader) loader.style.display = 'none';
}

// ── Spinner procesar ───────────────────────────────────────────
function showProcSpinner(msg) {
    var sp = document.getElementById('proc-spinner');
    if (sp) {
        sp.style.display = 'flex';
        var msgEl = document.getElementById('proc-spinner-msg');
        if (msgEl) msgEl.textContent = msg || 'Cargando...';
    }
}

function hideProcSpinner() {
    var sp = document.getElementById('proc-spinner');
    if (sp) sp.style.display = 'none';
}

function _setFuenteLabel(ruta) {
    var el = document.getElementById('archivo-seleccionado');
    if (!el) return;
    if (ruta) {
        el.textContent = ruta;
        el.style.color = 'var(--text-primary)';
    } else {
        el.textContent = '—';
        el.style.color = 'var(--text-muted)';
    }
}

// ── Acciones header ────────────────────────────────────────────
function procesarPendientes() { navegarA('procesar'); }
function abrirConfig()        { navegarA('config'); }

async function sincronizar() {
    showToast('Sincronizando...', 'info');
    await cargarDashboard();
    var el = document.getElementById('ultima-sync');
    if (el) el.textContent = new Date().toLocaleTimeString('es-PE', { hour:'2-digit', minute:'2-digit' });
    showToast('Sincronización completada', 'success');
}

async function cerrarApp() {
    if (confirm('¿Cerrar Motor CPE DisateQ?')) {
        try { await api('cerrar_sistema'); } catch(e) {}
        window.close();
    }
}

// ══════════════════════════════════════════════════════════════
//  PROCESAR
// ══════════════════════════════════════════════════════════════

async function initProcesar() {
    var empresa = await api('get_empresa_info');
    var info    = document.getElementById('proc-cliente-info');
    if (info && empresa) info.textContent = empresa.nombre + ' — RUC: ' + empresa.ruc;

    var clientes = await api('get_clientes_disponibles');
    if (clientes.exito && clientes.clientes.length) {
        var rutaResult = await api('get_ruta_fuente', clientes.clientes[0].alias);
        _setFuenteLabel(rutaResult.ruta);
    }
    await cargarPendientesDesdeMotor();
}

async function cargarPendientes() {
    await cargarPendientesDesdeMotor();
}

async function cargarPendientesDesdeMotor() {
    var status = document.getElementById('proc-status');
    if (!status) return;
    showProcSpinner('Leyendo fuente de datos...');
    status.style.display    = 'block';
    status.style.background = 'var(--info-bg)';
    status.style.color      = 'var(--info)';
    status.textContent      = 'Leyendo fuente configurada...';

    var clientes = await api('get_clientes_disponibles');
    if (!clientes.exito || !clientes.clientes.length) {
        hideProcSpinner();
        status.style.background = 'var(--error-bg)';
        status.style.color      = 'var(--error)';
        status.textContent      = 'No hay cliente configurado';
        return;
    }

    var cfg        = clientes.clientes[0];
    var rutaResult = await api('get_ruta_fuente', cfg.alias);
    _setFuenteLabel(rutaResult.ruta);

    var result = await api('conectar_fuente', cfg.tipo_fuente, rutaResult.ruta || cfg.alias);
    hideProcSpinner();

    if (result.exito) {
        status.style.background = 'var(--success-bg)';
        status.style.color      = 'var(--success)';
        status.textContent      = result.pendientes + ' comprobantes pendientes encontrados';
        mostrarTabla(result.comprobantes, result.pendientes);
    } else {
        status.style.background = 'var(--error-bg)';
        status.style.color      = 'var(--error)';
        status.textContent      = result.error;
    }
    if (typeof feather !== 'undefined') feather.replace();
}

function mostrarTabla(comprobantes, total) {
    var tbody   = document.getElementById('preview-tbody');
    var counter = document.getElementById('proc-count');
    var preview = document.getElementById('preview-container');
    if (!tbody || !counter || !preview) return;
    counter.textContent = 'Mostrando ' + comprobantes.length + ' de ' + total + ' pendientes';
    tbody.innerHTML = comprobantes.map(function(c, i) {
        var totalHtml = c.total > 0
            ? '<strong>S/ ' + Number(c.total).toFixed(2) + '</strong>'
            : '<span style="color:var(--text-muted)">—</span>';
        return '<tr>' +
            '<td style="width:40px;"><input type="checkbox" class="comp-check" data-index="' + i + '" checked></td>' +
            '<td><strong>' + c.serie + '-' + String(c.numero).padStart(8, '0') + '</strong></td>' +
            '<td>' + (c.cliente || 'CLIENTES VARIOS') + '</td>' +
            '<td style="text-align:right;">' + totalHtml + '</td>' +
            '</tr>';
    }).join('');
    preview.style.display = 'block';
    if (typeof feather !== 'undefined') feather.replace();
}

function toggleAll(cb) {
    document.querySelectorAll('.comp-check').forEach(function(c) { c.checked = cb.checked; });
}

async function procesarConMotor() {
    if (!appState.clienteAlias) { showToast('No hay cliente configurado', 'error'); return; }
    var checks = document.querySelectorAll('.comp-check:checked');
    if (checks.length === 0) { showToast('Selecciona al menos un comprobante', 'warning'); return; }
    if (!confirm('¿Procesar ' + checks.length + ' comprobante(s)?')) return;

    var btn = document.getElementById('btn-procesar');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i data-feather="loader"></i> Procesando...'; }
    if (typeof feather !== 'undefined') feather.replace();
    showProcSpinner('Enviando comprobantes...');

    var result = await api('procesar_motor', appState.clienteAlias, null, 'mock');
    hideProcSpinner();
    if (btn) { btn.disabled = false; btn.innerHTML = '<i data-feather="play-circle"></i> Procesar con Motor'; }
    if (typeof feather !== 'undefined') feather.replace();

    if (result.exito) { mostrarResultado(result.resultados); await cargarDashboard(); }
    else showToast(result.error, 'error');
}

function mostrarResultado(r) {
    var div = document.getElementById('proc-resultado');
    if (!div) return;
    div.style.display = 'block';
    var pc = document.getElementById('preview-container');
    if (pc) pc.style.display = 'none';
    div.innerHTML =
        '<div style="background:var(--success-bg);border:1px solid var(--success-border);border-radius:var(--radius-lg);padding:1.5rem;">' +
        '<h4 style="margin:0 0 1rem 0;color:var(--success);">Procesamiento completado</h4>' +
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem;">' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;">'          + r.procesados + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Procesados</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--success);">'  + r.enviados   + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Enviados</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--error);">'    + r.errores    + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Errores</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--warning);">'  + r.ignorados  + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Ignorados</div></div>' +
        '</div><div style="display:flex;gap:0.75rem;">' +
        '<button class="btn btn-primary" onclick="volverAProcesar()">Procesar más</button>' +
        '<button class="btn btn-secondary" onclick="navegarA(\'logs\')">Ver logs</button>' +
        '<button class="btn btn-secondary" onclick="navegarA(\'dashboard\')">Dashboard</button>' +
        '</div></div>';
}

function volverAProcesar() {
    var pr = document.getElementById('proc-resultado');    if (pr) pr.style.display = 'none';
    var ps = document.getElementById('proc-status');       if (ps) ps.style.display = 'none';
    var pc = document.getElementById('preview-container'); if (pc) pc.style.display = 'none';
    cargarPendientesDesdeMotor();
}

function update_progress(current, total) {
    showToast('Procesando ' + current + '/' + total, 'info');
}

// ══════════════════════════════════════════════════════════════
//  LOGS
// ══════════════════════════════════════════════════════════════

var _logsData      = [];
var _logFiltTipo   = '';
var _logFiltEstado = 'REMITIDO';

async function cargarLogs() {
    try {
        var result = await api('get_logs', null, 500);
        var page   = document.getElementById('page-logs');
        if (!result.exito) { page.querySelector('.card-body').innerHTML = '<p>' + result.error + '</p>'; return; }
        _logsData      = result.logs || [];
        _logFiltTipo   = '';
        _logFiltEstado = 'REMITIDO';

        var html =
            '<div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-bottom:0.75rem;align-items:center;">' +
            '<span style="font-size:0.72rem;color:var(--text-muted);margin-right:0.1rem;">TIPO:</span>' +
            '<button class="btn-filt active" id="lfilt-tipo-todos"        onclick="setLogFiltTipo(\'\')">Todos</button>' +
            '<button class="btn-filt"        id="lfilt-tipo-boleta"       onclick="setLogFiltTipo(\'boleta\')">Boleta</button>' +
            '<button class="btn-filt"        id="lfilt-tipo-factura"      onclick="setLogFiltTipo(\'factura\')">Factura</button>' +
            '<button class="btn-filt"        id="lfilt-tipo-nota_credito" onclick="setLogFiltTipo(\'nota_credito\')">N.Crédito</button>' +
            '<button class="btn-filt"        id="lfilt-tipo-nota_debito"  onclick="setLogFiltTipo(\'nota_debito\')">N.Débito</button>' +
            '<button class="btn-filt"        id="lfilt-tipo-anulacion"    onclick="setLogFiltTipo(\'anulacion\')">Anulación</button>' +
            '<div style="width:1px;background:var(--border-light);margin:0 0.25rem;"></div>' +
            '<span style="font-size:0.72rem;color:var(--text-muted);margin-right:0.1rem;">ESTADO:</span>' +
            '<button class="btn-filt"        id="lfilt-est-todos"    onclick="setLogFiltEstado(\'\')">Todos</button>' +
            '<button class="btn-filt active" id="lfilt-est-REMITIDO" onclick="setLogFiltEstado(\'REMITIDO\')">Remitido</button>' +
            '<button class="btn-filt"        id="lfilt-est-ERROR"    onclick="setLogFiltEstado(\'ERROR\')">Error</button>' +
            '<button class="btn-filt"        id="lfilt-est-IGNORADO" onclick="setLogFiltEstado(\'IGNORADO\')">Ignorado</button>' +
            '<button class="btn-filt"        id="lfilt-est-GENERADO" onclick="setLogFiltEstado(\'GENERADO\')">Generado</button>' +
            '<button class="btn-filt"        id="lfilt-est-LEIDO"    onclick="setLogFiltEstado(\'LEIDO\')">Leído</button>' +
            '</div>' +
            '<div style="margin-bottom:0.5rem;font-size:0.8rem;color:var(--text-muted);">Mostrando <strong id="logs-count">0</strong> registros</div>' +
            '<div style="max-height:500px;overflow-y:auto;border:1px solid var(--border-light);border-radius:var(--radius-md);">' +
            '<table class="table" id="tabla-logs" style="margin:0;">' +
            '<thead style="position:sticky;top:0;background:var(--bg-table-head);z-index:1;"><tr>' +
            '<th style="width:14%;">Fecha/Hora</th><th style="width:14%;">Comprobante</th><th style="width:8%;">Tipo</th>' +
            '<th style="width:22%;">Cliente</th><th style="width:10%;">Endpoint</th>' +
            '<th style="width:18%;">Detalle</th><th style="width:14%;text-align:right;">Estado</th>' +
            '</tr></thead><tbody id="logs-tbody"></tbody></table></div>';

        page.querySelector('.card-body').innerHTML = html;
        _inyectarEstilosFilt();
        aplicarFiltrosLogs();
    } catch(e) { console.error('Error logs:', e); }
}

function setLogFiltTipo(tipo) {
    _logFiltTipo = tipo;
    document.querySelectorAll('[id^="lfilt-tipo-"]').forEach(function(b) { b.classList.remove('active'); });
    var el = document.getElementById('lfilt-tipo-' + (tipo || 'todos'));
    if (el) el.classList.add('active');
    aplicarFiltrosLogs();
}

function setLogFiltEstado(estado) {
    _logFiltEstado = estado;
    document.querySelectorAll('[id^="lfilt-est-"]').forEach(function(b) { b.classList.remove('active'); });
    var el = document.getElementById('lfilt-est-' + (estado || 'todos'));
    if (el) el.classList.add('active');
    aplicarFiltrosLogs();
}

function aplicarFiltrosLogs() {
    var filtrado = _logsData.filter(function(r) {
        return (!_logFiltTipo   || (r.tipo_doc || '') === _logFiltTipo) &&
               (!_logFiltEstado || r.estado === _logFiltEstado);
    });
    var countEl = document.getElementById('logs-count');
    if (countEl) countEl.textContent = filtrado.length;
    renderLogsTabla(filtrado);
}

var TIPO_LABEL_LOG = { boleta:'Boleta', factura:'Factura', nota_credito:'N.Crédito', nota_debito:'N.Débito', anulacion:'Anulación' };

function renderLogsTabla(data) {
    var tbody = document.getElementById('logs-tbody');
    if (!tbody) return;
    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:2rem;">Sin resultados</td></tr>';
        return;
    }
    tbody.innerHTML = data.map(function(r) {
        var tipoBadge = r.tipo_doc
            ? '<span class="badge badge-' + _tipoBadgeClass(r.tipo_doc) + '">' + (TIPO_LABEL_LOG[r.tipo_doc] || r.tipo_doc) + '</span>'
            : '-';
        return '<tr>' +
            '<td style="font-size:0.75rem;white-space:nowrap;">' + (r.fecha ? r.fecha.substring(0,19).replace('T',' ') : '-') + '</td>' +
            '<td><strong>' + r.serie + '-' + String(r.numero).padStart(8,'0') + '</strong></td>' +
            '<td>' + tipoBadge + '</td>' +
            '<td style="font-size:0.78rem;overflow:hidden;text-overflow:ellipsis;" title="' + (r.cliente_nombre||'') + '">' + (r.cliente_nombre || '-') + '</td>' +
            '<td><span class="badge badge-neutral" style="font-size:0.65rem;">' + (r.endpoint || '-') + '</span></td>' +
            '<td style="font-size:0.75rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + (r.detalle||'') + '">' + (r.detalle || '-') + '</td>' +
            '<td style="text-align:right;"><span class="badge badge-' + getBadgeClass(r.estado.toLowerCase()) + '">' + r.estado + '</span></td>' +
            '</tr>';
    }).join('');
}

// ══════════════════════════════════════════════════════════════
//  HISTORIAL
// ══════════════════════════════════════════════════════════════

var _historialData = [];
var _filtTipo      = '';
var _filtEstado    = '';

async function cargarHistorial() {
    var page = document.getElementById('page-historial');
    page.querySelector('.card-body').innerHTML = '<p style="color:var(--text-muted)">Cargando...</p>';
    var result = await api('get_historial', 500);
    if (!result.exito) {
        page.querySelector('.card-body').innerHTML = '<p style="color:var(--error)">Error: ' + result.error + '</p>';
        return;
    }
    _historialData = result.comprobantes || [];

    var remitidos = _historialData.filter(function(c) { return c.estado === 'remitido'; });
    var totalRem  = remitidos.length;
    var sumaRem   = remitidos.reduce(function(a, c) { return a + (c.total || 0); }, 0);

    var html =
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;flex-wrap:wrap;gap:0.5rem;">' +
        '<span style="font-size:0.85rem;color:var(--text-muted);">Total: <strong id="hist-count">' + result.total + '</strong> comprobantes</span>' +
        '<input type="text" id="hist-search" placeholder="Buscar serie, cliente..." ' +
        'style="padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.85rem;width:220px;" ' +
        'oninput="aplicarFiltrosHistorial()"></div>' +

        '<div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-bottom:0.75rem;">' +
        '<div style="display:flex;gap:0.3rem;align-items:center;">' +
        '<span style="font-size:0.72rem;color:var(--text-muted);margin-right:0.2rem;">TIPO:</span>' +
        '<button class="btn-filt active" id="filt-tipo-todos"        onclick="setFiltTipo(\'\')">Todos</button>' +
        '<button class="btn-filt"        id="filt-tipo-boleta"       onclick="setFiltTipo(\'boleta\')">Boleta</button>' +
        '<button class="btn-filt"        id="filt-tipo-factura"      onclick="setFiltTipo(\'factura\')">Factura</button>' +
        '<button class="btn-filt"        id="filt-tipo-nota_credito" onclick="setFiltTipo(\'nota_credito\')">N.Crédito</button>' +
        '<button class="btn-filt"        id="filt-tipo-nota_debito"  onclick="setFiltTipo(\'nota_debito\')">N.Débito</button>' +
        '</div>' +
        '<div style="width:1px;background:var(--border-light);margin:0 0.25rem;"></div>' +
        '<div style="display:flex;gap:0.3rem;align-items:center;">' +
        '<span style="font-size:0.72rem;color:var(--text-muted);margin-right:0.2rem;">ESTADO:</span>' +
        '<button class="btn-filt active" id="filt-est-todos"    onclick="setFiltEstado(\'\')">Todos</button>' +
        '<button class="btn-filt"        id="filt-est-remitido" onclick="setFiltEstado(\'remitido\')">Remitido</button>' +
        '<button class="btn-filt"        id="filt-est-error"    onclick="setFiltEstado(\'error\')">Error</button>' +
        '<button class="btn-filt"        id="filt-est-ignorado" onclick="setFiltEstado(\'ignorado\')">Ignorado</button>' +
        '</div></div>' +

        '<div style="border:1px solid var(--border-light);border-radius:var(--radius-md) var(--radius-md) 0 0;overflow:hidden;">' +
        '<div style="max-height:420px;overflow-y:auto;">' +
        '<table class="table" id="tabla-historial" style="margin:0;">' +
        '<thead style="position:sticky;top:0;background:var(--bg-table-head);z-index:1;"><tr>' +
        '<th style="width:14%;">Comprobante</th>' +
        '<th style="width:9%;">Tipo</th>' +
        '<th style="width:11%;">Fecha</th>' +
        '<th style="width:28%;">Cliente</th>' +
        '<th style="width:11%;text-align:right;">Total</th>' +
        '<th style="width:13%;text-align:right;">Estado</th>' +
        '<th style="width:14%;">Endpoint</th>' +
        '</tr></thead><tbody id="historial-tbody"></tbody></table></div></div>' +

        '<div class="table-footer">' +
        '<div class="tf-stats">' +
        '<div class="tf-item"><span class="tf-label">Remitidos</span><span class="tf-value ok" id="hist-total-remitidos">' + totalRem + '</span></div>' +
        '<div class="tf-item"><span class="tf-label">Monto remitido</span><span class="tf-value" id="hist-suma-total">S/ ' + sumaRem.toFixed(2) + '</span></div>' +
        '</div>' +
        '<span class="tf-info">Mostrando <strong id="hist-count-footer">' + _historialData.length + '</strong> de ' + result.total + '</span>' +
        '</div>';

    page.querySelector('.card-body').innerHTML = html;
    _inyectarEstilosFilt();
    renderHistorialTabla(_historialData);
}

function setFiltTipo(tipo) {
    _filtTipo = tipo;
    document.querySelectorAll('[id^="filt-tipo-"]').forEach(function(b) { b.classList.remove('active'); });
    var el = document.getElementById('filt-tipo-' + (tipo || 'todos'));
    if (el) el.classList.add('active');
    aplicarFiltrosHistorial();
}

function setFiltEstado(estado) {
    _filtEstado = estado;
    document.querySelectorAll('[id^="filt-est-"]').forEach(function(b) { b.classList.remove('active'); });
    var el = document.getElementById('filt-est-' + (estado || 'todos'));
    if (el) el.classList.add('active');
    aplicarFiltrosHistorial();
}

function aplicarFiltrosHistorial() {
    var query = (document.getElementById('hist-search') || {}).value || '';
    var q     = query.toLowerCase();
    var filtrado = _historialData.filter(function(c) {
        return (!_filtTipo   || c.tipo_doc === _filtTipo) &&
               (!_filtEstado || c.estado   === _filtEstado) &&
               (!q || (c.serie + '-' + c.numero).toLowerCase().includes(q) ||
                       (c.cliente || '').toLowerCase().includes(q));
    });
    var el  = document.getElementById('hist-count');          if (el)  el.textContent  = filtrado.length;
    var el2 = document.getElementById('hist-count-footer');   if (el2) el2.textContent = filtrado.length;
    var remFilt = filtrado.filter(function(c) { return c.estado === 'remitido'; });
    var el3 = document.getElementById('hist-total-remitidos'); if (el3) el3.textContent = remFilt.length;
    var el4 = document.getElementById('hist-suma-total');
    if (el4) el4.textContent = 'S/ ' + remFilt.reduce(function(a,c){return a+(c.total||0);},0).toFixed(2);
    renderHistorialTabla(filtrado);
}

function filtrarHistorial() { aplicarFiltrosHistorial(); }

function renderHistorialTabla(data) {
    var tbody = document.getElementById('historial-tbody');
    if (!tbody) return;
    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:2rem;">Sin resultados</td></tr>';
        return;
    }
    tbody.innerHTML = data.map(function(c) {
        var tipoBadge = c.tipo_doc
            ? '<span class="badge badge-' + _tipoBadgeClass(c.tipo_doc) + '">' + _tipoLabel(c.tipo_doc) + '</span>'
            : '-';
        return '<tr>' +
            '<td><strong>' + c.serie + '-' + String(c.numero).padStart(8,'0') + '</strong></td>' +
            '<td>' + tipoBadge + '</td>' +
            '<td style="font-size:0.78rem;">' + c.fecha + '</td>' +
            '<td style="overflow:hidden;text-overflow:ellipsis;" title="' + (c.cliente||'') + '">' + (c.cliente || 'CLIENTES VARIOS') + '</td>' +
            '<td style="text-align:right;font-weight:600;">S/ ' + Number(c.total||0).toFixed(2) + '</td>' +
            '<td style="text-align:right;"><span class="badge badge-' + getBadgeClass(c.estado) + '">' + c.estado + '</span></td>' +
            '<td><span class="badge badge-neutral" style="font-size:0.65rem;">' + (c.endpoint || '-') + '</span></td>' +
            '</tr>';
    }).join('');
}

// ══════════════════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════════════════

function _tipoLabel(tipo) {
    var map = { boleta:'Boleta', factura:'Factura', nota_credito:'N.Cred', nota_debito:'N.Deb', anulacion:'Anul.' };
    return map[tipo] || tipo;
}

function _tipoBadgeClass(tipo) {
    var map = { boleta:'boleta', factura:'factura', nota_credito:'nc', nota_debito:'nd', anulacion:'anulacion' };
    return map[tipo] || 'neutral';
}

function getBadgeClass(estado) {
    var map = { remitido:'success', enviado:'success', pendiente:'warning', error:'error', ignorado:'info', leido:'info', generado:'info' };
    return map[estado] || 'info';
}

function verTodos() { navegarA('historial'); }

function _inyectarEstilosFilt() {
    if (document.getElementById('style-btn-filt')) return;
    var s = document.createElement('style');
    s.id  = 'style-btn-filt';
    s.textContent =
        '.btn-filt{padding:0.22rem 0.6rem;font-size:0.72rem;border:1px solid var(--border-medium);border-radius:5px;' +
        'background:var(--bg-card);color:var(--text-secondary);cursor:pointer;transition:all 0.15s;}' +
        '.btn-filt:hover{border-color:var(--border-dark);}' +
        '.btn-filt.active{background:var(--slate-800,#1e293b);color:#fff;border-color:var(--slate-800,#1e293b);}';
    document.head.appendChild(s);
}

// ══════════════════════════════════════════════════════════════
//  SCHEDULER
// ══════════════════════════════════════════════════════════════

async function cargarSchedulerConfig() {
    try {
        var result = await api('get_scheduler_status');
        if (!result.exito) return;
        var s           = result.status;
        var modoManual  = document.getElementById('sched-modo-manual');
        var modoAuto    = document.getElementById('sched-modo-auto');
        var intervalBox = document.getElementById('sched-intervalo-box');
        var intervalo   = document.getElementById('sched-intervalo');
        if (!modoManual) return;
        if (s.modo === 'automatico') {
            modoAuto.checked = true;
            if (intervalBox) intervalBox.style.display = 'block';
            document.getElementById('lbl-modo-auto').style.borderColor   = 'var(--success)';
            document.getElementById('lbl-modo-manual').style.borderColor = 'var(--border-medium)';
        } else {
            modoManual.checked = true;
            if (intervalBox) intervalBox.style.display = 'none';
            document.getElementById('lbl-modo-manual').style.borderColor = 'var(--success)';
            document.getElementById('lbl-modo-auto').style.borderColor   = 'var(--border-medium)';
        }
        if (intervalo) intervalo.value = String(s.intervalo_minutos || 10);
    } catch(e) { console.error('Error cargando scheduler:', e); }
}

function onSchedModoChange() {
    var modo = document.querySelector('input[name="sched-modo"]:checked');
    if (!modo) return;
    var intervalBox = document.getElementById('sched-intervalo-box');
    var lblManual   = document.getElementById('lbl-modo-manual');
    var lblAuto     = document.getElementById('lbl-modo-auto');
    if (modo.value === 'automatico') {
        if (intervalBox) intervalBox.style.display = 'block';
        if (lblAuto)     lblAuto.style.borderColor   = 'var(--success)';
        if (lblManual)   lblManual.style.borderColor = 'var(--border-medium)';
    } else {
        if (intervalBox) intervalBox.style.display = 'none';
        if (lblManual)   lblManual.style.borderColor = 'var(--success)';
        if (lblAuto)     lblAuto.style.borderColor   = 'var(--border-medium)';
    }
}

// ══════════════════════════════════════════════════════════════
//  CONFIGURACIÓN
// ══════════════════════════════════════════════════════════════

var _configDesbloqueada = false;
var _SL = 'opacity:0.6;background:var(--bg-table-head);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:0.4rem 0.75rem;font-size:0.875rem;color:var(--text-secondary);display:block;';

async function initConfig() {
    if (_configDesbloqueada) await mostrarConfigCompleta();
    else mostrarLockConfig();
}

function mostrarLockConfig() {
    var page = document.getElementById('page-config');
    var pins = '';
    for (var i = 0; i < 4; i++) {
        pins += '<input type="password" maxlength="1" id="pin-' + i + '" ' +
            'style="width:52px;height:52px;text-align:center;font-size:1.5rem;border:2px solid var(--border-medium);border-radius:var(--radius-md);outline:none;" ' +
            'oninput="onPinInput(' + i + ',this)" onkeydown="onPinKey(event,' + i + ')">';
    }
    page.querySelector('.card-body').innerHTML =
        '<div style="max-width:320px;margin:3rem auto;text-align:center;">' +
        '<div style="font-size:3rem;margin-bottom:1rem;">&#128274;</div>' +
        '<h3 style="margin-bottom:0.5rem;">Acceso Restringido</h3>' +
        '<p style="color:var(--text-muted);margin-bottom:1.5rem;font-size:0.875rem;">Esta sección requiere clave del técnico instalador.</p>' +
        '<div style="display:flex;gap:0.75rem;justify-content:center;margin-bottom:1.25rem;">' + pins + '</div>' +
        '<button class="btn btn-primary" onclick="verificarPin()" style="width:100%;justify-content:center;">Acceder</button>' +
        '<div id="pin-error" style="color:var(--error);margin-top:0.75rem;font-size:0.875rem;display:none;">Clave incorrecta</div></div>';
    setTimeout(function() { var el = document.getElementById('pin-0'); if (el) el.focus(); }, 100);
}

function onPinInput(idx, input) {
    input.value = input.value.replace(/[^0-9]/g, '');
    if (input.value && idx < 3) { var n = document.getElementById('pin-' + (idx + 1)); if (n) n.focus(); }
    if (idx === 3 && input.value) verificarPin();
}

function onPinKey(e, idx) {
    if (e.key === 'Backspace' && !e.target.value && idx > 0) {
        var p = document.getElementById('pin-' + (idx - 1)); if (p) p.focus();
    }
}

async function verificarPin() {
    var clave = '';
    for (var i = 0; i < 4; i++) { var el = document.getElementById('pin-' + i); clave += el ? el.value : ''; }
    if (clave.length < 4) return;
    var result = await api('verificar_clave_instalador', clave);
    if (result.valida) { _configDesbloqueada = true; await mostrarConfigCompleta(); }
    else {
        var err = document.getElementById('pin-error'); if (err) err.style.display = 'block';
        for (var i = 0; i < 4; i++) { var el = document.getElementById('pin-' + i); if (el) { el.value = ''; el.style.borderColor = 'var(--error)'; } }
        setTimeout(function() {
            var e0 = document.getElementById('pin-0'); if (e0) e0.focus();
            for (var i = 0; i < 4; i++) { var el = document.getElementById('pin-' + i); if (el) el.style.borderColor = 'var(--border-medium)'; }
        }, 1000);
    }
}

function _renderSL(val) { return '<div style="' + _SL + '">' + (val || '-') + '</div>'; }

function _renderSeries(tipo, lista) {
    if (!lista || !lista.length) return '<div style="color:var(--text-muted);font-size:0.85rem;padding:0.5rem;">Sin series</div>';
    var html = '';
    for (var i = 0; i < lista.length; i++) {
        var s = lista[i];
        html += '<div style="display:flex;align-items:center;gap:0.5rem;padding:0.4rem 0.6rem;' +
            'background:' + (s.activa ? 'var(--success-bg)' : 'var(--bg-table-head)') + ';' +
            'border:1px solid ' + (s.activa ? 'var(--success-border)' : 'var(--border-light)') + ';border-radius:var(--radius-md);margin-bottom:0.35rem;">' +
            '<strong style="min-width:55px;font-size:0.875rem;">' + s.serie + '</strong>' +
            '<span style="color:var(--text-muted);font-size:0.78rem;">desde:</span>' +
            '<input type="number" value="' + s.correlativo_inicio + '" id="serie-' + tipo + '-' + i + '-corr" style="width:75px;padding:0.2rem 0.4rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;">' +
            '<input type="hidden" id="serie-' + tipo + '-' + i + '-codigo" value="' + s.serie + '">' +
            '<label style="display:flex;align-items:center;gap:0.25rem;cursor:pointer;font-size:0.82rem;">' +
            '<input type="checkbox" id="serie-' + tipo + '-' + i + '-activa" ' + (s.activa ? 'checked' : '') + '> Activa</label>' +
            '<button onclick="this.parentElement.remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:var(--error);font-size:1rem;">&#10005;</button></div>';
    }
    return html + '<button onclick="agregarSerie(\'' + tipo + '\')" style="font-size:0.78rem;color:var(--primary);background:none;border:1px dashed var(--blue-400);border-radius:var(--radius-md);padding:0.25rem 0.75rem;cursor:pointer;margin-top:0.25rem;">+ Agregar serie</button>';
}

function _renderEndpoints(eps) {
    var URL_CAMPOS = [
        { id:'url_comprobantes', label:'Comprobantes', desc:'Facturas, Boletas, Notas Crédito/Débito', req:true  },
        { id:'url_anulaciones',  label:'Anulaciones',  desc:'Comunicaciones de Baja',                 req:false },
        { id:'url_guias',        label:'Guías',        desc:'Guías de Remisión',                      req:false },
        { id:'url_retenciones',  label:'Retenciones',  desc:'Comprobantes de Retención',              req:false },
        { id:'url_percepciones', label:'Percepciones', desc:'Comprobantes de Percepción',             req:false },
    ];
    var html = '';
    for (var i = 0; i < eps.length; i++) {
        var ep = eps[i];
        var u  = ep.credenciales && ep.credenciales.usuario ? ep.credenciales.usuario : '';
        var t  = ep.credenciales && ep.credenciales.token   ? ep.credenciales.token   : '';
        var vals = {};
        URL_CAMPOS.forEach(function(c) { vals[c.id] = ep[c.id] || ''; });
        if (!vals.url_comprobantes) {
            vals.url_comprobantes = (ep.urls && (ep.urls.boleta || ep.urls.factura)) || ep.url || '';
            vals.url_anulaciones  = (ep.urls && ep.urls.anulacion) || ep.url_anulaciones || '';
        }
        var urlRows = URL_CAMPOS.map(function(c) {
            var val = vals[c.id] || '';
            var hab = !!val || c.req;
            return '<tr style="border-bottom:1px solid var(--border-light);">' +
                '<td style="padding:0.4rem 0.5rem;white-space:nowrap;min-width:110px;">' +
                '<label style="display:flex;align-items:center;gap:0.35rem;cursor:pointer;">' +
                '<input type="checkbox" id="ep-' + i + '-habilitar-' + c.id + '" ' + (hab ? 'checked' : '') +
                ' onchange="toggleUrlRow(this,\'ep-' + i + '-' + c.id + '\')">' +
                '<span style="font-size:0.75rem;font-weight:' + (c.req ? '600' : '400') + ';color:var(--text-secondary);">' + c.label + '</span>' +
                (c.req ? '<span style="color:var(--error);font-size:0.65rem;">*</span>' : '') +
                '</label><div style="font-size:0.65rem;color:var(--text-muted);margin-left:1.2rem;">' + c.desc + '</div></td>' +
                '<td style="padding:0.4rem 0.5rem;width:100%;">' +
                '<input type="text" id="ep-' + i + '-' + c.id + '" value="' + val + '" placeholder="https://..." ' +
                (hab ? '' : 'disabled ') +
                'style="width:100%;padding:0.25rem 0.5rem;border:1px solid ' + (val ? 'var(--success-border)' : 'var(--border-medium)') + ';border-radius:var(--radius-sm);font-size:0.78rem;font-family:var(--font-mono);' +
                (hab ? '' : 'background:var(--bg-input-disabled);color:var(--text-muted);') + '"></td></tr>';
        }).join('');
        html +=
            '<div style="border:1px solid var(--border-medium);border-radius:var(--radius-lg);padding:1rem;margin-bottom:0.75rem;">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">' +
            '<div style="display:flex;align-items:center;gap:0.75rem;">' +
            '<input type="text" id="ep-' + i + '-nombre" value="' + (ep.nombre||'') + '" style="font-weight:600;border:1px solid var(--border-medium);border-radius:var(--radius-sm);padding:0.25rem 0.5rem;font-size:0.875rem;width:150px;">' +
            '<label style="display:flex;align-items:center;gap:0.3rem;font-size:0.82rem;cursor:pointer;"><input type="checkbox" id="ep-' + i + '-activo" ' + (ep.activo ? 'checked' : '') + '> Activo</label>' +
            '<select id="ep-' + i + '-formato" style="padding:0.25rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.78rem;">' +
            '<option value="txt" '  + (!ep.formato || ep.formato === 'txt'  ? 'selected' : '') + '>TXT</option>'  +
            '<option value="json" ' + (ep.formato === 'json' ? 'selected' : '') + '>JSON</option>' +
            '<option value="xml" '  + (ep.formato === 'xml'  ? 'selected' : '') + '>XML</option>'  +
            '</select></div>' +
            '<button onclick="this.parentNode.parentNode.remove()" style="background:none;border:none;cursor:pointer;color:var(--error);font-size:1.2rem;">&#10005;</button></div>' +
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:0.75rem;">' +
            '<div><label style="font-size:0.72rem;color:var(--text-muted);">Usuario API (opcional)</label>' +
            '<input type="text" id="ep-' + i + '-usuario" value="' + u + '" placeholder="Dejar vacío" style="width:100%;padding:0.3rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;"></div>' +
            '<div><label style="font-size:0.72rem;color:var(--text-muted);">Token (opcional)</label>' +
            '<input type="password" id="ep-' + i + '-token" value="' + t + '" placeholder="Dejar vacío" style="width:100%;padding:0.3rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;"></div></div>' +
            '<table style="width:100%;border-collapse:collapse;border:1px solid var(--border-light);border-radius:var(--radius-md);overflow:hidden;">' +
            urlRows + '</table></div>';
    }
    return html + '<button onclick="agregarEndpointConfig()" style="font-size:0.78rem;color:var(--primary);background:none;border:1px dashed var(--blue-400);border-radius:var(--radius-md);padding:0.35rem 1rem;cursor:pointer;">+ Agregar servicio</button>';
}

function agregarSerie(tipo) {
    var serie = prompt('Código de serie (ej: B002):');
    if (!serie) return;
    var corr = prompt('Correlativo de inicio:', '0');
    var container = document.getElementById('series-' + tipo);
    if (!container) return;
    var idx = container.querySelectorAll('input[type=number]').length;
    var div = document.createElement('div');
    div.style.cssText = 'display:flex;align-items:center;gap:0.5rem;padding:0.4rem 0.6rem;background:var(--success-bg);border:1px solid var(--success-border);border-radius:var(--radius-md);margin-bottom:0.35rem;';
    div.innerHTML =
        '<strong style="min-width:55px;font-size:0.875rem;">' + serie.toUpperCase() + '</strong>' +
        '<span style="color:var(--text-muted);font-size:0.78rem;">desde:</span>' +
        '<input type="number" value="' + (corr||0) + '" id="serie-' + tipo + '-' + idx + '-corr" style="width:75px;padding:0.2rem 0.4rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;">' +
        '<input type="hidden" id="serie-' + tipo + '-' + idx + '-codigo" value="' + serie.toUpperCase() + '">' +
        '<label style="display:flex;align-items:center;gap:0.25rem;cursor:pointer;font-size:0.82rem;"><input type="checkbox" id="serie-' + tipo + '-' + idx + '-activa" checked> Activa</label>' +
        '<button onclick="this.parentElement.remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:var(--error);font-size:1rem;">&#10005;</button>';
    var btn = container.querySelector('button');
    if (btn) container.insertBefore(div, btn);
    else container.appendChild(div);
}

function toggleUrlRow(checkbox, inputId) {
    var input = document.getElementById(inputId);
    if (!input) return;
    input.disabled    = !checkbox.checked;
    input.style.background = checkbox.checked ? '' : 'var(--bg-input-disabled)';
    input.style.color      = checkbox.checked ? '' : 'var(--text-muted)';
}

function agregarEndpointConfig() {
    var container = document.getElementById('endpoints-container');
    var btn       = container.querySelector('button[onclick="agregarEndpointConfig()"]');
    var idx       = container.querySelectorAll('input[id$="-nombre"]').length;
    var URL_CAMPOS = [
        { id:'url_comprobantes', label:'Comprobantes', desc:'Facturas, Boletas, Notas', req:true  },
        { id:'url_anulaciones',  label:'Anulaciones',  desc:'Comunicaciones de Baja',  req:false },
        { id:'url_guias',        label:'Guías',        desc:'Guías de Remisión',        req:false },
        { id:'url_retenciones',  label:'Retenciones',  desc:'Ret./Percepciones',        req:false },
        { id:'url_percepciones', label:'Percepciones', desc:'Comprobantes Percepción',  req:false },
    ];
    var urlRows = URL_CAMPOS.map(function(c) {
        return '<tr style="border-bottom:1px solid var(--border-light);">' +
            '<td style="padding:0.4rem 0.5rem;white-space:nowrap;min-width:110px;">' +
            '<label style="display:flex;align-items:center;gap:0.35rem;cursor:pointer;">' +
            '<input type="checkbox" id="ep-' + idx + '-habilitar-' + c.id + '" ' + (c.req ? 'checked' : '') +
            ' onchange="toggleUrlRow(this,\'ep-' + idx + '-' + c.id + '\')">' +
            '<span style="font-size:0.75rem;font-weight:' + (c.req ? '600' : '400') + ';color:var(--text-secondary);">' + c.label + '</span>' +
            (c.req ? '<span style="color:var(--error);font-size:0.65rem;">*</span>' : '') +
            '</label></td>' +
            '<td style="padding:0.4rem 0.5rem;width:100%;">' +
            '<input type="text" id="ep-' + idx + '-' + c.id + '" placeholder="https://..." ' +
            (c.req ? '' : 'disabled ') +
            'style="width:100%;padding:0.25rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.78rem;font-family:var(--font-mono);' +
            (c.req ? '' : 'background:var(--bg-input-disabled);color:var(--text-muted);') + '"></td></tr>';
    }).join('');
    var div = document.createElement('div');
    div.style.cssText = 'border:1px solid var(--border-medium);border-radius:var(--radius-lg);padding:1rem;margin-bottom:0.75rem;';
    div.innerHTML =
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">' +
        '<input type="text" id="ep-' + idx + '-nombre" placeholder="Nombre servicio" style="font-weight:600;border:1px solid var(--border-medium);border-radius:var(--radius-sm);padding:0.25rem 0.5rem;font-size:0.875rem;width:180px;">' +
        '<label style="display:flex;align-items:center;gap:0.3rem;font-size:0.82rem;cursor:pointer;margin-left:0.75rem;"><input type="checkbox" id="ep-' + idx + '-activo" checked> Activo</label>' +
        '<select id="ep-' + idx + '-formato" style="padding:0.25rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.78rem;margin-left:0.5rem;">' +
        '<option value="txt">TXT</option><option value="json">JSON</option><option value="xml">XML</option></select>' +
        '<button onclick="this.parentNode.parentNode.remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:var(--error);font-size:1.2rem;">&#10005;</button></div>' +
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:0.75rem;">' +
        '<div><label style="font-size:0.72rem;color:var(--text-muted);">Usuario API (opcional)</label>' +
        '<input type="text" id="ep-' + idx + '-usuario" placeholder="Dejar vacío" style="width:100%;padding:0.3rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;"></div>' +
        '<div><label style="font-size:0.72rem;color:var(--text-muted);">Token (opcional)</label>' +
        '<input type="password" id="ep-' + idx + '-token" placeholder="Dejar vacío" style="width:100%;padding:0.3rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;"></div></div>' +
        '<table style="width:100%;border-collapse:collapse;border:1px solid var(--border-light);border-radius:var(--radius-md);overflow:hidden;">' + urlRows + '</table>';
    if (btn) container.insertBefore(div, btn);
    else container.appendChild(div);
}

async function guardarConfig() {
    var nueva    = document.getElementById('cfg-clave-nueva')    ? document.getElementById('cfg-clave-nueva').value    : '';
    var confirma = document.getElementById('cfg-clave-confirma') ? document.getElementById('cfg-clave-confirma').value : '';
    var msg      = document.getElementById('cfg-mensaje');
    if (nueva && nueva !== confirma)      { msg.style.display = 'block'; msg.style.color = 'var(--error)'; msg.textContent = 'Las claves no coinciden'; return; }
    if (nueva && !/^\d{4}$/.test(nueva)) { msg.style.display = 'block'; msg.style.color = 'var(--error)'; msg.textContent = 'La clave debe ser 4 dígitos'; return; }

    var epEls      = document.querySelectorAll('[id$="-nombre"][id^="ep-"]');
    var endpoints  = [];
    var URL_CAMPOS = ['url_comprobantes','url_anulaciones','url_guias','url_retenciones','url_percepciones'];
    epEls.forEach(function(el) {
        var idx = el.id.replace('ep-','').replace('-nombre','');
        var ae  = document.getElementById('ep-' + idx + '-activo');
        var us  = document.getElementById('ep-' + idx + '-usuario');
        var tk  = document.getElementById('ep-' + idx + '-token');
        var fmt = document.getElementById('ep-' + idx + '-formato');
        var ep  = { nombre: el.value, activo: ae ? ae.checked : false, formato: fmt ? fmt.value : 'txt', usuario: us ? us.value : '', token: tk ? tk.value : '' };
        URL_CAMPOS.forEach(function(campo) {
            var urlEl = document.getElementById('ep-' + idx + '-' + campo);
            ep[campo] = (urlEl && !urlEl.disabled) ? urlEl.value.trim() : '';
        });
        endpoints.push(ep);
    });

    var tiposSeries = ['boleta','factura','nota_credito','nota_debito'];
    var series      = {};
    tiposSeries.forEach(function(tipo) {
        var container = document.getElementById('series-' + tipo);
        if (!container) { series[tipo] = []; return; }
        var items = [];
        container.querySelectorAll('input[type=number]').forEach(function(inp) {
            var match = inp.id.match(/^serie-[^-]+-(\d+)-corr$/);
            if (!match) return;
            var ii    = match[1];
            var codEl = document.getElementById('serie-' + tipo + '-' + ii + '-codigo');
            var actEl = document.getElementById('serie-' + tipo + '-' + ii + '-activa');
            if (!codEl) return;
            items.push({ serie: codEl.value, correlativo_inicio: parseInt(inp.value)||0, activa: actEl ? actEl.checked : true });
        });
        series[tipo] = items;
    });

    var schedModo      = document.querySelector('input[name="sched-modo"]:checked');
    var schedIntervalo = document.getElementById('sched-intervalo');
    if (schedModo) {
        await api('guardar_config_scheduler', { modo: schedModo.value, intervalo_boletas: schedIntervalo ? parseInt(schedIntervalo.value) : 10 });
    }

    var result = await api('guardar_config', {
        nombre_comercial: document.getElementById('cfg-nombre-comercial') ? document.getElementById('cfg-nombre-comercial').value : '',
        alias:            document.getElementById('cfg-alias')             ? document.getElementById('cfg-alias').value             : '',
        endpoints: endpoints,
        series:    series,
        clave_nueva: nueva || null,
    });

    msg.style.display = 'block';
    if (result.exito) {
        msg.style.color = 'var(--success)'; msg.textContent = 'Configuración guardada correctamente';
        setTimeout(function() { mostrarConfigCompleta(); }, 1500);
    } else {
        msg.style.color = 'var(--error)'; msg.textContent = 'Error: ' + result.error;
    }
}

function bloquearConfig() { _configDesbloqueada = false; mostrarLockConfig(); }

async function mostrarConfigCompleta() {
    var page   = document.getElementById('page-config');
    var result = await api('get_config_cliente');
    if (!result.exito) { page.querySelector('.card-body').innerHTML = '<p style="color:var(--error)">Error</p>'; return; }
    var d         = result;
    var series    = d.series    || {};
    var endpoints = d.endpoints || [];
    var rutas = (d.fuente.rutas || []).map(function(r) {
        return '<div style="' + _SL + 'font-family:var(--font-mono);font-size:0.82rem;margin-bottom:0.25rem;">' + r + '</div>';
    }).join('');

    var html =
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">' +
        '<span style="color:var(--success);font-size:0.875rem;">&#128275; Modo técnico activo</span>' +
        '<button class="btn btn-secondary" onclick="bloquearConfig()" style="font-size:0.8rem;">&#128274; Bloquear</button></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>&#127968; Empresa</h3></div>' +
        '<div class="card-body"><div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">' +
        '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">RUC</label>'           + _renderSL(d.empresa.ruc)          + '</div>' +
        '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Razón Social</label>'   + _renderSL(d.empresa.razon_social) + '</div>' +
        '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Nombre Comercial</label>' +
        '<input type="text" id="cfg-nombre-comercial" value="' + (d.empresa.nombre_comercial||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;"></div>' +
        '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Alias / Local</label>' +
        '<input type="text" id="cfg-alias" value="' + (d.empresa.alias||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;"></div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>&#128451; Fuente de Datos</h3></div>' +
        '<div class="card-body"><div style="display:grid;grid-template-columns:100px 1fr;gap:1rem;align-items:start;">' +
        '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Tipo</label>' + _renderSL((d.fuente.tipo||'').toUpperCase()) + '</div>' +
        '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Ruta(s)</label>' + rutas + '</div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>&#128203; Series y Correlativos</h3></div>' +
        '<div class="card-body"><div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;">' +
        '<div><label style="font-size:0.72rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;display:block;margin-bottom:0.5rem;">Boletas</label><div id="series-boleta">'       + _renderSeries('boleta',       series.boleta)       + '</div></div>' +
        '<div><label style="font-size:0.72rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;display:block;margin-bottom:0.5rem;">Facturas</label><div id="series-factura">'     + _renderSeries('factura',      series.factura)      + '</div></div>' +
        '<div><label style="font-size:0.72rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;display:block;margin-bottom:0.5rem;">Notas Crédito</label><div id="series-nota_credito">' + _renderSeries('nota_credito', series.nota_credito) + '</div></div>' +
        '<div><label style="font-size:0.72rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;display:block;margin-bottom:0.5rem;">Notas Débito</label><div id="series-nota_debito">'   + _renderSeries('nota_debito',  series.nota_debito)  + '</div></div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>&#128225; Endpoints de Envío</h3></div>' +
        '<div class="card-body"><div id="endpoints-container">' + _renderEndpoints(endpoints) + '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>&#9201; Procesamiento Automático</h3></div>' +
        '<div class="card-body">' +
        '<div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:1rem;">' +
        '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.35rem;">MODO</label>' +
        '<div style="display:flex;gap:0.5rem;">' +
        '<label style="display:flex;align-items:center;gap:0.4rem;cursor:pointer;font-size:0.875rem;padding:0.5rem 1rem;border:2px solid var(--border-medium);border-radius:var(--radius-md);" id="lbl-modo-manual"><input type="radio" name="sched-modo" id="sched-modo-manual" value="manual" onchange="onSchedModoChange()"> Manual</label>' +
        '<label style="display:flex;align-items:center;gap:0.4rem;cursor:pointer;font-size:0.875rem;padding:0.5rem 1rem;border:2px solid var(--border-medium);border-radius:var(--radius-md);" id="lbl-modo-auto"><input type="radio" name="sched-modo" id="sched-modo-auto" value="automatico" onchange="onSchedModoChange()"> Automático</label>' +
        '</div></div>' +
        '<div id="sched-intervalo-box" style="display:none;"><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.35rem;">INTERVALO</label>' +
        '<select id="sched-intervalo" style="padding:0.45rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;">' +
        '<option value="5">Cada 5 minutos</option><option value="10">Cada 10 minutos</option><option value="15">Cada 15 minutos</option><option value="30">Cada 30 minutos</option>' +
        '</select></div></div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>&#128273; Clave del Instalador</h3></div>' +
        '<div class="card-body"><div style="display:flex;gap:1rem;align-items:flex-end;max-width:400px;">' +
        '<div style="flex:1;"><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Nueva clave (4 dígitos)</label>' +
        '<input type="password" id="cfg-clave-nueva" maxlength="4" placeholder="..." style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:1rem;letter-spacing:0.5rem;"></div>' +
        '<div style="flex:1;"><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Confirmar clave</label>' +
        '<input type="password" id="cfg-clave-confirma" maxlength="4" placeholder="..." style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:1rem;letter-spacing:0.5rem;"></div>' +
        '</div></div></div>' +

        '<div style="display:flex;gap:0.75rem;justify-content:flex-end;padding-top:0.5rem;">' +
        '<button class="btn btn-secondary" onclick="bloquearConfig()">Cancelar</button>' +
        '<button class="btn btn-primary" onclick="guardarConfig()">&#128190; Guardar Cambios</button></div>' +
        '<div id="cfg-mensaje" style="text-align:right;margin-top:0.5rem;font-size:0.85rem;display:none;"></div>';

    page.querySelector('.card-body').innerHTML = html;
    setTimeout(cargarSchedulerConfig, 100);
}
