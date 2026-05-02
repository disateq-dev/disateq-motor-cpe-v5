# patch_wizard_paso1.ps1
# Actualiza paso 1 del wizard con campos completos de cliente
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5

$ErrorActionPreference = "Stop"
$html = "src\ui\frontend\wizard.html"
$c    = Get-Content $html -Raw -Encoding UTF8

$viejo = @'
    <!-- ── PASO 1 — CLIENTE ─────────────────────────────── -->
    <div class="panel" id="p1">
      <div class="fg">
        <div class="f s2">
          <label>RUC Emisor <span class="req">*</span></label>
          <input type="text" id="f_ruc" class="mono" maxlength="11" placeholder="20XXXXXXXXX" autocomplete="off">
          <div class="hint">11 dígitos — persona natural (10) o empresa (20)</div>
          <div class="ferr hidden" id="e_ruc"></div>
        </div>
        <div class="f s2">
          <label>Razón Social / Nombre <span class="req">*</span></label>
          <input type="text" id="f_rs" placeholder="Ej: Farmacia Central SAC" autocomplete="off">
          <div class="ferr hidden" id="e_rs"></div>
        </div>
        <div class="f">
          <label>Régimen Fiscal <span class="req">*</span></label>
          <select id="f_reg">
            <option value="">— Seleccionar —</option>
            <option value="RER">RER — Régimen Especial</option>
'@

$nuevo = @'
    <!-- ── PASO 1 — CLIENTE ─────────────────────────────── -->
    <div class="panel" id="p1">
      <div class="fg">

        <!-- RUC -->
        <div class="f s2">
          <label>RUC Emisor <span class="req">*</span></label>
          <input type="text" id="f_ruc" class="mono" maxlength="11" placeholder="20XXXXXXXXX" autocomplete="off">
          <div class="hint">11 dígitos — persona natural (10) o empresa (20)</div>
          <div class="ferr hidden" id="e_ruc"></div>
        </div>

        <!-- Razón Social -->
        <div class="f s2">
          <label>Razón Social <span class="req">*</span></label>
          <input type="text" id="f_rs" placeholder="Nombre legal/tributario — Ej: Farmacia Central SAC" autocomplete="off">
          <div class="hint">Tal como figura en SUNAT</div>
          <div class="ferr hidden" id="e_rs"></div>
        </div>

        <!-- Nombre Comercial -->
        <div class="f s2">
          <label>Nombre Comercial</label>
          <input type="text" id="f_nc" placeholder="Marca o nombre de fantasía — Ej: FarmaPlus" autocomplete="off">
          <div class="hint">Si es distinto a la razón social. Opcional.</div>
        </div>

        <!-- Alias -->
        <div class="f s2">
          <label>Alias / Local <span class="req">*</span></label>
          <input type="text" id="f_alias" placeholder="Ej: Local Cercado Piura, Sta. Eulalia Castilla" autocomplete="off">
          <div class="hint">Nombre corto para identificar este punto de venta o local</div>
          <div class="ferr hidden" id="e_alias"></div>
        </div>

        <!-- Régimen -->
        <div class="f">
          <label>Régimen Tributario <span class="req">*</span></label>
          <select id="f_reg">
            <option value="">— Seleccionar —</option>
            <option value="NRUS">NRUS — Nuevo RUS</option>
            <option value="RER">RER — Régimen Especial</option>
'@

# Verificar que el viejo bloque existe
if (-not ($c -match [regex]::Escape("RUC Emisor") )) {
    Write-Error "No se encontro el bloque del paso 1 en wizard.html"
    exit 1
}

# Reemplazar hasta la opcion RER inclusive
$c = $c -replace [regex]::Escape($viejo), $nuevo

[System.IO.File]::WriteAllText((Resolve-Path $html).Path, $c, [System.Text.Encoding]::UTF8)
Write-Host "[OK] Paso 1 actualizado en wizard.html" -ForegroundColor Green

# ── Parchear wizard.js — saveCliente() y v1() ─────────────────
$js   = "src\ui\frontend\js\wizard.js"
$jsC  = Get-Content $js -Raw -Encoding UTF8

# 1. saveCliente — agregar nombre_comercial y alias
$viejoSave = @'
function saveCliente() {
  W.data.cliente = {
    ruc_emisor:   document.getElementById('f_ruc').value.trim(),
    razon_social: document.getElementById('f_rs').value.trim(),
    regimen:      document.getElementById('f_reg').value,
    cliente_id:   document.getElementById('f_id').value.trim(),
  };
}
'@

$nuevoSave = @'
function saveCliente() {
  W.data.cliente = {
    ruc_emisor:      document.getElementById('f_ruc').value.trim(),
    razon_social:    document.getElementById('f_rs').value.trim(),
    nombre_comercial:document.getElementById('f_nc').value.trim(),
    alias:           document.getElementById('f_alias').value.trim(),
    regimen:         document.getElementById('f_reg').value,
    cliente_id:      document.getElementById('f_id').value.trim(),
  };
}
'@

$jsC = $jsC -replace [regex]::Escape($viejoSave), $nuevoSave

# 2. v1() — agregar validacion de alias
$viejoV1 = "  if (!id || /\s/.test(id))     { showErr('f_id',  'e_id',  'El ID no puede estar vacío ni contener espacios'); ok = false; }"
$nuevoV1  = "  if (!id || /\s/.test(id))     { showErr('f_id',  'e_id',  'El ID no puede estar vacío ni contener espacios'); ok = false; }
  const alias = document.getElementById('f_alias').value.trim();
  if (!alias)                       { showErr('f_alias','e_alias','El alias del local es obligatorio'); ok = false; }"

$jsC = $jsC -replace [regex]::Escape($viejoV1), $nuevoV1

# 3. bindRucAutoId — auto-generar id desde RUC (ya existe, no tocar)

[System.IO.File]::WriteAllText((Resolve-Path $js).Path, $jsC, [System.Text.Encoding]::UTF8)
Write-Host "[OK] wizard.js actualizado (saveCliente + v1)" -ForegroundColor Green

# ── Commit ─────────────────────────────────────────────────────
git add $html $js
git commit -m "feat: TASK-005 paso 1 campos completos (nombre comercial, alias, NRUS)"
Write-Host "[OK] Commit realizado`n" -ForegroundColor Green

Write-Host "Reinicia la app: python main.py`n" -ForegroundColor Cyan
