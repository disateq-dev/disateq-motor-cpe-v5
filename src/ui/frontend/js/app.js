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
  }
}
