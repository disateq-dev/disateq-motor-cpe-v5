# =============================================================================
# build_installer.ps1 -- DisateQ Motor CPE v5.0
# Genera el instalador Setup.exe GENERICO (sin cliente precargado)
# El Wizard configura el cliente en el primer arranque
#
# Uso:
#   .\installer\build_installer.ps1
#
# Prerequisitos:
#   - Haber ejecutado build PyInstaller (genera dist\)
#   - Inno Setup 6 instalado (https://jrsoftware.org/isdl.php)
# =============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot  = Split-Path $PSScriptRoot -Parent
$InstallerDir = $PSScriptRoot
$IssFile      = Join-Path $InstallerDir "disateq_setup.iss"
$DistDir      = Join-Path $ProjectRoot  "dist\DisateQ-Motor-CPE"
$PublicPem    = Join-Path $ProjectRoot  "src\licenses\keys\disateq_public.pem"
$OutputExe    = Join-Path $InstallerDir "Output\DisateQ-Motor-CPE-Setup.exe"

Write-Host ""
Write-Host "=== DisateQ Motor CPE -- Build Instalador Generico ===" -ForegroundColor Cyan
Write-Host "  Proyecto : $ProjectRoot" -ForegroundColor Gray

# Verificar dist
if (-not (Test-Path $DistDir)) {
    Write-Host "ERROR: No existe dist\DisateQ-Motor-CPE\" -ForegroundColor Red
    Write-Host "       Ejecuta primero el build PyInstaller" -ForegroundColor Yellow
    exit 1
}

# Verificar clave publica
if (-not (Test-Path $PublicPem)) {
    Write-Host "ERROR: No existe src\licenses\keys\disateq_public.pem" -ForegroundColor Red
    exit 1
}

# Buscar Inno Setup
$IsccCandidatos = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$IsccEnPath = Get-Command iscc -ErrorAction SilentlyContinue
if ($IsccEnPath) { $IsccCandidatos += $IsccEnPath.Source }

$Iscc = $IsccCandidatos | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) {
    Write-Host "ERROR: Inno Setup 6 no encontrado." -ForegroundColor Red
    Write-Host "       Descarga: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    exit 1
}
Write-Host "  Inno Setup: $Iscc" -ForegroundColor Gray

Write-Host ""
Write-Host "  Generando instalador..." -ForegroundColor Cyan

& $Iscc $IssFile
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Inno Setup fallo con codigo $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== INSTALADOR LISTO ===" -ForegroundColor Green
Write-Host "  Archivo: $OutputExe" -ForegroundColor White
Write-Host ""
Write-Host "Entregar al cliente:" -ForegroundColor Yellow
Write-Host "  1. DisateQ-Motor-CPE-Setup.exe  (instalar en maquina cliente)"
Write-Host "  2. Correr DisateQ-Licensor.exe en la maquina del cliente"
Write-Host "  3. Generar .lic y cargarlo desde Configuracion del Motor"
Write-Host ""
