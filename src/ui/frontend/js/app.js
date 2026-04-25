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

// HISTORIAL
async function cargarHistorial() {
    const result = await eel.get_logs('ENVIADO', 200)();
    const page   = document.getElementById('page-historial');

    if (!result.exito) return;

    page.querySelector('.card-body').innerHTML = `
        <table class="table">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Serie-Número</th>
                    <th>Archivo</th>
                    <th>Duración</th>
                </tr>
            </thead>
            <tbody>
                ${result.logs.map(r => `
                    <tr>
                        <td>${r.fecha ? r.fecha.substring(0,19).replace('T',' ') : '-'}</td>
                        <td><strong>${r.serie}-${String(r.numero).padStart(8,'0')}</strong></td>
                        <td>${r.archivo_generado ? r.archivo_generado.split('\\').pop() : '-'}</td>
                        <td>${r.duracion_ms ? r.duracion_ms+'ms' : '-'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
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



