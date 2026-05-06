/**
 * app.js — DisateQ CPE™ v5.0
 * Rediseño FIX-UI-07: nuevas tabs, glosario oficial, header actualizado
 */

'use strict';

var appState = {
  initialized:         false,
  currentPage:         'dashboard',
  clienteAlias:        null,
};

function api(method) {
  var args = Array.prototype.slice.call(arguments, 1);
  return window.pywebview.api[method].apply(window.pywebview.api, args);
}

document.addEventListener('DOMContentLoaded', function() {
  if (window.pywebview) {
    inicializarSistema();
  } else {
    window.addEventListener('pywebviewready', function() { inicializarSistema(); });
  }
  configurarNavegacion();
  if (typeof feather !== 'undefined') feather.replace();
});

async function inicializarSistema() {
  try {
    var result = await api('inicializar_sistema');
    if (!result.success) { mostrarToast(result.error || 'Error al inicializar', 'error'); return; }
    var clientes = await api('get_clientes_disponibles');
    if (clientes.exito && clientes.clientes.length > 0) {
      appState.clienteAlias = clientes.clientes[0].id || clientes.clientes[0].alias;
    }
    appState.initialized = true;
    cargarDashboard();
    actualizarFooterLicencia();
  } catch(e) {
    console.error('[App] inicializarSistema:', e);
  }
}

// ============================================================
//  NAVEGACIÓN
// ============================================================
function configurarNavegacion() {
  document.querySelectorAll('.tab-item').forEach(function(tab) {
    tab.addEventListener('click', function() { navegarA(tab.dataset.page); });
  });
}

function navegarA(page) {
  document.querySelectorAll('.tab-item').forEach(function(t) { t.classList.remove('active'); });
  var tabEl = document.querySelector('[data-page="' + page + '"]');
  if (tabEl) tabEl.classList.add('active');

  document.querySelectorAll('.content-page').forEach(function(p) { p.classList.remove('active'); });
  var pageEl = document.getElementById('page-' + page);
  if (pageEl) pageEl.classList.add('active');

  appState.currentPage = page;

  if (page === 'dashboard')   cargarDashboard();
  if (page === 'entregas')    cargarEntregas();
  if (page === 'pendientes')  cargarPendientesTab();
  if (page === 'eventos')     cargarEventos();
  if (page === 'ajustes')     initAjustes();

  if (typeof feather !== 'undefined') feather.replace();
  actualizarFooterLicencia();
}

// Alias para index.html
function irA(page) { navegarA(page); }

// ============================================================
//  ACCIONES HEADER
// ============================================================
async function procesarPendientes() {
  if (!appState.clienteAlias) { mostrarToast('No hay cliente configurado', 'error'); return; }
  mostrarToast('Iniciando ejecución...', 'info');
  try {
    var result = await api('procesar_motor', appState.clienteAlias, null, 'mock');
    if (result.exito) {
      var r = result.resultados;
      mostrarToast(r.enviados + ' entregados · ' + r.errores + ' con problema', r.errores > 0 ? 'warning' : 'success');
      await cargarDashboard();
    } else {
      mostrarToast(result.error, 'error');
    }
  } catch(e) {
    mostrarToast('Error al procesar', 'error');
  }
}

async function sincronizar() {
  mostrarToast('Sincronizando...', 'info');
  await cargarDashboard();
  actualizarFooterLicencia();
  var el = document.getElementById('ultima-sync');
  if (el) el.textContent = new Date().toLocaleTimeString('es-PE', { hour:'2-digit', minute:'2-digit' });
  mostrarToast('Sincronización completada', 'success');
}

async function abrirConfig() { navegarA('ajustes'); }

async function cerrarApp() {
  if (confirm('¿Cerrar DisateQ CPE™?')) {
    try { await api('cerrar_sistema'); } catch(e) {}
    window.close();
  }
}

function schedulerCicloCompletado(resultados) {
  mostrarToast(resultados.enviados + ' entregados · ' + resultados.errores + ' con problema', 'info');
  cargarDashboard();
  actualizarFooterLicencia();
}

// ============================================================
//  ENTREGAS (ex Historial)
// ============================================================
var _historialData = [];
var _filtTipo      = '';
var _filtEstado    = '';

