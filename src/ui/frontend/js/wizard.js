// ══════════════════════════════════════════════════════════════════
//  DisateQ Motor CPE v5.0  —  Wizard JS
//  Migrado: eel.xxx() → window.pywebview.api.xxx()
//  TASK-005 — 2026-05-01
// ══════════════════════════════════════════════════════════════════

'use strict';

// ── Metadatos de pasos ─────────────────────────────────────────
const STEPS = {
  1: { title: 'Datos del cliente',     desc: 'Información básica del emisor de comprobantes' },
  2: { title: 'Fuente de datos',       desc: 'Tipo de sistema y ruta o conexión de origen' },
  3: { title: 'Verificación',          desc: 'Lectura de muestra para confirmar acceso a la fuente' },
  4: { title: 'Contrato de campos',    desc: 'Mapeo entre campos del sistema fuente y la estructura CPE' },
  5: { title: 'Series habilitadas',    desc: 'Tipos y series de comprobantes que serán procesados' },
  6: { title: 'Credenciales de envío', desc: 'Proveedor y token para envío a SUNAT' },
};

const FILE_TYPES = new Set(['dbf', 'excel', 'csv', 'access']);
const DB_PORTS   = { sqlserver: '1433', mysql: '3306', postgresql: '5432' };

// ── Estado global ──────────────────────────────────────────────
const W = {
  step:       1,
  maxStep:    1,      // máximo paso desbloqueado
  conexionOk: false,  // paso 3 validado
  endpoint:   'apifas',
  data: {
    cliente:      {},
    fuente:       {},
    contrato:     {},
    series:       {},
    credenciales: {},
  },
};

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  bindSidebarClicks();
  bindRucAutoId();
  renderSidebar();
  updateHeader();
});

// ── Sidebar clicks ─────────────────────────────────────────────
function bindSidebarClicks() {
  document.querySelectorAll('.step-row').forEach(el => {
    el.addEventListener('click', () => {
      const n = parseInt(el.dataset.step, 10);
      if (n <= W.maxStep) goTo(n);
    });
  });
}

// ── RUC → clienteId automático ─────────────────────────────────
function bindRucAutoId() {
  document.getElementById('f_ruc').addEventListener('input', () => {
    const ruc = document.getElementById('f_ruc').value.trim();
    if (ruc.length >= 8) {
      document.getElementById('f_id').value = 'cliente_' + ruc.slice(-6);
    }
  });
}

// ── Navegación principal ───────────────────────────────────────
function goTo(n) {
  document.getElementById(`p${W.step}`).classList.add('hidden');
  document.getElementById(`p${n}`).classList.remove('hidden');
  W.step = n;
  if (n > W.maxStep) W.maxStep = n;
  renderSidebar();
  updateHeader();
  updateFooter();
}

function goNext() {
  clearErrors();
  if (!validate(W.step)) return;
  saveStep(W.step);
  if (W.step === 6) { guardarWizard(); return; }
  goTo(W.step + 1);
}

function goBack() {
  if (W.step > 1) goTo(W.step - 1);
}

// ── Sidebar render ─────────────────────────────────────────────
function renderSidebar() {
  for (let i = 1; i <= 6; i++) {
    const row = document.getElementById(`sr${i}`);
    const bul = document.getElementById(`sb${i}`);
    row.className = 'step-row';
    if (i < W.step) {
      row.classList.add('done');
      bul.textContent = '✓';
    } else if (i === W.step) {
      row.classList.add('active');
      bul.textContent = i;
    } else if (i <= W.maxStep) {
      bul.textContent = i;                     // unlocked, not active
    } else {
      row.classList.add('locked');
      bul.textContent = i;
    }
  }
}

// ── Header y progress ──────────────────────────────────────────
function updateHeader() {
  const m = STEPS[W.step];
  if (!m) return;
  document.getElementById('stepTitle').textContent = m.title;
  document.getElementById('stepDesc').textContent  = m.desc;
  document.getElementById('stepBadge').textContent = `Paso ${W.step} de 6`;
  document.getElementById('progressFill').style.width = ((W.step / 6) * 100) + '%';
}

