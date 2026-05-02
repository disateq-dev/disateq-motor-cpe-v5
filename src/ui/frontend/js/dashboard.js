/**
 * dashboard.js — DisateQ Motor CPE v5.0
 * TASK-004 JS: migrado eel → window.pywebview.api
 */

'use strict';

let chartEnvios = null;

async function cargarDashboard() {
    try {
        const empresa = await window.pywebview.api.get_empresa_info();
        if (empresa) {
            const el    = document.getElementById('empresa-nombre');
            const ruc   = document.getElementById('empresa-ruc');
            const alias = document.getElementById('empresa-alias');
            if (el)    el.textContent    = empresa.nombre;
            if (ruc)   ruc.textContent   = empresa.ruc;
            if (alias) alias.textContent = empresa.alias
                ? empresa.alias.replace(/_/g,' ').toUpperCase()
                : '';
        }

        const stats = await window.pywebview.api.get_dashboard_stats();
        const eRem  = document.getElementById('stat-remitidos');
        const eErr  = document.getElementById('stat-errores');
        const eIgn  = document.getElementById('stat-ignorados');
        if (eRem) eRem.textContent = stats.remitidos  || 0;
        if (eErr) eErr.textContent = stats.errores    || 0;
        if (eIgn) eIgn.textContent = stats.ignorados  || 0;

        cargarGrafico(stats.ultimos_7_dias || [0,0,0,0,0,0,0]);
        cargarTablaRecientes();
        verificarConexionAPI();

        window.pywebview.api.get_pendientes_fuente().then(r => {
            const val = r ? (r.count || 0) : 0;
            const ep  = document.getElementById('stat-pendientes');
            const eb  = document.getElementById('badge-pendientes');
            if (ep) ep.textContent = val;
            if (eb) eb.textContent = val;
        }).catch(() => {
            const ep = document.getElementById('stat-pendientes');
            if (ep) ep.textContent = '?';
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
        labels.push(d.toLocaleDateString('es-PE', { weekday: 'short' }));
    }

    chartEnvios = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label:           'Remitidos',
                data:            datos,
                backgroundColor: 'rgba(34,197,94,0.7)',
                borderColor:     '#16a34a',
                borderWidth:     1,
                borderRadius:    4,
            }],
        },
        options: {
            responsive:          true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales:  { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
        },
    });
}

async function cargarTablaRecientes() {
    try {
        const rows  = await window.pywebview.api.get_recent_comprobantes();
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
                <td style="text-align:right;"><span class="badge badge-success">remitido</span></td>
            </tr>
        `).join('');

    } catch(e) {
        console.error('Error cargando tabla recientes:', e);
    }
}

async function verificarConexionAPI() {
    try {
        const result = await window.pywebview.api.verificar_conexion_api();
        const dot    = document.getElementById('api-status-dot');
        const label  = document.getElementById('api-status-label');
        if (!dot || !label) return;
        if (result && result.conectado) {
            dot.style.background = '#22c55e';
            label.textContent    = 'API: ' + (result.nombre || 'Conectada');
            label.style.color    = '#166534';
        } else {
            dot.style.background = '#ef4444';
            label.textContent    = 'API: Sin conexión';
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
        remitido:'success', enviado:'success',
        pendiente:'warning', error:'error',
        ignorado:'info', leido:'info', generado:'info',
    };
    return map[estado] || 'info';
}

function verTodos() { navegarA('historial'); }