async function cargarEntregas() {
  var page = document.getElementById('page-entregas');
  var tbody = document.getElementById('tabla-entregas');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--text-muted);">Cargando...</td></tr>';

  var result = await api('get_historial', 500);
  if (!result.exito) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--error);">Error: ' + result.error + '</td></tr>';
    return;
  }
  _historialData = result.comprobantes || [];
  renderEntregasTabla(_historialData);
}

function renderEntregasTabla(data) {
  var tbody = document.getElementById('tabla-entregas');
  if (!tbody) return;
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--text-muted);">Sin entregas</td></tr>';
    return;
  }
  tbody.innerHTML = data.slice(0, 100).map(function(c) {
    var est    = _estadoGlosario(c.estado);
    var tipo   = _tipoBadgeHtml(c.tipo_doc);
    var accion = (c.estado === 'error' || c.estado === 'abandonado')
      ? '<button class="btn btn-xs btn-outline-warning" onclick="forzarReenvioIndividual(\'' + c.serie + '\',\'' + c.numero + '\')">Reintentar</button>'
      : '<button class="btn btn-xs btn-ghost" onclick="">Ver</button>';
    return '<tr>' +
      '<td><strong class="font-mono">' + c.serie + '-' + String(c.numero).padStart(8,'0') + '</strong></td>' +
      '<td>' + tipo + '</td>' +
      '<td>' + (c.fecha || '—') + '</td>' +
      '<td>' + (c.cliente || 'CLIENTE VARIOS') + '</td>' +
      '<td class="right"><strong>S/ ' + Number(c.total||0).toFixed(2) + '</strong></td>' +
      '<td style="text-align:center;"><span class="badge ' + est.badge + '"><div class="badge-dot"></div>' + est.label + '</span></td>' +
      '<td style="text-align:center;">' + accion + '</td>' +
      '</tr>';
  }).join('');
  if (typeof feather !== 'undefined') feather.replace();
}

// ============================================================
//  PENDIENTES TAB
// ============================================================
async function cargarPendientesTab() {
  var tbody = document.getElementById('tabla-pendientes');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted);">Cargando...</td></tr>';
  try {
    var result = await api('get_historial', 500);
    if (!result.exito) return;
    var pendientes = (result.comprobantes || []).filter(function(c) {
      return c.estado === 'pendiente' || c.estado === 'error';
    });
    if (!pendientes.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted);">Sin pendientes en cola</td></tr>';
      return;
    }
    tbody.innerHTML = pendientes.map(function(c) {
      var est  = _estadoGlosario(c.estado);
      var tipo = _tipoBadgeHtml(c.tipo_doc);
      return '<tr>' +
        '<td><strong class="font-mono">' + c.serie + '-' + String(c.numero).padStart(8,'0') + '</strong></td>' +
        '<td>' + tipo + '</td>' +
        '<td>' + (c.fecha || '—') + '</td>' +
        '<td>' + (c.cliente || 'CLIENTE VARIOS') + '</td>' +
        '<td class="right"><strong>S/ ' + Number(c.total||0).toFixed(2) + '</strong></td>' +
        '<td style="text-align:center;"><span class="badge ' + est.badge + '"><div class="badge-dot"></div>' + est.label + '</span></td>' +
        '</tr>';
    }).join('');
  } catch(e) { console.error('[App] cargarPendientesTab:', e); }
}

// ============================================================
//  EVENTOS TAB
// ============================================================
var _eventosData   = [];
var _evFiltTipo    = 'todos';
var _evFiltEstado  = 'todos';

async function cargarEventos() {
  var tbody = document.getElementById('tabla-eventos');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--text-muted);">Cargando...</td></tr>';
  try {
    var result = await api('get_logs', null, 500);
    if (!result.exito) return;
    _eventosData = result.logs || [];
    filtrarEventos();
  } catch(e) { console.error('[App] cargarEventos:', e); }
}

function filtrarEventos() {
  var search = (document.getElementById('eventos-search') || {}).value || '';
  var q      = search.toLowerCase();

  var filtrado = _eventosData.filter(function(r) {
    var tipoOk   = _evFiltTipo   === 'todos' || (r.tipo_doc||'') === _evFiltTipo;
    var estadoOk = _evFiltEstado === 'todos' || _mapEstadoFiltro(r.estado) === _evFiltEstado;
    var searchOk = !q || (r.serie+'-'+r.numero).toLowerCase().includes(q) || (r.cliente||'').toLowerCase().includes(q);
    return tipoOk && estadoOk && searchOk;
  });

  renderEventosTabla(filtrado);
}

