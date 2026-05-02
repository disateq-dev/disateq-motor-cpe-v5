// ══════════════════════════════════════════════════════════════════
//  DisateQ Motor CPE v5.0  —  wizard.js
//  TASK-005 — 2026-05-02  REESCRITURA COMPLETA
//  PyWebView: window.pywebview.api.metodo().then()
// ══════════════════════════════════════════════════════════════════

'use strict';

// ── Metadatos de pasos ─────────────────────────────────────────
const STEPS = {
  1: { title: 'Datos del cliente',      desc: 'Información básica del emisor de comprobantes' },
  2: { title: 'Fuente de datos',        desc: 'Tipo de sistema y ruta o conexión de origen' },
  3: { title: 'Verificación',           desc: 'Lectura de muestra para confirmar acceso a la fuente' },
  4: { title: 'Contrato de campos',     desc: 'Mapeo entre campos del sistema fuente y la estructura CPE' },
  5: { title: 'Series habilitadas',     desc: 'Tipos y series de comprobantes que serán procesados' },
  6: { title: 'Servicio de envío',      desc: 'Proveedor, credenciales y endpoints de envío a SUNAT' },
};

const FILE_TYPES = new Set(['dbf', 'excel', 'csv', 'access']);
const DB_PORTS   = { sqlserver: '1433', mysql: '3306', postgresql: '5432' };

const EP_TIPOS = [
  { value: 'comprobantes', label: 'Comprobantes (F/B)' },
  { value: 'anulaciones',  label: 'Anulaciones / Resumen' },
  { value: 'guias',        label: 'Guías de remisión' },
  { value: 'retenciones',  label: 'Retenciones / Percepciones' },
  { value: 'soap',         label: 'SUNAT SOAP' },
];

// ── Estado global ──────────────────────────────────────────────
const W = {
  step:    1,
  maxStep: 1,
  conexionOk: false,
  mapeo:   {},
  data: {
    cliente:      {},
    fuente:       {},
    contrato:     {},
    series:       {},
    credenciales: {},
    endpoints_lista: [],
  },
};

// ══════════════════════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  bindSidebarClicks();
  bindRucAutoId();
  renderSidebar();
  updateHeader();
  updateFooter();
});

function bindSidebarClicks() {
  document.querySelectorAll('.step-row').forEach(el => {
    el.addEventListener('click', () => {
      const n = parseInt(el.dataset.step, 10);
      if (n <= W.maxStep) goTo(n);
    });
  });
}

function bindRucAutoId() {
  const rucEl = document.getElementById('f_ruc');
  const idEl  = document.getElementById('f_id');
  if (!rucEl || !idEl) return;
  rucEl.addEventListener('input', () => {
    const ruc = rucEl.value.trim();
    if (ruc.length >= 6) {
      idEl.value = 'cliente_' + ruc.slice(-6);
    }
  });
}

// ══════════════════════════════════════════════════════════════
//  NAVEGACIÓN
// ══════════════════════════════════════════════════════════════
function goTo(n) {
  const cur = document.getElementById('p' + W.step);
  if (cur) cur.classList.add('hidden');
  const next = document.getElementById('p' + n);
  if (next) next.classList.remove('hidden');
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
  if (W.step === 3) { analizarYAvanzar(); return; }
  goTo(W.step + 1);
}

function goBack() {
  if (W.step > 1) goTo(W.step - 1);
}

function cancelar() {
  if (confirm('¿Cancelar la configuración? Los datos no serán guardados.')) {
    window.location.href = 'index.html';
  }
}

// ══════════════════════════════════════════════════════════════
//  SIDEBAR / HEADER / FOOTER
// ══════════════════════════════════════════════════════════════
function renderSidebar() {
  for (let i = 1; i <= 6; i++) {
    const row = document.getElementById('sr' + i);
    const bul = document.getElementById('sb' + i);
    if (!row || !bul) continue;
    row.className = 'step-row';
    if (i < W.step) {
      row.classList.add('done');
      bul.textContent = '✓';
    } else if (i === W.step) {
      row.classList.add('active');
      bul.textContent = i;
    } else if (i <= W.maxStep) {
      bul.textContent = i;
    } else {
      row.classList.add('locked');
      bul.textContent = i;
    }
  }
}

