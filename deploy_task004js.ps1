# deploy_task004js.ps1
# TASK-004 JS: migración eel → window.pywebview.api
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5

$ErrorActionPreference = "Stop"
$dl  = "D:\DATA\Downloads"
$js  = "src\ui\frontend\js"

Copy-Item "$dl\app.js"       "$js\app.js"       -Force
Copy-Item "$dl\dashboard.js" "$js\dashboard.js" -Force
Copy-Item "$dl\processor.js" "$js\processor.js" -Force
Write-Host "[OK] 3 archivos JS copiados" -ForegroundColor Green

# Verificar sintaxis
$errors = 0
foreach ($f in @("$js\app.js","$js\dashboard.js","$js\processor.js")) {
    $r = node --check $f 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] $f : $r" -ForegroundColor Red
        $errors++
    } else {
        Write-Host "[OK] $f sintaxis OK" -ForegroundColor Green
    }
}

if ($errors -gt 0) { Write-Error "Hay errores de sintaxis. Abortando commit."; exit 1 }

git add "$js\app.js" "$js\dashboard.js" "$js\processor.js"
git commit -m "feat: TASK-004 JS migracion eel → window.pywebview.api completa"
Write-Host "[OK] Commit realizado`n" -ForegroundColor Green
Write-Host "Reinicia: python main.py`n" -ForegroundColor Cyan
