/**
 * processor.js — DisateQ Motor CPE v5.0
 * TASK-004 JS: migrado eel -> window.pywebview.api
 * TASK-011: columna Tipo (B/F/NC/ND) en tabla de pendientes
 * TASK-013: label fuente muestra ruta real desde arranque
 * TASK-020: panel Reenvio Forzado por Rango
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

    // TASK-020: inyectar panel de reenvio forzado por rango
    _inyectarPanelReenvio();

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
        'Factura':   'badge-factura',
        'Boleta':    'badge-boleta',
        'N.Crédito': 'badge-nc',
        'N.Débito':  'badge-nd',
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

    const result = await window.pywebview.api.procesar_motor(appState.clienteAlias, null, null);

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

// =============================================================================
// TASK-020 — Reenvio Forzado por Rango
// =============================================================================

/**
 * Inyecta el panel de reenvio forzado en la pestana Procesar.
 * Se llama una vez desde initProcesar(). Si el panel ya existe no hace nada.
 */
function _inyectarPanelReenvio() {
    if (document.getElementById('panel-reenvio-rango')) return;

    // Buscar contenedor padre: seccion principal de la pestana procesar
    const contenedor = document.getElementById('proc-resultado')
        || document.getElementById('preview-container')
        || document.querySelector('.procesar-section')
        || document.querySelector('[data-tab="procesar"]');

    if (!contenedor) return;

    const panel = document.createElement('div');
    panel.id    = 'panel-reenvio-rango';
    panel.style.cssText = [
        'margin-top:1.5rem',
        'border:1px solid var(--border)',
        'border-radius:var(--radius-lg)',
        'overflow:hidden',
    ].join(';');

    panel.innerHTML =
        '<div id="reenvio-header" style="' +
            'display:flex;align-items:center;justify-content:space-between;' +
            'padding:0.75rem 1rem;background:var(--surface-2,var(--bg-secondary,#f5f5f5));' +
            'cursor:pointer;user-select:none;' +
        '" onclick="_togglePanelReenvio()">' +
            '<span style="font-weight:600;font-size:0.9rem;display:flex;align-items:center;gap:0.5rem;">' +
                '<i data-feather="refresh-cw" style="width:15px;height:15px;"></i>' +
                ' Reenvio Forzado por Rango' +
            '</span>' +
            '<i id="reenvio-chevron" data-feather="chevron-down" style="width:16px;height:16px;"></i>' +
        '</div>' +
        '<div id="reenvio-body" style="display:none;padding:1rem;">' +
            '<p style="margin:0 0 1rem 0;font-size:0.82rem;color:var(--text-muted);">' +
                'Marca comprobantes ya registrados para que el Motor los reenvie en el proximo ciclo. ' +
                'Solo afecta registros existentes en la base de datos.' +
            '</p>' +
            '<div style="display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:0.75rem;align-items:end;">' +
                '<div>' +
                    '<label style="display:block;font-size:0.8rem;font-weight:600;margin-bottom:0.3rem;">Serie</label>' +
                    '<input id="rr-serie" type="text" placeholder="B001" maxlength="4" ' +
                        'style="width:100%;padding:0.45rem 0.6rem;border:1px solid var(--border);' +
                        'border-radius:var(--radius);font-size:0.875rem;background:var(--input-bg,#fff);' +
                        'color:var(--text);" ' +
                        'oninput="this.value=this.value.toUpperCase()">' +
                '</div>' +
                '<div>' +
                    '<label style="display:block;font-size:0.8rem;font-weight:600;margin-bottom:0.3rem;">Desde</label>' +
                    '<input id="rr-desde" type="number" min="1" placeholder="1" ' +
                        'style="width:100%;padding:0.45rem 0.6rem;border:1px solid var(--border);' +
                        'border-radius:var(--radius);font-size:0.875rem;background:var(--input-bg,#fff);' +
                        'color:var(--text);">' +
                '</div>' +
                '<div>' +
                    '<label style="display:block;font-size:0.8rem;font-weight:600;margin-bottom:0.3rem;">' +
                        'Hasta <span style="font-weight:400;color:var(--text-muted);">(opcional)</span>' +
                    '</label>' +
                    '<input id="rr-hasta" type="number" min="1" placeholder="mismo que Desde" ' +
                        'style="width:100%;padding:0.45rem 0.6rem;border:1px solid var(--border);' +
                        'border-radius:var(--radius);font-size:0.875rem;background:var(--input-bg,#fff);' +
                        'color:var(--text);">' +
                '</div>' +
                '<div>' +
                    '<button id="btn-forzar-reenvio" class="btn btn-secondary" ' +
                        'onclick="forzarReenvioRango()" ' +
                        'style="white-space:nowrap;display:flex;align-items:center;gap:0.4rem;">' +
                        '<i data-feather="refresh-cw" style="width:14px;height:14px;"></i> Marcar' +
                    '</button>' +
                '</div>' +
            '</div>' +
            '<div id="rr-resultado" style="display:none;margin-top:0.75rem;padding:0.6rem 0.85rem;' +
                'border-radius:var(--radius);font-size:0.85rem;"></div>' +
        '</div>';

    // Insertar antes del primer elemento hijo del contenedor
    contenedor.parentNode.insertBefore(panel, contenedor.nextSibling);

    if (typeof feather !== 'undefined') feather.replace();
}

