/**
 * app.js — Motor CPE DisateQ™ v4.0
 */

let appState = {
    initialized: false,
    currentPage: 'dashboard',
    clienteAlias: null,
    archivoSeleccionado: null
};

// Interceptar cierre por botón X
window.addEventListener('beforeunload', (e) => {
    e.preventDefault();
    e.returnValue = '';
    return '';
});

// Interceptar cierre por botón X
window.addEventListener('beforeunload', (e) => {
    e.preventDefault();
    e.returnValue = '';
    return '';
});

// INIT
document.addEventListener('DOMContentLoaded', async () => {
    await inicializarSistema();
    configurarNavegacion();
    configurarReloj();
    feather.replace();
});

async function inicializarSistema() {
    const result = await eel.inicializar_sistema()();
    if (!result.success) {
        showToast(result.error || 'Error al inicializar', 'error');
        return;
    }

    // Cargar clientes disponibles
    const clientes = await eel.get_clientes_disponibles()();
    if (clientes.exito && clientes.clientes.length > 0) {
        appState.clienteAlias = clientes.clientes[0].alias;
    }

    appState.initialized = true;
    cargarDashboard();
}

// NAVEGACIÓN
function configurarNavegacion() {
    document.querySelectorAll('.tab-item').forEach(tab => {
        tab.addEventListener('click', () => navegarA(tab.dataset.page));
    });
}

