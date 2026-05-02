# ══════════════════════════════════════════════════════════════════
#  DisateQ Motor CPE v5.0  —  deploy_task005.ps1
#  TASK-005: Wizard end-to-end
#  Ejecutar desde D:\DisateQ\Proyectos\disateq-motor-cpe-v5
# ══════════════════════════════════════════════════════════════════

param(
    [string]$DescargasDir = "D:\DATA\Downloads"
)

$ErrorActionPreference = "Stop"
$ProyectoDir = "D:\DisateQ\Proyectos\disateq-motor-cpe-v5"

Write-Host "`n[TASK-005] Iniciando deploy del Wizard...`n" -ForegroundColor Cyan

# ── 1. Verificar que estamos en el directorio correcto ─────────
if (-not (Test-Path "$ProyectoDir\main.py")) {
    Write-Error "No se encontró main.py en $ProyectoDir. Verifica la ruta del proyecto."
    exit 1
}
Set-Location $ProyectoDir

# ── 2. Copiar wizard_service.py → src/tools/ ──────────────────
$src = "$DescargasDir\wizard_service.py"
$dst = "$ProyectoDir\src\tools\wizard_service.py"
if (-not (Test-Path $src)) {
    Write-Error "No se encontró $src. Descarga el archivo del chat primero."
    exit 1
}
Copy-Item $src $dst -Force
Write-Host "[OK] wizard_service.py   → src/tools/" -ForegroundColor Green

# ── 3. Copiar wizard.html → src/ui/frontend/ ──────────────────
$src = "$DescargasDir\wizard.html"
$dst = "$ProyectoDir\src\ui\frontend\wizard.html"
if (-not (Test-Path $src)) {
    Write-Error "No se encontró $src"
    exit 1
}
Copy-Item $src $dst -Force
Write-Host "[OK] wizard.html          → src/ui/frontend/" -ForegroundColor Green

# ── 4. Copiar wizard.js → src/ui/frontend/js/ ─────────────────
$src = "$DescargasDir\wizard.js"
$dst = "$ProyectoDir\src\ui\frontend\js\wizard.js"
if (-not (Test-Path $src)) {
    Write-Error "No se encontró $src"
    exit 1
}
Copy-Item $src $dst -Force
Write-Host "[OK] wizard.js            → src/ui/frontend/js/" -ForegroundColor Green

# ── 5. Parche manual api.py — instrucciones ────────────────────
Write-Host "`n[MANUAL] Parche api.py requerido:" -ForegroundColor Yellow
Write-Host "  1. Abrir src\ui\api.py"
Write-Host "  2. Agregar import (ver api_wizard_methods.py):"
Write-Host "       from src.tools.wizard_service import test_fuente, guardar_wizard"
Write-Host "  3. Pegar los 4 métodos de api_wizard_methods.py"
Write-Host "     dentro de la clase DisateQAPI`n"

# ── 6. Verificar que PyYAML está instalado ─────────────────────
Write-Host "[CHECK] Verificando PyYAML..." -ForegroundColor Cyan
$yamlCheck = python -c "import yaml; print('ok')" 2>&1
if ($yamlCheck -ne "ok") {
    Write-Host "[INSTALL] Instalando PyYAML..." -ForegroundColor Yellow
    python -m pip install PyYAML --quiet
}
Write-Host "[OK] PyYAML disponible" -ForegroundColor Green

# ── 7. Git commit ──────────────────────────────────────────────
Write-Host "`n[GIT] Preparando commit..." -ForegroundColor Cyan
git add src/tools/wizard_service.py
git add src/ui/frontend/wizard.html
git add src/ui/frontend/js/wizard.js
git add src/ui/api.py   2>$null   # puede no haberse editado aún

$status = git status --porcelain
if ($status) {
    git commit -m "feat: TASK-005 wizard end-to-end 6 pasos (PyWebView)"
    Write-Host "[OK] Commit realizado" -ForegroundColor Green
} else {
    Write-Host "[INFO] Nada que commitear (sin cambios detectados)" -ForegroundColor DarkYellow
}

Write-Host "`n[TASK-005] Deploy completado.`n" -ForegroundColor Cyan
Write-Host "Checklist de validacion manual:" -ForegroundColor White
Write-Host "  [ ] wizard.html abre sin errores en PyWebView"
Write-Host "  [ ] Paso 1 — validacion RUC 11 digitos"
Write-Host "  [ ] Paso 2 — selector DBF muestra input de carpeta"
Write-Host "  [ ] Paso 3 — test_fuente lee D:\FFEESUNAT\Test correctamente"
Write-Host "  [ ] Paso 4 — campos pre-llenados con datos de farmacias_fas"
Write-Host "  [ ] Paso 5 — toggle habilita input de serie"
Write-Host "  [ ] Paso 6 — guardar crea config/clientes/XXX.yaml + config/contratos/XXX.yaml"
Write-Host "  [ ] YAML generado tiene estructura correcta (revisar con notepad)`n"
