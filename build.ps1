# ============================================================
# build.ps1 - DisateQ Motor CPE v5.0
# Build PyInstaller -> dist\DisateQ-Motor-CPE\
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5
# ============================================================

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

Write-Host ""
Write-Host "DisateQ Motor CPE v5.0 - Build" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Verificar raiz del proyecto
if (-not (Test-Path "$ROOT\main.py")) {
    Write-Host "ERROR: Ejecutar desde la raiz del proyecto." -ForegroundColor Red
    exit 1
}

# Verificar PyInstaller
try {
    $pi = python -c "import PyInstaller; print(PyInstaller.__version__)" 2>&1
    Write-Host "PyInstaller: $pi" -ForegroundColor Green
} catch {
    Write-Host "PyInstaller no instalado." -ForegroundColor Red
    exit 1
}

# Verificar pywebview
try {
    $wv = python -c "import webview; print(webview.__version__)" 2>&1
    Write-Host "PyWebView:   $wv" -ForegroundColor Green
} catch {
    Write-Host "PyWebView no instalado." -ForegroundColor Red
    exit 1
}

# Limpiar builds anteriores
Write-Host ""
Write-Host "Limpiando builds anteriores..." -ForegroundColor Yellow

if (Test-Path "$ROOT\dist\DisateQ-Motor-CPE") {
    Remove-Item "$ROOT\dist\DisateQ-Motor-CPE" -Recurse -Force
    Write-Host "  dist\DisateQ-Motor-CPE eliminado." -ForegroundColor Gray
}
if (Test-Path "$ROOT\build") {
    Remove-Item "$ROOT\build" -Recurse -Force
    Write-Host "  build\ eliminado." -ForegroundColor Gray
}

# Crear carpetas necesarias
New-Item -ItemType Directory -Force -Path "$ROOT\data"   | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\output" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\dist"   | Out-Null

# Ejecutar PyInstaller
Write-Host ""
Write-Host "Ejecutando PyInstaller..." -ForegroundColor Yellow
Write-Host ""

Set-Location $ROOT
python -m PyInstaller disateq.spec --clean --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: PyInstaller fallo." -ForegroundColor Red
    exit 1
}

# Copiar archivos de datos
Write-Host ""
Write-Host "Copiando archivos de datos..." -ForegroundColor Yellow

$DIST = "$ROOT\dist\DisateQ-Motor-CPE"

if (Test-Path "$ROOT\config") {
    Copy-Item "$ROOT\config" "$DIST\config" -Recurse -Force
    Write-Host "  config\ copiado." -ForegroundColor Gray
}

# Limpiar configs de cliente -- instalador debe ser generico
if (Test-Path "$DIST\config\clientes") {
    Get-ChildItem "$DIST\config\clientes\*" -Include "*.yaml" | Remove-Item -Force
    Write-Host "  config\clientes\ limpiado." -ForegroundColor Gray
}
if (Test-Path "$DIST\config\contratos") {
    Get-ChildItem "$DIST\config\contratos\*" -Include "*.yaml" | Remove-Item -Force
    Write-Host "  config\contratos\ limpiado." -ForegroundColor Gray
}

Write-Host "  Instalador limpio -- sin clientes preconfigurados." -ForegroundColor Green

# Verificar ejecutable
Write-Host ""
if (Test-Path "$DIST\DisateQ-Motor-CPE.exe") {
    $size = (Get-Item "$DIST\DisateQ-Motor-CPE.exe").Length / 1MB
    Write-Host "BUILD EXITOSO" -ForegroundColor Green
    Write-Host "  Ejecutable: dist\DisateQ-Motor-CPE\DisateQ-Motor-CPE.exe" -ForegroundColor White
    Write-Host ("  Tamano .exe: {0:F1} MB" -f $size) -ForegroundColor White

    $total = (Get-ChildItem "$DIST" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ("  Tamano total carpeta: {0:F0} MB" -f $total) -ForegroundColor White
} else {
    Write-Host "ERROR: No se encontro el ejecutable." -ForegroundColor Red
    exit 1
}

# Checklist de validacion
Write-Host ""
Write-Host "CHECKLIST DE VALIDACION" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host " [ ] Ejecutar: dist\DisateQ-Motor-CPE\DisateQ-Motor-CPE.exe"
Write-Host " [ ] Abre Wizard (instalacion nueva sin cliente)"
Write-Host " [ ] Wizard completa configuracion correctamente"
Write-Host " [ ] Ventana abre sin consola visible"
Write-Host " [ ] Header muestra empresa y RUC"
Write-Host " [ ] Tab Procesar carga pendientes"
Write-Host " [ ] Historial muestra registros"
Write-Host " [ ] Config abre con PIN"
Write-Host ""
Write-Host "Ruta de entrega: $DIST" -ForegroundColor White
Write-Host ""
