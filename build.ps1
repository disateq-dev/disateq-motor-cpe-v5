# build.ps1
# Build script — Motor CPE DisateQ™ v4.0

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Motor CPE DisateQ™ v4.0 - BUILD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Limpiar builds anteriores
Write-Host "1. Limpiando builds anteriores..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
Write-Host "   ✓ Limpieza completada" -ForegroundColor Green
Write-Host ""

# 2. Instalar PyInstaller
Write-Host "2. Verificando PyInstaller..." -ForegroundColor Yellow
pip show pyinstaller > $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Instalando PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller --break-system-packages
}
Write-Host "   ✓ PyInstaller OK" -ForegroundColor Green
Write-Host ""

# 3. Build con PyInstaller
Write-Host "3. Generando ejecutable..." -ForegroundColor Yellow
pyinstaller motor_cpe.spec --clean

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ Build completado" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ejecutable generado:" -ForegroundColor Cyan
    Write-Host "   dist\MotorCPE.exe" -ForegroundColor White
    Write-Host ""
    
    # Tamaño
    $size = (Get-Item "dist\MotorCPE.exe").Length / 1MB
    Write-Host "Tamaño: $([math]::Round($size, 2)) MB" -ForegroundColor Gray
} else {
    Write-Host "   ✗ Error en build" -ForegroundColor Red
    exit 1
}