function updateHeader() {
  const m = STEPS[W.step];
  if (!m) return;
  const t = document.getElementById('stepTitle');
  const d = document.getElementById('stepDesc');
  const b = document.getElementById('stepBadge');
  const p = document.getElementById('progressFill');
  if (t) t.textContent = m.title;
  if (d) d.textContent = m.desc;
  if (b) b.textContent = 'Paso ' + W.step + ' de 6';
  if (p) p.style.width = ((W.step / 6) * 100) + '%';
}

function updateFooter() {
  const back = document.getElementById('btnBack');
  const next = document.getElementById('btnNext');
  if (!back || !next) return;
  back.style.display = W.step > 1 ? 'inline-flex' : 'none';
  if (W.step === 6) {
    next.className   = 'btn btn-success';
    next.textContent = 'Guardar configuración ✓';
  } else {
    next.className   = 'btn btn-primary';
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
  const ruc   = document.getElementById('f_ruc').value.trim();
  const rs    = document.getElementById('f_rs').value.trim();
  const alias = document.getElementById('f_alias').value.trim();
  const reg   = document.getElementById('f_reg').value;
  const id    = document.getElementById('f_id').value.trim();
  let ok = true;
  if (!/^\d{11}$/.test(ruc))  { showErr('f_ruc',   'e_ruc',   'El RUC debe tener exactamente 11 dígitos'); ok = false; }
  if (rs.length < 3)          { showErr('f_rs',    'e_rs',    'Ingresa la razón social'); ok = false; }
  if (!alias)                 { showErr('f_alias', 'e_alias', 'El alias del local es obligatorio'); ok = false; }
  if (!reg)                   { showErr('f_reg',   'e_reg',   'Selecciona el régimen tributario'); ok = false; }
  if (!id || /\s/.test(id))   { showErr('f_id',    'e_id',    'El ID no puede estar vacío ni tener espacios'); ok = false; }
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
    alert('Debes probar la conexión antes de continuar.');
    return false;
  }
  return true;
}

function v4() {
  const req = ['c_tabla', 'c_flag_c', 'c_flag_v', 'c_num', 'c_ser', 'c_tdc', 'c_fec', 'c_tot'];
  for (const id of req) {
    const el = document.getElementById(id);
    if (el && !el.value.trim()) {
      el.classList.add('err');
      el.focus();
      alert('El campo "' + (el.placeholder || id) + '" es obligatorio en el contrato.');
      return false;
    }
  }
  return true;
}

function v5() {
  const some = ['01','02','07','an'].some(k => {
    const el = document.getElementById('tog_' + k);
    return el && el.checked;
  });
  if (!some) { alert('Habilita al menos una serie antes de continuar.'); return false; }
  return true;
}

function v6() {
  const nombre = document.getElementById('sv_nombre') ? document.getElementById('sv_nombre').value.trim() : '';
  const tipo   = document.getElementById('sv_tipo')   ? document.getElementById('sv_tipo').value : '';
  let ok = true;
  if (!nombre) { showErr('sv_nombre', 'e_sv_nombre', 'El nombre del servicio es obligatorio'); ok = false; }
  if (!tipo)   { showErr('sv_tipo',   'e_sv_tipo',   'Selecciona el tipo de integración'); ok = false; }
  const eps = W.data.endpoints_lista || [];
  const tieneComp = eps.some(e => e.tipo === 'comprobantes' && e.url && e.url.trim());
  if (!tieneComp) {
    const el = document.getElementById('e_eps');
    if (el) { el.textContent = 'Agrega al menos un endpoint de tipo Comprobantes.'; el.classList.remove('hidden'); }
    ok = false;
  }
  return ok;
}

