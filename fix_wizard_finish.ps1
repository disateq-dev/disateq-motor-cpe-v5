# fix_wizard_finish.ps1
# Agrega metodo cargar_motor() en api.py
# y actualiza funcion irDashboard() en wizard.js
# Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5

$ErrorActionPreference = "Stop"

# ── 1. Parchear api.py — agregar metodo cargar_motor() ────────
$apiPath   = "src\ui\api.py"
$contenido = Get-Content $apiPath -Raw -Encoding UTF8

if ($contenido -match "def cargar_motor") {
    Write-Host "[INFO] cargar_motor ya existe en api.py" -ForegroundColor DarkYellow
} else {
    $metodo = @'

    def cargar_motor(self) -> dict:
        """Navega la ventana PyWebView al dashboard (index.html)."""
        try:
            if self._window:
                self._window.load_url(
                    self._window.get_current_url().replace("wizard.html", "index.html")
                )
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
'@

    # Insertar antes del ultimo metodo interno _cargar_cliente
    $contenido = $contenido -replace '(\n    def _cargar_cliente)', "$metodo`$1"
    [System.IO.File]::WriteAllText((Resolve-Path $apiPath).Path, $contenido, [System.Text.Encoding]::UTF8)
    Write-Host "[OK] metodo cargar_motor() agregado a api.py" -ForegroundColor Green
}

# ── 2. Parchear wizard.js — reemplazar irDashboard() ──────────
$jsPath    = "src\ui\frontend\js\wizard.js"
$jsContenido = Get-Content $jsPath -Raw -Encoding UTF8

$viejo = 'function irDashboard()  { window.location.href = ''index.html''; }'
$nuevo = @'
function irDashboard() {
    window.pywebview.api.cargar_motor()
        .then(() => { window.location.href = 'index.html'; })
        .catch(() => { window.location.href = 'index.html'; });
}
'@

if ($jsContenido -match "cargar_motor") {
    Write-Host "[INFO] wizard.js ya tiene cargar_motor" -ForegroundColor DarkYellow
} else {
    $jsContenido = $jsContenido -replace [regex]::Escape($viejo), $nuevo
    # Fallback si no matcheo exacto
    if (-not ($jsContenido -match "cargar_motor")) {
        $jsContenido = $jsContenido -replace 'function irDashboard\(\)\s*\{[^}]+\}', $nuevo
    }
    [System.IO.File]::WriteAllText((Resolve-Path $jsPath).Path, $jsContenido, [System.Text.Encoding]::UTF8)
    Write-Host "[OK] irDashboard() actualizado en wizard.js" -ForegroundColor Green
}

# ── 3. Actualizar texto del boton en wizard.html ───────────────
$htmlPath    = "src\ui\frontend\wizard.html"
$htmlContenido = Get-Content $htmlPath -Raw -Encoding UTF8

$htmlContenido = $htmlContenido -replace 'Ir al Dashboard', 'Finalizar y cargar Motor'

[System.IO.File]::WriteAllText((Resolve-Path $htmlPath).Path, $htmlContenido, [System.Text.Encoding]::UTF8)
Write-Host "[OK] Texto boton actualizado en wizard.html" -ForegroundColor Green

# ── 4. Commit ──────────────────────────────────────────────────
git add $apiPath $jsPath $htmlPath
git commit -m "feat: TASK-005 boton Finalizar y cargar Motor en wizard"
Write-Host "[OK] Commit realizado`n" -ForegroundColor Green

Write-Host "Prueba:" -ForegroundColor Cyan
Write-Host "  Rename-Item config\clientes\farmacias_fas.yaml farmacias_fas.yaml.bak"
Write-Host "  python main.py"
Write-Host "  (recorre wizard -> Finalizar y cargar Motor -> debe abrir dashboard)`n"
