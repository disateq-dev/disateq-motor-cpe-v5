/**
 * processor.js — Motor CPE DisateQ™ v4.0
 * Página Procesar — conectada al Motor orquestador
 */

let _pendientesData = [];

async function initProcesar() {
    const empresa = await eel.get_empresa_info()();
    const info = document.getElementById('proc-cliente-info');
    if (info && empresa) info.textContent = empresa.nombre + ' — RUC: ' + empresa.ruc;

    // Mostrar ruta antes de cargar
    const clientes = await eel.get_clientes_disponibles()();
    if (clientes.exito && clientes.clientes.length) {
        const rutaResult = await eel.get_ruta_fuente(clientes.clientes[0].alias)();
        const el = document.getElementById('archivo-seleccionado');
        if (el && rutaResult.ruta) {
            el.textContent = rutaResult.ruta;
            el.style.color = 'var(--text-primary)';
        }
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
    status.style.display = 'block';
    status.style.background = 'var(--info-bg)';
    status.style.color = 'var(--info)';
    status.textContent = 'Leyendo fuente configurada...';

    const clientes = await eel.get_clientes_disponibles()();
    if (!clientes.exito || !clientes.clientes.length) {
        hideProcSpinner();
        status.style.background = 'var(--error-bg)';
        status.style.color = 'var(--error)';
        status.textContent = 'No hay cliente configurado';
        return;
    }

    const cfg = clientes.clientes[0];
    const rutaResult = await eel.get_ruta_fuente(cfg.alias)();

    // Actualizar label de fuente
    const el = document.getElementById('archivo-seleccionado');
    if (el && rutaResult.ruta) {
        el.textContent = rutaResult.ruta;
        el.style.color = 'var(--text-primary)';
    }

    const result = await eel.conectar_fuente(cfg.tipo_fuente, rutaResult.ruta || cfg.alias)();
    hideProcSpinner();

    if (result.exito) {
        status.style.background = 'var(--success-bg)';
        status.style.color = 'var(--success)';
        status.textContent = result.pendientes + ' comprobantes pendientes encontrados';
        _pendientesData = result.comprobantes;
        mostrarTabla(result.comprobantes, result.pendientes);
    } else {
        status.style.background = 'var(--error-bg)';
        status.style.color = 'var(--error)';
        status.textContent = result.error;
    }
    feather.replace();
}

function mostrarTabla(comprobantes, total) {
    const tbody   = document.getElementById('preview-tbody');
    const counter = document.getElementById('proc-count');
    const preview = document.getElementById('preview-container');

    counter.textContent = 'Mostrando ' + comprobantes.length + ' de ' + total + ' pendientes';

    tbody.innerHTML = comprobantes.map(function(c, i) {
        const totalHtml = c.total > 0
            ? '<strong>S/ ' + Number(c.total).toFixed(2) + '</strong>'
            : '<span style="color:var(--text-muted)">—</span>';
        return '<tr>' +
            '<td style="width:40px;"><input type="checkbox" class="comp-check" data-index="' + i + '" checked></td>' +
            '<td><strong>' + c.serie + '-' + String(c.numero).padStart(8,'0') + '</strong></td>' +
            '<td>' + (c.cliente || 'CLIENTES VARIOS') + '</td>' +
            '<td style="text-align:right;">' + totalHtml + '</td>' +
            '</tr>';
    }).join('');

    preview.style.display = 'block';
    feather.replace();
}

function toggleAll(cb) {
    document.querySelectorAll('.comp-check').forEach(function(c) { c.checked = cb.checked; });
}

async function procesarConMotor() {
    if (!appState.clienteAlias) { showToast('No hay cliente configurado', 'error'); return; }

    const checks = document.querySelectorAll('.comp-check:checked');
    if (checks.length === 0) { showToast('Selecciona al menos un comprobante', 'warning'); return; }
    if (!confirm('Procesar ' + checks.length + ' comprobante(s) con el Motor?')) return;

    const btn = document.getElementById('btn-procesar');
    btn.disabled = true;
    btn.innerHTML = '<i data-feather="loader"></i> Procesando...';
    feather.replace();
    showProcSpinner('Enviando comprobantes...');

    const result = await eel.procesar_motor(appState.clienteAlias, null, 'mock')();

    hideProcSpinner();
    btn.disabled = false;
    btn.innerHTML = '<i data-feather="play-circle"></i> Procesar con Motor';
    feather.replace();

    if (result.exito) {
        mostrarResultado(result.resultados);
        await cargarDashboard();
    } else {
        showToast(result.error, 'error');
    }
}

function mostrarResultado(r) {
    const div = document.getElementById('proc-resultado');
    div.style.display = 'block';
    document.getElementById('preview-container').style.display = 'none';
    div.innerHTML =
        '<div style="background:var(--success-bg);border:1px solid var(--success-border);border-radius:var(--radius-lg);padding:1.5rem;">' +
        '<h4 style="margin:0 0 1rem 0;color:var(--success);">Procesamiento completado</h4>' +
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem;">' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;">' + r.procesados + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Procesados</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--success);">' + r.enviados + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Enviados</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--error);">' + r.errores + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Errores</div></div>' +
        '<div style="text-align:center;"><div style="font-size:2rem;font-weight:700;color:var(--warning);">' + r.ignorados + '</div><div style="font-size:0.8rem;color:var(--text-muted);">Ignorados</div></div>' +
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
    _pendientesData = [];
    cargarPendientesDesdeMotor();
}

eel.expose(update_progress);
function update_progress(current, total) {
    showToast('Procesando ' + current + '/' + total, 'info');
}