// ══════════════════════════════════════════════════════════════
//  GUARDAR DATOS POR PASO
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
    ruc_emisor:       document.getElementById('f_ruc').value.trim(),
    razon_social:     document.getElementById('f_rs').value.trim(),
    nombre_comercial: document.getElementById('f_nc') ? document.getElementById('f_nc').value.trim() : '',
    alias:            document.getElementById('f_alias').value.trim(),
    regimen:          document.getElementById('f_reg').value,
    cliente_id:       document.getElementById('f_id').value.trim(),
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
      numero:          document.getElementById('c_num').value.trim(),
      serie:           document.getElementById('c_ser').value.trim(),
      tipo_doc:        document.getElementById('c_tdc').value.trim(),
      fecha:           document.getElementById('c_fec').value.trim(),
      ruc_cliente:     document.getElementById('c_ruc').value.trim(),
      nombre_cliente:  document.getElementById('c_nom').value.trim(),
      total:           document.getElementById('c_tot').value.trim(),
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
  const s    = {};
  const get  = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
  const corr = id => { const el = document.getElementById(id); return el ? (parseInt(el.value) || 1) : 1; };
  if (document.getElementById('tog_01') && document.getElementById('tog_01').checked)
    s['01'] = [{ serie: get('s_01') || 'F001', correlativo_inicio: corr('corr_01') }];
  if (document.getElementById('tog_02') && document.getElementById('tog_02').checked)
    s['02'] = [{ serie: get('s_02') || 'B001', correlativo_inicio: corr('corr_02') }];
  if (document.getElementById('tog_07') && document.getElementById('tog_07').checked) {
    const arr = [];
    if (get('s_07a')) arr.push({ serie: get('s_07a'), correlativo_inicio: corr('corr_07') });
    if (get('s_07b')) arr.push({ serie: get('s_07b'), correlativo_inicio: corr('corr_07') });
    s['07'] = arr.length ? arr : [{ serie: 'FC01', correlativo_inicio: 1 }];
  }
  if (document.getElementById('tog_an') && document.getElementById('tog_an').checked)
    s['anulacion'] = [{ serie: get('s_an') || 'BEE1', correlativo_inicio: corr('corr_an') }];
  W.data.series = s;
}

function saveCreds() {
  W.data.credenciales = {
    nombre:    document.getElementById('sv_nombre') ? document.getElementById('sv_nombre').value.trim() : '',
    tipo:      document.getElementById('sv_tipo')   ? document.getElementById('sv_tipo').value : '',
    usuario:   document.getElementById('sv_user')   ? document.getElementById('sv_user').value.trim() : '',
    token:     document.getElementById('sv_token')  ? document.getElementById('sv_token').value : '',
    endpoints: W.data.endpoints_lista || [],
  };
}

// ══════════════════════════════════════════════════════════════
//  PASO 2 — TIPO FUENTE
// ══════════════════════════════════════════════════════════════
function onTipoFuente() {
  const tipo   = document.getElementById('f_tipo').value;
  const isFile = FILE_TYPES.has(tipo);

  document.getElementById('grp_file').classList.toggle('hidden', !isFile);
  ['grp_db_host','grp_db_port','grp_db_name','grp_db_user','grp_db_pass'].forEach(id => {
    document.getElementById(id).classList.toggle('hidden', isFile || !tipo);
  });

  if (isFile) {
    const labels = { dbf: 'de la carpeta DBF', excel: 'del archivo Excel', csv: 'del archivo CSV', access: 'del archivo Access' };
    const hints  = { dbf: 'Carpeta que contiene los archivos .DBF', excel: 'Archivo .xlsx o .xls', csv: 'Ruta completa al .csv', access: 'Archivo .mdb o .accdb' };
    const lbl = document.getElementById('lbl_file');
    const hnt = document.getElementById('hint_ruta');
    if (lbl) lbl.textContent = labels[tipo] ? labels[tipo] + ' ' : '';
    if (hnt) hnt.textContent = hints[tipo] || '';
  }
  if (!isFile && DB_PORTS[tipo]) {
    const portEl = document.getElementById('f_port');
    if (portEl) portEl.value = DB_PORTS[tipo];
  }
  W.conexionOk = false;
}

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
  if (spin) spin.classList.remove('hidden');
  if (res)  res.classList.add('hidden');
  const tblWrap = document.getElementById('tblWrap');
  if (tblWrap) tblWrap.classList.add('hidden');
  W.conexionOk = false;

  window.pywebview.api.wizard_test_fuente(W.data.fuente)
    .then(r => {
      btn.disabled = false;
      if (spin) spin.classList.add('hidden');
      if (res)  res.classList.remove('hidden');
      if (r.ok) {
        W.conexionOk = true;
        al.className = 'al al-success';
        al.innerHTML = '<span>✓</span><span>' + r.mensaje + '</span>';
        if (r.columnas && r.filas) renderTabla(r.columnas, r.filas);
        const info = document.getElementById('tblInfo');
        if (info) info.textContent = 'Mostrando ' + (r.filas ? r.filas.length : 0) + ' de ' + (r.total_registros || 0) + ' registros';
      } else {
        al.className = 'al al-error';
        al.innerHTML = '<span>✗</span><span>' + r.error + '</span>';
      }
    })
    .catch(err => {
      btn.disabled = false;
      if (spin) spin.classList.add('hidden');
      if (res)  res.classList.remove('hidden');
      al.className = 'al al-error';
      al.innerHTML = '<span>✗</span><span>Error: ' + err + '</span>';
    });
}

