/**
 * dashboard.js — DisateQ CPE™ v5.0
 * Rediseño FIX-UI-07: glosario oficial + nuevos componentes
 */

'use strict';

// ============================================================
//  INIT
// ============================================================
async function cargarDashboard() {
  try {
    await Promise.all([
      cargarEmpresa(),
      cargarStats(),
      cargarFeed(),
      cargarScheduler(),
      verificarConexion(),
    ]);
  } catch(e) {
    console.error('[Dashboard] Error:', e);
  }
}

// ============================================================
//  EMPRESA
// ============================================================
async function cargarEmpresa() {
  try {
    const e = await window.pywebview.api.get_empresa_info();
    if (!e) return;

    // Header empresa
    const nc  = document.getElementById('empresa-nombre-comercial');
    const rs  = document.getElementById('empresa-razon-social');
    const ruc = document.getElementById('empresa-ruc');
    if (nc)  nc.textContent  = e.nombre_comercial || e.nombre || '—';
    if (rs)  rs.textContent  = e.razon_social     || e.nombre || '—';
    if (ruc) ruc.textContent = 'RUC ' + (e.ruc || '—');

  } catch(e) { console.error('[Dashboard] cargarEmpresa:', e); }
}

// ============================================================
//  STATS + PIPELINE + DONUT
// ============================================================
async function cargarStats() {
  try {
    const s = await window.pywebview.api.get_dashboard_stats();
    if (!s) return;

    const detectados  = s.pendientes  || 0;
    const entregados  = s.remitidos   || 0;
    const enEspera    = s.ignorados   || 0;
    const conProblema = s.errores     || 0;
    const noProcesados= s.abandonados || 0;
    const total       = detectados;

    // Stat cards — glosario oficial
    _setText('stat-pendientes',  detectados);
    _setText('stat-remitidos',   entregados);
    _setText('stat-ignorados',   enEspera);
    _setText('stat-errores',     conProblema);
    _setText('stat-abandonados', noProcesados);

    // Colorear con problema si > 0
    const elProblema = document.getElementById('stat-errores');
    if (elProblema) elProblema.style.color = conProblema > 0 ? 'var(--error)' : '';
    const elNoProcesados = document.getElementById('stat-abandonados');
    if (elNoProcesados) elNoProcesados.style.color = noProcesados > 0 ? 'var(--error)' : '';

    // Badge pendientes tab
    actualizarStatPendientes(detectados);

    // Badge eventos tab
    const badgeEv = document.getElementById('badge-eventos');
    if (badgeEv) {
      badgeEv.textContent   = conProblema;
      badgeEv.style.display = conProblema > 0 ? 'inline-flex' : 'none';
    }

    // Pipeline
    _setText('pipe-origen',    detectados);
    _setText('pipe-lectura',   detectados);
    _setText('pipe-transform', detectados);
    _setText('pipe-generado',  detectados);
    _setText('pipe-entrega',   entregados + conProblema);
    _setText('pipe-respuesta', entregados);

    // Colorear respuesta
    const elResp = document.getElementById('pipe-respuesta');
    if (elResp) {
      elResp.className = 'pipe-count ' + (conProblema > 0 ? 'warning' : 'success');
    }

    // Sparklines
    const hist = s.ultimos_7_dias || [0,0,0,0,0,0,0];
    ['origen','lectura','transform','generado'].forEach(id => renderSpark('spark-' + id, hist, 'var(--navy-400)'));
    renderSpark('spark-entrega',   hist, 'var(--amber-500)');
    renderSpark('spark-respuesta', hist, 'var(--success-light)');

    // Estado global
    actualizarEstadoGlobal(conProblema, enEspera, noProcesados);

    // Donut
    actualizarDonut(entregados, enEspera, conProblema, total);

    // Alertas panel
    actualizarAlertas(conProblema, enEspera, noProcesados);

    // Panel estado servicio
    _setText('ps-cola', enEspera > 0 ? enEspera + ' pendientes' : '0 pendientes');
    const psColaEl = document.getElementById('ps-cola');
    if (psColaEl) psColaEl.className = 'panel-stat-value ' + (enEspera > 0 ? 'warning' : 'ok');

    _setText('ps-reintentos', conProblema > 0 ? conProblema + ' activos' : '0');
    const psReinEl = document.getElementById('ps-reintentos');
    if (psReinEl) psReinEl.className = 'panel-stat-value ' + (conProblema > 0 ? 'warning' : 'ok');

    // Sched procesados
    _setText('sched-procesados', detectados);

  } catch(e) { console.error('[Dashboard] cargarStats:', e); }
}

