# CONTEXTO MAESTRO — DisateQ Motor CPE v5.2
**Para retomar sesion — pegar al inicio de cada chat nuevo**
**Ultima actualizacion:** 2026-05-02
**Proyecto activo:** DisateQ Motor CPE v5.0

---

## INSTRUCCION DE INICIO

Al pegar este documento en un chat nuevo, indicar:

```
Contexto: DISATEQ DEV FLOW v1
Proyecto: DisateQ Motor CPE v5.0

Actua como arquitecto de software senior.
Conoces el proyecto completo segun este documento.
Continuamos el desarrollo desde donde quedamos.
Etapa actual: EJECUCION — TASK-006
```

---

## 1. QUE ES ESTE PROYECTO

Motor generador y enrutador universal de Comprobantes de Pago Electronicos (CPE)
para SUNAT Peru. Lee datos desde sistemas legacy o modernos de cualquier cliente,
genera archivos TXT/JSON y los envia a servicios de validacion tercerizados
(OSE/PSE/SEE).

**Desarrollador:** Fernando Hernan Tejada Quevedo — DisateQ DEV
**Repo:** https://github.com/disateq-dev/disateq-motor-cpe-v5
**Ruta local:** D:\DisateQ\Proyectos\disateq-motor-cpe-v5

---

## 2. FLUJO DEL MOTOR

```
Fuente de datos (DBF, Excel, SQL, CSV, Access...)
        ↓
AdapterFactory — detecta tipo, instancia adaptador
        ↓
GenericAdapter + contrato YAML
        ↓
Motor / Orquestador
    read_pending()  → lee comprobantes con flag correcto
    read_items()    → lee items de cada comprobante (cache)
    normalize()     → convierte a estructura CPE interna
        ↓
Verificar en SQLite — ¿ya fue REMITIDO?
    Si  → IGNORADO (anti-duplicado)
    No  → continuar
        ↓
Validar serie — ¿permitida en config del cliente?
    No  → IGNORADO
    Si  → continuar
        ↓
Generador — produce .txt o .json segun endpoint
        ↓
UniversalSender — envia a endpoints activos del cliente
    APIFAS / Nubefact / DisateQ Platform
        ↓
Respuesta SUNAT — CDR
        ↓
CpeLogger — registra estado en SQLite
write_flag() — marca en fuente si es posible
```

---

## 3. DOS CASOS DE USO

**Caso 1 — Cliente con programador**
Programador conoce su sistema. Llena contrato YAML indicando tablas y campos.
Motor lo lee y procesa. Sin intervencion adicional.

**Caso 2 — Cliente sin programador**
source_explorer escanea la carpeta del sistema legacy.
smart_mapper (IA) genera contrato YAML borrador con score de confianza.
Score >= 0.80 → procede automatico.
Score < 0.80  → UI muestra solo los campos faltantes al tecnico.

---

## 4. DECISIONES DE ARQUITECTURA VIGENTES