function updateFooter() {
  const back = document.getElementById('btnBack');
  const next = document.getElementById('btnNext');
  back.style.display = W.step > 1 ? 'inline-flex' : 'none';
  if (W.step === 6) {
    next.className  = 'btn btn-success';
    next.textContent = 'Guardar configuración ✓';
  } else {
    next.className  = 'btn btn-primary';
    next.textContent = 'Siguiente →';
  }
  next.disabled = false;
}

// ══════════════════════════════════════════════════════════════
//  VALIDACIONES
// ══════════════════════════════════════════════════════════════
function validate(step) {
  switch (step) {
    case 1: return v1();
    case 2: return v2();
    case 3: return v3();
    case 4: return v4();
    case 5: return v5();
    case 6: return v6();
    default: return true;
  }
}

function showErr(inputId, errId, msg) {
  const el = document.getElementById(inputId);
  const er = document.getElementById(errId);
  if (el) el.classList.add('err');
  if (er) { er.textContent = msg; er.classList.remove('hidden'); }
}

function clearErrors() {
  document.querySelectorAll('.err').forEach(e => e.classList.remove('err'));
  document.querySelectorAll('.ferr').forEach(e => e.classList.add('hidden'));
}

function v1() {
  const ruc = document.getElementById('f_ruc').value.trim();
  const rs  = document.getElementById('f_rs').value.trim();
  const reg = document.getElementById('f_reg').value;
  const id  = document.getElementById('f_id').value.trim();
  let ok = true;
  if (!/^\d{11}$/.test(ruc))    { showErr('f_ruc', 'e_ruc', 'El RUC debe tener exactamente 11 dígitos'); ok = false; }
  if (rs.length < 3)            { showErr('f_rs',  'e_rs',  'Ingresa la razón social o nombre'); ok = false; }
  if (!reg)                     { showErr('f_reg', 'e_reg', 'Selecciona el régimen fiscal'); ok = false; }
  if (!id || /\s/.test(id))     { showErr('f_id',  'e_id',  'El ID no puede estar vacío ni contener espacios'); ok = false; }
  return ok;
}

function v2() {
  const tipo = document.getElementById('f_tipo').value;
  if (!tipo) { alert('Selecciona el tipo de fuente de datos.'); return false; }
  if (FILE_TYPES.has(tipo)) {
    const ruta = document.getElementById('f_ruta').value.trim();
    if (!ruta) { showErr('f_ruta', 'e_ruta', 'La ruta es obligatoria'); return false; }
  } else {
    const host = document.getElementById('f_host').value.trim();
    const db   = document.getElementById('f_dbname').value.trim();
    const user = document.getElementById('f_dbuser').value.trim();
    if (!host || !db || !user) { alert('Host, base de datos y usuario son obligatorios.'); return false; }
  }
  return true;
}

function v3() {
  if (!W.conexionOk) {
    alert('Debes probar la conexión antes de continuar.\nHaz clic en "Probar conexión".');
    return false;
  }
  return true;
}

function v4() {
  const req = ['c_tabla', 'c_flag_c', 'c_flag_v', 'c_num', 'c_ser', 'c_tdc', 'c_fec', 'c_tot'];
  for (const id of req) {
    const el = document.getElementById(id);
    if (!el.value.trim()) {
      el.classList.add('err');
      el.focus();
      alert(`El campo "${el.placeholder}" es obligatorio en el contrato.`);
      return false;
    }
  }
  return true;
}

function v5() {
  const some = ['01','02','07','an'].some(k => document.getElementById(`tog_${k}`).checked);
  if (!some) { alert('Habilita al menos una serie antes de continuar.'); return false; }
  return true;
}

function v6() {
  const ep = W.endpoint;
  const tokens = { apifas: 'ap_tok', nubef: 'nb_tok', disateq: 'dq_key' };
  const field = tokens[ep];
  if (field && !document.getElementById(field).value.trim()) {
    alert('El token / API key es obligatorio.');
    return false;
  }
  return true;
}