// ============================================================
//  ESTADO GLOBAL
// ============================================================
function actualizarEstadoGlobal(conProblema, enEspera, noProcesados) {
  const ring  = document.getElementById('estado-ring');
  const title = document.getElementById('estado-title');
  const sub   = document.getElementById('estado-sub');
  const pill  = document.getElementById('status-pill');
  const label = document.getElementById('status-label');

  if (noProcesados > 0 || conProblema > 20) {
    // Rojo
    ['ok','warn'].forEach(c => { ring?.classList.remove(c); title?.classList.remove(c); pill?.classList.remove(c); });
    ring?.classList.add('error'); title?.classList.add('error'); pill?.classList.add('error');
    if (title) title.textContent = 'Atención requerida';
    if (sub)   sub.textContent   = conProblema + ' comprobantes con problema requieren revisión';
    if (label) label.textContent = 'Atención requerida';
  } else if (conProblema > 0 || enEspera > 50) {
    // Amarillo
    ['ok','error'].forEach(c => { ring?.classList.remove(c); title?.classList.remove(c); pill?.classList.remove(c); });
    ring?.classList.add('warn'); title?.classList.add('warn'); pill?.classList.add('warn');
    if (title) title.textContent = 'Flujo con observaciones';
    if (sub)   sub.textContent   = conProblema + ' con problema · ' + enEspera + ' en espera';
    if (label) label.textContent = 'Con observaciones';
  } else {
    // Verde
    ['warn','error'].forEach(c => { ring?.classList.remove(c); title?.classList.remove(c); pill?.classList.remove(c); });
    ring?.classList.add('ok'); title?.classList.add('ok'); pill?.classList.add('ok');
    if (title) title.textContent = 'Flujo estable';
    if (sub)   sub.textContent   = 'Todos los procesos operando correctamente';
    if (label) label.textContent = 'Sistema operativo';
  }
}

// ============================================================
//  DONUT
// ============================================================
function actualizarDonut(entregados, enEspera, conProblema, total) {
  if (!total) return;
  const circ = 2 * Math.PI * 50; // r=50
  const pct  = v => (v / total) * circ;

  const setArc = (id, dash, offset, color) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.setAttribute('stroke-dasharray', dash + ' ' + (circ - dash));
    el.setAttribute('stroke-dashoffset', -offset);
    el.setAttribute('stroke', color);
  };

  const dEnt = pct(entregados);
  const dEsp = pct(enEspera);
  const dProb= pct(conProblema);

  setArc('donut-entregado', dEnt,             0,       'var(--success-light)');
  setArc('donut-espera',    dEsp,             dEnt,    'var(--warning-light)');
  setArc('donut-problema',  dProb,            dEnt+dEsp,'var(--error-light)');

  _setText('donut-total',          total);
  _setText('leg-entregado',        entregados);
  _setText('leg-espera',           enEspera);
  _setText('leg-problema',         conProblema);
  _setText('leg-omitido',          0);
  _setText('leg-pct-entregado',    pct_(entregados, total));
  _setText('leg-pct-espera',       pct_(enEspera,   total));
  _setText('leg-pct-problema',     pct_(conProblema,total));
  _setText('leg-pct-omitido',      '0%');
}

function pct_(v, total) { return total ? Math.round(v/total*100) + '%' : '0%'; }

