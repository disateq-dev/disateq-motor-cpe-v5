# fix_p5_p6.ps1
# Reescribe paso 5 (correlativos) y paso 6 (endpoints sin token obligatorio)
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5

$ErrorActionPreference = "Stop"
$html = "src\ui\frontend\wizard.html"
$c    = Get-Content $html -Raw -Encoding UTF8

# ══════════════════════════════════════════════════════════════════
#  PASO 5 — reemplazar bloque completo series-grid
# ══════════════════════════════════════════════════════════════════
$viejoP5 = @'
        <div class="series-grid">
          <!-- 01 Facturas -->
          <div class="scard" id="sc_01">
            <div class="scard-hdr">
              <div><div class="scard-name">Facturas</div><div class="scard-type">Tipo 01 — F</div></div>
              <label class="tog"><input type="checkbox" id="tog_01" onchange="toggleSerie('01')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_01" class="mono" placeholder="F001" disabled></div>
          </div>
          <!-- 02 Boletas -->
          <div class="scard" id="sc_02">
            <div class="scard-hdr">
              <div><div class="scard-name">Boletas</div><div class="scard-type">Tipo 02 — B</div></div>
              <label class="tog"><input type="checkbox" id="tog_02" onchange="toggleSerie('02')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_02" class="mono" placeholder="B001" disabled></div>
          </div>
          <!-- 07 Notas crédito -->
          <div class="scard" id="sc_07">
            <div class="scard-hdr">
              <div><div class="scard-name">Notas de crédito</div><div class="scard-type">Tipo 07 — FC / BC</div></div>
              <label class="tog"><input type="checkbox" id="tog_07" onchange="toggleSerie('07')"><span class="tog-s"></span></label>
            </div>
            <div class="row">
              <input type="text" id="s_07a" class="mono" placeholder="FC01" disabled style="flex:1">
              <input type="text" id="s_07b" class="mono" placeholder="BC01" disabled style="flex:1">
            </div>
          </div>
          <!-- AN Anulaciones -->
          <div class="scard" id="sc_an">
            <div class="scard-hdr">
              <div><div class="scard-name">Anulaciones</div><div class="scard-type">Resumen — BEE / FEE</div></div>
              <label class="tog"><input type="checkbox" id="tog_an" onchange="toggleSerie('an')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_an" class="mono" placeholder="BEE1" disabled></div>
          </div>
        </div>
'@

$nuevoP5 = @'
        <div class="series-grid">
          <!-- 01 Facturas -->
          <div class="scard" id="sc_01">
            <div class="scard-hdr">
              <div><div class="scard-name">Facturas</div><div class="scard-type">Tipo 01 — F</div></div>
              <label class="tog"><input type="checkbox" id="tog_01" onchange="toggleSerie('01')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_01" class="mono" placeholder="F001" disabled></div>
            <div class="f mt8">
              <label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em">Correlativo inicio</label>
              <input type="number" id="corr_01" class="mono" value="1" min="1" disabled style="width:110px;opacity:.4">
            </div>
          </div>
          <!-- 02 Boletas -->
          <div class="scard" id="sc_02">
            <div class="scard-hdr">
              <div><div class="scard-name">Boletas</div><div class="scard-type">Tipo 02 — B</div></div>
              <label class="tog"><input type="checkbox" id="tog_02" onchange="toggleSerie('02')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_02" class="mono" placeholder="B001" disabled></div>
            <div class="f mt8">
              <label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em">Correlativo inicio</label>
              <input type="number" id="corr_02" class="mono" value="1" min="1" disabled style="width:110px;opacity:.4">
            </div>
          </div>
          <!-- 07 Notas crédito -->
          <div class="scard" id="sc_07">
            <div class="scard-hdr">
              <div><div class="scard-name">Notas de crédito</div><div class="scard-type">Tipo 07 — FC / BC</div></div>
              <label class="tog"><input type="checkbox" id="tog_07" onchange="toggleSerie('07')"><span class="tog-s"></span></label>
            </div>
            <div class="row" style="gap:6px">
              <input type="text" id="s_07a" class="mono" placeholder="FC01" disabled style="flex:1">
              <input type="text" id="s_07b" class="mono" placeholder="BC01" disabled style="flex:1">
            </div>
            <div class="f mt8">
              <label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em">Correlativo inicio</label>
              <input type="number" id="corr_07" class="mono" value="1" min="1" disabled style="width:110px;opacity:.4">
            </div>
          </div>
          <!-- AN Anulaciones -->
          <div class="scard" id="sc_an">
            <div class="scard-hdr">
              <div><div class="scard-name">Anulaciones</div><div class="scard-type">Resumen — BEE / FEE</div></div>
              <label class="tog"><input type="checkbox" id="tog_an" onchange="toggleSerie('an')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_an" class="mono" placeholder="BEE1" disabled></div>
            <div class="f mt8">
              <label style="font-size:10px;text-transform:uppercase;letter-spacing:.06em">Correlativo inicio</label>
              <input type="number" id="corr_an" class="mono" value="1" min="1" disabled style="width:110px;opacity:.4">
            </div>
          </div>
        </div>