// ══════════════════════════════════════════════════════════════
//  GUARDAR DATOS POR PASO → W.data
// ══════════════════════════════════════════════════════════════
function saveStep(step) {
  switch (step) {
    case 1: saveCliente();  break;
    case 2: saveFuente();   break;
    case 4: saveContrato(); break;
    case 5: saveSeries();   break;
    case 6: saveCreds();    break;
  }
}

function saveCliente() {
  W.data.cliente = {
    ruc_emisor:   document.getElementById('f_ruc').value.trim(),
    razon_social: document.getElementById('f_rs').value.trim(),
    regimen:      document.getElementById('f_reg').value,
    cliente_id:   document.getElementById('f_id').value.trim(),
  };
}

function saveFuente() {
  const tipo = document.getElementById('f_tipo').value;
  if (FILE_TYPES.has(tipo)) {
    W.data.fuente = { tipo, ruta: document.getElementById('f_ruta').value.trim() };
  } else {
    W.data.fuente = {
      tipo,
      host:     document.getElementById('f_host').value.trim(),
      puerto:   document.getElementById('f_port').value.trim(),
      database: document.getElementById('f_dbname').value.trim(),
      usuario:  document.getElementById('f_dbuser').value.trim(),
      password: document.getElementById('f_dbpass').value,
    };
  }
}

function saveContrato() {
  W.data.contrato = {
    tabla:      document.getElementById('c_tabla').value.trim(),
    flag_campo: document.getElementById('c_flag_c').value.trim(),
    flag_valor: document.getElementById('c_flag_v').value.trim(),
    flag_tipo:  document.getElementById('c_flag_t').value,
    campos: {
      numero:         document.getElementById('c_num').value.trim(),
      serie:          document.getElementById('c_ser').value.trim(),
      tipo_doc:       document.getElementById('c_tdc').value.trim(),
      fecha:          document.getElementById('c_fec').value.trim(),
      ruc_cliente:    document.getElementById('c_ruc').value.trim(),
      nombre_cliente: document.getElementById('c_nom').value.trim(),
      total:          document.getElementById('c_tot').value.trim(),
    },
    items: {
      tabla:       document.getElementById('c_ti').value.trim(),
      join_campo:  document.getElementById('c_tj').value.trim(),
      codigo:      document.getElementById('c_tc').value.trim(),
      descripcion: document.getElementById('c_td').value.trim(),
      cantidad:    document.getElementById('c_tq').value.trim(),
      precio:      document.getElementById('c_tp').value.trim(),
    },
  };
}

function saveSeries() {
  const s = {};
  const get = id => document.getElementById(id).value.trim();
  if (document.getElementById('tog_01').checked) s['01'] = [get('s_01') || 'F001'];
  if (document.getElementById('tog_02').checked) s['02'] = [get('s_02') || 'B001'];
  if (document.getElementById('tog_07').checked) {
    const vals = [get('s_07a'), get('s_07b')].filter(Boolean);
    s['07'] = vals.length ? vals : ['FC01'];
  }
  if (document.getElementById('tog_an').checked) s['anulacion'] = [get('s_an') || 'BEE1'];
  W.data.series = s;
}

function saveCreds() {
  const ep = W.endpoint;
  const c  = { proveedor: ep };
  if (ep === 'apifas')  { c.token = document.getElementById('ap_tok').value; c.url_base = document.getElementById('ap_url').value.trim(); }
  if (ep === 'nubef')   { c.token = document.getElementById('nb_tok').value; }
  if (ep === 'disateq') { c.api_key = document.getElementById('dq_key').value; c.url_base = document.getElementById('dq_url').value.trim(); }
  W.data.credenciales = c;
}

