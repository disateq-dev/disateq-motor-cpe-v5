# =============================================================================
# build_installer.ps1 -- DisateQ Motor CPE v5.0
# Genera el instalador Setup.exe para un cliente especifico.
#
# Uso:
#   .\installer\build_installer.ps1 -Cliente farmacia_central
#
# Prerequisitos:
#   - Haber ejecutado .\build.ps1 (genera dist\)
#   - Inno Setup 6 instalado (https://jrsoftware.org/isdl.php)
# =============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$Cliente
)

$ErrorActionPreference = "Stop"

$ProjectRoot  = Split-Path $PSScriptRoot -Parent
$InstallerDir = $PSScriptRoot
$IssFile      = Join-Path $InstallerDir "disateq_setup.iss"
$DistDir      = Join-Path $ProjectRoot  "dist\DisateQ-Motor-CPE"
$PublicPem    = Join-Path $ProjectRoot  "src\licenses\keys\disateq_public.pem"
$OutputExe    = Join-Path $InstallerDir "Output\DisateQ-Motor-CPE-Setup.exe"

Write-Host ""
Write-Host "=== DisateQ Motor CPE -- Build Instalador ===" -ForegroundColor Cyan
Write-Host "  Cliente  : $Cliente" -ForegroundColor Yellow
Write-Host "  Proyecto : $ProjectRoot" -ForegroundColor Gray

if (-not (Test-Path $DistDir)) {
    Write-Host "ERROR: No existe dist\DisateQ-Motor-CPE\" -ForegroundColor Red
    Write-Host "       Ejecuta primero: .\build.ps1" -ForegroundColor Yellow
    exit 1
}

$ClienteYaml  = Join-Path $DistDir "config\clientes\$Cliente.yaml"
$ContratoYaml = Join-Path $DistDir "config\contratos\$Cliente.yaml"

if (-not (Test-Path $ClienteYaml)) {
    Write-Host "ERROR: No existe config\clientes\$Cliente.yaml en dist\" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $ContratoYaml)) {
    Write-Host "ERROR: No existe config\contratos\$Cliente.yaml en dist\" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $PublicPem)) {
    Write-Host "ERROR: No existe src\licenses\keys\disateq_public.pem" -ForegroundColor Red
    exit 1
}

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

$IssContent = Get-Content $IssFile -Raw -Encoding UTF8
$IssContent = $IssContent -replace '#define ClienteID\s+"[^"]*"', "#define ClienteID      `"$Cliente`""
$TempIss = Join-Path $InstallerDir "disateq_setup_build.iss"
Set-Content -Path $TempIss -Value $IssContent -Encoding UTF8

Write-Host ""
Write-Host "  Generando instalador..." -ForegroundColor Cyan

try {
    & $Iscc $TempIss
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Inno Setup fallo con codigo $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
} finally {
    Remove-Item $TempIss -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "=== INSTALADOR LISTO ===" -ForegroundColor Green
Write-Host "  Archivo : $OutputExe" -ForegroundColor White
Write-Host "  Cliente : $Cliente" -ForegroundColor White
Write-Host ""
Write-Host "Entregar al cliente:" -ForegroundColor Yellow
Write-Host "  1. DisateQ-Motor-CPE-Setup.exe  (instalador)"
Write-Host "  2. disateq_motor.lic            (por email separado)"
Write-Host ""
