# =============================================================================
# deploy_mover_cercado_piura.ps1 -- DisateQ Motor CPE v5.0
# Mueve local_cercado_piura a config\ejemplos\ y limpia config activa
# =============================================================================

$ErrorActionPreference = "Stop"
$Root = "D:\DisateQ\Proyectos\disateq-motor-cpe-v5"

Write-Host "=== Mover local_cercado_piura a ejemplos ===" -ForegroundColor Cyan

$EjClientes  = "$Root\config\ejemplos\clientes"
$EjContratos = "$Root\config\ejemplos\contratos"
New-Item -ItemType Directory -Force -Path $EjClientes  | Out-Null
New-Item -ItemType Directory -Force -Path $EjContratos | Out-Null

# Copiar a ejemplos
$CpCliente  = "$Root\config\clientes\local_cercado_piura.yaml"
$CpContrato = "$Root\config\contratos\local_cercado_piura.yaml"

if (Test-Path $CpCliente) {
    Copy-Item $CpCliente  "$EjClientes\local_cercado_piura.yaml"  -Force
    Remove-Item $CpCliente -Force
    Write-Host "  [OK] clientes\local_cercado_piura.yaml -> ejemplos" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] clientes\local_cercado_piura.yaml no encontrado" -ForegroundColor Yellow
}

if (Test-Path $CpContrato) {
    Copy-Item $CpContrato "$EjContratos\local_cercado_piura.yaml" -Force
    Remove-Item $CpContrato -Force
    Write-Host "  [OK] contratos\local_cercado_piura.yaml -> ejemplos" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] contratos\local_cercado_piura.yaml no encontrado" -ForegroundColor Yellow
}

# Verificacion final
Write-Host ""
Write-Host "Verificacion config\clientes\:" -ForegroundColor Yellow
$restantes = Get-ChildItem "$Root\config\clientes\" -Filter "*.yaml" -ErrorAction SilentlyContinue
if ($restantes) {
    $restantes | ForEach-Object { Write-Host "  ATENCION: queda $($_.Name)" -ForegroundColor Red }
} else {
    Write-Host "  Vacio -- OK" -ForegroundColor Green
}

# Git
Write-Host ""
Write-Host "Git:" -ForegroundColor Cyan
Set-Location $Root
git add config\ejemplos\ "-A"
git add config\clientes\ "-A"
git add config\contratos\ "-A"
git commit -m "Limpieza: local_cercado_piura a ejemplos -- motor listo para instalacion real"
git push

Write-Host ""
Write-Host "=== Listo -- python main.py debe arrancar en Wizard ===" -ForegroundColor Green
Write-Host ""
