/**
 * dashboard.js — Motor CPE DisateQ™ v4.0
 */

let chartEnvios = null;

async function cargarDashboard() {
    try {
        // Info empresa
        const empresa = await eel.get_empresa_info()();
        if (empresa) {
            const el = document.getElementById('empresa-nombre');
            const ruc = document.getElementById('empresa-ruc');
            const alias = document.getElementById('empresa-alias');
            if (el) el.textContent = empresa.nombre;
            if (ruc) ruc.textContent = empresa.ruc;
            if (alias) alias.textContent = empresa.alias ? empresa.alias.replace(/_/g,' ').toUpperCase() : '';
        }

        // Stats
        const stats = await eel.get_dashboard_stats()();
        document.getElementById('stat-pendientes').textContent  = stats.total;
        document.getElementById('stat-aceptados').textContent   = stats.enviados;
        document.getElementById('stat-rechazados').textContent  = stats.fallidos;
        document.getElementById('stat-errores').textContent     = stats.fallidos;
        document.getElementById('badge-pendientes').textContent = stats.total;

        // Grafico
        cargarGrafico(stats.ultimos_7_dias);

        // Tabla recientes
        cargarTablaRecientes();

    } catch(e) {
        console.error('Error cargando dashboard:', e);
    }
}

function cargarGrafico(datos) {
    const ctx = document.getElementById('chart-envios').getContext('2d');
    if (chartEnvios) chartEnvios.destroy();

    const labels = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        labels.push(d.toLocaleDateString('es-PE', {weekday:'short'}));
    }

    chartEnvios = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Enviados',
                data: datos,
                borderColor: '#22c55e',
                backgroundColor: 'rgba(34,197,94,0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } }
            }
        }
    });
}

async function cargarTablaRecientes() {
    try {
        const rows = await eel.get_recent_comprobantes()();
        const tbody = document.getElementById('tabla-recientes');

        if (!rows || rows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-muted">Sin comprobantes recientes</td></tr>';
            return;
        }

        tbody.innerHTML = rows.map(c => `
            <tr>
                <td><strong>${c.serie}-${String(c.numero).padStart(8,'0')}</strong></td>
                <td>${c.fecha}</td>
                <td>${c.cliente}</td>
                <td>S/ ${Number(c.total).toFixed(2)}</td>
                <td><span class="badge badge-${getBadgeClass(c.estado)}">${c.estado}</span></td>
            </tr>
        `).join('');

    } catch(e) {
        console.error('Error cargando tabla:', e);
    }
}

function getBadgeClass(estado) {
    const map = { 'enviado':'success', 'pendiente':'warning', 'error':'error', 'ignorado':'info' };
    return map[estado] || 'info';
}

function verTodos() {
    navegarA('historial');
}


