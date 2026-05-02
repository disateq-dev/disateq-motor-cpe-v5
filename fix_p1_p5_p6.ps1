# fix_p1_p5_p6.ps1
# Fix régimen (quitar MYPE) + correlativos paso5 + paso6 rediseñado
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5

$ErrorActionPreference = "Stop"
$html = "src\ui\frontend\wizard.html"
$js   = "src\ui\frontend\js\wizard.js"
$c    = Get-Content $html -Raw -Encoding UTF8
$jsC  = Get-Content $js   -Raw -Encoding UTF8

# ══════════════════════════════════════════════════════════════════
#  FIX 1 — Quitar MYPE del select de régimen
# ══════════════════════════════════════════════════════════════════
$c = $c -replace '<option value="MYPE">.*?</option>\s*', ''
Write-Host "[OK] Regimen MYPE eliminado" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════════
#  FIX 2 — Paso 5: correlativos (reemplazar series-grid completo)
# ══════════════════════════════════════════════════════════════════
$oldGrid = $c -match '(?s)(<div class="series-grid">)(.*?)(</div>\s*</div>\s*</div>\s*<!-- ── PASO 6)'
$p5Nuevo = @'
        <div class="series-grid">

          <!-- 01 Facturas -->
          <div class="scard" id="sc_01">
            <div class="scard-hdr">
              <div><div class="scard-name">Facturas</div><div class="scard-type">Tipo 01 — F</div></div>
              <label class="tog"><input type="checkbox" id="tog_01" onchange="toggleSerie('01')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)">Serie</label>
              <input type="text" id="s_01" class="mono" placeholder="F001" disabled></div>
            <div class="f mt8"><label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)">Correlativo inicio</label>
              <input type="number" id="corr_01" class="mono" value="1" min="1" disabled style="width:110px;opacity:.4"></div>
          </div>

          <!-- 02 Boletas -->
          <div class="scard" id="sc_02">
            <div class="scard-hdr">
              <div><div class="scard-name">Boletas</div><div class="scard-type">Tipo 02 — B</div></div>
              <label class="tog"><input type="checkbox" id="tog_02" onchange="toggleSerie('02')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)">Serie</label>
              <input type="text" id="s_02" class="mono" placeholder="B001" disabled></div>
            <div class="f mt8"><label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)">Correlativo inicio</label>
              <input type="number" id="corr_02" class="mono" value="1" min="1" disabled style="width:110px;opacity:.4"></div>
          </div>

          <!-- 07 Notas crédito -->
          <div class="scard" id="sc_07">
            <div class="scard-hdr">
              <div><div class="scard-name">Notas de crédito</div><div class="scard-type">Tipo 07 — FC / BC</div></div>
              <label class="tog"><input type="checkbox" id="tog_07" onchange="toggleSerie('07')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)">Series (FC / BC)</label>
              <div class="row" style="gap:6px">
                <input type="text" id="s_07a" class="mono" placeholder="FC01" disabled style="flex:1">
                <input type="text" id="s_07b" class="mono" placeholder="BC01" disabled style="flex:1">
              </div>
            </div>
            <div class="f mt8"><label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)">Correlativo inicio</label>
              <input type="number" id="corr_07" class="mono" value="1" min="1" disabled style="width:110px;opacity:.4"></div>
          </div>

          <!-- AN Anulaciones -->
          <div class="scard" id="sc_an">
            <div class="scard-hdr">
              <div><div class="scard-name">Anulaciones</div><div class="scard-type">Resumen — BEE / FEE</div></div>
              <label class="tog"><input type="checkbox" id="tog_an" onchange="toggleSerie('an')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)">Serie</label>
              <input type="text" id="s_an" class="mono" placeholder="BEE1" disabled></div>
            <div class="f mt8"><label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)">Correlativo inicio</label>
              <input type="number" id="corr_an" class="mono" value="1" min="1" disabled style="width:110px;opacity:.4"></div>
          </div>

        </div>
