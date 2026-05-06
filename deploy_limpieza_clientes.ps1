# =============================================================================
# deploy_limpieza_clientes.ps1 -- DisateQ Motor CPE v5.0
# Limpia clientes de prueba y deja el motor listo para instalacion real.
#
# Acciones:
#   1. Copia farmacia_central a config\ejemplos\ (referencia)
#   2. Elimina farmacia_central de config\clientes\ y config\contratos\
#   3. Elimina itera_prueba de config\clientes\ y config\contratos\
#   4. Elimina data\itera_prueba.db
#   5. Elimina data\disateq_cpe.db (historial de envios)
#   6. Git: commit de limpieza
#
# Al terminar: motor arranca sin clientes -> Wizard se activa
# =============================================================================

$ErrorActionPreference = "Stop"
$Root = "D:\DisateQ\Proyectos\disateq-motor-cpe-v5"

Write-Host "=== Limpieza clientes -- DisateQ Motor CPE ===" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# 1. Crear carpeta ejemplos y copiar farmacia_central
# -----------------------------------------------------------------------------
$EjClientes   = "$Root\config\ejemplos\clientes"
$EjContratos  = "$Root\config\ejemplos\contratos"
New-Item -ItemType Directory -Force -Path $EjClientes  | Out-Null
New-Item -ItemType Directory -Force -Path $EjContratos | Out-Null

$FarmCliente  = "$Root\config\clientes\farmacia_central.yaml"
$FarmContrato = "$Root\config\contratos\farmacia_central.yaml"

if (Test-Path $FarmCliente) {
    Copy-Item $FarmCliente  "$EjClientes\farmacia_central.yaml"  -Force
    Write-Host "  [OK] farmacia_central.yaml copiado a config\ejemplos\clientes" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] farmacia_central.yaml (clientes) no encontrado" -ForegroundColor Yellow
}

if (Test-Path $FarmContrato) {
    Copy-Item $FarmContrato "$EjContratos\farmacia_central.yaml" -Force
    Write-Host "  [OK] farmacia_central.yaml copiado a config\ejemplos\contratos" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] farmacia_central.yaml (contratos) no encontrado" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# 2. Eliminar farmacia_central de config activa
# -----------------------------------------------------------------------------
if (Test-Path $FarmCliente)  { Remove-Item $FarmCliente  -Force }
if (Test-Path $FarmContrato) { Remove-Item $FarmContrato -Force }
Write-Host "  [OK] farmacia_central eliminado de config activa" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 3. Eliminar itera_prueba de config activa
# -----------------------------------------------------------------------------
$IteraCliente  = "$Root\config\clientes\itera_prueba.yaml"
$IteraContrato = "$Root\config\contratos\itera_prueba.yaml"

if (Test-Path $IteraCliente)  { Remove-Item $IteraCliente  -Force }
if (Test-Path $IteraContrato) { Remove-Item $IteraContrato -Force }
Write-Host "  [OK] itera_prueba eliminado de config activa" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 4. Eliminar itera_prueba.db
# -----------------------------------------------------------------------------
$IteraDb = "$Root\data\itera_prueba.db"
if (Test-Path $IteraDb) {
    Remove-Item $IteraDb -Force
    Write-Host "  [OK] data\itera_prueba.db eliminado" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] data\itera_prueba.db no encontrado" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# 5. Eliminar disateq_cpe.db (historial de envios -- se regenera en runtime)
# -----------------------------------------------------------------------------
$CpeDb = "$Root\data\disateq_cpe.db"
if (Test-Path $CpeDb) {
    Remove-Item $CpeDb -Force
    Write-Host "  [OK] data\disateq_cpe.db eliminado" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] data\disateq_cpe.db no encontrado" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# Verificacion final
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "Verificacion config\clientes\:" -ForegroundColor Yellow
$clientesRestantes = Get-ChildItem "$Root\config\clientes\" -Filter "*.yaml" -ErrorAction SilentlyContinue
if ($clientesRestantes) {
    $clientesRestantes | ForEach-Object { Write-Host "  ATENCI0N: queda $_" -ForegroundColor Red }
} else {
    Write-Host "  Vacio -- OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "Ejemplos guardados en:" -ForegroundColor Yellow
Write-Host "  config\ejemplos\clientes\farmacia_central.yaml"
Write-Host "  config\ejemplos\contratos\farmacia_central.yaml"

# -----------------------------------------------------------------------------
# 6. Git
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "Git:" -ForegroundColor Cyan
Set-Location $Root
git add config\ejemplos\ "-A"
git add config\clientes\ "-A"
git add config\contratos\ "-A"
git add data\ "-A"
git commit -m "Limpieza: farmacia_central a ejemplos, itera_prueba eliminado, DB limpia"
git push

Write-Host ""
Write-Host "=== Motor listo para instalacion real ===" -ForegroundColor Green
Write-Host "Al iniciar, el Wizard se activara automaticamente." -ForegroundColor White
Write-Host ""
