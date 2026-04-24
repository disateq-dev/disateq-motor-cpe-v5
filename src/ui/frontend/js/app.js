/**
 * app.js — Motor CPE DisateQ™ v4.0
 */

let appState = {
  initialized: false,
  currentPage: 'dashboard'
};

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
    showToast(result.error, 'error');
    return;
  }
  
  appState.initialized = true;
  cargarDashboard();
}

// NAVEGACIÓN
function configurarNavegacion() {
  document.querySelectorAll('.tab-item').forEach(tab => {
    tab.addEventListener('click', () => {
      const page = tab.dataset.page;
      navegarA(page);
    });
  });
}

function navegarA(page) {
  // Tabs
  document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
  document.querySelector(`[data-page="${page}"]`).classList.add('active');
  
  // Pages
  document.querySelectorAll('.content-page').forEach(p => p.classList.remove('active'));
  document.getElementById(`page-${page}`).classList.add('active');
  
  appState.currentPage = page;
  
  // Cargar datos
  if (page === 'dashboard') cargarDashboard();
}

// RELOJ
function configurarReloj() {
  setInterval(() => {
    const now = new Date();
    const fecha = now.toLocaleDateString('es-PE');
    const hora = now.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
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

// ACCIONES
async function procesarPendientes() {
  navegarA('procesar');
}

async function sincronizar() {
  showToast('Sincronizando...', 'info');
  await cargarDashboard();
  showToast('Sincronización completada', 'success');
}

function abrirConfig() {
  navegarA('config');
}

async function seleccionarArchivo() {
  const archivo = await eel.seleccionar_archivo()();
  if (archivo) {
    document.getElementById('archivo-seleccionado').value = archivo;
    showToast('Archivo cargado', 'success');
    
    // Auto-cargar preview
    await conectarYPreview(archivo);
  }
}

async function conectarYPreview(archivo) {
  showLoader('Conectando a fuente...');
  
  const tipo = archivo.endsWith('.xlsx') ? 'xlsx' : 'dbf';
  const result = await eel.conectar_fuente(tipo, archivo)();
  
  hideLoader();
  
  if (result.exito) {
    showToast(`${result.pendientes} comprobantes encontrados`, 'success');
    mostrarPreview(result.comprobantes);
  } else {
    showToast(result.error, 'error');
  }
}

function mostrarPreview(comprobantes) {
  const container = document.getElementById('preview-container');
  
  if (!comprobantes || comprobantes.length === 0) {
    container.style.display = 'none';
    return;
  }
  
  container.innerHTML = `
    <h4>Comprobantes Pendientes (${comprobantes.length})</h4>
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
            <td>${c.serie}-${String(c.numero).padStart(8, '0')}</td>
            <td>${c.cliente}</td>
            <td>S/ ${c.total.toFixed(2)}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <button class="btn btn-primary" onclick="procesarSeleccionados()">
      Procesar Seleccionados
    </button>
  `;
  
  container.style.display = 'block';
}

function toggleAll(checkbox) {
  document.querySelectorAll('.comp-check').forEach(c => c.checked = checkbox.checked);
}

async function procesarSeleccionados() {
  const checks = document.querySelectorAll('.comp-check:checked');
  
  if (checks.length === 0) {
    showToast('Selecciona al menos un comprobante', 'warning');
    return;
  }
  
  showToast(`Procesando ${checks.length} comprobantes...`, 'info');
  
  // TODO: Llamar a eel.procesar_comprobantes()
}
