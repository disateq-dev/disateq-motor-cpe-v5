/**
 * processor.js — Motor CPE DisateQ™ v4.0
 * Página Procesar — conectada al Motor orquestador
 */

let _pendientesData = [];

// Cargar info cliente al entrar a la página
async function initProcesar() {
    const empresa = await eel.get_empresa_info()();
    const info = document.getElementById('proc-cliente-info');
    if (info && empresa) {
        info.textContent = `${empresa.nombre} — RUC: ${empresa.ruc}`;
    }

    // Auto-cargar pendientes desde config cliente
    await cargarPendientesDesdeMotor();
}

async function seleccionarArchivo() {
    const carpeta = await eel.seleccionar_carpeta()();
    if (carpeta) {
        document.getElementById('archivo-seleccionado').value = carpeta;
        appState.archivoSeleccionado = carpeta;
        await cargarPendientes();
    }
}

async function cargarPendientes() {
    const archivo = document.getElementById('archivo-seleccionado').value;
    const status  = document.getElementById('proc-status');
    const preview = document.getElementById('preview-container');

    if (!archivo || archivo === 'Configurado en cliente YAML') {
        // Usar config del cliente directamente
        await cargarPendientesDesdeMotor();
        return;
    }

    status.style.display = 'block';
    status.style.background = '#dbeafe';
    status.style.color = '#1e40af';
    status.textContent = '⏳ Conectando a fuente de datos...';
    preview.style.display = 'none';

    const result = await eel.conectar_fuente('dbf', archivo)();

    if (result.exito) {
        status.style.background = '#dcfce7';
        status.style.color = '#166534';
        status.textContent = `✅ ${result.pendientes} comprobantes pendientes encontrados`;
        _pendientesData = result.comprobantes;
        mostrarTabla(result.comprobantes, result.pendientes);
    } else {
        status.style.background = '#fee2e2';
        status.style.color = '#991b1b';
        status.textContent = `❌ ${result.error}`;
    }

    feather.replace();
}

async function cargarPendientesDesdeMotor() {
    const status = document.getElementById('proc-status');
    status.style.display = 'block';
    status.style.background = '#dbeafe';
    status.style.color = '#1e40af';
    status.textContent = '⏳ Leyendo fuente configurada...';

    const clientes = await eel.get_clientes_disponibles()();
    if (!clientes.exito || !clientes.clientes.length) {
        status.style.background = '#fee2e2';
        status.style.color = '#991b1b';
        status.textContent = '❌ No hay cliente configurado';
        return;
    }

    const cfg = clientes.clientes[0];

    // Obtener ruta real desde config
    const rutaResult = await eel.get_ruta_fuente(cfg.alias)();
    const input = document.getElementById('archivo-seleccionado');
    if (input && rutaResult.ruta) input.value = rutaResult.ruta;

    const result = await eel.conectar_fuente(cfg.tipo_fuente, rutaResult.ruta || cfg.alias)();

    if (result.exito) {
        status.style.background = '#dcfce7';
        status.style.color = '#166534';
        status.textContent = `✅ ${result.pendientes} comprobantes pendientes encontrados`;
        _pendientesData = result.comprobantes;
        mostrarTabla(result.comprobantes, result.pendientes);
    } else {
        status.style.background = '#fee2e2';
        status.style.color = '#991b1b';
        status.textContent = `❌ ${result.error}`;
    }
    feather.replace();
}

function mostrarTabla(comprobantes, total) {
    const tbody   = document.getElementById('preview-tbody');
    const counter = document.getElementById('proc-count');
    const preview = document.getElementById('preview-container');

    counter.textContent = `Mostrando ${comprobantes.length} de ${total} pendientes`;

    tbody.innerHTML = comprobantes.map((c, i) => `
        <tr>
            <td><input type="checkbox" class="comp-check" data-index="${i}" checked></td>
            <td><strong>${c.serie}-${String(c.numero).padStart(8,'0')}</strong></td>
            <td>${c.cliente || 'CLIENTES VARIOS'}</td>
            <td>S/ ${Number(c.total || 0).toFixed(2)}</td>
        </tr>
    `).join('');

    preview.style.display = 'block';
    feather.replace();
}