function _mapEstadoFiltro(estado) {
  var map = { remitido:'entregado', enviado:'entregado', error:'problema', ignorado:'omitido', pendiente:'espera', generado:'espera', leido:'espera', abandonado:'problema' };
  return map[estado] || 'espera';
}

function renderEventosTabla(data) {
  var tbody = document.getElementById('tabla-eventos');
  if (!tbody) return;
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--text-muted);">Sin eventos</td></tr>';
    return;
  }
  tbody.innerHTML = data.slice(0, 200).map(function(r) {
    var est    = _estadoGlosario(r.estado);
    var tipo   = _tipoBadgeHtml(r.tipo_doc);
    var hora   = r.fecha ? r.fecha.substring(11,19) : '—';
    var comp   = r.serie + '-' + String(r.numero).padStart(8,'0');
    var detalle= _eventoDetalle(r.estado);
    var accion = (r.estado === 'error' || r.estado === 'abandonado')
      ? '<button class="btn btn-xs btn-outline-warning" onclick="forzarReenvioIndividual(\'' + r.serie + '\',\'' + r.numero + '\')">Reintentar</button>'
      : '';
    return '<tr>' +
      '<td class="mono">' + hora + '</td>' +
      '<td><strong class="mono">' + comp + '</strong></td>' +
      '<td>' + tipo + '</td>' +
      '<td>' +
        '<div style="font-size:var(--text-sm);font-weight:600;color:var(--text-primary);">' + est.label + '</div>' +
        '<div style="font-size:var(--text-xs);color:var(--text-muted);">' + detalle + '</div>' +
      '</td>' +
      '<td class="right">S/ ' + Number(r.total||0).toFixed(2) + '</td>' +
      '<td style="text-align:center;"><span class="badge ' + est.badge + '"><div class="badge-dot"></div>' + est.label + '</span></td>' +
      '<td style="text-align:center;">' + accion + '</td>' +
      '</tr>';
  }).join('');
  if (typeof feather !== 'undefined') feather.replace();
}

function _eventoDetalle(estado) {
  var map = {
    remitido:  'Servicio externo confirmó recepción',
    enviado:   'Servicio externo confirmó recepción',
    error:     'El servicio externo no respondió',
    ignorado:  'Registro omitido en este ciclo',
    pendiente: 'Esperando próxima ejecución',
    generado:  'Comprobante TXT generado',
    leido:     'Detectado en sistema de origen',
    abandonado:'Superó el máximo de reintentos',
  };
  return map[estado] || '—';
}

// ============================================================
//  AJUSTES (ex Config)
// ============================================================
var _ajustesDesbloqueados = false;
var _SL = 'opacity:0.6;background:var(--bg-table-head);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:0.4rem 0.75rem;font-size:0.875rem;color:var(--text-secondary);display:block;';

async function initAjustes() {
  if (_ajustesDesbloqueados) await mostrarAjustesCompletos();
  else mostrarLockAjustes();
}

function mostrarLockAjustes() {
  var page = document.getElementById('page-ajustes');
  var body = page ? page.querySelector('.card-body') : null;
  if (!body) return;
  var pins = '';
  for (var i = 0; i < 4; i++) {
    pins += '<input type="password" maxlength="1" id="pin-' + i + '" ' +
      'style="width:52px;height:52px;text-align:center;font-size:1.5rem;border:2px solid var(--border-medium);border-radius:var(--radius-md);outline:none;" ' +
      'oninput="onPinInput(' + i + ',this)" onkeydown="onPinKey(event,' + i + ')">';
  }
  body.innerHTML =
    '<div style="max-width:320px;margin:3rem auto;text-align:center;">' +
    '<div style="font-size:3rem;margin-bottom:1rem;">🔒</div>' +
    '<h3 style="margin-bottom:0.5rem;">Acceso Restringido</h3>' +
    '<p style="color:var(--text-muted);margin-bottom:1.5rem;font-size:0.875rem;">Esta sección requiere clave del técnico instalador.</p>' +
    '<div style="display:flex;gap:0.75rem;justify-content:center;margin-bottom:1.25rem;">' + pins + '</div>' +
    '<button class="btn btn-primary" onclick="verificarPin()" style="width:100%;justify-content:center;">Acceder</button>' +
    '<div id="pin-error" style="color:var(--error);margin-top:0.75rem;font-size:0.875rem;display:none;">Clave incorrecta</div></div>';
  setTimeout(function() { var el = document.getElementById('pin-0'); if (el) el.focus(); }, 100);
}