// ══════════════════════════════════════════════════════════════
//  PASO 2 — cambio de tipo fuente
// ══════════════════════════════════════════════════════════════
function onTipoFuente() {
  const tipo  = document.getElementById('f_tipo').value;
  const isFile = FILE_TYPES.has(tipo);

  // archivo
  document.getElementById('grp_file').classList.toggle('hidden', !isFile);

  // db
  ['grp_db_host','grp_db_port','grp_db_name','grp_db_user','grp_db_pass'].forEach(id => {
    document.getElementById(id).classList.toggle('hidden', isFile || !tipo);
  });

  if (isFile) {
    const labels = { dbf: 'de la carpeta DBF', excel: 'del archivo Excel', csv: 'del archivo CSV', access: 'del archivo Access' };
    const hints  = { dbf: 'Carpeta que contiene los archivos .DBF', excel: 'Archivo .xlsx o .xls', csv: 'Ruta completa al .csv', access: 'Archivo .mdb o .accdb' };
    document.getElementById('lbl_file').textContent  = labels[tipo] ? labels[tipo] + ' ' : '';
    document.getElementById('hint_ruta').textContent = hints[tipo]  || '';
  }
  if (!isFile && DB_PORTS[tipo]) {
    document.getElementById('f_port').value = DB_PORTS[tipo];
  }

  W.conexionOk = false; // resetear verificación al cambiar fuente
}

// ── Explorar ruta (diálogo nativo via PyWebView) ───────────────
function explorarRuta() {
  const tipo = document.getElementById('f_tipo').value;
  window.pywebview.api.explorar_ruta(tipo === 'dbf').then(ruta => {
    if (ruta) document.getElementById('f_ruta').value = ruta;
  });
}

// ══════════════════════════════════════════════════════════════
//  PASO 3 — TEST CONEXIÓN
// ══════════════════════════════════════════════════════════════
function testConexion() {
  saveFuente();

  const btn  = document.getElementById('btnTest');
  const spin = document.getElementById('spinTest');
  const res  = document.getElementById('resTest');
  const al   = document.getElementById('alTest');

  btn.disabled = true;
  spin.classList.remove('hidden');
  res.classList.add('hidden');
  document.getElementById('tblWrap').classList.add('hidden');
  document.getElementById('tblInfo').textContent = '';
  W.conexionOk = false;

  window.pywebview.api.wizard_test_fuente(W.data.fuente)
    .then(r => {
      btn.disabled = false;
      spin.classList.add('hidden');
      res.classList.remove('hidden');

      if (r.ok) {
        W.conexionOk = true;
        al.className   = 'al al-success';
        al.innerHTML   = `<span>✓</span><span>${r.mensaje}</span>`;
        if (r.columnas && r.filas) renderTabla(r.columnas, r.filas);
        document.getElementById('tblInfo').textContent =
          `Mostrando ${r.filas ? r.filas.length : 0} de ${r.total_registros || 0} registros`;
      } else {
        al.className = 'al al-error';
        al.innerHTML = `<span>✗</span><span>${r.error}</span>`;
      }
    })
    .catch(err => {
      btn.disabled = false;
      spin.classList.add('hidden');
      res.classList.remove('hidden');
      al.className = 'al al-error';
      al.innerHTML = `<span>✗</span><span>Error inesperado: ${err}</span>`;
    });
}

function renderTabla(cols, rows) {
  const head = document.getElementById('tblHead');
  const body = document.getElementById('tblBody');
  const wrap = document.getElementById('tblWrap');

  head.innerHTML = '<tr>' + cols.map(c => `<th>${c}</th>`).join('') + '</tr>';
  body.innerHTML = rows.map(row =>
    '<tr>' + cols.map(c => `<td title="${row[c] ?? ''}">${row[c] ?? '—'}</td>`).join('') + '</tr>'
  ).join('');
  wrap.classList.remove('hidden');
}

// ══════════════════════════════════════════════════════════════
//  PASO 4 — AUTOCONTRATO IA
// ══════════════════════════════════════════════════════════════
function autoContrato() {
  const btn = document.getElementById('btnAuto');
  btn.disabled = true;
  btn.textContent = '⏳ Analizando...';

  window.pywebview.api.wizard_generar_contrato_auto(W.data.fuente)
    .then(r => {
      btn.disabled = false;
      btn.textContent = '✦ Generar automático (IA)';
      if (r.ok) {
        poblarContrato(r.contrato);
        showAlAuto('Contrato generado. Revisa y ajusta si es necesario.', 'success');
      } else {
        showAlAuto(`No fue posible generar automáticamente: ${r.error}. Completa los campos manualmente.`, 'warn');
      }
    })
    .catch(() => {
      btn.disabled = false;
      btn.textContent = '✦ Generar automático (IA)';
      showAlAuto('Función disponible próximamente (TASK-009). Completa los campos manualmente.', 'info');
    });
}