function renderTabla(cols, rows) {
  const head = document.getElementById('tblHead');
  const body = document.getElementById('tblBody');
  const wrap = document.getElementById('tblWrap');
  if (!head || !body || !wrap) return;
  head.innerHTML = '<tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr>';
  body.innerHTML = rows.map(row =>
    '<tr>' + cols.map(c => '<td title="' + (row[c] || '') + '">' + (row[c] || '—') + '</td>').join('') + '</tr>'
  ).join('');
  wrap.classList.remove('hidden');
}

// ══════════════════════════════════════════════════════════════
//  PASO 3→4 — ANÁLISIS HEURÍSTICO
// ══════════════════════════════════════════════════════════════
function analizarYAvanzar() {
  const btn  = document.getElementById('btnNext');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Analizando campos...';

  window.pywebview.api.wizard_analizar_fuente(W.data.fuente)
    .then(r => {
      btn.disabled = false;
      btn.textContent = orig;
      W.mapeo = r || {};
      if (r && r.ok) {
        poblarContrato(r.contrato || {});
        aplicarScores(r.scores || {}, r.sin_resolver || []);
        mostrarScoreGlobal(r.score_global || 0, r.metodo, r.sin_resolver || []);
      }
      goTo(4);
    })
    .catch(() => {
      btn.disabled = false;
      btn.textContent = orig;
      goTo(4);
    });
}

function aplicarScores(scores, sinResolver) {
  const MAP = {
    numero: 'c_num', serie: 'c_ser', tipo_doc: 'c_tdc', fecha: 'c_fec',
    ruc_cliente: 'c_ruc', nombre_cliente: 'c_nom', total: 'c_tot',
    flag_campo: 'c_flag_c', join_campo: 'c_tj', codigo: 'c_tc',
    descripcion: 'c_td', cantidad: 'c_tq', precio: 'c_tp',
  };
  for (const [campo, id] of Object.entries(MAP)) {
    const el = document.getElementById(id);
    if (!el) continue;
    const sc = scores[campo] || 0;
    el.style.borderColor = sc >= 0.8 ? 'var(--success)' : sc >= 0.5 ? 'var(--accent)' : 'var(--error)';
    el.title = 'Confianza: ' + Math.round(sc * 100) + '%';
    el.style.background = sc >= 0.8 ? 'rgba(16,185,129,.07)' : (sc < 0.5 && !el.value ? 'rgba(239,68,68,.07)' : '');
  }
}

function mostrarScoreGlobal(score, metodo, sinResolver) {
  const sw = document.getElementById('scoreWrap');
  const sp = document.getElementById('scorePct');
  const sd = document.getElementById('scoreDesc');
  if (!sw) return;
  const pct = Math.round(score * 100);
  if (sp) { sp.textContent = pct + '%'; sp.className = 'score-pct ' + (pct >= 80 ? 'hi' : pct >= 50 ? 'mid' : 'lo'); }
  if (sd) {
    let desc = 'Confianza del mapeo automático';
    if (metodo === 'manual') desc = 'Completa los campos manualmente';
    if (sinResolver && sinResolver.length) desc += ' — pendientes: ' + sinResolver.join(', ');
    sd.textContent = desc;
  }
  sw.classList.remove('hidden');
}

