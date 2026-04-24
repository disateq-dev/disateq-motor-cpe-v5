/**
 * dashboard.js — Motor CPE DisateQ™ v4.0
 */

let chartEnvios = null;

async function cargarDashboard() {
  const stats = await eel.get_dashboard_stats()();
  
  // Stats
  document.getElementById('stat-pendientes').textContent = stats.total;
  document.getElementById('stat-aceptados').textContent = stats.enviados;
  document.getElementById('stat-rechazados').textContent = stats.fallidos;
  document.getElementById('stat-errores').textContent = stats.pendientes;
  document.getElementById('badge-pendientes').textContent = stats.total;
  
  // Gráfico
  cargarGrafico(stats.ultimos_7_dias);
  
  // Tabla
  cargarTablaRecientes();
}

function cargarGrafico(datos) {
  const ctx = document.getElementById('chart-envios').getContext('2d');
  
  if (chartEnvios) chartEnvios.destroy();
  
  chartEnvios = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
      datasets: [{
        label: 'Enviados',
        data: datos,
        borderColor: '#22c55e',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      }
    }
  });
}

async function cargarTablaRecientes() {
  const comprobantes = await eel.get_recent_comprobantes()();
  const tbody = document.getElementById('tabla-recientes');
  
  tbody.innerHTML = comprobantes.map(c => `
    <tr>
      <td><strong>${c.serie}-${c.numero.toString().padStart(8, '0')}</strong></td>
      <td>${c.fecha}</td>
      <td>${c.cliente}</td>
      <td>S/ ${c.total.toFixed(2)}</td>
      <td><span class="badge badge-${getBadgeClass(c.estado)}">${c.estado}</span></td>
    </tr>
  `).join('');
}

function getBadgeClass(estado) {
  const map = {
    'enviado': 'success',
    'pendiente': 'warning',
    'error': 'error'
  };
  return map[estado] || 'info';
}

function verTodos() {
  navegarA('historial');
}