function poblarContrato(c) {
  const set = (id, v) => { if (v) document.getElementById(id).value = v; };
  set('c_tabla',  c.tabla);
  set('c_flag_c', c.flag_campo);
  set('c_flag_v', c.flag_valor);
  if (c.flag_tipo) document.getElementById('c_flag_t').value = c.flag_tipo;
  const cm = c.campos || {};
  set('c_num', cm.numero);    set('c_ser', cm.serie);
  set('c_tdc', cm.tipo_doc);  set('c_fec', cm.fecha);
  set('c_ruc', cm.ruc_cliente); set('c_nom', cm.nombre_cliente);
  set('c_tot', cm.total);
  const ci = c.items || {};
  set('c_ti', ci.tabla);      set('c_tj', ci.join_campo);
  set('c_tc', ci.codigo);     set('c_td', ci.descripcion);
  set('c_tq', ci.cantidad);   set('c_tp', ci.precio);
}

function showAlAuto(msg, tipo) {
  const el = document.getElementById('alAuto');
  const icon = { success: '✓', warn: '⚠', info: 'ℹ', error: '✗' }[tipo] || 'ℹ';
  el.className = `al al-${tipo}`;
  el.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
  el.classList.remove('hidden');
}

// ══════════════════════════════════════════════════════════════
//  PASO 5 — TOGGLES DE SERIES
// ══════════════════════════════════════════════════════════════
function toggleSerie(k) {
  const on  = document.getElementById(`tog_${k}`).checked;
  document.getElementById(`sc_${k}`).classList.toggle('on', on);
  const ids = k === '07' ? ['s_07a','s_07b'] : [`s_${k}`];
  ids.forEach(id => {
    const el = document.getElementById(id);
    el.disabled = !on;
    el.style.opacity = on ? '1' : '0.4';
  });
}

// ══════════════════════════════════════════════════════════════
//  PASO 6 — ENDPOINT TABS
// ══════════════════════════════════════════════════════════════
function selectEp(ep) {
  W.endpoint = ep;
  ['apifas','nubef','disateq'].forEach(e => {
    document.getElementById(`et_${e}`).classList.toggle('active', e === ep);
    document.getElementById(`cred_${e}`).classList.toggle('hidden', e !== ep);
  });
}

// ══════════════════════════════════════════════════════════════
//  GUARDAR WIZARD — llamada final a Python
// ══════════════════════════════════════════════════════════════
function guardarWizard() {
  saveCreds();

  const btn = document.getElementById('btnNext');
  btn.disabled = true;
  btn.textContent = '⏳ Guardando...';

  const payload = {
    cliente:      W.data.cliente,
    fuente:       W.data.fuente,
    contrato:     W.data.contrato,
    series:       W.data.series,
    credenciales: W.data.credenciales,
  };

  window.pywebview.api.wizard_guardar(payload)
    .then(r => {
      btn.disabled = false;
      if (r.ok) {
        // mostrar pantalla de éxito
        document.getElementById('p6').classList.add('hidden');
        document.getElementById('pOK').classList.remove('hidden');
        document.getElementById('okId').textContent = r.cliente_id;
        document.getElementById('navFooter').classList.add('hidden');
        document.getElementById('mainHeader').classList.add('hidden');
        document.getElementById('progressFill').style.width = '100%';
        W.step = 7;
        renderSidebar();
      } else {
        updateFooter();
        alert(`Error al guardar: ${r.error}`);
      }
    })
    .catch(err => {
      btn.disabled = false;
      updateFooter();
      alert(`Error inesperado: ${err}`);
    });
}

// ── Acciones post-éxito ────────────────────────────────────────
function irDashboard() {
    window.pywebview.api.cargar_motor()
        .then(() => { window.location.href = 'index.html'; })
        .catch(() => { window.location.href = 'index.html'; });
}
function nuevoCliente() { window.location.reload(); }
function cancelar() {
  if (confirm('¿Cancelar la configuración? Los datos no serán guardados.')) {
    window.location.href = 'index.html';
  }
}
