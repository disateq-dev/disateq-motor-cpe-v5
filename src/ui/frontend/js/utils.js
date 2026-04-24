/**
 * utils.js — Motor CPE DisateQ™ v4.0
 */

// Formateo
function formatCurrency(amount) {
  return `S/ ${parseFloat(amount).toFixed(2)}`;
}

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('es-PE');
}

function formatDateTime(dateStr) {
  const d = new Date(dateStr);
  return `${d.toLocaleDateString('es-PE')} ${d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}`;
}

// Loader
function showLoader(message = 'Cargando...') {
  const loader = document.createElement('div');
  loader.id = 'loader';
  loader.innerHTML = `
    <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                background: rgba(0,0,0,0.5); z-index: 9999; display: flex; 
                align-items: center; justify-content: center;">
      <div style="background: white; padding: 2rem; border-radius: 8px;">
        <p>${message}</p>
      </div>
    </div>
  `;
  document.body.appendChild(loader);
}

function hideLoader() {
  const loader = document.getElementById('loader');
  if (loader) loader.remove();
}