function onPinInput(idx, input) {
  input.value = input.value.replace(/[^0-9]/g, '');
  if (input.value && idx < 3) { var n = document.getElementById('pin-' + (idx + 1)); if (n) n.focus(); }
  if (idx === 3 && input.value) verificarPin();
}

function onPinKey(e, idx) {
  if (e.key === 'Backspace' && !e.target.value && idx > 0) {
    var p = document.getElementById('pin-' + (idx - 1)); if (p) p.focus();
  }
}

async function verificarPin() {
  var clave = '';
  for (var i = 0; i < 4; i++) { var el = document.getElementById('pin-' + i); clave += el ? el.value : ''; }
  if (clave.length < 4) return;
  var result = await api('verificar_clave_instalador', clave);
  if (result.valida) { _ajustesDesbloqueados = true; await mostrarAjustesCompletos(); }
  else {
    var err = document.getElementById('pin-error'); if (err) err.style.display = 'block';
    for (var i = 0; i < 4; i++) { var el = document.getElementById('pin-' + i); if (el) { el.value = ''; el.style.borderColor = 'var(--error)'; } }
    setTimeout(function() {
      var e0 = document.getElementById('pin-0'); if (e0) e0.focus();
      for (var i = 0; i < 4; i++) { var el = document.getElementById('pin-' + i); if (el) el.style.borderColor = 'var(--border-medium)'; }
    }, 1000);
  }
}

