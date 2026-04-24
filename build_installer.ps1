# build_installer.ps1
# Compila instalador NSIS - Motor CPE DisateQ™ v4.0

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Motor CPE - Build Instalador NSIS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar NSIS instalado
Write-Host "1. Verificando NSIS..." -ForegroundColor Yellow
$nsisPath = "C:\Program Files (x86)\NSIS\makensis.exe"

if (-not (Test-Path $nsisPath)) {
    Write-Host "   ✗ NSIS no encontrado" -ForegroundColor Red
    Write-Host ""
    Write-Host "Descarga NSIS desde: https://nsis.sourceforge.io/Download" -ForegroundColor Yellow
    Write-Host "Instala y vuelve a ejecutar este script." -ForegroundColor Yellow
    exit 1
}

Write-Host "   ✓ NSIS encontrado" -ForegroundColor Green
Write-Host ""

# 2. Verificar ejecutable
Write-Host "2. Verificando ejecutable..." -ForegroundColor Yellow
if (-not (Test-Path "dist\MotorCPE.exe")) {
    Write-Host "   ✗ dist\MotorCPE.exe no encontrado" -ForegroundColor Red
    Write-Host "   Ejecuta primero: .\build.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "   ✓ MotorCPE.exe encontrado" -ForegroundColor Green
Write-Host ""

# 3. Crear LICENSE.txt si no existe
Write-Host "3. Preparando archivos..." -ForegroundColor Yellow
if (-not (Test-Path "LICENSE.txt")) {
    @"
Motor CPE DisateQ™ v4.0
Copyright © 2026 DisateQ™

Todos los derechos reservados.

Este software es propiedad de DisateQ™ y está protegido por
las leyes de propiedad intelectual.

Uso autorizado solo con licencia válida.
"@ | Out-File -FilePath "LICENSE.txt" -Encoding UTF8
}

Write-Host "   ✓ Archivos preparados" -ForegroundColor Green
Write-Host ""

# 4. Compilar instalador
Write-Host "4. Compilando instalador NSIS..." -ForegroundColor Yellow
& $nsisPath installer.nsi

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " ✅ INSTALADOR GENERADO EXITOSAMENTE" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    
    $installerFile = Get-Item "MotorCPE_Installer_v4.0.0.exe"
    $sizeMB = [math]::Round($installerFile.Length / 1MB, 2)
    
    Write-Host "Archivo: $($installerFile.Name)" -ForegroundColor Cyan
    Write-Host "Tamaño: $sizeMB MB" -ForegroundColor Cyan
    Write-Host "Ubicación: $($installerFile.FullName)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "El instalador está listo para distribuir." -ForegroundColor Green
    
} else {
    Write-Host ""
    Write-Host "✗ Error compilando instalador" -ForegroundColor Red
    exit 1
}
