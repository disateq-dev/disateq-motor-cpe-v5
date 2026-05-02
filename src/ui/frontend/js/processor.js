/**
 * processor.js — DisateQ Motor CPE v5.0
 * TASK-004 JS: migrado eel → window.pywebview.api
 * TASK-011: columna Tipo (B/F/NC/ND) en tabla de pendientes
 * TASK-013: label fuente muestra ruta real desde arranque
 */

'use strict';

let _pendientesData = [];

async function initProcesar() {
    const empresa = await window.pywebview.api.get_empresa_info();
    const info    = document.getElementById('proc-cliente-info');
    if (info && empresa) info.textContent = empresa.nombre + ' — RUC: ' + empresa.ruc;

    const clientes = await window.pywebview.api.get_clientes_disponibles();
    if (clientes.exito && clientes.clientes.length) {
        const rutaResult = await window.pywebview.api.get_ruta_fuente(clientes.clientes[0].alias);
        // TASK-013: setear ruta real desde arranque, no "Cargando..."
        _setFuenteLabel(rutaResult.ruta);
    }
    await cargarPendientesDesdeMotor();
}

async function cargarPendientes() {
    await cargarPendientesDesdeMotor();
}

async function cargarPendientesDesdeMotor() {
    const status = document.getElementById('proc-status');
    if (!status) return;

    showProcSpinner('Leyendo fuente de datos...');
    status.style.display    = 'block';
    status.style.background = 'var(--info-bg)';
    status.style.color      = 'var(--info)';
    status.textContent      = 'Leyendo fuente configurada...';

    const clientes = await window.pywebview.api.get_clientes_disponibles();
    if (!clientes.exito || !clientes.clientes.length) {
        hideProcSpinner();
        status.style.background = 'var(--error-bg)';
        status.style.color      = 'var(--error)';
        status.textContent      = 'No hay cliente configurado';
        return;
    }

    const cfg        = clientes.clientes[0];
    const rutaResult = await window.pywebview.api.get_ruta_fuente(cfg.alias);

    // TASK-013: actualizar label con ruta real
    _setFuenteLabel(rutaResult.ruta);

    const result = await window.pywebview.api.conectar_fuente(cfg.tipo_fuente, rutaResult.ruta || cfg.alias);
    hideProcSpinner();

    if (result.exito) {
        status.style.background = 'var(--success-bg)';
        status.style.color      = 'var(--success)';
        status.textContent      = result.pendientes + ' comprobantes pendientes encontrados';
        _pendientesData         = result.comprobantes;
        mostrarTabla(result.comprobantes, result.pendientes);
    } else {
        status.style.background = 'var(--error-bg)';
        status.style.color      = 'var(--error)';
        status.textContent      = result.error;
    }
    if (typeof feather !== 'undefined') feather.replace();
}

// TASK-011: extraer tipo legible desde serie
function _tipoDesde(serie) {
    if (!serie) return '—';
    const s = serie.toUpperCase();
    if (s.startsWith('F'))  return 'Factura';
    if (s.startsWith('B'))  return 'Boleta';
    if (s.startsWith('FC') || s.startsWith('BC')) return 'N.Crédito';
    if (s.startsWith('FD') || s.startsWith('BD')) return 'N.Débito';
    return serie;
}

// TASK-011: badge de tipo
function _tipoBadge(serie) {
    const tipo = _tipoDesde(serie);
    const map  = {
        'Factura':    'badge-factura',
        'Boleta':     'badge-boleta',
        'N.Crédito':  'badge-nc',
        'N.Débito':   'badge-nd',
    };
    const cls = map[tipo] || 'badge-neutral';
    return '<span class="badge ' + cls + '">' + tipo + '</span>';
}

