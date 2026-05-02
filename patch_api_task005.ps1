# ══════════════════════════════════════════════════════════════════
#  DisateQ Motor CPE v5.0  —  patch_api_task005.ps1
#  Parchea src/ui/api.py con los 4 métodos del Wizard (TASK-005)
#  Ejecutar desde: D:\DisateQ\Proyectos\disateq-motor-cpe-v5
# ══════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"
$ApiPath = "src\ui\api.py"

Write-Host "`n[PATCH] Parcheando $ApiPath ...`n" -ForegroundColor Cyan

if (-not (Test-Path $ApiPath)) {
    Write-Error "No se encontro $ApiPath. Ejecuta desde la raiz del proyecto."
    exit 1
}

$contenido = Get-Content $ApiPath -Raw -Encoding UTF8

# ── Verificar que no este ya parcheado ─────────────────────────
if ($contenido -match "wizard_guardar") {
    Write-Host "[INFO] api.py ya contiene los metodos del wizard. Nada que hacer." -ForegroundColor DarkYellow
    exit 0
}

# ── 1. Agregar import ──────────────────────────────────────────
$importNuevo = "from src.tools.wizard_service import test_fuente, guardar_wizard"

# Busca la ultima linea de imports (from/import) y agrega despues
if ($contenido -match "(?m)^(from src\.|import )") {
    # Agrega el import despues de la ultima linea 'from src.'
    $contenido = $contenido -replace "(?m)(^from src\.[^\r\n]+)", {
        param($m)
        $m.Value  # retorna cada match igual; el replace final agrega al final
    }
    # Estrategia simple: insertar despues del bloque de imports
    $contenido = $contenido -replace "(?m)(^import [^\r\n]+\r?\n)(?!import |from )", "`$1$importNuevo`n"
    if (-not ($contenido -match [regex]::Escape($importNuevo))) {
        # Fallback: insertar al principio del archivo despues del primer import
        $contenido = $contenido -replace "(?m)(^from [^\r\n]+\r?\n)", "`$1$importNuevo`n"
    }
}

# ── 2. Metodos a inyectar ──────────────────────────────────────
$metodos = @'

    # ------------------------------------------------------------------
    # WIZARD — paso 2: dialogo de exploracion de ruta / carpeta
    # ------------------------------------------------------------------
    def explorar_ruta(self, es_carpeta: bool = True):
        import webview
        try:
            if es_carpeta:
                resultado = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            else:
                resultado = self._window.create_file_dialog(
                    webview.OPEN_DIALOG,
                    file_types=(
                        "Archivos de datos (*.dbf;*.xlsx;*.xls;*.csv;*.mdb;*.accdb)",
                        "Todos los archivos (*.*)",
                    ),
                )
            if resultado and len(resultado) > 0:
                return resultado[0]
        except Exception as exc:
            print(f"[WIZARD] explorar_ruta error: {exc}")
        return None

    # ------------------------------------------------------------------
    # WIZARD — paso 3: test de lectura de la fuente
    # ------------------------------------------------------------------
    def wizard_test_fuente(self, fuente: dict) -> dict:
        try:
            from src.tools.wizard_service import test_fuente
            return test_fuente(fuente)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # WIZARD — paso 4: autocontrato IA (stub hasta TASK-009)
    # ------------------------------------------------------------------
    def wizard_generar_contrato_auto(self, fuente: dict) -> dict:
        try:
            from src.tools.smart_mapper import SmartMapper
            mapper = SmartMapper()
            result = mapper.generar(fuente)
            if result.get("score", 0) >= 0.80:
                return {"ok": True, "contrato": result["contrato"], "score": result["score"]}
            else:
                return {
                    "ok": False,
                    "error": f"Score insuficiente ({result.get('score', 0):.0%}). Completa manualmente.",
                }
        except ImportError:
            return {"ok": False, "error": "smart_mapper no disponible aun (TASK-009). Completa manualmente."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # WIZARD — paso 6 final: guardar cliente + contrato
    # ------------------------------------------------------------------
    def wizard_guardar(self, payload: dict) -> dict:
        try:
            from src.tools.wizard_service import guardar_wizard
            return guardar_wizard(payload)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
'@

# ── 3. Insertar metodos justo antes del cierre de clase ────────
# Busca el ultimo metodo de la clase (linea "    def ") e inserta despues
# Estrategia: agregar antes de la ultima linea no-vacia del archivo

if ($contenido -match "(?s)(    def \w+[^}]+)$") {
    # Insertar al final del archivo (antes del EOF)
    $contenido = $contenido.TrimEnd() + "`n" + $metodos + "`n"
} else {
    $contenido = $contenido.TrimEnd() + "`n" + $metodos + "`n"
}

# ── 4. Escribir archivo ────────────────────────────────────────
[System.IO.File]::WriteAllText(
    (Resolve-Path $ApiPath).Path,
    $contenido,
    [System.Text.Encoding]::UTF8
)

Write-Host "[OK] api.py parcheado con 4 metodos wizard" -ForegroundColor Green

# ── 5. Commit ─────────────────────────────────────────────────
Write-Host "[GIT] Commiteando parche api.py..." -ForegroundColor Cyan
git add $ApiPath
git commit -m "feat: TASK-005 agregar metodos wizard a DisateQAPI"
Write-Host "[OK] Commit realizado`n" -ForegroundColor Green

Write-Host "[PATCH] Listo. Continua con el checklist de validacion.`n" -ForegroundColor Cyan