// ══════════════════════════════════════════════════════════════
//  PASO 4 — CONTRATO
// ══════════════════════════════════════════════════════════════
function poblarContrato(c) {
  const set = (id, v) => { const el = document.getElementById(id); if (el && v) el.value = v; };
  set('c_tabla',  c.tabla);
  set('c_flag_c', c.flag_campo);
  set('c_flag_v', c.flag_valor);
  if (c.flag_tipo) { const el = document.getElementById('c_flag_t'); if (el) el.value = c.flag_tipo; }
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

function autoContrato() {
  const btn = document.getElementById('btnAuto');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Analizando...'; }

  window.pywebview.api.wizard_generar_contrato_auto(W.data.fuente)
    .then(r => {
      if (btn) { btn.disabled = false; btn.textContent = '✦ IA'; }
      if (r.ok) {
        poblarContrato(r.contrato);
        showAlAuto('Contrato generado. Revisa y ajusta si es necesario.', 'success');
      } else {
        showAlAuto('No fue posible generar automáticamente: ' + r.error, 'warn');
      }
    })
    .catch(() => {
      if (btn) { btn.disabled = false; btn.textContent = '✦ IA'; }
      showAlAuto('Función disponible en TASK-009. Completa los campos manualmente.', 'info');
    });
}

function showAlAuto(msg, tipo) {
  const el = document.getElementById('alAuto');
  if (!el) return;
  const icon = { success: '✓', warn: '⚠', info: 'ℹ', error: '✗' }[tipo] || 'ℹ';
  el.className = 'al al-' + tipo;
  el.innerHTML = '<span>' + icon + '</span><span>' + msg + '</span>';
  el.classList.remove('hidden');
}

function probarMapeo() {
  const contrato = buildContratoActual();
  const btn  = document.getElementById('btnPrueba');
  const orig = btn ? btn.textContent : '';
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Probando...'; }

  const sec = document.getElementById('pruebaSec');
  if (sec) sec.classList.remove('hidden');

  window.pywebview.api.wizard_probar_mapeo(W.data.fuente, contrato)
    .then(r => {
      if (btn) { btn.disabled = false; btn.textContent = orig; }
      const al   = document.getElementById('alPrueba');
      const wrap = document.getElementById('pruebaWrap');
      if (r.ok && r.filas && r.filas.length > 0) {
        if (al) { al.className = 'al al-success'; al.innerHTML = '✓ ' + r.filas.length + ' registro(s) leídos correctamente.'; al.classList.remove('hidden'); }
        if (wrap) { renderPrueba(r.columnas, r.filas); wrap.classList.remove('hidden'); }
      } else {
        if (al)   { al.className = 'al al-error'; al.innerHTML = '✗ ' + (r.error || 'No se pudieron leer registros.'); al.classList.remove('hidden'); }
        if (wrap) wrap.classList.add('hidden');
      }
    })
    .catch(e => {
      if (btn) { btn.disabled = false; btn.textContent = orig; }
      const al = document.getElementById('alPrueba');
      if (al) { al.className = 'al al-error'; al.innerHTML = '✗ Error: ' + e; al.classList.remove('hidden'); }
    });
}

function renderPrueba(cols, filas) {
  const thead = document.getElementById('pruebaTHead');
  const tbody = document.getElementById('pruebaTBody');
  if (!thead || !tbody) return;
  thead.innerHTML = '<tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr>';
  tbody.innerHTML = filas.map(f =>
    '<tr>' + cols.map(c => {
      const v   = f[c] || '';
      const cls = (!v || v === 'None') ? ' class="vacio"' : '';
      return '<td' + cls + ' title="' + v + '">' + (v || '(vacío)') + '</td>';
    }).join('') + '</tr>'
  ).join('');
}

function buildContratoActual() {
  const gv = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
  return {
    tabla:      gv('c_tabla'),
    flag_campo: gv('c_flag_c'),
    flag_valor: gv('c_flag_v'),
    flag_tipo:  gv('c_flag_t'),
    campos: {
      numero:          gv('c_num'),
      serie:           gv('c_ser'),
      tipo_doc:        gv('c_tdc'),
      fecha:           gv('c_fec'),
      ruc_cliente:     gv('c_ruc'),
      nombre_cliente:  gv('c_nom'),
      total:           gv('c_tot'),
    },
    items: {
      tabla:       gv('c_ti'),
      join_campo:  gv('c_tj'),
      codigo:      gv('c_tc'),
      descripcion: gv('c_td'),
      cantidad:    gv('c_tq'),
      precio:      gv('c_tp'),
    },
  };
}

// ══════════════════════════════════════════════════════════════
//  PASO 5 — SERIES Y CORRELATIVOS
// ══════════════════════════════════════════════════════════════
function toggleSerie(k) {
  const tog = document.getElementById('tog_' + k);
  if (!tog) return;
  const on = tog.checked;
  const sc = document.getElementById('sc_' + k);
  if (sc) sc.classList.toggle('on', on);
  const ids = k === '07' ? ['s_07a', 's_07b'] : ['s_' + k];
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.disabled = !on;
    el.style.opacity = on ? '1' : '0.4';
  });
  const corrEl = document.getElementById('corr_' + k);
  if (corrEl) { corrEl.disabled = !on; corrEl.style.opacity = on ? '1' : '0.4'; }
}