function mostrarTabla(comprobantes, total) {
    const tbody   = document.getElementById('preview-tbody');
    const counter = document.getElementById('proc-count');
    const preview = document.getElementById('preview-container');
    if (!tbody || !counter || !preview) return;

    counter.textContent = 'Mostrando ' + comprobantes.length + ' de ' + total + ' pendientes';

    // TASK-011: cabecera con columna Tipo
    const thead = document.querySelector('#preview-tbody').closest('table').querySelector('thead tr');
    if (thead && thead.children.length < 5) {
        // Insertar <th>Tipo</th> después de Comprobante
        const thTipo = document.createElement('th');
        thTipo.textContent = 'Tipo';
        thead.children[1].after(thTipo);
    }

    tbody.innerHTML = comprobantes.map((c, i) => {
        const totalHtml = c.total > 0
            ? '<strong>S/ ' + Number(c.total).toFixed(2) + '</strong>'
            : '<span style="color:var(--text-muted)">—</span>';
        return '<tr>' +
            '<td style="width:40px;"><input type="checkbox" class="comp-check" data-index="' + i + '" checked></td>' +
            '<td><strong>' + c.serie + '-' + String(c.numero).padStart(8, '0') + '</strong></td>' +
            '<td>' + _tipoBadge(c.serie) + '</td>' +
            '<td>' + (c.cliente || 'CLIENTES VARIOS') + '</td>' +
            '<td style="text-align:right;">' + totalHtml + '</td>' +
            '</tr>';
    }).join('');

    preview.style.display = 'block';
    if (typeof feather !== 'undefined') feather.replace();
}

function toggleAll(cb) {
    document.querySelectorAll('.comp-check').forEach(c => { c.checked = cb.checked; });
}

async function procesarConMotor() {
    if (!appState.clienteAlias) { showToast('No hay cliente configurado', 'error'); return; }

    const checks = document.querySelectorAll('.comp-check:checked');
    if (checks.length === 0) { showToast('Selecciona al menos un comprobante', 'warning'); return; }
    if (!confirm('¿Procesar ' + checks.length + ' comprobante(s) con el Motor?')) return;

    const btn = document.getElementById('btn-procesar');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i data-feather="loader"></i> Procesando...'; }
    if (typeof feather !== 'undefined') feather.replace();
    showProcSpinner('Enviando comprobantes...');

    const result = await window.pywebview.api.procesar_motor(appState.clienteAlias, null, 'mock');

    hideProcSpinner();
    if (btn) { btn.disabled = false; btn.innerHTML = '<i data-feather="play-circle"></i> Procesar con Motor'; }
    if (typeof feather !== 'undefined') feather.replace();

    if (result.exito) {
        mostrarResultado(result.resultados);
        await cargarDashboard();
    } else {
        showToast(result.error, 'error');
    }
}

function mostrarResultado(r) {
    const div = document.getElementById('proc-resultado');
    if (!div) return;
    div.style.display = 'block';
    const pc = document.getElementById('preview-container');
    if (pc) pc.style.display = 'none';
    div.innerHTML =
        '<div style="background:var(--success-bg);border:1px solid var(--success-border);border-radius:var(--radius-lg);padding:1.5rem;">' +
        '<h4 style="margin:0 0 1rem 0;color:var(--success);">Procesamiento completado</h4>' +
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem;">' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;">'                        + r.procesados + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Procesados</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--success);">'  + r.enviados   + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Enviados</div></div>'   +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--error);">'    + r.errores    + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Errores</div></div>'    +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--warning);">'  + r.ignorados  + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Ignorados</div></div>' +
        '</div><div style="display:flex;gap:0.75rem;">' +
        '<button class="btn btn-primary"   onclick="volverAProcesar()">Procesar más</button>' +
        '<button class="btn btn-secondary" onclick="navegarA(\'logs\')">Ver logs</button>' +
        '<button class="btn btn-secondary" onclick="navegarA(\'dashboard\')">Dashboard</button>' +
        '</div></div>';
}

function volverAProcesar() {
    const pr = document.getElementById('proc-resultado');    if (pr) pr.style.display = 'none';
    const ps = document.getElementById('proc-status');       if (ps) ps.style.display = 'none';
    const pc = document.getElementById('preview-container'); if (pc) pc.style.display = 'none';
    _pendientesData = [];
    cargarPendientesDesdeMotor();
}

function update_progress(current, total) {
    showToast('Procesando ' + current + '/' + total, 'info');
}