'@

# Usar regex para reemplazar el bloque series-grid completo
$c = [regex]::Replace($c, '(?s)<div class="series-grid">.*?</div>\s*</div>\s*</div>\s*\n\s*</div>\s*\n\s*</div>', $p5Nuevo + "`n      </div>`n    </div>")
Write-Host "[OK] Paso 5 correlativos OK" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════════
#  FIX 3 — Paso 6: rediseño completo (servicio libre + N endpoints)
# ══════════════════════════════════════════════════════════════════

# CSS adicional para paso 6
$cssP6 = @'
/* ─── STEP 6 endpoints ────────────────────────────────────── */
.ep-card { background:var(--surface-2); border:1.5px solid var(--border); border-radius:9px; padding:14px 16px; display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.ep-card select, .ep-card input { background:var(--bg); border:1.5px solid var(--border); border-radius:7px; color:var(--text); font-family:var(--mono); font-size:13px; padding:7px 10px; outline:none; }
.ep-card select:focus, .ep-card input:focus { border-color:var(--accent); }
.ep-card select { width:170px; flex-shrink:0; }
.ep-card input  { flex:1; min-width:0; }
.ep-card .ep-del { background:transparent; border:1px solid var(--border); color:var(--text-muted); border-radius:6px; cursor:pointer; padding:5px 9px; font-size:13px; flex-shrink:0; }
.ep-card .ep-del:hover { border-color:var(--error); color:var(--error); }
.ep-empty { font-size:12px; color:var(--text-muted); font-style:italic; padding:8px 0; }
'@
$c = $c -replace '(?s)(\.ep-tabs.*?\.ep-tab\.active.*?\})', "$1`n$cssP6"

# Reemplazar bloque paso 6 completo
$oldP6Pattern = '(?s)<!-- ── PASO 6 — CREDENCIALES[^>]*>.*?</div>\s*\n\s*</div>\s*\n\s*</div>'
$nuevoP6 = @'
    <!-- ── PASO 6 — SERVICIO DE ENVÍO ─────────────────── -->
    <div class="panel hidden" id="p6">
      <div style="max-width:560px">

        <!-- Nombre del servicio -->
        <div class="fg w1" style="margin-bottom:20px">
          <div class="f">
            <label>Nombre del servicio <span class="req">*</span></label>
            <input type="text" id="sv_nombre" placeholder="Ej: APIFAS, Nubefact, SUNAT directo..." autocomplete="off">
            <div class="hint">Nombre con el que identificarás este proveedor de envío</div>
            <div class="ferr hidden" id="e_sv_nombre"></div>
          </div>
          <div class="f">
            <label>Tipo de integración <span class="req">*</span></label>
            <select id="sv_tipo">
              <option value="">— Seleccionar —</option>
              <option value="api_rest">API REST</option>
              <option value="ose">OSE (Operador de Servicios Electrónicos)</option>
              <option value="pse">PSE (Proveedor de Servicios Electrónicos)</option>
              <option value="sunat_soap">SUNAT SOAP directo</option>
            </select>
            <div class="ferr hidden" id="e_sv_tipo"></div>
          </div>
        </div>

        <!-- Credenciales (opcionales) -->
        <div style="font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-muted);font-family:var(--mono);margin-bottom:10px">
          Credenciales <span style="font-weight:400;text-transform:none;letter-spacing:0">(opcional según proveedor)</span>
        </div>
        <div class="fg" style="margin-bottom:22px">
          <div class="f">
            <label>Usuario / RUC</label>
            <input type="text" id="sv_user" class="mono" placeholder="Opcional" autocomplete="off">
          </div>
          <div class="f">
            <label>Token / API Key / Clave SOL</label>
            <input type="password" id="sv_token" class="mono" placeholder="Opcional" autocomplete="new-password">
          </div>
        </div>

        <!-- Endpoints dinámicos -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
          <div style="font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-muted);font-family:var(--mono)">
            Endpoints
          </div>
          <button class="btn btn-outline btn-sm" onclick="agregarEndpoint()">+ Agregar endpoint</button>
        </div>
        <div id="ep_lista">
          <div class="ep-empty" id="ep_vacio">Sin endpoints configurados. Agrega al menos uno de tipo Comprobantes.</div>
        </div>
        <div class="ferr hidden mt8" id="e_eps"></div>

      </div>
    </div>
'@

$c = [regex]::Replace($c, $oldP6Pattern, $nuevoP6)
Write-Host "[OK] Paso 6 rediseñado" -ForegroundColor Green

[System.IO.File]::WriteAllText((Resolve-Path $html).Path, $c, [System.Text.Encoding]::UTF8)

# ══════════════════════════════════════════════════════════════════
#  wizard.js — updates
# ══════════════════════════════════════════════════════════════════

# 1. toggleSerie con corr
if (-not ($jsC -match "corrEl")) {
    $jsC = $jsC -replace '(?s)(function toggleSerie\(k\) \{.*?\})', @'
function toggleSerie(k) {
  const on = document.getElementById(`tog_${k}`).checked;
  document.getElementById(`sc_${k}`).classList.toggle('on', on);
  const ids = k === '07' ? ['s_07a','s_07b'] : [`s_${k}`];
  ids.forEach(id => {
    const el = document.getElementById(id); if (!el) return;
    el.disabled = !on; el.style.opacity = on ? '1' : '0.4';
  });
  const corrEl = document.getElementById(`corr_${k}`);
  if (corrEl) { corrEl.disabled = !on; corrEl.style.opacity = on ? '1' : '0.4'; }
}
'@
    Write-Host "[OK] toggleSerie actualizado" -ForegroundColor Green
}

# 2. saveSeries con correlativos
$jsC = $jsC -replace '(?s)function saveSeries\(\) \{.*?\}', @'
function saveSeries() {
  const s    = {};
  const get  = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
  const corr = id => { const el = document.getElementById(id); return el ? (parseInt(el.value)||1) : 1; };
  if (document.getElementById('tog_01').checked)
    s['01'] = [{ serie: get('s_01')||'F001', correlativo_inicio: corr('corr_01') }];
  if (document.getElementById('tog_02').checked)
    s['02'] = [{ serie: get('s_02')||'B001', correlativo_inicio: corr('corr_02') }];
  if (document.getElementById('tog_07').checked) {
    const arr = [];
    if (get('s_07a')) arr.push({ serie: get('s_07a'), correlativo_inicio: corr('corr_07') });
    if (get('s_07b')) arr.push({ serie: get('s_07b'), correlativo_inicio: corr('corr_07') });
    s['07'] = arr.length ? arr : [{ serie:'FC01', correlativo_inicio:1 }];
  }
  if (document.getElementById('tog_an').checked)
    s['anulacion'] = [{ serie: get('s_an')||'BEE1', correlativo_inicio: corr('corr_an') }];
  W.data.series = s;
}
'@
Write-Host "[OK] saveSeries con correlativos" -ForegroundColor Green

# 3. Reemplazar bloque selectEp + credenciales por lógica de endpoints dinámicos
$jsC = $jsC -replace '(?s)// ══+\s*//  PASO 6 — ENDPOINT TABS\s*// ══+.*?function selectEp\(ep\) \{.*?\}', ''

# 4. v6 — validar servicio + min 1 endpoint comprobantes
$jsC = $jsC -replace '(?s)function v6\(\) \{.*?\}', @'
function v6() {
  const nombre = document.getElementById('sv_nombre').value.trim();
  const tipo   = document.getElementById('sv_tipo').value;
  let ok = true;
  if (!nombre) { showErr('sv_nombre','e_sv_nombre','El nombre del servicio es obligatorio'); ok = false; }
  if (!tipo)   { showErr('sv_tipo',  'e_sv_tipo',  'Selecciona el tipo de integración'); ok = false; }
  const eps = W.data.endpoints_lista || [];
  const tieneComp = eps.some(e => e.tipo === 'comprobantes' && e.url);
  if (!tieneComp) {
    const el = document.getElementById('e_eps');
    el.textContent = 'Agrega al menos un endpoint de tipo Comprobantes.';
    el.classList.remove('hidden');
    ok = false;
  }
  return ok;
}
'@
Write-Host "[OK] v6() actualizado" -ForegroundColor Green

# 5. saveCreds — guardar servicio + endpoints dinámicos
$jsC = $jsC -replace '(?s)function saveCreds\(\) \{.*?\}', @'
function saveCreds() {
  W.data.credenciales = {
    nombre:    document.getElementById('sv_nombre').value.trim(),
    tipo:      document.getElementById('sv_tipo').value,
    usuario:   document.getElementById('sv_user').value.trim(),
    token:     document.getElementById('sv_token').value,
    endpoints: W.data.endpoints_lista || [],
  };
}
'@
Write-Host "[OK] saveCreds actualizado" -ForegroundColor Green

# 6. Agregar funciones de endpoints dinámicos al final del archivo
$epFns = @'

// ══════════════════════════════════════════════════════════════
//  PASO 6 — ENDPOINTS DINÁMICOS
// ══════════════════════════════════════════════════════════════
if (!W.data.endpoints_lista) W.data.endpoints_lista = [];

const EP_TIPOS = [
  { value: 'comprobantes', label: 'Comprobantes (F/B)' },
  { value: 'anulaciones',  label: 'Anulaciones / Resumen' },
  { value: 'guias',        label: 'Guías de remisión' },
  { value: 'retenciones',  label: 'Retenciones / Percepciones' },
  { value: 'soap',         label: 'SUNAT SOAP' },
];

function agregarEndpoint() {
  const id  = 'ep_' + Date.now();
  const ep  = { id, tipo: 'comprobantes', url: '' };
  W.data.endpoints_lista.push(ep);
  renderEndpoints();
  document.getElementById('ep_vacio').classList.add('hidden');
}

function eliminarEndpoint(id) {
  W.data.endpoints_lista = W.data.endpoints_lista.filter(e => e.id !== id);
  renderEndpoints();
  if (!W.data.endpoints_lista.length)
    document.getElementById('ep_vacio').classList.remove('hidden');
}

function renderEndpoints() {
  const lista = document.getElementById('ep_lista');
  // mantener el div vacio
  const vacio = document.getElementById('ep_vacio');
  lista.innerHTML = '';
  lista.appendChild(vacio);

  W.data.endpoints_lista.forEach(ep => {
    const div = document.createElement('div');
    div.className = 'ep-card';
    div.id = 'epc_' + ep.id;

    const sel = document.createElement('select');
    sel.title = 'Tipo de endpoint';
    EP_TIPOS.forEach(t => {
      const o = document.createElement('option');
      o.value = t.value; o.textContent = t.label;
      if (t.value === ep.tipo) o.selected = true;
      sel.appendChild(o);
    });
    sel.addEventListener('change', () => {
      ep.tipo = sel.value;
      document.getElementById('e_eps').classList.add('hidden');
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
'@

$jsC = $jsC.TrimEnd() + "`n$epFns`n"
Write-Host "[OK] Funciones endpoints dinamicos agregadas" -ForegroundColor Green

[System.IO.File]::WriteAllText((Resolve-Path $js).Path, $jsC, [System.Text.Encoding]::UTF8)

# ══════════════════════════════════════════════════════════════════
#  Commit
# ══════════════════════════════════════════════════════════════════
git add $html $js
git commit -m "feat: TASK-005 paso6 servicio libre + N endpoints dinamicos + correlativos paso5"
Write-Host "[OK] Commit realizado`n" -ForegroundColor Green
Write-Host "Reinicia: python main.py`n" -ForegroundColor Cyan