// ============================================================
//  ALERTAS PANEL
// ============================================================
function actualizarAlertas(conProblema, enEspera, noProcesados) {
  const container = document.getElementById('panel-alertas');
  const badge     = document.getElementById('panel-badge-alertas');
  if (!container) return;

  const alertas = [];
  if (noProcesados > 0) alertas.push({ tipo: 'error', titulo: noProcesados + ' no procesados', detalle: 'Superaron el máximo de reintentos', n: noProcesados });
  if (conProblema > 0)  alertas.push({ tipo: 'error', titulo: conProblema + ' con problema',   detalle: 'El servicio externo no respondió',  n: conProblema });
  if (enEspera > 0)     alertas.push({ tipo: 'warn',  titulo: enEspera + ' en espera',         detalle: 'Esperando próxima ejecución',        n: enEspera });

  if (badge) {
    badge.textContent   = alertas.length;
    badge.style.display = alertas.length > 0 ? 'inline-flex' : 'none';
  }

  if (alertas.length === 0) {
    container.innerHTML = 
      <div class="alert-item">
        <div class="alert-icon"><i data-feather="check-circle" style="width:16px;height:16px;stroke:var(--success)"></i></div>
        <div class="alert-body"><div class="alert-title">Sin alertas activas</div><div class="alert-detail">Todo operando correctamente</div></div>
      </div>;
    feather.replace();
    return;
  }

  const iconos = { error: 'alert-circle', warn: 'alert-triangle' };
  const colores= { error: 'var(--error)', warn: 'var(--warning)' };

  container.innerHTML = alertas.map(a => 
    <div class="alert-item">
      <div class="alert-icon"><i data-feather="" style="width:16px;height:16px;stroke:"></i></div>
      <div class="alert-body">
        <div class="alert-title"></div>
        <div class="alert-detail"></div>
      </div>
      <div class="alert-count"></div>
    </div>
  ).join('');
  feather.replace();
}

// ============================================================
//  ACTIVITY FEED
// ============================================================
async function cargarFeed() {
  try {
    const rows = await window.pywebview.api.get_recent_comprobantes();
    const feed = document.getElementById('feed-actividad');
    if (!feed) return;

    if (!rows || rows.length === 0) {
      feed.innerHTML = '<div style="padding:var(--space-5);text-align:center;color:var(--text-muted);font-size:var(--text-sm);">Sin actividad reciente</div>';
      return;
    }

    // Glosario de estados
    const estadoMap = {
      remitido:  { label: 'Entregado',            clase: 'success', icon: 'check' },
      enviado:   { label: 'Entregado',            clase: 'success', icon: 'check' },
      error:     { label: 'Con problema',          clase: 'error',   icon: 'x' },
      ignorado:  { label: 'Omitido',              clase: 'info',    icon: 'minus-circle' },
      generado:  { label: 'Comprobante preparado', clase: 'info',    icon: 'file-text' },
      leido:     { label: 'Detectado',            clase: 'info',    icon: 'eye' },
      pendiente: { label: 'En espera',             clase: 'warning', icon: 'clock' },
      abandonado:{ label: 'No procesado',          clase: 'error',   icon: 'alert-octagon' },
    };

    const iconSvg = {
      check:         '<polyline points="1.5,4.5 3.5,6.5 7.5,2.5"/>',
      x:             '<path d="M2 2l5 5M7 2L2 7"/>',
      'minus-circle':'<circle cx="4.5" cy="4.5" r="3.5"/><path d="M2.5 4.5h4"/>',
      'file-text':   '<rect x="1.5" y="1" width="6" height="8" rx="0.5"/><path d="M3 3h3M3 5h3M3 7h2"/>',
      eye:           '<circle cx="4.5" cy="4.5" r="1.5"/><path d="M1 4.5s1.5-3 3.5-3 3.5 3 3.5 3-1.5 3-3.5 3-3.5-3-3.5-3"/>',
      clock:         '<circle cx="4.5" cy="4.5" r="3.5"/><path d="M4.5 2.5v2l1.5 1.5"/>',
      'alert-octagon':'<path d="M3 1.5h3l2 2v3l-2 2H3l-2-2v-3z"/><path d="M4.5 3v2.5M4.5 6.5v.5"/>',
    };

    feed.innerHTML = rows.slice(0, 8).map(c => {
      const est  = estadoMap[c.estado] || estadoMap['pendiente'];
      const hora = c.fecha ? c.fecha.split(' ')[1] || c.fecha : '—';
      const comp = c.serie + '-' + String(c.numero).padStart(8,'0');
      const desc = est.label === 'Entregado'
        ? 'Servicio externo confirmó recepción'
        : est.label === 'Con problema'
        ? 'El servicio externo no respondió'
        : est.label === 'En espera'
        ? 'Esperando próxima ejecución'
        : est.label === 'Comprobante preparado'
        ? 'TXT generado correctamente'
        : est.label;

      return 
        <div class="feed-item">
          <div class="feed-icon ">
            <svg viewBox="0 0 9 9" fill="none" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"></svg>
          </div>
          <div class="feed-time"></div>
          <div class="feed-content">
            <div class="feed-title"></div>
            <div class="feed-detail"></div>
          </div>
          <div class="feed-comp"></div>
        </div>;
    }).join('');

  } catch(e) { console.error('[Dashboard] cargarFeed:', e); }
}