function navegarA(page) {
    document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-page="${page}"]`).classList.add('active');
    document.querySelectorAll('.content-page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');
    appState.currentPage = page;

    if (page === 'dashboard') cargarDashboard();
    if (page === 'procesar')  initProcesar();
    if (page === 'logs')      cargarLogs();
    if (page === 'historial') cargarHistorial();
    if (page === 'config')    initConfig();
}

// RELOJ
function configurarReloj() {
    setInterval(() => {
        const now  = new Date();
        const fecha = now.toLocaleDateString('es-PE');
        const hora  = now.toLocaleTimeString('es-PE', {hour:'2-digit', minute:'2-digit'});
        document.getElementById('fecha-hora').textContent = `${fecha} ${hora}`;
    }, 1000);
}

// TOAST
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// LOADER
function showLoader(msg) {
    let loader = document.getElementById('loader-overlay');
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
    const loader = document.getElementById('loader-overlay');
    if (loader) loader.style.display = 'none';
}

// ACCIONES HEADER
async function procesarPendientes() {
    navegarA('procesar');
}

async function sincronizar() {
    showToast('Sincronizando...', 'info');
    await cargarDashboard();
    document.getElementById('ultima-sync').textContent =
        new Date().toLocaleTimeString('es-PE', {hour:'2-digit', minute:'2-digit'});
    showToast('Sincronización completada', 'success');
}

function abrirConfig() {
    navegarA('config');
}

// SELECCIÓN DE ARCHIVO/CARPETA
async function seleccionarArchivo() {
    const archivo = await eel.seleccionar_carpeta()();
    if (archivo) {
        document.getElementById('archivo-seleccionado').value = archivo;
        appState.archivoSeleccionado = archivo;
        await conectarYPreview(archivo);
    }
}

async function conectarYPreview(archivo) {
    showLoader('Conectando a fuente DBF...');
    const result = await eel.conectar_fuente('dbf', archivo)();
    hideLoader();

    if (result.exito) {
        showToast(`${result.pendientes} comprobantes encontrados`, 'success');
        mostrarPreview(result.comprobantes, result.pendientes);
    } else {
        showToast(result.error, 'error');
    }
}

function mostrarPreview(comprobantes, total) {
    const container = document.getElementById('preview-container');

    container.innerHTML = `
        <div style="margin-top:1rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
                <h4 style="margin:0;">Pendientes: <strong>${total}</strong> comprobantes</h4>
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="toggleAll(document.getElementById('select-all'))">
                        Seleccionar todos
                    </button>
                    <button class="btn btn-primary" onclick="procesarConMotor()" style="margin-left:0.5rem;">
                        <i data-feather="send"></i> Procesar con Motor
                    </button>
                </div>
            </div>
            <table class="table">
                <thead>
                    <tr>
                        <th><input type="checkbox" id="select-all" onchange="toggleAll(this)"></th>
                        <th>Serie-Número</th>
                        <th>Cliente</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${comprobantes.map((c, i) => `
                        <tr>
                            <td><input type="checkbox" class="comp-check" data-index="${i}"></td>
                            <td>${c.serie}-${String(c.numero).padStart(8,'0')}</td>
                            <td>${c.cliente || '-'}</td>
                            <td>S/ ${Number(c.total).toFixed(2)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            ${total > comprobantes.length ? `<p class="text-muted">Mostrando ${comprobantes.length} de ${total}. El Motor procesará todos los pendientes.</p>` : ''}
        </div>
    `;

    container.style.display = 'block';
    feather.replace();
}

function toggleAll(checkbox) {
    document.querySelectorAll('.comp-check').forEach(c => c.checked = checkbox.checked);
}

async function procesarConMotor() {
    if (!appState.clienteAlias) {
        showToast('No hay cliente configurado', 'error');
        return;
    }

    showLoader('Procesando comprobantes...');

    const result = await eel.procesar_motor(appState.clienteAlias, null, 'mock')();

    hideLoader();

    if (result.exito) {
        const r = result.resultados;
        showToast(`✅ ${r.enviados} enviados | ❌ ${r.errores} errores | ⏭ ${r.ignorados} ignorados`, 'success');
        await cargarDashboard();
        navegarA('logs');
    } else {
        showToast(result.error, 'error');
    }
}

// LOGS
async function cargarLogs() {
    try {
        const result = await eel.get_logs(null, 100)();
        const page = document.getElementById('page-logs');

        if (!result.exito) {
            page.querySelector('.card-body').innerHTML = `<p class="text-muted">${result.error}</p>`;
            return;
        }

        const logs = result.logs;
        page.querySelector('.card-body').innerHTML = `
            <div style="margin-bottom:0.75rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
                <button class="btn btn-sm btn-ghost" onclick="filtrarLogs(null)">Todos</button>
                <button class="btn btn-sm btn-ghost" onclick="filtrarLogs('ENVIADO')">Enviados</button>
                <button class="btn btn-sm btn-ghost" onclick="filtrarLogs('ERROR')">Errores</button>
                <button class="btn btn-sm btn-ghost" onclick="filtrarLogs('IGNORADO')">Ignorados</button>
            </div>
            <table class="table" id="tabla-logs">
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Serie-Número</th>
                        <th>Estado</th>
                        <th>Endpoint</th>
                        <th>Detalle</th>
                    </tr>
                </thead>
                <tbody>
                    ${logs.map(r => `
                        <tr>
                            <td>${r.fecha ? r.fecha.substring(0,19).replace('T',' ') : '-'}</td>
                            <td>${r.serie}-${String(r.numero).padStart(8,'0')}</td>
                            <td><span class="badge badge-${getBadgeClass(r.estado.toLowerCase())}">${r.estado}</span></td>
                            <td>${r.endpoint || '-'}</td>
                            <td>${r.detalle || '-'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch(e) {
        console.error('Error cargando logs:', e);
    }
}

async function filtrarLogs(estado) {
    const result = await eel.get_logs(estado, 100)();
    if (!result.exito) return;
    const tbody = document.querySelector('#tabla-logs tbody');
    if (!tbody) return;
    tbody.innerHTML = result.logs.map(r => `
        <tr>
            <td>${r.fecha ? r.fecha.substring(0,19).replace('T',' ') : '-'}</td>
            <td>${r.serie}-${String(r.numero).padStart(8,'0')}</td>
            <td><span class="badge badge-${getBadgeClass(r.estado.toLowerCase())}">${r.estado}</span></td>
            <td>${r.endpoint || '-'}</td>
            <td>${r.detalle || '-'}</td>
        </tr>
    `).join('');
}

// HISTORIAL CONSOLIDADO
async function cargarHistorial() {
    const page = document.getElementById('page-historial');
    page.querySelector('.card-body').innerHTML = '<p style="color:var(--text-muted)">Cargando...</p>';

    const result = await eel.get_historial(200)();
    if (!result.exito) {
        page.querySelector('.card-body').innerHTML = '<p style="color:var(--error)">Error cargando historial</p>';
        return;
    }

    const estadoColor = {
        'remitido':'#22c55e','error':'#ef4444',
        'ignorado':'#f59e0b','generado':'#3b82f6','leido':'#94a3b8'
    };

    page.querySelector('.card-body').innerHTML = `
        <div style="margin-bottom:0.75rem;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.85rem;color:var(--text-muted);">Total: <strong>${result.total}</strong> comprobantes</span>
            <div style="display:flex;gap:0.5rem;">
                <input type="text" id="hist-search" placeholder="Buscar serie o número..."
                    style="padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.85rem;"
                    oninput="filtrarHistorial(this.value)">
            </div>
        </div>
        <div style="max-height:500px;overflow-y:auto;border:1px solid var(--border-light);border-radius:var(--radius-md);">
            <table class="table" id="tabla-historial" style="margin:0;">
                <thead style="position:sticky;top:0;background:var(--bg-card);z-index:1;">
                    <tr>
                        <th>Comprobante</th>
                        <th>Fecha</th>
                        <th>Cliente</th>
                        <th>Total</th>
                        <th>Estado</th>
                        <th>Endpoint</th>
                    </tr>
                </thead>
                <tbody id="historial-tbody">
                    ${result.comprobantes.map(c => `
                        <tr>
                            <td><strong>${c.serie}-${String(c.numero).padStart(8,'0')}</strong></td>
                            <td>${c.fecha}</td>
                            <td>${c.cliente}</td>
                            <td>S/ ${Number(c.total).toFixed(2)}</td>
                            <td><span class="badge badge-${getBadgeClass(c.estado)}">${c.estado}</span></td>
                            <td>${c.endpoint}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function filtrarHistorial(query) {
    const rows = document.querySelectorAll('#historial-tbody tr');
    const q = query.toLowerCase();
    rows.forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}

function getBadgeClass(estado) {
    const map = {'enviado':'success','pendiente':'warning','error':'error','ignorado':'info','leido':'info','generado':'info'};
    return map[estado] || 'info';
}

async function cerrarApp() {
    if (confirm('¿Cerrar Motor CPE DisateQ™?')) {
        try {
            await eel.cerrar_sistema()();
        } catch(e) {}
        window.close();
    }
}





// ================================================================
// CONFIGURACION
// ================================================================

let _configDesbloqueada = false;

async function initConfig() {
    if (_configDesbloqueada) {
        await mostrarConfigCompleta();
    } else {
        mostrarLockConfig();
    }
}

function mostrarLockConfig() {
    const page = document.getElementById('page-config');
    page.querySelector('.card-body').innerHTML = `
        <div style="max-width:320px;margin:2rem auto;text-align:center;">
            <div style="font-size:3rem;margin-bottom:1rem;">&#128274;</div>
            <h3 style="margin-bottom:0.5rem;">Acceso Restringido</h3>
            <p style="color:var(--text-muted);margin-bottom:1.5rem;font-size:0.875rem;">
                Esta seccion requiere clave del tecnico instalador.
            </p>
            <div style="display:flex;gap:0.5rem;justify-content:center;margin-bottom:1rem;">
                ${[0,1,2,3].map(i => '<input type="password" maxlength="1" id="pin-'+i+'" style="width:48px;height:48px;text-align:center;font-size:1.5rem;border:2px solid var(--border-medium);border-radius:var(--radius-md);outline:none;" oninput="onPinInput('+i+', this)" onkeydown="onPinKey(event, '+i+')">').join('')}
            </div>
            <button class="btn btn-primary" onclick="verificarPin()" style="width:100%;">Acceder</button>
            <div id="pin-error" style="color:var(--error);margin-top:0.75rem;font-size:0.875rem;display:none;">Clave incorrecta</div>
        </div>
    `;
    setTimeout(() => document.getElementById('pin-0')?.focus(), 100);
}

function onPinInput(idx, input) {
    input.value = input.value.replace(/[^0-9]/g, '');
    if (input.value && idx < 3) document.getElementById('pin-' + (idx+1))?.focus();
    if (idx === 3 && input.value) verificarPin();
}

function onPinKey(e, idx) {
    if (e.key === 'Backspace' && !e.target.value && idx > 0)
        document.getElementById('pin-' + (idx-1))?.focus();
}

async function verificarPin() {
    const clave = [0,1,2,3].map(i => document.getElementById('pin-'+i)?.value || '').join('');
    if (clave.length < 4) return;
    const result = await eel.verificar_clave_instalador(clave)();
    if (result.valida) {
        _configDesbloqueada = true;
        await mostrarConfigCompleta();
    } else {
        document.getElementById('pin-error').style.display = 'block';
        [0,1,2,3].forEach(i => { const el = document.getElementById('pin-'+i); if (el) { el.value = ''; el.style.borderColor = 'var(--error)'; } });
        setTimeout(() => { document.getElementById('pin-0')?.focus(); [0,1,2,3].forEach(i => { const el = document.getElementById('pin-'+i); if (el) el.style.borderColor = 'var(--border-medium)'; }); }, 1000);
    }
}

async function mostrarConfigCompleta() {
    const page = document.getElementById('page-config');
    const result = await eel.get_config_cliente()();
    if (!result.exito) { page.querySelector('.card-body').innerHTML = '<p style="color:var(--error)">Error</p>'; return; }
    const d = result;
    const series = d.series || {};
    const creds = d.envio?.api_tercero?.credenciales || {};

    const renderSeries = (tipo, lista) => {
        if (!lista || !lista.length) return '<span style="color:var(--text-muted);font-size:0.85rem;">Sin series</span>';
        return lista.map((s, i) => '<div style="display:flex;align-items:center;gap:0.75rem;padding:0.5rem;background:' + (s.activa ? '#f0fdf4' : '#f9fafb') + ';border:1px solid ' + (s.activa ? '#86efac' : '#e5e7eb') + ';border-radius:var(--radius-md);margin-bottom:0.4rem;"><strong style="min-width:60px;">' + s.serie + '</strong><span style="color:var(--text-muted);font-size:0.8rem;">desde:</span><input type="number" value="' + s.correlativo_inicio + '" id="serie-' + tipo + '-' + i + '-corr" style="width:80px;padding:0.25rem 0.5rem;border:1px solid var(--border-medium);border-radius:4px;font-size:0.85rem;"><label style="display:flex;align-items:center;gap:0.3rem;cursor:pointer;font-size:0.85rem;"><input type="checkbox" id="serie-' + tipo + '-' + i + '-activa" ' + (s.activa ? 'checked' : '') + '> Activa</label></div>').join('');
    };

    page.querySelector('.card-body').innerHTML =
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">' +
        '<span style="color:var(--success);font-size:0.875rem;">Modo tecnico activo</span>' +
        '<button class="btn btn-secondary" onclick="bloquearConfig()" style="font-size:0.8rem;">Bloquear</button></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Empresa</h3><span style="font-size:0.75rem;color:var(--text-muted);background:#f3f4f6;padding:2px 8px;border-radius:10px;">Solo lectura parcial</span></div><div class="card-body"><div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">' +
        '<div><label style="font-size:0.75rem;color:var(--text-muted);">RUC</label><p style="font-weight:600;font-family:monospace;">' + d.empresa.ruc + '</p></div>' +
        '<div><label style="font-size:0.75rem;color:var(--text-muted);">Razon Social</label><p style="font-weight:600;">' + d.empresa.razon_social + '</p></div>' +
        '<div><label style="font-size:0.75rem;color:var(--text-muted);">Nombre Comercial</label><input type="text" id="cfg-nombre-comercial" value="' + (d.empresa.nombre_comercial||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;"></div>' +
        '<div><label style="font-size:0.75rem;color:var(--text-muted);">Alias / Local</label><input type="text" id="cfg-alias" value="' + (d.empresa.alias||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;"></div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Fuente de Datos</h3><span style="font-size:0.75rem;color:var(--text-muted);background:#f3f4f6;padding:2px 8px;border-radius:10px;">Solo lectura</span></div><div class="card-body"><div style="display:grid;grid-template-columns:120px 1fr;gap:1rem;align-items:start;">' +
        '<div><label style="font-size:0.75rem;color:var(--text-muted);">Tipo</label><p style="font-weight:700;text-transform:uppercase;color:var(--blue-600);">' + (d.fuente.tipo||'-') + '</p></div>' +
        '<div><label style="font-size:0.75rem;color:var(--text-muted);">Ruta(s)</label>' + (d.fuente.rutas||[]).map(r => '<p style="font-family:monospace;font-size:0.82rem;background:#f8fafc;padding:0.3rem 0.6rem;border-radius:4px;margin-top:0.25rem;">' + r + '</p>').join('') + '</div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Series y Correlativos</h3><span style="font-size:0.75rem;color:var(--success);background:#dcfce7;padding:2px 8px;border-radius:10px;">Editable</span></div><div class="card-body"><div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;">' +
        '<div><label style="font-size:0.75rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;display:block;margin-bottom:0.5rem;">Boletas</label>' + renderSeries('boleta', series.boleta) + '</div>' +
        '<div><label style="font-size:0.75rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;display:block;margin-bottom:0.5rem;">Facturas</label>' + renderSeries('factura', series.factura) + '</div>' +
        '<div><label style="font-size:0.75rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;display:block;margin-bottom:0.5rem;">Notas Credito</label>' + renderSeries('nota_credito', series.nota_credito) + '</div>' +
        '<div><label style="font-size:0.75rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;display:block;margin-bottom:0.5rem;">Notas Debito</label>' + renderSeries('nota_debito', series.nota_debito) + '</div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Configuracion de Envio</h3><span style="font-size:0.75rem;color:var(--success);background:#dcfce7;padding:2px 8px;border-radius:10px;">Editable</span></div><div class="card-body"><div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">' +
        '<div style="grid-column:span 2;"><label style="font-size:0.75rem;color:var(--text-muted);">URL Endpoint</label><input type="text" id="cfg-url" value="' + (d.envio?.api_tercero?.url||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.85rem;font-family:monospace;"></div>' +
        '<div><label style="font-size:0.75rem;color:var(--text-muted);">Usuario API</label><input type="text" id="cfg-usuario" value="' + (creds.usuario||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;"></div>' +
        '<div><label style="font-size:0.75rem;color:var(--text-muted);">Token / Clave API</label><input type="password" id="cfg-token" value="' + (creds.token||'') + '" placeholder="..." style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;"></div>' +
        '</div></div></div>' +

        '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Clave del Instalador</h3><span style="font-size:0.75rem;color:var(--success);background:#dcfce7;padding:2px 8px;border-radius:10px;">Editable</span></div><div class="card-body"><div style="display:flex;gap:1rem;align-items:flex-end;max-width:400px;">' +
        '<div style="flex:1;"><label style="font-size:0.75rem;color:var(--text-muted);">Nueva clave (4 digitos)</label><input type="password" id="cfg-clave-nueva" maxlength="4" placeholder="..." style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:1rem;letter-spacing:0.5rem;"></div>' +
        '<div style="flex:1;"><label style="font-size:0.75rem;color:var(--text-muted);">Confirmar clave</label><input type="password" id="cfg-clave-confirma" maxlength="4" placeholder="..." style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:1rem;letter-spacing:0.5rem;"></div>' +
        '</div></div></div>' +

        '<div style="display:flex;gap:0.75rem;justify-content:flex-end;padding-top:0.5rem;">' +
        '<button class="btn btn-secondary" onclick="bloquearConfig()">Cancelar</button>' +
        '<button class="btn btn-primary" onclick="guardarConfig()">Guardar Cambios</button></div>' +
        '<div id="cfg-mensaje" style="text-align:right;margin-top:0.5rem;font-size:0.85rem;display:none;"></div>';
}

async function guardarConfig() {
    const nueva    = document.getElementById('cfg-clave-nueva')?.value || '';
    const confirma = document.getElementById('cfg-clave-confirma')?.value || '';
    const msg      = document.getElementById('cfg-mensaje');
    if (nueva && nueva !== confirma) { msg.style.display='block'; msg.style.color='var(--error)'; msg.textContent='Las claves no coinciden'; return; }
    if (nueva && !/^\d{4}$/.test(nueva)) { msg.style.display='block'; msg.style.color='var(--error)'; msg.textContent='La clave debe ser 4 digitos'; return; }
    const payload = {
        nombre_comercial: document.getElementById('cfg-nombre-comercial')?.value || '',
        alias:            document.getElementById('cfg-alias')?.value || '',
        url:              document.getElementById('cfg-url')?.value || '',
        usuario:          document.getElementById('cfg-usuario')?.value || '',
        token:            document.getElementById('cfg-token')?.value || '',
        clave_nueva:      nueva || null
    };
    const result = await eel.guardar_config(payload)();
    msg.style.display = 'block';
    if (result.exito) {
        msg.style.color = 'var(--success)';
        msg.textContent = 'Configuracion guardada correctamente';
        setTimeout(() => mostrarConfigCompleta(), 1500);
    } else {
        msg.style.color = 'var(--error)';
        msg.textContent = 'Error: ' + result.error;
    }
}

function bloquearConfig() {
    _configDesbloqueada = false;
    mostrarLockConfig();
}
