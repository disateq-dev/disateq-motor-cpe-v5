# deploy_mapper_v2.ps1
# Cambio 2 TASK-005:
#   - Motor heurístico mapeo DBF->CPE
#   - Botón "Probar mapeo" en paso 4
#   - Correlativos inicio en paso 5
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5

$ErrorActionPreference = "Stop"
$dl = "D:\DATA\Downloads"

# ── 1. Copiar archivos Python ──────────────────────────────────
Copy-Item "$dl\wizard_mapper.py"  "src\tools\wizard_mapper.py"  -Force
Copy-Item "$dl\wizard_service.py" "src\tools\wizard_service.py" -Force
Write-Host "[OK] wizard_mapper.py + wizard_service.py" -ForegroundColor Green

# ── 2. api.py — agregar 2 metodos nuevos ──────────────────────
$apiPath = "src\ui\api.py"
$apiC    = Get-Content $apiPath -Raw -Encoding UTF8

if (-not ($apiC -match "wizard_analizar_fuente")) {
    $m1 = @'

    def wizard_analizar_fuente(self, fuente: dict) -> dict:
        """Paso 3->4: heuristica de mapeo sobre la fuente."""
        try:
            from src.tools.wizard_service import analizar_fuente
            return analizar_fuente(fuente)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "score_global": 0,
                    "contrato": {}, "scores": {}, "sin_resolver": []}
'@
    $apiC = $apiC -replace '(\n    def wizard_guardar)', "$m1`$1"
    Write-Host "[OK] wizard_analizar_fuente agregado" -ForegroundColor Green
}

if (-not ($apiC -match "wizard_probar_mapeo")) {
    $m2 = @'

    def wizard_probar_mapeo(self, fuente: dict, contrato: dict) -> dict:
        """
        Paso 4 — lee 5 registros reales usando el contrato actual
        y retorna los valores extraídos para que el técnico valide.
        """
        try:
            from src.tools.wizard_service import probar_mapeo
            return probar_mapeo(fuente, contrato)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "filas": []}
'@
    $apiC = $apiC -replace '(\n    def wizard_guardar)', "$m2`$1"
    Write-Host "[OK] wizard_probar_mapeo agregado" -ForegroundColor Green
}

[System.IO.File]::WriteAllText((Resolve-Path $apiPath).Path, $apiC, [System.Text.Encoding]::UTF8)

# ── 3. wizard.html — paso 4: boton Probar mapeo + tabla resultado
$htmlPath = "src\ui\frontend\wizard.html"
$htmlC    = Get-Content $htmlPath -Raw -Encoding UTF8

