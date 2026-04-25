/**
 * dashboard.js — Motor CPE DisateQ™ v4.0
 */

let chartEnvios = null;

async function cargarDashboard() {
    try {
        const empresa = await eel.get_empresa_info()();
        if (empresa) {
            const el    = document.getElementById('empresa-nombre');
            const ruc   = document.getElementById('empresa-ruc');
            const alias = document.getElementById('empresa-alias');
            if (el)    el.textContent    = empresa.nombre;
            if (ruc)   ruc.textContent   = empresa.ruc;
            if (alias) alias.textContent = empresa.alias ? empresa.alias.replace(/_/g,' ').toUpperCase() : '';
        }

        const stats = await eel.get_dashboard_stats()();
        document.getElementById('stat-remitidos').textContent  = stats.remitidos  || 0;
        document.getElementById('stat-errores').textContent    = stats.errores    || 0;
        document.getElementById('stat-ignorados').textContent  = stats.ignorados  || 0;

        cargarGrafico(stats.ultimos_7_dias || [0,0,0,0,0,0,0]);
        cargarTablaRecientes();
        verificarConexionAPI();

        eel.get_pendientes_fuente()().then(r => {
            const val = r ? (r.count || 0) : 0;
            document.getElementById('stat-pendientes').textContent  = val;
            document.getElementById('badge-pendientes').textContent = val;
        }).catch(() => {
            document.getElementById('stat-pendientes').textContent = '?';
        });

    } catch(e) {
        console.error('Error cargando dashboard:', e);
    }
}

function cargarGrafico(datos) {
    const canvas = document.getElementById('chart-envios');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (chartEnvios) chartEnvios.destroy();

    const labels = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        labels.push(d.toLocaleDateString('es-PE', {weekday:'short'}));
    }

    chartEnvios = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Remitidos',
                data: datos,
                backgroundColor: 'rgba(34,197,94,0.7)',
                borderColor: '#16a34a',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
        }
    });
}

async function cargarTablaRecientes() {
    try {
        const rows  = await eel.get_recent_comprobantes()();
        const tbody = document.getElementById('tabla-recientes');
        if (!tbody) return;

        if (!rows || rows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:1rem;color:var(--text-muted);">Sin comprobantes remitidos recientes</td></tr>';
            return;
        }

        tbody.innerHTML = rows.map(c => `
            <tr>
                <td><strong>${c.serie}-${String(c.numero).padStart(8,'0')}</strong></td>
                <td>${c.fecha}</td>
                <td>${c.cliente || 'CLIENTES VARIOS'}</td>
                <td>S/ ${Number(c.total || 0).toFixed(2)}</td>
                <td><span class="badge badge-success">remitido</span></td>
            </tr>
        `).join('');

    } catch(e) {
        console.error('Error cargando tabla recientes:', e);
    }
}

async function verificarConexionAPI() {
    try {
        const result = await eel.verificar_conexion_api()();
        const dot    = document.getElementById('api-status-dot');
        const label  = document.getElementById('api-status-label');
        if (!dot || !label) return;
        if (result && result.conectado) {
            dot.style.background = '#22c55e';
            label.textContent    = 'API: ' + (result.nombre || 'Conectada');
            label.style.color    = '#166534';
        } else {
            dot.style.background = '#ef4444';
            label.textContent    = 'API: Sin conexion';
            label.style.color    = '#991b1b';
        }
    } catch(e) {
        const dot   = document.getElementById('api-status-dot');
        const label = document.getElementById('api-status-label');
        if (dot)   dot.style.background = '#f59e0b';
        if (label) label.textContent    = 'API: verificando...';
    }
}

function getBadgeClass(estado) {
    const map = {
        'remitido':'success','enviado':'success',
        'pendiente':'warning','error':'error',
        'ignorado':'info','leido':'info','generado':'info'
    };
    return map[estado] || 'info';
}

function verTodos() { navegarA('historial'); }
