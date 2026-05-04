# disateq.spec
# PyInstaller spec — DisateQ Motor CPE v5.0
# Modo: onedir (carpeta con .exe + dependencias)
# Comando: pyinstaller disateq.spec
import sys
from pathlib import Path
ROOT = Path(SPECPATH)
# ── Datos adicionales: frontend + config + assets ─────────────────
added_files = [
    # Frontend completo (HTML, CSS, JS, assets)
    (str(ROOT / 'src' / 'ui' / 'frontend'), 'frontend'),
    # Configuracion (clientes + contratos YAML)
    (str(ROOT / 'config'), 'config'),
    # Icono de la aplicacion
    (str(ROOT / 'src' / 'ui' / 'frontend' / 'assets' / 'icons' / 'cpe_disateq.ico'),
     'assets/icons'),
    # Clave publica RSA para validacion de licencias
    (str(ROOT / 'src' / 'licenses' / 'keys' / 'disateq_public.pem'),
     'src/licenses/keys'),
]
# ── Analisis ───────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex     = [str(ROOT)],
    binaries   = [],
    datas      = added_files,
    hiddenimports = [
        # pywebview backends Windows
        'webview',
        'webview.platforms.winforms',
        'clr',
        'System',
        'System.Windows.Forms',
        # dbfread
        'dbfread',
        'dbfread.dbf',
        'dbfread.field_parser',
        # PyYAML
        'yaml',
        # requests
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
        # openpyxl
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        # cryptography
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.backends',
        # sqlite3 (stdlib)
        'sqlite3',
        # tkinter (dialogos nativos)
        'tkinter',
        'tkinter.filedialog',
        # src modules
        'src.ui.api',
        'src.ui.app',
        'src.motor',
        'src.scheduler',
        'src.adapters.base_adapter',
        'src.adapters.adapter_factory',
        'src.adapters.generic_adapter',
        'src.generators.txt_generator',
        'src.generators.anulacion_generator',
        'src.generators.json_generator',
        'src.sender.universal_sender',
        'src.config.client_loader',
        'src.database.schema',
        'src.database.cpe_logger',
        'src.licenses.validator',
        'src.tools.wizard_service',
        'src.tools.wizard_mapper',
        'src.tools.smart_mapper',
        'src.tools.source_explorer',
        'src.tools.contract_validator',
    ],
    hookspath  = [],
    hooksconfig= {},
    runtime_hooks = [],
    excludes   = [
        'Eel',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'tensorflow',
        'torch',
        'jupyter',
        'notebook',
    ],
    noarchive  = False,
    optimize   = 0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries = True,
    name             = 'DisateQ-Motor-CPE',
    debug            = False,
    bootloader_ignore_signals = False,
    strip            = False,
    upx              = False,
    console = False,
    disable_windowed_traceback = False,
    target_arch      = None,
    codesign_identity= None,
    entitlements_file= None,
    icon             = str(ROOT / 'src' / 'ui' / 'frontend' / 'assets' / 'icons' / 'cpe_disateq.ico'),
    version          = 'version_info.txt' if (ROOT / 'version_info.txt').exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip      = False,
    upx        = False,
    upx_exclude= [],
    name       = 'DisateQ-Motor-CPE',
)
