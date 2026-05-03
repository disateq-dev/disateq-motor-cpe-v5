# CONTEXTO MAESTRO — DisateQ Motor CPE v5.9
**Para retomar sesion — pegar al inicio de cada chat nuevo**
**Ultima actualizacion:** 2026-05-03
**Proyecto activo:** DisateQ Motor CPE v5.0

---

## INSTRUCCION DE INICIO

```
Contexto: DISATEQ DEV FLOW v1
Proyecto: DisateQ Motor CPE v5.0

Actua como arquitecto de software senior.
Conoces el proyecto completo segun este documento.
Continuamos el desarrollo desde donde quedamos.
Etapa actual: TASK-INS-01 — Instalador Inno Setup
```

---

## 1. QUE ES ESTE PROYECTO

Motor generador y enrutador universal de CPE para SUNAT Peru.
Lee DBF/SQLite/MySQL/SQL Server, genera TXT y envia a APIFAS (SEE/OSE).

**Desarrollador:** Fernando Hernan Tejada Quevedo — DisateQ DEV
**Repo:** https://github.com/disateq-dev/disateq-motor-cpe-v5
**Ruta local:** D:\DisateQ\Proyectos\disateq-motor-cpe-v5

---

## 2. FLUJO DEL MOTOR

```
Fuente (DBF/SQLite) → AdapterFactory → GenericAdapter
    _normalizar_config_cliente() — ruc en raiz ✓
    _norm_num() — strip leading zeros ✓
        ↓
Motor → Anti-duplicado SQLite (ruc_emisor correcto) ✓
        ↓
TxtGenerator v5 / AnulacionGenerator v5
        ↓
UniversalSender — multipart/form-data
    _es_exito(body) — parsea body APIFAS ✓
        ↓
CpeLogger SQLite ✓
```

---

## 3. APIFAS — ENDPOINTS

| Tipo | Comprobantes | Anulaciones | Exito body |
|---|---|---|---|
| SEE | produccion_text.php | anulacion_text.php | Proceso-Aceptado |
| OSE | ose_produccion.php | ose_anular.php | Procesando OSE |

**Formato:** multipart/form-data, field `file`, sin credenciales.
**HTTP 200 siempre** — parsear body para exito.

---

## 4. BUILD EXE — ESTADO ACTUAL

```
.\build.ps1   # PyInstaller 6.20+, Python 3.14
# Resultado: dist\DisateQ-Motor-CPE\
#   DisateQ-Motor-CPE.exe  (8.6 MB)
#   _internal\             (dependencias, ~50 MB total)
#   config\                (clientes + contratos YAML)
#   data\                  (SQLite — copiar manualmente)
#   output\
# Log exe: data\disateq.log
# IMPORTANTE: copiar data\disateq_cpe.db al dist antes de entregar
```

**disateq.spec en .gitignore** → `git add -f disateq.spec`

---

## 5. TASK-INS-01 — INSTALADOR INNO SETUP

### Objetivo
Generar `DisateQ-Motor-CPE-Setup.exe` — instalador profesional para entregar a clientes.

### Flujo de entrega a cliente
```
1. build.ps1 → dist\DisateQ-Motor-CPE\   (motor empaquetado)
2. inno_setup.iss → DisateQ-Motor-CPE-Setup.exe  (instalador)
3. Cliente ejecuta Setup.exe
4. Motor se instala en C:\Program Files\DisateQ\Motor CPE\
5. Acceso directo en escritorio + menú inicio
6. Cliente recibe disateq_motor.lic por email → la carga desde Config UI
```

### Lo que debe hacer el instalador
- Instalar todos los archivos de `dist\DisateQ-Motor-CPE\`
- Crear acceso directo en escritorio y menú inicio
- Verificar que WebView2 está instalado (Windows 10/11)
- Crear carpeta `data\` y `output\` vacías
- Copiar `config\clientes\` del cliente específico (por parámetro)
- Copiar `src\licenses\keys\disateq_public.pem` para validación RSA
- Crear desinstalador limpio
- NO incluir `disateq_private.pem` — nunca

### Archivos a generar
| Archivo | Descripcion |
|---|---|
| `installer\disateq_setup.iss` | Script Inno Setup |
| `installer\build_installer.ps1` | Script que corre Inno Setup + build completo |
| `installer\README_INSTALADOR.md` | Instrucciones internas DisateQ |

### Estructura instalación destino
```
C:\Program Files\DisateQ\Motor CPE\
    DisateQ-Motor-CPE.exe
    _internal\
    config\
        clientes\{cliente}.yaml
        contratos\{cliente}.yaml
    data\              (vacío, se crea en runtime)
    output\            (vacío)
    licenses\
        disateq_public.pem