function toggleAll(cb) {
    document.querySelectorAll('.comp-check').forEach(c => c.checked = cb.checked);
}

async function procesarConMotor() {
    if (!appState.clienteAlias) {
        showToast('No hay cliente configurado', 'error');
        return;
    }

    const checks = document.querySelectorAll('.comp-check:checked');
    if (checks.length === 0) {
        showToast('Selecciona al menos un comprobante', 'warning');
        return;
    }

    if (!confirm(`¿Procesar ${checks.length} comprobante(s) con el Motor?`)) return;

    const btnProcesar = document.getElementById('btn-procesar');
    btnProcesar.disabled = true;
    btnProcesar.innerHTML = '<i data-feather="loader"></i> Procesando...';
    feather.replace();

    showToast('Procesando comprobantes...', 'info');

    const result = await eel.procesar_motor(appState.clienteAlias, null, 'mock')();

    btnProcesar.disabled = false;
    btnProcesar.innerHTML = '<i data-feather="play-circle"></i> Procesar con Motor';
    feather.replace();

    if (result.exito) {
        const r = result.resultados;
        mostrarResultado(r);
        await cargarDashboard();
    } else {
        showToast(result.error, 'error');
    }
}

function mostrarResultado(r) {
    const div = document.getElementById('proc-resultado');
    div.style.display = 'block';
    document.getElementById('preview-container').style.display = 'none';

    const color_env  = r.enviados > 0 ? '#166534' : '#6b7280';
    const color_err  = r.errores  > 0 ? '#991b1b' : '#6b7280';
    const color_ign  = r.ignorados> 0 ? '#92400e' : '#6b7280';

    div.innerHTML = `
        <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:1.5rem;">
            <h4 style="margin:0 0 1rem 0;color:#166534;">✅ Procesamiento completado</h4>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem;">
                <div style="text-align:center;">
                    <div style="font-size:2rem;font-weight:700;color:#1e293b;">${r.procesados}</div>
                    <div style="font-size:0.8rem;color:var(--text-muted);">Procesados</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:2rem;font-weight:700;color:${color_env};">${r.enviados}</div>
                    <div style="font-size:0.8rem;color:var(--text-muted);">Enviados</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:2rem;font-weight:700;color:${color_err};">${r.errores}</div>
                    <div style="font-size:0.8rem;color:var(--text-muted);">Errores</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:2rem;font-weight:700;color:${color_ign};">${r.ignorados}</div>
                    <div style="font-size:0.8rem;color:var(--text-muted);">Ignorados</div>
                </div>
            </div>
            <div style="display:flex;gap:0.75rem;">
                <button class="btn btn-primary" onclick="volverAProcesar()">
                    <i data-feather="refresh-cw"></i> Procesar más
                </button>
                <button class="btn btn-secondary" onclick="navegarA('logs')">
                    <i data-feather="list"></i> Ver logs
                </button>
                <button class="btn btn-secondary" onclick="navegarA('dashboard')">
                    <i data-feather="activity"></i> Dashboard
                </button>
            </div>
        </div>
    `;
    feather.replace();
}

function volverAProcesar() {
    document.getElementById('proc-resultado').style.display = 'none';
    document.getElementById('proc-status').style.display = 'none';
    document.getElementById('preview-container').style.display = 'none';
    _pendientesData = [];
    cargarPendientesDesdeMotor();
}

// Exponer función de progreso a Python
eel.expose(update_progress);
function update_progress(current, total) {
    const pct = Math.round((current / total) * 100);
    showToast(`Procesando ${current}/${total} (${pct}%)`, 'info');
}