// ══════════════════════════════════════════════════════════════
//  PASO 6 — ENDPOINTS DINÁMICOS
// ══════════════════════════════════════════════════════════════
function agregarEndpoint() {
  const id = 'ep_' + Date.now();
  W.data.endpoints_lista.push({ id, tipo: 'comprobantes', url: '' });
  renderEndpoints();
  const vacio = document.getElementById('ep_vacio');
  if (vacio) vacio.classList.add('hidden');
}

function eliminarEndpoint(id) {
  W.data.endpoints_lista = W.data.endpoints_lista.filter(e => e.id !== id);
  renderEndpoints();
  if (!W.data.endpoints_lista.length) {
    const vacio = document.getElementById('ep_vacio');
    if (vacio) vacio.classList.remove('hidden');
  }
}

function renderEndpoints() {
  const lista = document.getElementById('ep_lista');
  if (!lista) return;
  const vacio = document.getElementById('ep_vacio');
  lista.innerHTML = '';
  if (vacio) lista.appendChild(vacio);

  W.data.endpoints_lista.forEach(ep => {
    const div = document.createElement('div');
    div.className = 'ep-card';
    div.id = 'epc_' + ep.id;

    const sel = document.createElement('select');
    EP_TIPOS.forEach(t => {
      const o = document.createElement('option');
      o.value = t.value; o.textContent = t.label;
      if (t.value === ep.tipo) o.selected = true;
      sel.appendChild(o);
    });
    sel.addEventListener('change', () => {
      ep.tipo = sel.value;
      const errEl = document.getElementById('e_eps');
      if (errEl) errEl.classList.add('hidden');
    });

    const inp = document.createElement('input');
    inp.type = 'text'; inp.value = ep.url;
    inp.placeholder = 'https://...';
    inp.addEventListener('input', () => { ep.url = inp.value.trim(); });

    const btn = document.createElement('button');
    btn.className = 'ep-del'; btn.textContent = '×';
    btn.onclick = () => eliminarEndpoint(ep.id);

    div.appendChild(sel); div.appendChild(inp); div.appendChild(btn);
    lista.appendChild(div);
  });
}

// ══════════════════════════════════════════════════════════════
//  GUARDAR WIZARD FINAL
// ══════════════════════════════════════════════════════════════
function guardarWizard() {
  saveCreds();
  const btn = document.getElementById('btnNext');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Guardando...'; }

  const payload = {
    cliente:      W.data.cliente,
    fuente:       W.data.fuente,
    contrato:     W.data.contrato,
    series:       W.data.series,
    credenciales: W.data.credenciales,
  };

  window.pywebview.api.wizard_guardar(payload)
    .then(r => {
      if (btn) btn.disabled = false;
      if (r.ok) {
        const p6 = document.getElementById('p6');
        const pOK = document.getElementById('pOK');
        const nav = document.getElementById('navFooter');
        const hdr = document.getElementById('mainHeader');
        const pf  = document.getElementById('progressFill');
        const okId = document.getElementById('okId');
        if (p6)    p6.classList.add('hidden');
        if (pOK)   pOK.classList.remove('hidden');
        if (nav)   nav.classList.add('hidden');
        if (hdr)   hdr.classList.add('hidden');
        if (pf)    pf.style.width = '100%';
        if (okId)  okId.textContent = r.cliente_id;
        W.step = 7;
        renderSidebar();
      } else {
        updateFooter();
        alert('Error al guardar: ' + r.error);
      }
    })
    .catch(err => {
      if (btn) btn.disabled = false;
      updateFooter();
      alert('Error inesperado: ' + err);
    });
}

// ══════════════════════════════════════════════════════════════
//  POST-ÉXITO
// ══════════════════════════════════════════════════════════════
function irDashboard() {
  window.pywebview.api.cargar_motor()
    .then(() => { window.location.href = 'index.html'; })
    .catch(() => { window.location.href = 'index.html'; });
}

function nuevoCliente() {
  window.location.reload();
}