// ============================================================
//  SCHEDULER
// ============================================================
async function cargarScheduler() {
  try {
    const info = await window.pywebview.api.get_scheduler_info?.();
    if (!info) return;

    _setText('sched-estado',      info.activo ? 'Activo' : 'Pausado');
    _setText('sched-estado-sub',  info.activo ? 'Corriendo' : 'En pausa');
    _setText('sched-ultimo',      info.ultimo_ciclo  || '—');
    _setText('sched-ultimo-sub',  info.hace          || '—');
    _setText('sched-proximo',     info.proximo_ciclo || '—');
    _setText('sched-intervalo',   'Intervalo: ' + (info.intervalo || '5') + ' min');
    _setText('sched-ciclos',      'en ' + (info.ciclos_hoy || 0) + ' ciclos');

    // Estado color
    const elEst = document.getElementById('sched-estado');
    if (elEst) elEst.className = 'sched-value ' + (info.activo ? 'success' : 'warning');

    // Barra próximo ciclo
    const bar = document.getElementById('sched-bar');
    if (bar && info.pct_proximo != null) bar.style.width = info.pct_proximo + '%';

  } catch(e) { /* scheduler info opcional */ }
}

// ============================================================
//  CONEXION
// ============================================================
async function verificarConexion() {
  try {
    const r = await window.pywebview.api.verificar_conexion_api();

    const dotInternet = document.getElementById('dot-internet');
    const lblInternet = document.getElementById('lbl-internet');
    const dotLocal    = document.getElementById('dot-local');
    const lblLocal    = document.getElementById('lbl-local');
    const psMode      = document.getElementById('ps-modo');
    const psResp      = document.getElementById('ps-respuesta');
    const psHace      = document.getElementById('ps-hace');
    const footerDot   = document.getElementById('footer-dot');
    const footerConn  = document.getElementById('footer-conexion');

    const online = r && r.conectado;

    if (dotInternet) dotInternet.className = 'conexion-dot ' + (online ? 'online' : 'offline');
    if (lblInternet) lblInternet.textContent = 'Internet: ' + (online ? 'OK' : 'Sin conexión');
    if (dotLocal)    dotLocal.className = 'conexion-dot online';
    if (lblLocal)    lblLocal.textContent = 'Local: OK';

    if (psMode) psMode.textContent = online ? 'Híbrido' : 'Solo local';
    if (psMode) psMode.className = 'panel-stat-value ' + (online ? 'ok' : 'warning');

    if (psResp) { psResp.textContent = online ? '200 OK' : 'Sin respuesta'; psResp.className = 'panel-stat-value ' + (online ? 'ok' : 'error'); }
    if (psHace && r?.hace) psHace.textContent = r.hace;

    if (footerDot)  footerDot.className = 'status-dot ' + (online ? 'ok' : 'error');
    if (footerConn) footerConn.textContent = online ? 'Conectado' : 'Sin conexión';

  } catch(e) { console.error('[Dashboard] verificarConexion:', e); }
}

// ============================================================
//  SPARKLINES
// ============================================================
function renderSpark(containerId, datos, color) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const max = Math.max(...datos, 1);
  el.innerHTML = datos.map(v => {
    const h = Math.max(2, Math.round((v / max) * 18));
    return <div class="spark-bar" style="height:px;background:"></div>;
  }).join('');
}

// ============================================================
//  HELPERS
// ============================================================
function _setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? '—';
}

function actualizarStatPendientes(count) {
  const val = Number(count) || 0;
  const ep  = document.getElementById('stat-pendientes');
  const eb  = document.getElementById('badge-pendientes');
  if (ep) ep.textContent = val;
  if (eb) { eb.textContent = val; eb.style.display = val > 0 ? 'inline-flex' : 'none'; }
}

function getBadgeClass(estado) {
  const map = {
    remitido:'entregado', enviado:'entregado',
    pendiente:'en-espera', error:'con-problema',
    ignorado:'omitido', generado:'preparado',
    leido:'preparado', abandonado:'no-procesado',
  };
  return 'badge-' + (map[estado] || 'neutral');
}

function toggleScheduler() {
  // Implementar cuando api.py exponga toggle_scheduler
  mostrarToast('Función disponible próximamente', 'info');
}

function reprocesarErrores() {
  // Implementar cuando api.py exponga reprocesar_errores
  mostrarToast('Reprocesando comprobantes con problema...', 'info');
}