'@

if ($c -match [regex]::Escape("scard-name`">Facturas")) {
    $c = $c.Replace($viejoP5, $nuevoP5)
    Write-Host "[OK] Paso 5 — correlativos agregados" -ForegroundColor Green
} else {
    Write-Host "[WARN] No se encontro bloque paso 5 exacto" -ForegroundColor Yellow
}

# ══════════════════════════════════════════════════════════════════
#  PASO 6 — reemplazar bloque credenciales APIFAS
#  Token NO obligatorio — APIFAS usa endpoints, no token
# ══════════════════════════════════════════════════════════════════
$viejoP6 = @'
        <div id="cred_apifas" class="fg w1">
          <div class="f">
            <label>Token API <span class="req">*</span></label>
            <input type="password" id="ap_tok" class="mono" placeholder="••••••••••••" autocomplete="new-password">
          </div>
          <div class="f">
            <label>URL Base</label>
            <input type="text" id="ap_url" class="mono" value="https://api.apifas.com/v1">
          </div>
          <div class="al al-info"><span>ℹ</span><span>Test de envío real en TASK-008. Aquí solo se guardan las credenciales.</span></div>
        </div>
'@

$nuevoP6 = @'
        <div id="cred_apifas" class="fg w1">
          <div class="f">
            <label>URL Comprobantes <span class="req">*</span></label>
            <input type="text" id="ap_url_comp" class="mono" placeholder="https://..." autocomplete="off">
            <div class="hint">Endpoint para envío de facturas y boletas</div>
          </div>
          <div class="f">
            <label>URL Anulaciones</label>
            <input type="text" id="ap_url_anul" class="mono" placeholder="https://..." autocomplete="off">
            <div class="hint">Endpoint para resúmenes de anulación. Opcional.</div>
          </div>
          <div class="f">
            <label>Token / API Key</label>
            <input type="password" id="ap_tok" class="mono" placeholder="Opcional — dejar vacío si no aplica" autocomplete="new-password">
          </div>
          <div class="al al-info"><span>ℹ</span><span>Test de envío real en TASK-008. Aquí solo se guardan los endpoints.</span></div>
        </div>
'@

if ($c -match [regex]::Escape("Token API")) {
    $c = $c.Replace($viejoP6, $nuevoP6)
    Write-Host "[OK] Paso 6 — APIFAS endpoints sin token obligatorio" -ForegroundColor Green
} else {
    Write-Host "[WARN] No se encontro bloque APIFAS" -ForegroundColor Yellow
}

[System.IO.File]::WriteAllText((Resolve-Path $html).Path, $c, [System.Text.Encoding]::UTF8)

# ── Parchear wizard.js — toggleSerie con correlativos ─────────
$js  = "src\ui\frontend\js\wizard.js"
$jsC = Get-Content $js -Raw -Encoding UTF8

# toggleSerie — agregar habilitacion de correlativo
$viejoTog = @'
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
'@

$nuevoTog = @'
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

if ($jsC -match [regex]::Escape("el.disabled = !on;")) {
    $jsC = $jsC.Replace($viejoTog, $nuevoTog)
    Write-Host "[OK] toggleSerie con correlativos" -ForegroundColor Green
}

# saveSeries — incluir correlativo_inicio
$viejoSS = @'
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
'@

$nuevoSS = @'
function saveSeries() {
  const s    = {};
  const get  = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
  const corr = id => { const el = document.getElementById(id); return el ? (parseInt(el.value) || 1) : 1; };
  if (document.getElementById('tog_01').checked)
    s['01'] = [{ serie: get('s_01') || 'F001', correlativo_inicio: corr('corr_01') }];
  if (document.getElementById('tog_02').checked)
    s['02'] = [{ serie: get('s_02') || 'B001', correlativo_inicio: corr('corr_02') }];
  if (document.getElementById('tog_07').checked) {
    const arr = [];
    if (get('s_07a')) arr.push({ serie: get('s_07a'), correlativo_inicio: corr('corr_07') });
    if (get('s_07b')) arr.push({ serie: get('s_07b'), correlativo_inicio: corr('corr_07') });
    s['07'] = arr.length ? arr : [{ serie: 'FC01', correlativo_inicio: 1 }];
  }
  if (document.getElementById('tog_an').checked)
    s['anulacion'] = [{ serie: get('s_an') || 'BEE1', correlativo_inicio: corr('corr_an') }];
  W.data.series = s;
}
'@

$jsC = $jsC.Replace($viejoSS, $nuevoSS)
Write-Host "[OK] saveSeries con correlativos" -ForegroundColor Green

# saveCreds — actualizar para APIFAS con endpoints
$viejoCreds = @'
  if (ep === 'apifas')  { c.token = document.getElementById('ap_tok').value; c.url_base = document.getElementById('ap_url').value.trim(); }
'@
$nuevoCreds = @'
  if (ep === 'apifas')  {
    c.url_comprobantes = document.getElementById('ap_url_comp') ? document.getElementById('ap_url_comp').value.trim() : '';
    c.url_anulaciones  = document.getElementById('ap_url_anul') ? document.getElementById('ap_url_anul').value.trim() : '';
    const tok = document.getElementById('ap_tok');
    if (tok && tok.value.trim()) c.token = tok.value.trim();
  }
'@
$jsC = $jsC.Replace($viejoCreds, $nuevoCreds)
Write-Host "[OK] saveCreds APIFAS con endpoints" -ForegroundColor Green

# v6 — token no obligatorio para apifas
$viejoV6 = @'
  const ep = W.endpoint;
  const tokens = { apifas: 'ap_tok', nubef: 'nb_tok', disateq: 'dq_key' };
  const field = tokens[ep];
  if (field && !document.getElementById(field).value.trim()) {
    alert('El token / API key es obligatorio.');
    return false;
  }
  return true;
'@
$nuevoV6 = @'
  const ep = W.endpoint;
  // APIFAS requiere al menos la URL de comprobantes
  if (ep === 'apifas') {
    const urlEl = document.getElementById('ap_url_comp');
    if (urlEl && !urlEl.value.trim()) {
      alert('La URL de comprobantes es obligatoria para APIFAS.');
      return false;
    }
  }
  // Nubefact y DisateQ requieren token
  if (ep === 'nubef' && !document.getElementById('nb_tok').value.trim()) {
    alert('El token de Nubefact es obligatorio.'); return false;
  }
  if (ep === 'disateq' && !document.getElementById('dq_key').value.trim()) {
    alert('La API Key de DisateQ es obligatoria.'); return false;
  }
  return true;
'@
$jsC = $jsC.Replace($viejoV6, $nuevoV6)
Write-Host "[OK] v6() validacion endpoints actualizada" -ForegroundColor Green

[System.IO.File]::WriteAllText((Resolve-Path $js).Path, $jsC, [System.Text.Encoding]::UTF8)

# ── Commit ─────────────────────────────────────────────────────
git add $html $js
git commit -m "fix: TASK-005 paso5 correlativos + paso6 APIFAS endpoints sin token obligatorio"
Write-Host "[OK] Commit realizado`n" -ForegroundColor Green
Write-Host "Listo. Reinicia: python main.py`n" -ForegroundColor Cyan