async function mostrarAjustesCompletos() {
  // Reutiliza la lógica de mostrarConfigCompleta del código anterior
  var page = document.getElementById('page-ajustes');
  var body = page ? page.querySelector('#ajustes-body') : null;
  if (!body) return;

  var result = await api('get_config_cliente');
  if (!result.exito) { body.innerHTML = '<p style="color:var(--error)">Error cargando configuración</p>'; return; }

  var d         = result;
  var series    = d.series    || {};
  var endpoints = d.endpoints || [];
  var rutas = (d.fuente.rutas || []).map(function(r) {
    return '<div style="' + _SL + 'font-family:var(--font-mono);font-size:0.82rem;margin-bottom:0.25rem;">' + r + '</div>';
  }).join('');

  var lic = await api('get_licencia_info');
  var licHtml = _renderLicencia(lic);

  body.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">' +
    '<span style="color:var(--success);font-size:0.875rem;">🔓 Modo técnico activo</span>' +
    '<button class="btn btn-ghost btn-sm" onclick="bloquearAjustes()">🔒 Bloquear</button></div>' +

    '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Empresa</h3></div>' +
    '<div class="card-body"><div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">' +
    '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">RUC</label>' + _renderSL(d.empresa.ruc) + '</div>' +
    '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Razón Social</label>' + _renderSL(d.empresa.razon_social) + '</div>' +
    '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Nombre Comercial</label>' +
    '<input type="text" id="cfg-nombre-comercial" value="' + (d.empresa.nombre_comercial||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;"></div>' +
    '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Alias / Local</label>' +
    '<input type="text" id="cfg-alias" value="' + (d.empresa.alias||'') + '" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;"></div>' +
    '</div></div></div>' +

    '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Fuente de Datos</h3></div>' +
    '<div class="card-body"><div style="display:grid;grid-template-columns:100px 1fr;gap:1rem;align-items:start;">' +
    '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Tipo</label>' + _renderSL((d.fuente.tipo||'').toUpperCase()) + '</div>' +
    '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Ruta(s)</label>' + rutas + '</div>' +
    '</div></div></div>' +

    '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Servicio de Destino</h3></div>' +
    '<div class="card-body"><div id="endpoints-container">' + _renderEndpoints(endpoints) + '</div></div></div>' +

    '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Ciclo Automático</h3></div>' +
    '<div class="card-body"><div style="display:flex;align-items:center;gap:1.5rem;">' +
    '<label style="display:flex;align-items:center;gap:0.4rem;cursor:pointer;font-size:0.875rem;padding:0.5rem 1rem;border:2px solid var(--border-medium);border-radius:var(--radius-md);" id="lbl-modo-manual"><input type="radio" name="sched-modo" id="sched-modo-manual" value="manual" onchange="onSchedModoChange()"> Manual</label>' +
    '<label style="display:flex;align-items:center;gap:0.4rem;cursor:pointer;font-size:0.875rem;padding:0.5rem 1rem;border:2px solid var(--border-medium);border-radius:var(--radius-md);" id="lbl-modo-auto"><input type="radio" name="sched-modo" id="sched-modo-auto" value="automatico" onchange="onSchedModoChange()"> Automático</label>' +
    '<div id="sched-intervalo-box" style="display:none;">' +
    '<select id="sched-intervalo" style="padding:0.45rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;">' +
    '<option value="5">Cada 5 minutos</option><option value="10">Cada 10 minutos</option><option value="15">Cada 15 minutos</option><option value="30">Cada 30 minutos</option>' +
    '</select></div></div></div></div>' +

    '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Licencia DisateQ™</h3></div>' +
    '<div class="card-body">' + licHtml +
    '<div style="display:flex;align-items:center;gap:0.75rem;">' +
    '<button class="btn btn-ghost btn-sm" onclick="cargarLicencia()">📂 Cargar licencia (.lic)</button>' +
    '</div><div id="lic-mensaje" style="margin-top:0.75rem;font-size:0.85rem;display:none;"></div>' +
    '</div></div>' +

    '<div class="card" style="margin-bottom:1rem;"><div class="card-header"><h3>Clave del Instalador</h3></div>' +
    '<div class="card-body"><div style="display:flex;gap:1rem;align-items:flex-end;max-width:400px;">' +
    '<div style="flex:1;"><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Nueva clave (4 dígitos)</label>' +
    '<input type="password" id="cfg-clave-nueva" maxlength="4" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:1rem;letter-spacing:0.5rem;"></div>' +
    '<div style="flex:1;"><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Confirmar clave</label>' +
    '<input type="password" id="cfg-clave-confirma" maxlength="4" style="width:100%;padding:0.4rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:1rem;letter-spacing:0.5rem;"></div>' +
    '</div></div></div>' +

    '<div style="display:flex;gap:0.75rem;justify-content:flex-end;padding-top:0.5rem;">' +
    '<button class="btn btn-ghost" onclick="bloquearAjustes()">Cancelar</button>' +
    '<button class="btn btn-primary" onclick="guardarAjustes()">💾 Guardar cambios</button></div>' +
    '<div id="cfg-mensaje" style="text-align:right;margin-top:0.5rem;font-size:0.85rem;display:none;"></div>';

  setTimeout(cargarSchedulerConfig, 100);
}

function _renderLicencia(lic) {
  if (lic && lic.valida) {
    var color = lic.dias_restantes > 60 ? 'var(--success)' : lic.dias_restantes > 15 ? 'var(--warning)' : 'var(--error)';
    return '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem;">' +
      '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Estado</label>' +
      '<div style="display:flex;align-items:center;gap:0.5rem;"><span style="width:10px;height:10px;border-radius:50%;background:var(--success);display:inline-block;"></span>' +
      '<span style="font-size:0.875rem;font-weight:600;color:var(--success);">Licencia válida</span></div></div>' +
      '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Cliente</label>' + _renderSL(lic.cliente + ' (' + lic.ruc + ')') + '</div>' +
      '<div><label style="font-size:0.72rem;color:var(--text-muted);display:block;margin-bottom:0.25rem;">Vencimiento</label>' +
      '<div style="' + _SL + 'color:' + color + ';font-weight:600;">' + lic.vencimiento + ' (' + lic.dias_restantes + ' días)</div></div>' +
      '</div>';
  }
  return '<div style="display:flex;align-items:center;gap:0.75rem;padding:0.75rem;background:var(--error-bg);border:1px solid var(--error-border);border-radius:var(--radius-md);margin-bottom:1rem;">' +
    '<span>⚠️</span><span style="color:var(--error);font-size:0.875rem;">' + (lic ? lic.mensaje : 'Sin licencia activa') + '</span></div>';
}

function bloquearAjustes() { _ajustesDesbloqueados = false; mostrarLockAjustes(); }

async function guardarAjustes() {
  var nueva    = (document.getElementById('cfg-clave-nueva')    || {}).value || '';
  var confirma = (document.getElementById('cfg-clave-confirma') || {}).value || '';
  var msg      = document.getElementById('cfg-mensaje');
  if (nueva && nueva !== confirma)      { if(msg){msg.style.display='block';msg.style.color='var(--error)';msg.textContent='Las claves no coinciden';} return; }
  if (nueva && !/^\d{4}$/.test(nueva)) { if(msg){msg.style.display='block';msg.style.color='var(--error)';msg.textContent='La clave debe ser 4 dígitos';} return; }

  var epEls     = document.querySelectorAll('[id$="-nombre"][id^="ep-"]');
  var endpoints = [];
  var URL_CAMPOS = ['url_comprobantes','url_anulaciones','url_guias','url_retenciones','url_percepciones'];
  epEls.forEach(function(el) {
    var idx = el.id.replace('ep-','').replace('-nombre','');
    var ae  = document.getElementById('ep-' + idx + '-activo');
    var us  = document.getElementById('ep-' + idx + '-usuario');
    var tk  = document.getElementById('ep-' + idx + '-token');
    var fmt = document.getElementById('ep-' + idx + '-formato');
    var ep  = { nombre: el.value, activo: ae?ae.checked:false, formato: fmt?fmt.value:'txt', usuario: us?us.value:'', token: tk?tk.value:'' };
    URL_CAMPOS.forEach(function(campo) {
      var urlEl = document.getElementById('ep-' + idx + '-' + campo);
      ep[campo] = (urlEl && !urlEl.disabled) ? urlEl.value.trim() : '';
    });
    endpoints.push(ep);
  });

  var schedModo      = document.querySelector('input[name="sched-modo"]:checked');
  var schedIntervalo = document.getElementById('sched-intervalo');
  if (schedModo) {
    await api('guardar_config_scheduler', { modo: schedModo.value, intervalo_boletas: schedIntervalo ? parseInt(schedIntervalo.value) : 10 });
  }

  var result = await api('guardar_config', {
    nombre_comercial: (document.getElementById('cfg-nombre-comercial')||{}).value || '',
    alias:            (document.getElementById('cfg-alias')||{}).value || '',
    endpoints: endpoints,
    clave_nueva: nueva || null,
  });

  if (msg) msg.style.display = 'block';
  if (result.exito) {
    if (msg) { msg.style.color = 'var(--success)'; msg.textContent = 'Ajustes guardados correctamente'; }
    mostrarToast('Ajustes guardados', 'success');
    setTimeout(function() { mostrarAjustesCompletos(); }, 1500);
  } else {
    if (msg) { msg.style.color = 'var(--error)'; msg.textContent = 'Error: ' + result.error; }
  }
}

async function cargarLicencia() {
  try {
    var ruta = await api('abrir_dialogo_archivo', '*.lic', 'Archivos de Licencia (*.lic)');
    if (!ruta) return;
    var msg = document.getElementById('lic-mensaje');
    if (msg) { msg.style.display='block'; msg.style.color='var(--info)'; msg.textContent='Validando licencia...'; }
    var result = await api('cargar_licencia', ruta);
    if (msg) { msg.style.color = result.exito ? 'var(--success)' : 'var(--error)'; msg.textContent = result.mensaje; }
    if (result.exito) {
      mostrarToast('Licencia activada correctamente', 'success');
      actualizarFooterLicencia();
      setTimeout(function() { mostrarAjustesCompletos(); }, 1500);
    }
  } catch(e) { mostrarToast('Error al cargar licencia', 'error'); }
}

// ============================================================
//  HELPERS COMUNES
// ============================================================
function _renderSL(val) { return '<div style="' + _SL + '">' + (val || '-') + '</div>'; }

function _estadoGlosario(estado) {
  var map = {
    remitido:  { label: 'Entregado',         badge: 'badge-entregado' },
    enviado:   { label: 'Entregado',         badge: 'badge-entregado' },
    error:     { label: 'Con problema',      badge: 'badge-con-problema' },
    ignorado:  { label: 'Omitido',           badge: 'badge-omitido' },
    pendiente: { label: 'En espera',         badge: 'badge-en-espera' },
    generado:  { label: 'Preparado',         badge: 'badge-preparado' },
    leido:     { label: 'Detectado',         badge: 'badge-preparado' },
    abandonado:{ label: 'No procesado',      badge: 'badge-no-procesado' },
  };
  return map[estado] || { label: estado || '—', badge: 'badge-neutral' };
}

function _tipoBadgeHtml(tipo) {
  var map = { boleta:'badge-boleta', factura:'badge-factura', nota_credito:'badge-nc', nota_debito:'badge-nd', anulacion:'badge-anulacion' };
  var lbl = { boleta:'Boleta', factura:'Factura', nota_credito:'N.Créd', nota_debito:'N.Déb', anulacion:'Anul.' };
  if (!tipo) return '—';
  return '<span class="badge ' + (map[tipo]||'badge-neutral') + '">' + (lbl[tipo]||tipo) + '</span>';
}

async function forzarReenvioIndividual(serie, numero) {
  var res = await api('forzar_reenvio_individual', { serie: serie, numero: numero });
  if (res.exito) {
    mostrarToast('Marcado para reintento: ' + serie + '-' + String(numero).padStart(8,'0'), 'success');
    if (appState.currentPage === 'eventos')   cargarEventos();
    if (appState.currentPage === 'entregas')  cargarEntregas();
  } else {
    mostrarToast(res.error || 'Error al marcar reintento', 'error');
  }
}

function _renderEndpoints(eps) {
  if (!eps || !eps.length) return '<p style="color:var(--text-muted)">Sin servicios configurados</p>';
  var URL_CAMPOS = [
    { id:'url_comprobantes', label:'Comprobantes', req:true },
    { id:'url_anulaciones',  label:'Anulaciones',  req:false },
  ];
  return eps.map(function(ep, i) {
    var u = ep.credenciales && ep.credenciales.usuario ? ep.credenciales.usuario : '';
    var t = ep.credenciales && ep.credenciales.token   ? ep.credenciales.token   : '';
    var urlRows = URL_CAMPOS.map(function(c) {
      var val = ep[c.id] || ep.url || '';
      return '<div style="margin-bottom:0.5rem;">' +
        '<label style="font-size:0.72rem;color:var(--text-muted);">' + c.label + (c.req ? ' *' : '') + '</label>' +
        '<input type="text" id="ep-' + i + '-' + c.id + '" value="' + val + '" placeholder="https://..." style="width:100%;padding:0.3rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;font-family:var(--font-mono);"></div>';
    }).join('');
    return '<div style="border:1px solid var(--border-medium);border-radius:var(--radius-lg);padding:1rem;margin-bottom:0.75rem;">' +
      '<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem;">' +
      '<input type="text" id="ep-' + i + '-nombre" value="' + (ep.nombre||'') + '" style="font-weight:600;border:1px solid var(--border-medium);border-radius:var(--radius-sm);padding:0.25rem 0.5rem;font-size:0.875rem;width:160px;">' +
      '<label style="display:flex;align-items:center;gap:0.3rem;font-size:0.82rem;cursor:pointer;"><input type="checkbox" id="ep-' + i + '-activo" ' + (ep.activo ? 'checked' : '') + '> Activo</label>' +
      '<select id="ep-' + i + '-formato" style="padding:0.25rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.78rem;">' +
      '<option value="txt" ' + (!ep.formato||ep.formato==='txt'?'selected':'') + '>TXT</option>' +
      '<option value="json" ' + (ep.formato==='json'?'selected':'') + '>JSON</option>' +
      '</select>' +
      '<button onclick="this.parentNode.parentNode.remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:var(--error);font-size:1.2rem;">✕</button></div>' +
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:0.75rem;">' +
      '<div><label style="font-size:0.72rem;color:var(--text-muted);">Usuario (opcional)</label>' +
      '<input type="text" id="ep-' + i + '-usuario" value="' + u + '" style="width:100%;padding:0.3rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;"></div>' +
      '<div><label style="font-size:0.72rem;color:var(--text-muted);">Token (opcional)</label>' +
      '<input type="password" id="ep-' + i + '-token" value="' + t + '" style="width:100%;padding:0.3rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;"></div></div>' +
      urlRows + '</div>';
  }).join('') +
  '<button onclick="agregarEndpointConfig()" style="font-size:0.78rem;color:var(--primary);background:none;border:1px dashed var(--primary-border);border-radius:var(--radius-md);padding:0.35rem 1rem;cursor:pointer;">+ Agregar servicio</button>';
}

function agregarEndpointConfig() {
  var container = document.getElementById('endpoints-container');
  if (!container) return;
  var idx = container.querySelectorAll('[id$="-nombre"][id^="ep-"]').length;
  var div = document.createElement('div');
  div.style.cssText = 'border:1px solid var(--border-medium);border-radius:var(--radius-lg);padding:1rem;margin-bottom:0.75rem;';
  div.innerHTML =
    '<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem;">' +
    '<input type="text" id="ep-' + idx + '-nombre" placeholder="Nombre servicio" style="font-weight:600;border:1px solid var(--border-medium);border-radius:var(--radius-sm);padding:0.25rem 0.5rem;font-size:0.875rem;width:180px;">' +
    '<label style="display:flex;align-items:center;gap:0.3rem;font-size:0.82rem;cursor:pointer;"><input type="checkbox" id="ep-' + idx + '-activo" checked> Activo</label>' +
    '<select id="ep-' + idx + '-formato" style="padding:0.25rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.78rem;">' +
    '<option value="txt">TXT</option><option value="json">JSON</option></select>' +
    '<button onclick="this.parentNode.parentNode.remove()" style="margin-left:auto;background:none;border:none;cursor:pointer;color:var(--error);font-size:1.2rem;">✕</button></div>' +
    '<div><label style="font-size:0.72rem;color:var(--text-muted);">URL Comprobantes *</label>' +
    '<input type="text" id="ep-' + idx + '-url_comprobantes" placeholder="https://..." style="width:100%;padding:0.3rem 0.5rem;border:1px solid var(--border-medium);border-radius:var(--radius-sm);font-size:0.82rem;font-family:var(--font-mono);"></div>';
  var btn = container.querySelector('button[onclick="agregarEndpointConfig()"]');
  if (btn) container.insertBefore(div, btn);
  else container.appendChild(div);
}

function onSchedModoChange() {
  var modo = document.querySelector('input[name="sched-modo"]:checked');
  if (!modo) return;
  var box    = document.getElementById('sched-intervalo-box');
  var lblMan = document.getElementById('lbl-modo-manual');
  var lblAut = document.getElementById('lbl-modo-auto');
  if (modo.value === 'automatico') {
    if (box) box.style.display = 'block';
    if (lblAut) lblAut.style.borderColor = 'var(--success)';
    if (lblMan) lblMan.style.borderColor = 'var(--border-medium)';
  } else {
    if (box) box.style.display = 'none';
    if (lblMan) lblMan.style.borderColor = 'var(--success)';
    if (lblAut) lblAut.style.borderColor = 'var(--border-medium)';
  }
}

async function cargarSchedulerConfig() {
  try {
    var result = await api('get_scheduler_status');
    if (!result.exito) return;
    var s = result.status;
    var modoAuto = document.getElementById('sched-modo-auto');
    var modoMan  = document.getElementById('sched-modo-manual');
    var box      = document.getElementById('sched-intervalo-box');
    var intEl    = document.getElementById('sched-intervalo');
    if (!modoAuto) return;
    if (s.modo === 'automatico') {
      modoAuto.checked = true;
      if (box) box.style.display = 'block';
    } else {
      if (modoMan) modoMan.checked = true;
    }
    if (intEl) intEl.value = String(s.intervalo_minutos || 5);
    onSchedModoChange();
  } catch(e) {}
}

// ============================================================
//  FOOTER LICENCIA
// ============================================================
async function actualizarFooterLicencia() {
  try {
    var lic   = await api('get_licencia_info');
    var label = document.getElementById('lic-footer-label');
    if (!label) return;
    if (lic && lic.valida) {
      var dias  = lic.dias_restantes;
      var color = dias > 60 ? 'rgba(255,255,255,0.65)' : dias > 15 ? 'var(--warning)' : 'var(--error)';
      label.style.color = color;
      label.textContent = 'Licencia activa · ' + dias + ' días restantes · vence ' + lic.vencimiento;
    } else {
      label.style.color = 'var(--error)';
      label.textContent = 'Sin licencia activa';
    }
  } catch(e) {}
}

// ============================================================
//  TOAST
// ============================================================
function mostrarToast(message, type) {
  type = type || 'info';
  var toast = document.createElement('div');
  toast.className   = 'toast ' + type;
  toast.textContent = message;
  var container = document.getElementById('toast-container');
  if (container) container.appendChild(toast);
  setTimeout(function() {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(function() { toast.remove(); }, 300);
  }, 3000);
}

// Alias legacy
function showToast(msg, type) { mostrarToast(msg, type); }
function update_progress(current, total) { mostrarToast('Procesando ' + current + '/' + total, 'info'); }
