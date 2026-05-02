# fix_wizard_nav.ps1
# Agrega boton "Nuevo Cliente" en index.html para abrir wizard desde PyWebView
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5

$ErrorActionPreference = "Stop"
$html = "src\ui\frontend\index.html"

if (-not (Test-Path $html)) { Write-Error "No se encontro $html"; exit 1 }

$contenido = Get-Content $html -Raw -Encoding UTF8

# Verificar si ya tiene el boton
if ($contenido -match "wizard\.html") {
    Write-Host "[INFO] index.html ya tiene navegacion al wizard." -ForegroundColor DarkYellow
    exit 0
}

# Busca el nav de pestanas y agrega boton wizard al final del header
# Inserta justo antes del cierre </nav> o </header> del topbar
$boton = @'
<button class="btn-wizard-nav" onclick="window.location.href='wizard.html'" title="Configurar nuevo cliente" style="
    margin-left:auto;
    background: rgba(245,158,11,.15);
    border: 1.5px solid rgba(245,158,11,.4);
    color: #f59e0b;
    font-size: 12.5px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 7px;
    cursor: pointer;
    font-family: inherit;
    white-space: nowrap;
">+ Nuevo Cliente</button>
'@

# Estrategia: insertar antes del primer </nav> del topbar
$nuevo = $contenido -replace '(<nav[^>]*class="[^"]*tab[^"]*"[^>]*>)(.*?)(</nav>)', {
    param($m)
    $m.Groups[1].Value + $m.Groups[2].Value + $boton + $m.Groups[3].Value
}

# Si no matcheo, insertar antes del primer </header>
if ($nuevo -eq $contenido) {
    $nuevo = $contenido -replace '</header>', "$boton</header>"
}

# Si tampoco, append antes del primer </body> como fallback
if ($nuevo -eq $contenido) {
    $nuevo = $contenido -replace '</body>', @"
<div style="position:fixed;top:12px;right:60px;z-index:9999">
    <button onclick="window.location.href='wizard.html'" style="
        background:rgba(245,158,11,.15);border:1.5px solid rgba(245,158,11,.4);
        color:#f59e0b;font-size:12.5px;font-weight:500;padding:6px 14px;
        border-radius:7px;cursor:pointer;font-family:inherit;">+ Nuevo Cliente</button>
</div>
</body>
"@
}

[System.IO.File]::WriteAllText((Resolve-Path $html).Path, $nuevo, [System.Text.Encoding]::UTF8)
Write-Host "[OK] Boton 'Nuevo Cliente' agregado a index.html" -ForegroundColor Green

git add $html
git commit -m "feat: TASK-005 boton Nuevo Cliente en index.html abre wizard"
Write-Host "[OK] Commit realizado" -ForegroundColor Green
Write-Host "`nReinicia la app: python main.py`n" -ForegroundColor Cyan