if (-not ($htmlC -match "btnPrueba")) {

    # 3a. Agregar CSS para tabla de prueba (antes de </style>)
    $cssPrueba = @'
/* ─── STEP 4 prueba mapeo ─────────────────────────────────── */
.prueba-wrap { margin-top:18px; border:1px solid var(--border); border-radius:8px; overflow:auto; max-width:100%; }
.prueba-tbl  { width:100%; border-collapse:collapse; font-size:12px; font-family:var(--mono); }
.prueba-tbl th { background:var(--surface-2); padding:8px 12px; text-align:left; color:var(--accent); border-bottom:1px solid var(--border); white-space:nowrap; }
.prueba-tbl td { padding:7px 12px; border-bottom:1px solid rgba(36,40,64,.4); color:var(--text); white-space:nowrap; max-width:160px; overflow:hidden; text-overflow:ellipsis; }
.prueba-tbl td.vacio { color:var(--error); font-style:italic; }
.prueba-tbl tr:last-child td { border-bottom:none; }
.score-bar { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.score-pct  { font-family:var(--mono); font-size:20px; font-weight:500; }
.score-pct.hi  { color:var(--success); }
.score-pct.mid { color:var(--accent); }
.score-pct.lo  { color:var(--error); }
'@
    $htmlC = $htmlC -replace '</style>', "$cssPrueba`n</style>"

    # 3b. Reemplazar bloque paso 4 — agregar boton Probar mapeo y tabla
    $viejop4hdr = @'
        <div class="row" style="justify-content:space-between; margin-bottom:22px">
          <div style="font-size:13px; color:var(--text-muted)">
            Mapea los campos del sistema fuente a la estructura CPE.
          </div>
          <button class="btn btn-outline btn-sm" id="btnAuto" onclick="autoContrato()">✦ Generar automático (IA)</button>
        </div>
        <div id="alAuto" class="hidden" style="margin-bottom:16px"></div>
'@
    $nuevop4hdr = @'
        <!-- Score global + acciones -->
        <div class="row" style="justify-content:space-between; align-items:flex-start; margin-bottom:18px; gap:12px; flex-wrap:wrap">
          <div id="scoreWrap" class="hidden" style="flex:1; min-width:200px">
            <div class="score-bar">
              <div class="score-pct hi" id="scorePct">—</div>
              <div style="font-size:12px; color:var(--text-muted); line-height:1.4" id="scoreDesc">Analizando...</div>
            </div>
          </div>
          <div class="row" style="gap:8px; flex-shrink:0">
            <button class="btn btn-outline btn-sm" id="btnPrueba" onclick="probarMapeo()">▶ Probar mapeo</button>
            <button class="btn btn-outline btn-sm" id="btnAuto" onclick="autoContrato()">✦ IA</button>
          </div>
        </div>
        <div id="alAuto" class="hidden" style="margin-bottom:12px"></div>
        <!-- Tabla resultado prueba -->
        <div id="pruebaSec" class="hidden" style="margin-bottom:20px">
          <div style="font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:var(--text-muted); margin-bottom:8px; font-family:var(--mono)">Muestra de datos reales</div>
          <div id="alPrueba" class="hidden" style="margin-bottom:8px"></div>
          <div class="prueba-wrap hidden" id="pruebaWrap">
            <table class="prueba-tbl"><thead id="pruebaTHead"></thead><tbody id="pruebaTBody"></tbody></table>
          </div>
        </div>
'@
    $htmlC = $htmlC -replace [regex]::Escape($viejop4hdr), $nuevop4hdr
    Write-Host "[OK] wizard.html paso 4 actualizado" -ForegroundColor Green
}

# ── 4. wizard.html — paso 5: correlativos por serie ───────────
if (-not ($htmlC -match "corr_01")) {

    # Boletas
    $htmlC = $htmlC -replace @'
          <!-- 02 Boletas -->
          <div class="scard" id="sc_02">
            <div class="scard-hdr">
              <div><div class="scard-name">Boletas</div><div class="scard-type">Tipo 02 — B</div></div>
              <label class="tog"><input type="checkbox" id="tog_02" onchange="toggleSerie('02')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_02" class="mono" placeholder="B001" disabled></div>
          </div>
'@, @'
          <!-- 02 Boletas -->
          <div class="scard" id="sc_02">
            <div class="scard-hdr">
              <div><div class="scard-name">Boletas</div><div class="scard-type">Tipo 02 — B</div></div>
              <label class="tog"><input type="checkbox" id="tog_02" onchange="toggleSerie('02')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_02" class="mono" placeholder="B001" disabled></div>
            <div class="f mt8"><label style="font-size:10px">Correlativo inicio</label>
              <input type="number" id="corr_02" class="mono" value="1" min="1" disabled style="width:100px"></div>
          </div>
'@

    # Facturas
    $htmlC = $htmlC -replace @'
          <!-- 01 Facturas -->
          <div class="scard" id="sc_01">
            <div class="scard-hdr">
              <div><div class="scard-name">Facturas</div><div class="scard-type">Tipo 01 — F</div></div>
              <label class="tog"><input type="checkbox" id="tog_01" onchange="toggleSerie('01')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_01" class="mono" placeholder="F001" disabled></div>
          </div>
'@, @'
          <!-- 01 Facturas -->
          <div class="scard" id="sc_01">
            <div class="scard-hdr">
              <div><div class="scard-name">Facturas</div><div class="scard-type">Tipo 01 — F</div></div>
              <label class="tog"><input type="checkbox" id="tog_01" onchange="toggleSerie('01')"><span class="tog-s"></span></label>
            </div>
            <div class="f"><input type="text" id="s_01" class="mono" placeholder="F001" disabled></div>
            <div class="f mt8"><label style="font-size:10px">Correlativo inicio</label>
              <input type="number" id="corr_01" class="mono" value="1" min="1" disabled style="width:100px"></div>
          </div>
'@

    Write-Host "[OK] wizard.html paso 5 correlativos agregados" -ForegroundColor Green
}

[System.IO.File]::WriteAllText((Resolve-Path $htmlPath).Path, $htmlC, [System.Text.Encoding]::UTF8)

# ── 5. wizard.js — goNext mapper + probarMapeo + saveSeries corr
$jsPath = "src\ui\frontend\js\wizard.js"
$jsC    = Get-Content $jsPath -Raw -Encoding UTF8

# 5a. goNext con analizarYAvanzar
if (-not ($jsC -match "analizarYAvanzar")) {
    $viejoGoNext = @'
function goNext() {
  clearErrors();
  if (!validate(W.step)) return;
  saveStep(W.step);
  if (W.step === 6) { guardarWizard(); return; }
  goTo(W.step + 1);
}
'@
    $nuevoGoNext = @'
function goNext() {
  clearErrors();
  if (!validate(W.step)) return;
  saveStep(W.step);
  if (W.step === 6) { guardarWizard(); return; }
  if (W.step === 3) { analizarYAvanzar(); return; }
  goTo(W.step + 1);
}

function analizarYAvanzar() {
  const btn  = document.getElementById('btnNext');
  const orig = btn.textContent;
  btn.disabled = true; btn.textContent = '⏳ Analizando campos...';
  window.pywebview.api.wizard_analizar_fuente(W.data.fuente)
    .then(r => {
      btn.disabled = false; btn.textContent = orig;
      W.mapeo = r || {};
      if (r && r.ok) {
        poblarContrato(r.contrato || {});
        aplicarScores(r.scores || {}, r.sin_resolver || []);
        mostrarScoreGlobal(r.score_global || 0, r.metodo, r.sin_resolver || []);
      }
      goTo(4);
    })
    .catch(() => { btn.disabled = false; btn.textContent = orig; goTo(4); });
}

function aplicarScores(scores, sinResolver) {
  const MAP = {
    'numero':'c_num','serie':'c_ser','tipo_doc':'c_tdc','fecha':'c_fec',
    'ruc_cliente':'c_ruc','nombre_cliente':'c_nom','total':'c_tot',
    'flag_campo':'c_flag_c','join_campo':'c_tj','codigo':'c_tc',
    'descripcion':'c_td','cantidad':'c_tq','precio':'c_tp',
  };
  for (const [campo, id] of Object.entries(MAP)) {
    const el = document.getElementById(id); if (!el) continue;
    const sc = scores[campo] || 0;
    el.style.borderColor = sc>=0.8 ? 'var(--success)' : sc>=0.5 ? 'var(--accent)' : 'var(--error)';
    el.title = `Confianza: ${Math.round(sc*100)}%`;
    el.style.background = sc>=0.8 ? 'rgba(16,185,129,.07)' : sc<0.5&&!el.value ? 'rgba(239,68,68,.07)' : '';
  }
}

function mostrarScoreGlobal(score, metodo, sinResolver) {
  const sw = document.getElementById('scoreWrap');
  const sp = document.getElementById('scorePct');
  const sd = document.getElementById('scoreDesc');
  if (!sw) return;
  const pct = Math.round(score * 100);
  sp.textContent = pct + '%';
  sp.className = 'score-pct ' + (pct>=80?'hi':pct>=50?'mid':'lo');
  let desc = 'Confianza del mapeo automático';
  if (metodo === 'manual') desc = 'Completa los campos manualmente';
  if (sinResolver && sinResolver.length)
    desc += ` — pendientes: ${sinResolver.join(', ')}`;
  sd.textContent = desc;
  sw.classList.remove('hidden');
}

function probarMapeo() {
  const contrato = buildContratoActual();
  const btn = document.getElementById('btnPrueba');
  const orig = btn.textContent;
  btn.disabled = true; btn.textContent = '⏳ Probando...';
  const sec = document.getElementById('pruebaSec');
  sec.classList.remove('hidden');
  window.pywebview.api.wizard_probar_mapeo(W.data.fuente, contrato)
    .then(r => {
      btn.disabled = false; btn.textContent = orig;
      const al   = document.getElementById('alPrueba');
      const wrap = document.getElementById('pruebaWrap');
      if (r.ok && r.filas && r.filas.length > 0) {
        al.className = 'al al-success'; al.innerHTML = `✓ ${r.filas.length} registro(s) leídos correctamente.`;
        al.classList.remove('hidden');
        renderPrueba(r.columnas, r.filas);
        wrap.classList.remove('hidden');
      } else {
        al.className = 'al al-error';
        al.innerHTML = `✗ ${r.error || 'No se pudieron leer registros. Verifica los campos.'}`;
        al.classList.remove('hidden');
        wrap.classList.add('hidden');
      }
    })
    .catch(e => {
      btn.disabled = false; btn.textContent = orig;
      const al = document.getElementById('alPrueba');
      al.className = 'al al-error'; al.innerHTML = `✗ Error: ${e}`;
      al.classList.remove('hidden');
    });
}

function renderPrueba(cols, filas) {
  const thead = document.getElementById('pruebaTHead');
  const tbody = document.getElementById('pruebaTBody');
  thead.innerHTML = '<tr>' + cols.map(c=>`<th>${c}</th>`).join('') + '</tr>';
  tbody.innerHTML = filas.map(f =>
    '<tr>' + cols.map(c => {
      const v = f[c] ?? '';
      const cls = (!v || v === 'None' || v === '') ? ' class="vacio"' : '';
      return `<td${cls} title="${v}">${v || '(vacío)'}</td>`;
    }).join('') + '</tr>'
  ).join('');
}

function buildContratoActual() {
  return {
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
'@
    $jsC = $jsC -replace [regex]::Escape($viejoGoNext), $nuevoGoNext
    Write-Host "[OK] wizard.js goNext + mapper + probar agregados" -ForegroundColor Green
}

# 5b. toggleSerie — habilitar correlativo
$viejoToggle = @'
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
$nuevoToggle = @'
function toggleSerie(k) {
  const on  = document.getElementById(`tog_${k}`).checked;
  document.getElementById(`sc_${k}`).classList.toggle('on', on);
  const ids = k === '07' ? ['s_07a','s_07b'] : [`s_${k}`];
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.disabled = !on;
    el.style.opacity = on ? '1' : '0.4';
  });
  // correlativo
  const corrId = `corr_${k}`;
  const corr   = document.getElementById(corrId);
  if (corr) { corr.disabled = !on; corr.style.opacity = on ? '1' : '0.4'; }
}
'@
$jsC = $jsC -replace [regex]::Escape($viejoToggle), $nuevoToggle

# 5c. saveSeries — incluir correlativo_inicio
$viejoSave = @'
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
$nuevoSave = @'
function saveSeries() {
  const s   = {};
  const get = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
  const getCorr = id => { const el = document.getElementById(id); return el ? (parseInt(el.value)||1) : 1; };
  if (document.getElementById('tog_01').checked)
    s['01'] = [{ serie: get('s_01') || 'F001', correlativo_inicio: getCorr('corr_01') }];
  if (document.getElementById('tog_02').checked)
    s['02'] = [{ serie: get('s_02') || 'B001', correlativo_inicio: getCorr('corr_02') }];
  if (document.getElementById('tog_07').checked) {
    const arr = [];
    if (get('s_07a')) arr.push({ serie: get('s_07a'), correlativo_inicio: getCorr('corr_07a') });
    if (get('s_07b')) arr.push({ serie: get('s_07b'), correlativo_inicio: getCorr('corr_07b') });
    s['07'] = arr.length ? arr : [{ serie: 'FC01', correlativo_inicio: 1 }];
  }
  if (document.getElementById('tog_an').checked)
    s['anulacion'] = [{ serie: get('s_an') || 'BEE1', correlativo_inicio: getCorr('corr_an') }];
  W.data.series = s;
}
'@
$jsC = $jsC -replace [regex]::Escape($viejoSave), $nuevoSave

[System.IO.File]::WriteAllText((Resolve-Path $jsPath).Path, $jsC, [System.Text.Encoding]::UTF8)
Write-Host "[OK] wizard.js series con correlativos" -ForegroundColor Green

# ── 6. wizard_service.py — agregar probar_mapeo() ─────────────
$svcPath = "src\tools\wizard_service.py"
$svcC    = Get-Content $svcPath -Raw -Encoding UTF8

if (-not ($svcC -match "def probar_mapeo")) {
    $fnPrueba = @'


# ══════════════════════════════════════════════════════════════════
#  PROBAR MAPEO — lee 5 registros reales con el contrato actual
# ══════════════════════════════════════════════════════════════════

def probar_mapeo(fuente: dict, contrato: dict) -> dict:
    """
    Lee hasta 5 registros reales de la tabla de comprobantes
    usando el contrato actual y retorna los valores extraídos.
    """
    tipo = fuente.get("tipo", "").lower()
    if tipo != "dbf":
        return {"ok": False, "error": "Prueba disponible solo para DBF por ahora."}

    try:
        from dbfread import DBF as DbfReader
    except ImportError:
        return {"ok": False, "error": "dbfread no instalado."}

    ruta   = fuente.get("ruta", "").strip()
    tabla  = contrato.get("tabla", "").strip()
    campos = contrato.get("campos", {})
    flag_c = contrato.get("flag_campo", "").strip()

    if not tabla:
        return {"ok": False, "error": "Tabla de comprobantes no definida en el contrato."}

    dbf_path = Path(ruta) / f"{tabla}.dbf"
    if not dbf_path.exists():
        dbf_path = Path(ruta) / f"{tabla.upper()}.DBF"
    if not dbf_path.exists():
        return {"ok": False, "error": f"Archivo no encontrado: {tabla}.dbf en {ruta}"}

    try:
        t = DbfReader(str(dbf_path), encoding="latin-1", load=False)
        # Columnas a mostrar: campos mapeados + flag
        cols_cpe = {
            "serie":          campos.get("serie", ""),
            "numero":         campos.get("numero", ""),
            "tipo_doc":       campos.get("tipo_doc", ""),
            "fecha":          campos.get("fecha", ""),
            "ruc_cliente":    campos.get("ruc_cliente", ""),
            "nombre_cliente": campos.get("nombre_cliente", ""),
            "total":          campos.get("total", ""),
        }
        if flag_c:
            cols_cpe["flag"] = flag_c

        cols_mostrar = [k for k, v in cols_cpe.items() if v]

        filas = []
        for i, rec in enumerate(t):
            if i >= 5:
                break
            fila = {}
            for col_cpe in cols_mostrar:
                campo_real = cols_cpe[col_cpe]
                v = rec.get(campo_real, "")
                fila[col_cpe] = str(v).strip() if v is not None else ""
            filas.append(fila)

        if not filas:
            return {"ok": False, "error": "La tabla está vacía o no tiene registros."}

        return {
            "ok":      True,
            "columnas": cols_mostrar,
            "filas":    filas,
            "tabla":    tabla,
        }
    except Exception as exc:
        return {"ok": False, "error": f"Error leyendo {tabla}.dbf: {exc}"}
'@
    $svcC = $svcC + $fnPrueba
    [System.IO.File]::WriteAllText((Resolve-Path $svcPath).Path, $svcC, [System.Text.Encoding]::UTF8)
    Write-Host "[OK] probar_mapeo() agregado a wizard_service.py" -ForegroundColor Green
}

# ── 7. Commit ──────────────────────────────────────────────────
git add src\tools\wizard_mapper.py src\tools\wizard_service.py `
        $apiPath $htmlPath $jsPath
git commit -m "feat: TASK-005 probar mapeo paso4 + correlativos paso5 + heuristica"
Write-Host "[OK] Commit realizado`n" -ForegroundColor Green

Write-Host "Prueba:" -ForegroundColor Cyan
Write-Host "  python main.py"
Write-Host "  Paso 2: D:\FFEESUNAT\Test -> Siguiente"
Write-Host "  Paso 3: Probar conexion -> Siguiente (analiza automaticamente)"
Write-Host "  Paso 4: campos pre-llenados con scores + boton Probar mapeo"
Write-Host "  Paso 5: series con correlativo inicio`n"