```

---

## 6. LICENCIAMIENTO

**Keypair RSA-2048:**
- Privada: `src/licenses/keys/disateq_private.pem` — en .gitignore, NUNCA incluir en instalador
- Pública: `src/licenses/keys/disateq_public.pem` — incluir en instalador

**Licencia activa:**
- `src/licenses/client_licenses/disateq_motor.lic`
- FARMACIA CENTRAL S.A.C. — válida hasta 2027-05-02

**Flujo licencia con instalador:**
1. Instalador copia `disateq_public.pem` al directorio de instalación
2. Motor arranca, busca licencia en `C:\Program Files\DisateQ\Motor CPE\`
3. Cliente carga su `.lic` desde Config UI → botón "Cargar licencia (.lic)"

**validator.py busca en este orden:**
```python
candidatos = [
    Path(r"C:\Program Files\DisateQ\Motor CPE"),  # produccion
    Path(__file__).parent / "client_licenses",     # desarrollo
    raiz,                                           # exe/raiz
]
```

---

## 7. CLIENTES CONFIGURADOS

**farmacia_central** — DBF, SEE, RUC 10715460632
- Encoding cp850, NUMERO_FAC normalizado con _norm_num
- 10 comprobantes enviados reales ✓

**itera_prueba** — SQLite, SEE, RUC 20123456789
- BD: data/itera_prueba.db
- 10 comprobantes mock, boletas + facturas ✓

---

## 8. ESTRUCTURA DEL PROYECTO

```
disateq-motor-cpe-v5/
├── src/
│   ├── adapters/
│   │   ├── adapter_factory.py   — _normalizar_config_cliente() ✓
│   │   └── generic_adapter.py   — cp850, _norm_num, SQLite ✓
│   ├── generators/
│   │   ├── txt_generator.py     — CPE plano v5 ✓
│   │   └── anulacion_generator.py
│   ├── sender/
│   │   └── universal_sender.py  — multipart + _es_exito() ✓
│   ├── licenses/
│   │   ├── keys/
│   │   │   ├── disateq_public.pem   — incluir en instalador
│   │   │   └── disateq_private.pem  — NUNCA incluir
│   │   ├── client_licenses/
│   │   │   └── disateq_motor.lic
│   │   └── validator.py         — cargar_licencia(), get_licencia_info() ✓
│   ├── motor.py                 ✓
│   └── ui/
│       ├── api.py               — _TIPO_CPE_MAP, get_licencia_info ✓
│       ├── app.py               — _resolver_frontend, logging exe ✓
│       └── frontend/
│           ├── index.html       — footer dias licencia ✓
│           └── js/app.js        — actualizarFooterLicencia ✓
├── config/
│   ├── clientes/
│   │   ├── farmacia_central.yaml
│   │   └── itera_prueba.yaml
│   └── contratos/
│       ├── farmacia_central.yaml
│       └── itera_prueba.yaml
├── data/
│   └── itera_prueba.db
├── installer/                   ← CREAR EN TASK-INS-01
│   ├── disateq_setup.iss
│   ├── build_installer.ps1
│   └── README_INSTALADOR.md
├── disateq.spec                 — git add -f
├── build.ps1
└── requirements.txt
```

---

## 9. ENTORNO DE DESARROLLO

| Item | Valor |
|---|---|
| OS | Windows 10/11 |
| Python | 3.14 |
| Ruta proyecto | D:\DisateQ\Proyectos\disateq-motor-cpe-v5 |
| Ruta descargas | D:\DATA\Downloads |
| Ruta datos | D:\FFEESUNAT\Test |
| PyInstaller | 6.20.0 |
| Inno Setup | Por instalar — descargar de jrsoftware.org |

**Deploy estandar:**
```powershell
Copy-Item D:\DATA\Downloads\archivo destino -Force
git add ... && git commit -m "..."
python main.py
```

---

## 10. REGLAS DEL PROYECTO (DISATEQ DEV FLOW v1)

- Sin GO humano no hay codigo
- NUNCA parches — siempre reescritura completa
- 1-2 archivos → comandos directos en chat (no .ps1)
- 3+ archivos o logica compleja → generar .ps1
- Deploy: `Copy-Item D:\DATA\Downloads\archivo destino -Force`
- `git add → commit → push`
- YAML dump: `sort_keys=False` siempre
- `disateq.spec` en .gitignore → `git add -f`
- `disateq_private.pem` en .gitignore — NUNCA subir ni incluir en instalador

---

## 11. PENDIENTES TRAS TASK-INS-01

| Task | Descripcion |
|---|---|
| TASK-INS-02 | Icono escritorio + menu inicio (ya en INS-01) |
| TASK-INS-03 | Desinstalador (ya en INS-01) |
| TASK-015b | MySQL prueba real (cliente iTERA) |
| FIX-WIZ-01 | Wizard Excel descargable |
| TASK-017 | XML UBL 2.1 |
| TASK-018 | DisateQ Platform |

---

## 12. NOTAS TECNICAS CRITICAS

**_TIPO_CPE_MAP en api.py:**
```python
_TIPO_CPE_MAP = {'1':'factura','2':'boleta','3':'nota_credito','7':'nota_debito','9':'anulacion'}
```

**universal_sender — exito APIFAS:**
```python
RESPUESTAS_EXITO = {'procesando ose','anulando ose','proceso-aceptado','por anular'}
def _es_exito(body): return body.strip().lower() in RESPUESTAS_EXITO
```

**adapter_factory — normalizar config:**
```python
def _normalizar_config_cliente(data):
    empresa = data.get('empresa', {})
    if 'ruc' not in data: data['ruc'] = empresa.get('ruc', '')
    return data
```

**validator.py — busqueda licencia:**
```python
candidatos = [
    Path(r"C:\Program Files\DisateQ\Motor CPE"),
    Path(__file__).parent / "client_licenses",
    raiz,
]
```

**Encoding DBF:** cp850
**_norm_num:** `numero.lstrip('0') or '0'`
**cliente_id SQLite:** file stem del YAML

---

*DisateQ™ Motor CPE v5.0 — Contexto Maestro v5.9 — 2026-05-03*
*Quick wins cerrados — Filtros OK — Footer licencia OK — Cierre rapido OK*
*Continuar en TASK-INS-01 — Instalador Inno Setup*