/** Abre/cierra el cuerpo del panel. */
function _togglePanelReenvio() {
    const body    = document.getElementById('reenvio-body');
    const chevron = document.getElementById('reenvio-chevron');
    if (!body) return;
    const visible = body.style.display !== 'none';
    body.style.display = visible ? 'none' : 'block';
    if (chevron) {
        chevron.setAttribute('data-feather', visible ? 'chevron-down' : 'chevron-up');
        if (typeof feather !== 'undefined') feather.replace();
    }
}

/**
 * TASK-020 — Llama a api.forzar_reenvio_rango y muestra el resultado.
 */
async function forzarReenvioRango() {
    const serie    = (document.getElementById('rr-serie')  || {}).value  || '';
    const desdeStr = (document.getElementById('rr-desde')  || {}).value  || '';
    const hastaStr = (document.getElementById('rr-hasta')  || {}).value  || '';
    const resultado = document.getElementById('rr-resultado');

    // Validacion basica en cliente
    if (!serie.trim()) {
        _mostrarRrResultado('error', 'Ingresa la Serie (ej: B001)');
        return;
    }
    if (!desdeStr || parseInt(desdeStr) <= 0) {
        _mostrarRrResultado('error', 'Ingresa un numero inicial valido');
        return;
    }

    const desde = parseInt(desdeStr);
    const hasta = hastaStr ? parseInt(hastaStr) : desde;

    if (hasta < desde) {
        _mostrarRrResultado('error', 'Hasta debe ser mayor o igual a Desde');
        return;
    }

    const btn = document.getElementById('btn-forzar-reenvio');
    if (btn) { btn.disabled = true; btn.textContent = 'Marcando...'; }

    try {
        const res = await window.pywebview.api.forzar_reenvio_rango({
            serie: serie.trim().toUpperCase(),
            desde: desde,
            hasta: hasta,
        });

        if (res.exito) {
            if (res.afectados === 0) {
                _mostrarRrResultado('warning',
                    'No se encontraron registros para ' + serie + ' ' + desde +
                    (hasta !== desde ? '-' + hasta : '') +
                    '. Verifica que los comprobantes existan en el historial.');
            } else {
                _mostrarRrResultado('success',
                    res.afectados + ' comprobante(s) marcados para reenvio (' +
                    serie + ' ' + desde + (hasta !== desde ? ' al ' + hasta : '') +
                    '). Se procesaran en el proximo ciclo del Motor.');
                // Limpiar campos tras exito
                document.getElementById('rr-serie').value  = '';
                document.getElementById('rr-desde').value  = '';
                document.getElementById('rr-hasta').value  = '';
            }
        } else {
            _mostrarRrResultado('error', res.error || 'Error desconocido');
        }
    } catch (e) {
        _mostrarRrResultado('error', 'Error de comunicacion: ' + e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i data-feather="refresh-cw" style="width:14px;height:14px;"></i> Marcar';
            if (typeof feather !== 'undefined') feather.replace();
        }
    }
}

/**
 * Muestra un mensaje de resultado dentro del panel de reenvio.
 * tipo: 'success' | 'warning' | 'error'
 */
function _mostrarRrResultado(tipo, mensaje) {
    const el = document.getElementById('rr-resultado');
    if (!el) return;
    const estilos = {
        success: 'background:var(--success-bg,#e6f4ea);color:var(--success,#1a7f37);border:1px solid var(--success-border,#a8d5b5);',
        warning: 'background:var(--warning-bg,#fff8e1);color:var(--warning,#b45309);border:1px solid var(--warning-border,#fcd34d);',
        error:   'background:var(--error-bg,#fef2f2);color:var(--error,#dc2626);border:1px solid var(--error-border,#fca5a5);',
    };
    el.style.cssText = 'display:block;margin-top:0.75rem;padding:0.6rem 0.85rem;' +
        'border-radius:var(--radius);font-size:0.85rem;' + (estilos[tipo] || estilos.error);
    el.textContent = mensaje;
}