| Decision | Detalle |
|---|---|
| PyWebView reemplaza Eel | WebView2 nativo Windows 10/11, sin Chrome |
| GenericAdapter unico adaptador | DBF, Excel, SQL, CSV via contrato YAML |
| XlsxAdapter (POS) eliminado | Proyecto POS cerrado definitivamente |
| DbfFarmaciaAdapter eliminado | Migrado a contrato YAML farmacias_fas |
| Un solo flujo para todas las fuentes | AdapterFactory → GenericAdapter → Motor |
| Ruta de fuente en YAML del cliente | No hardcoded en codigo |
| Score confianza 0.80 para autocontrato | Por debajo → UI muestra campos faltantes |
| SQLite es fuente de verdad de envios | Controla duplicados y reenvios |
| Marca en fuente es opcional | DBF/SQL/Excel si permiten escritura |
| Requirements opcionales por perfil | mysql y postgres en archivos separados |
| DisateQAPI clase unica | Todos los metodos expuestos a JS via js_api |
| write_flag DBF pendiente | dbfread es read-only — pendiente python-dbf |
| Items en cache | _load_items_cache() carga detalleventa una vez |
| SafeFieldParser | Maneja fechas y floats nulos en DBF |
| Wizard abre automaticamente | Si no hay config/clientes/*.yaml al arrancar |
| Motor usa file stem como alias | No empresa.alias para buscar archivos |
| ClientLoader robusto | Salta YAMLs invalidos, soporta estructura v4 y v5 |

---

## 5. CLIENTE ACTIVO — farmacia_central

**YAML cliente:** config/clientes/farmacia_central.yaml
**YAML contrato:** config/contratos/farmacia_central.yaml
**Ruta datos TEST:** D:\FFEESUNAT\Test
**Tipo fuente:** DBF (FoxPro legacy)
**Encoding:** latin-1

**Estructura YAML cliente (formato ClientLoader v5):**
```yaml
empresa:
  ruc: '10715460632'
  razon_social: FARMACIA CENTRAL S.A.C.
  nombre_comercial: Farmacia Central
  alias: LOCAL PRINCIPAL
fuente:
  tipo: dbf
  rutas: [D:/FFEESUNAT/test]
  contrato_path: contratos/farmacia_central.yaml
series:
  boleta: [{serie: B001, correlativo_inicio: 16377, activa: true}]
  factura: [{serie: F001, correlativo_inicio: 0, activa: true}]
envio:
  endpoints:
    - nombre: APIFAS
      activo: true
      formato: txt
      url_comprobantes: https://apifas.disateq.com/produccion_text.php
      url_anulaciones: https://apifas.disateq.com/anulacion_text.php
```

**Estructura YAML contrato (formato GenericAdapter v5):**
```yaml
cliente_id: farmacia_central
source:
  type: dbf
  path: D:\FFEESUNAT\Test
  encoding: latin-1
comprobantes:
  tabla: enviosffee
  flag_lectura: {campo: FLAG_ENVIO, valor: 2}
  flag_escritura: {campo: FLAG_ENVIO, enviado: 3, error: 4}
notas:
  tabla: notacredito
  tipo_registro: anulacion
  flag_lectura:
    campo_pendiente: PENDIENTE_
    valor_pendiente: '2'
    campo_tipo_movim: TIPO_MOVIM
    valor_tipo_movim: 2
  serie_prefijos: {F: FC, B: BC}
  tipo_comprobante_map: {F: '1', B: '2'}
items:
  tabla: detalleventa
totales:
  tabla: factura
productos:
  tabla: productox
  join_campo: CODIGO_PRO
motivos:
  tabla: motivonota
cliente_varios:
  tipo_doc: '-'
  num_doc: '00000000'
  nombre: CLIENTE VARIOS
```

**Archivos DBF verificados con datos reales 2026-04-29:**

| Archivo | Uso | Flag lectura |
|---|---|---|
| enviosffee.dbf | Comprobantes pendientes | FLAG_ENVIO = 2 (integer) |
| detalleventa.dbf | Items de cada comprobante | — |
| productox.dbf | Catalogo de productos | — |
| factura.dbf | Totales reales (REAL_FACTU) | — |
| notacredito.dbf | Anulaciones pendientes | PENDIENTE_ = '2' + TIPO_MOVIM = 2 |
| motivonota.dbf | Motivos de anulacion | — |

**Resultado prueba mock 2026-05-02:**
- 527 comprobantes pendientes leidos
- 400 procesados/enviados (mock)
- 127 ignorados (series no habilitadas o duplicados)
- 0 errores

**Nota:** detalleventa.dbf tiene fechas y floats nulos (b'\x00\x00').
SafeFieldParser los maneja — no bloquea el procesamiento.

---

## 6. CONTROL DE ENVIOS

SQLite es la fuente de verdad. Tabla `cpe_envios`.
Indice unico: `ruc_emisor + serie + numero`

| Estado | Cuando |
|---|---|
| LEIDO | Comprobante leido desde fuente |
| NORMALIZADO | Convertido a estructura CPE |
| GENERADO | Archivo .txt/.json generado |
| REMITIDO | Enviado al endpoint exitosamente |
| ERROR | Fallo en algun punto |
| IGNORADO | Serie no permitida o duplicado |

---

## 7. DRIVERS DE BASE DE DATOS

| Motor | Driver | Estado |
|---|---|---|
| SQL Server | pyodbc | Activo — base |
| DBF | dbfread | Activo — base (solo lectura) |
| Excel / XLSX | openpyxl | Activo — base |
| CSV | nativo Python | Sin dependencia |
| MySQL / MariaDB | mysql-connector-python | requirements-mysql.txt |
| PostgreSQL | psycopg2-binary | requirements-postgres.txt |
| Access | pyodbc + Access Engine | Requiere instalacion manual |

---

## 8. ESTRUCTURA DEL PROYECTO

```
disateq-motor-cpe-v5/
├── main.py
├── requirements.txt
├── requirements-mysql.txt
├── requirements-postgres.txt
│
├── src/
│   ├── adapters/
│   │   ├── base_adapter.py
│   │   ├── adapter_factory.py
│   │   └── generic_adapter.py        — SafeFieldParser + cache items ✓
│   │
│   ├── generators/
│   │   ├── txt_generator.py
│   │   ├── json_generator.py
│   │   └── anulacion_generator.py
│   │
│   ├── sender/
│   │   └── universal_sender.py
│   │
│   ├── config/
│   │   └── client_loader.py          — robusto v5, soporta estructura v4/v5 ✓
│   │
│   ├── database/
│   │   ├── schema.py
│   │   └── cpe_logger.py
│   │
│   ├── licenses/
│   │   └── validator.py
│   │
│   ├── tools/
│   │   ├── source_explorer.py
│   │   ├── smart_mapper.py
│   │   ├── wizard_mapper.py          — heuristica mapeo DBF→CPE ✓
│   │   ├── wizard_service.py         — test_fuente, analizar, guardar ✓
│   │   ├── contract_validator.py     — TASK-007 pendiente
│   │   └── autocontract_service.py  — TASK-009 pendiente
│   │
│   ├── motor.py                      — usa file stem, no empresa.alias ✓
│   ├── scheduler.py
│   │
│   └── ui/
│       ├── api.py                    — 4 metodos wizard + _cliente_stem ✓
│       ├── app.py                    — wizard auto si no hay cliente ✓
│       └── frontend/
│           ├── index.html            — v5.0, sin eel.js ✓
│           ├── wizard.html           — 6 pasos completos ✓
│           ├── css/
│           │   ├── variables.css
│           │   ├── layout.css        — separador naranja, nav-tabs ✓
│           │   └── components.css
│           └── js/
│               ├── app.js            — PyWebView completo ✓
│               ├── dashboard.js      — PyWebView completo ✓
│               ├── processor.js      — PyWebView completo ✓
│               ├── utils.js
│               └── wizard.js         — 6 pasos, endpoints dinamicos ✓
│
├── config/
│   ├── clientes/
│   │   ├── farmacia_central.yaml     — cliente activo ✓
│   │   └── local_cercado_piura.yaml
│   └── contratos/
│       └── farmacia_central.yaml    — contrato completo ✓
│
└── docs/
    └── manual_vivo.md
```

---

## 9. ENTORNO DE DESARROLLO

| Item | Valor |
|---|---|
| OS | Windows 10/11 |
| Python | 3.14 |
| Ruta proyecto | D:\DisateQ\Proyectos\disateq-motor-cpe-v5 |
| Ruta descargas | D:\DATA\Downloads |
| Ruta datos test | D:\FFEESUNAT\Test |
| pywebview | 6.2.1 (con pythonnet 3.1.0rc0) |
| dbfread | 2.0.7 |
| Git rama | main |
| Commits sesion | ~25 commits desde v5.1 |

**Deploy scripts — flujo estandar:**
```
1. Descargar archivos del chat → D:\DATA\Downloads
2. Unblock-File .\script.ps1  (si es .ps1 nuevo)
3. .\script.ps1  (desde raiz del proyecto)
4. Verificar en consola
```

**Regla de oro: NUNCA parches — siempre reescritura completa del archivo.**

---

## 10. PLAN DE TRABAJO — ESTADO ACTUAL

### FASE 1 — BASE SOLIDA (COMPLETA ✅)

| Task | Descripcion | Commit |
|---|---|---|
| TASK-001 | Migrar DbfFarmaciaAdapter → contrato YAML | 2313e39 |
| TASK-001B | Control anti-duplicado y reenvio | 2313e39 |
| TASK-002 | Eliminar XlsxAdapter + DbfFarmaciaAdapter | 03723b7 |
| TASK-003 | SQLite — inicializacion en arranque | 53cba0b |
| TASK-004 | Migrar UI Eel → PyWebView | 96d23c4 |

### FASE 2 — FUNCIONALIDAD COMPLETA (EN CURSO)

| Task | Descripcion | Estado |
|---|---|---|
| TASK-004 JS | Frontend eel → window.pywebview.api | ✅ COMPLETO |
| TASK-005 | Wizard end-to-end 6 pasos | ✅ COMPLETO |
| TASK-006 | Guardar series desde UI al YAML | PENDIENTE |
| TASK-007 | Validador de contrato con score confianza | PENDIENTE |
| TASK-008 | Credenciales APIFAS — primer envio real | PENDIENTE |
| TASK-009 | Autocontrato — flujo Caso 2 completo | PENDIENTE |

### FIXES PENDIENTES (antes de TASK-006)

| Fix | Descripcion |
|---|---|
| FIX-UI-01 | Header: separadores verticales faltantes |
| FIX-UI-02 | Header: fecha/hora agrupada separada del resto |
| FIX-UI-03 | Nav-tabs: contraste con header |
| FIX-DBF-01 | SafeFieldParser: floats nulos b'\x00\x00' |
| FIX-WIZ-01 | Wizard: contrato Excel descargable/subible (Cambio 3) |

### FASE 3 — UI/UX

| Task | Descripcion | Estado |
|---|---|---|
| TASK-010 | Colores pestanas CSS | PENDIENTE |
| TASK-011 | Tabla Procesar — columna Tipo B/F | PENDIENTE |
| TASK-012 | Dashboard — stepSize chart.js | PENDIENTE |
| TASK-013 | Fuente label — ruta real | PENDIENTE |

### FASE 4 — INFRAESTRUCTURA

| Task | Descripcion | Estado |
|---|---|---|
| TASK-014 | Build PyWebView + requirements por perfil | PENDIENTE |
| TASK-015 | SQL Server — prueba real | PENDIENTE |
| TASK-016 | Licenciamiento desde UI | PENDIENTE |

### FASE 5 — ROADMAP FUTURO

TASK-017 XML UBL 2.1 / TASK-018 DisateQ Platform /
TASK-019 WhatsApp notifier / TASK-020 Cierre Diario

---

## 11. FLUJO DE TRABAJO — DISATEQ FLOW OPS v1

```
inicio → input → analisis → plan → ejecucion → revision → validacion → commit
```

**Etapa actual: EJECUCION**
Herramienta: Claude Code en VS Code
Siguiente tarea: FIX-UI-01/02/03 → luego TASK-006

**Reglas activas:**
- Sin GO humano no hay codigo
- 1 tarea = 1 resultado verificable
- Sin input completo no se avanza
- Ningun commit sin pasar checklist de validacion
- Formato commit: feat|fix|refactor|docs|security: descripcion
- NUNCA parches — siempre reescritura completa

---

## 12. NOTAS TECNICAS IMPORTANTES

**ClientLoader — cargar() busca en este orden:**
1. Por stem de archivo ({alias}.yaml)
2. Por empresa.ruc
3. Por empresa.alias (case-insensitive)

**Motor — alias:**
```python
# CORRECTO: usar cliente_alias (file stem), no self.config.alias (empresa alias)
self.alias = cliente_alias  # 'farmacia_central', no 'LOCAL PRINCIPAL'
```

**GenericAdapter — _tabla_path():**
```python
# Agrega .dbf automaticamente si no tiene extension
def _tabla_path(self, nombre_tabla: str) -> str:
    nombre = nombre_tabla.strip()
    if not nombre.lower().endswith('.dbf'):
        nombre = nombre + '.dbf'
    return os.path.join(self.source_path, nombre)
```

**Wizard — YAML generado por wizard_service.py:**
Debe usar estructura formato ClientLoader (empresa.ruc, envio.endpoints)
NO la estructura plana (ruc_emisor, endpoints a nivel raiz).

**PyWebView — llamadas JS:**
```javascript
// CORRECTO:
window.pywebview.api.metodo(params).then(callback)
// MAL (legacy Eel):
eel.metodo(params)(callback)
```

**Scheduler callback JS:**
```python
self._window.evaluate_js(f'schedulerCicloCompletado({json.dumps(data)})')
```

**SafeFieldParser — DBF con datos nulos:**
```python
class SafeFieldParser(FieldParser):
    def parseD(self, field, data):
        try:
            if not data or b'\x00' in data:
                return None
            return super().parseD(field, data)
        except Exception:
            return None
    # TODO: agregar parseN/parseF para floats nulos b'\x00\x00'
```

---

## 13. ARCHIVOS GENERADOS — SESION 2026-05-02

| Archivo | Ruta en proyecto |
|---|---|
| wizard.html | src/ui/frontend/ |
| wizard.js | src/ui/frontend/js/ |
| wizard_service.py | src/tools/ |
| wizard_mapper.py | src/tools/ |
| api.py | src/ui/ (4 metodos wizard + _cliente_stem) |
| app.js | src/ui/frontend/js/ |
| dashboard.js | src/ui/frontend/js/ |
| processor.js | src/ui/frontend/js/ |
| generic_adapter.py | src/adapters/ (SafeFieldParser + cache items) |
| client_loader.py | src/config/ (robusto v5) |
| motor.py | src/ (alias = file stem) |
| farmacia_central.yaml | config/contratos/ |
| layout.css | src/ui/frontend/css/ |

---

*DisateQ™ Motor CPE v5.0 — Contexto Maestro v5.2 — 2026-05-02*
*FASE 1 + TASK-004JS + TASK-005 completos — Motor procesa 400/527 mock — Continuar en FIX-UI → TASK-006*
