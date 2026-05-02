# deploy_mapper.ps1
# Despliega motor heurístico de mapeo (Cambio 2 TASK-005)
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5

$ErrorActionPreference = "Stop"
$dl = "D:\DATA\Downloads"

# ── 1. Copiar archivos Python ──────────────────────────────────
Copy-Item "$dl\wizard_mapper.py"  "src\tools\wizard_mapper.py"  -Force
Copy-Item "$dl\wizard_service.py" "src\tools\wizard_service.py" -Force
Write-Host "[OK] wizard_mapper.py + wizard_service.py copiados" -ForegroundColor Green

# ── 2. Agregar metodo wizard_analizar_fuente en api.py ─────────
$apiPath = "src\ui\api.py"
$apiC    = Get-Content $apiPath -Raw -Encoding UTF8

if ($apiC -match "wizard_analizar_fuente") {
    Write-Host "[INFO] wizard_analizar_fuente ya existe en api.py" -ForegroundColor DarkYellow
} else {
    $metodo = @'

    def wizard_analizar_fuente(self, fuente: dict) -> dict:
        """Paso 3->4: corre heuristica de mapeo sobre la fuente."""
        try:
            from src.tools.wizard_service import analizar_fuente
            return analizar_fuente(fuente)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "score_global": 0,
                    "contrato": {}, "scores": {}, "sin_resolver": []}
'@
    $apiC = $apiC -replace '(\n    def wizard_guardar)', "$metodo`$1"
    [System.IO.File]::WriteAllText((Resolve-Path $apiPath).Path, $apiC, [System.Text.Encoding]::UTF8)
    Write-Host "[OK] wizard_analizar_fuente agregado a api.py" -ForegroundColor Green
}

# ── 3. Parchear wizard.js — goNext paso 3 llama al mapper ─────
$jsPath = "src\ui\frontend\js\wizard.js"
$jsC    = Get-Content $jsPath -Raw -Encoding UTF8

if ($jsC -match "wizard_analizar_fuente") {
    Write-Host "[INFO] wizard.js ya tiene llamada al mapper" -ForegroundColor DarkYellow
} else {
    # Reemplazar goNext para que en paso 3 llame al mapper antes de ir al 4
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
  btn.disabled    = true;
  btn.textContent = '⏳ Analizando campos...';

  window.pywebview.api.wizard_analizar_fuente(W.data.fuente)
    .then(r => {
      btn.disabled    = false;
      btn.textContent = orig;
      if (r.ok) {
        W.mapeo = r;
        poblarContrato(r.contrato);
        aplicarScores(r.scores, r.sin_resolver);
        mostrarScoreGlobal(r.score_global, r.metodo, r.sin_resolver);
      }
      goTo(4);
    })
    .catch(() => {
      btn.disabled    = false;
      btn.textContent = orig;
      goTo(4);
    });
}

function aplicarScores(scores, sinResolver) {
  const MAP = {
    'numero':         'c_num', 'serie':         'c_ser',
    'tipo_doc':       'c_tdc', 'fecha':         'c_fec',
    'ruc_cliente':    'c_ruc', 'nombre_cliente':'c_nom',
    'total':          'c_tot', 'flag_campo':    'c_flag_c',
    'join_campo':     'c_tj',  'codigo':        'c_tc',
    'descripcion':    'c_td',  'cantidad':      'c_tq',
    'precio':         'c_tp',
  };
  for (const [campo, inputId] of Object.entries(MAP)) {
    const el    = document.getElementById(inputId);
    const score = scores[campo] || 0;
    if (!el) continue;
    el.style.borderColor = score >= 0.8 ? 'var(--success)' :
                           score >= 0.5 ? 'var(--accent)'  : 'var(--error)';
    el.title = `Confianza: ${Math.round(score * 100)}%`;
    if (score >= 0.8) {
      el.style.background = 'rgba(16,185,129,.07)';
    } else if (score < 0.5 && el.value === '') {
      el.style.background = 'rgba(239,68,68,.07)';
    }
  }
}

function mostrarScoreGlobal(score, metodo, sinResolver) {
  const el = document.getElementById('alAuto');
  if (!el) return;
  const pct  = Math.round(score * 100);
  const icon = pct >= 80 ? '✓' : pct >= 50 ? '⚠' : '✗';
  const tipo = pct >= 80 ? 'success' : pct >= 50 ? 'warn' : 'error';
  let msg = `${icon} Análisis completado — Confianza global: <strong>${pct}%</strong>`;
  if (metodo === 'heuristica') msg += ' (motor heurístico)';
  if (sinResolver && sinResolver.length > 0)
    msg += `<br><span style="font-size:11px;opacity:.8">Campos a completar: ${sinResolver.join(', ')}</span>`;
  el.className = `al al-${tipo}`;
  el.innerHTML = msg;
  el.classList.remove('hidden');
}
'@

    $jsC = $jsC -replace [regex]::Escape($viejoGoNext), $nuevoGoNext
    [System.IO.File]::WriteAllText((Resolve-Path $jsPath).Path, $jsC, [System.Text.Encoding]::UTF8)
    Write-Host "[OK] wizard.js actualizado con mapper" -ForegroundColor Green
}

# ── 4. Commit ──────────────────────────────────────────────────
git add src\tools\wizard_mapper.py src\tools\wizard_service.py $apiPath $jsPath
git commit -m "feat: TASK-005 motor heuristico mapeo campos DBF -> CPE"
Write-Host "[OK] Commit realizado`n" -ForegroundColor Green

Write-Host "Prueba:" -ForegroundColor Cyan
Write-Host "  python main.py"
Write-Host "  Paso 2: ingresar D:\FFEESUNAT\Test"
Write-Host "  Paso 3: Probar conexion -> Siguiente"
Write-Host "  Paso 4: debe aparecer pre-llenado con score de confianza`n"
