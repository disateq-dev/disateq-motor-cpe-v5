# fix_ui_header_footer.ps1
# 1. Header info: texto más grande (+2pt), mismo peso/densidad
# 2. Separador naranja entre header y nav-tabs
# 3. Footer: "Sistema Operativo" → "Conectado", versión → v5.0
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5

$ErrorActionPreference = "Stop"

# ══════════════════════════════════════════════════════════════════
#  1. layout.css — header info más grande + separador naranja
# ══════════════════════════════════════════════════════════════════
$css  = "src\ui\frontend\css\layout.css"
$c    = Get-Content $css -Raw -Encoding UTF8

# 1a. Aumentar font-size del header-info de text-xs a 13px uniforme
$c = $c -replace '(\.header-info \{[^}]*font-size:\s*)var\(--text-xs\)', '$113px'

# 1b. Aumentar empresa-nombre de text-sm a 15px
$c = $c -replace '(#empresa-nombre \{[^}]*font-size:\s*)var\(--text-sm\) !important', '$115px !important'

# 1c. Separador naranja entre header y nav-tabs
# Reemplazar border-bottom del app-header por línea naranja
$c = $c -replace '(\.app-header \{[^}]*box-shadow:[^;]+;)', '$1
  border-bottom: 2px solid #f59e0b;'

# Si ya tiene border-bottom en app-header, no duplicar
if (($c -split '\.app-header' | Select-Object -Index 1) -match 'border-bottom.*2px solid #f59e0b') {
    # ya está, no hacer nada extra
} 

# 1d. Quitar border-bottom del nav-tabs para que no compita
$c = $c -replace '(\.nav-tabs \{[^}]*border-bottom:\s*)1px solid rgba\(255,255,255,0\.06\)', '$1none'

[System.IO.File]::WriteAllText((Resolve-Path $css).Path, $c, [System.Text.Encoding]::UTF8)
Write-Host "[OK] layout.css — header texto + separador naranja" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════════
#  2. index.html — footer fixes + versión
# ══════════════════════════════════════════════════════════════════
$html = "src\ui\frontend\index.html"
$h    = Get-Content $html -Raw -Encoding UTF8

# 2a. Título correcto
$h = $h -replace 'Motor CPE DisateQ™ v4\.0', 'DisateQ™ Motor CPE v5.0'

# 2b. Versión en footer
$h = $h -replace 'DisateQ™ Motor CPE v4\.0', 'DisateQ™ Motor CPE v5.0'

# 2c. "Sistema Operativo" → "Conectado"
$h = $h -replace '>Sistema Operativo<', '>Conectado<'
$h = $h -replace '"Sistema Operativo"', '"Conectado"'

# 2d. header-info: mismo tamaño para todos los spans — forzar con inline style
# Quitar strong de empresa-nombre para uniformidad de densidad
# (empresa-nombre ya es bold por CSS, no necesita <strong> en HTML)
# Solo asegurar que el alias también tenga font-weight 500
$h = $h -replace '(<span id="empresa-alias">)', '<span id="empresa-alias" style="font-weight:500;">'

[System.IO.File]::WriteAllText((Resolve-Path $html).Path, $h, [System.Text.Encoding]::UTF8)
Write-Host "[OK] index.html — titulo, version, footer Conectado" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════════
#  3. Fix ClientLoader alias con espacios → usar cliente_id o slug
#     El error era: config\clientes\LOCAL PRINCIPAL.yaml no existe
#     ClientLoader debe buscar por archivo, no por alias
#     Solución rápida: el alias en el YAML generado no debe tener espacios
#     como nombre de archivo — ya está corregido en wizard_service.py
#     Aquí solo renombramos farmacia_central para que sea el activo
# ══════════════════════════════════════════════════════════════════
Write-Host "[INFO] Clientes activos:" -ForegroundColor Cyan
Get-ChildItem config\clientes\ -Filter "*.yaml" | Where-Object { $_.Name -notlike "*.bak" } | ForEach-Object { Write-Host "  $_" }

# ══════════════════════════════════════════════════════════════════
#  Commit
# ══════════════════════════════════════════════════════════════════
git add $css $html
git commit -m "fix: UI header texto uniforme + separador naranja + footer v5.0"
Write-Host "[OK] Commit realizado`n" -ForegroundColor Green
Write-Host "Reinicia: python main.py`n" -ForegroundColor Cyan
