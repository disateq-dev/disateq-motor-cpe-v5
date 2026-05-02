# CONTEXTO MAESTRO — DisateQ Motor CPE v5.0
**Para retomar sesion — pegar al inicio de cada chat nuevo**
**Ultima actualizacion:** 2026-04-29
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
Etapa actual: EJECUCION — TASK-001
```

---

## 1. QUE ES ESTE PROYECTO

Motor generador y enrutador universal de Comprobantes de Pago Electronicos (CPE)
para SUNAT Peru. Lee datos desde sistemas legacy o modernos de cualquier cliente,
genera archivos TXT/JSON y los envia a servicios de validacion tercerizados
(OSE/PSE/SEE).

**Desarrollador:** Fernando Hernan Tejada Quevedo — DisateQ DEV
**Repo:** https://github.com/disateq-dev/disateq-motor-cpe-v5
**Ruta local:** D:\disateq\Proyectos\disateq-motor-cpe-v5

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
    read_items()    → lee items de cada comprobante
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

---

## 5. CLIENTE ACTIVO — farmacias_fas

**Antes llamado:** farmacia_central
**Ruta datos:** C:\sistemas\data
**Tipo fuente:** DBF (FoxPro legacy)

**Archivos DBF:**

| Archivo | Uso | Flag lectura |
|---|---|---|
| enviosffee.dbf | Comprobantes pendientes | FLAG_ENVIO = '2' |
| detalleventa.dbf | Items de cada comprobante | — |
| productox.dbf | Catalogo de productos | — |
| factura.dbf | Totales reales (REAL_FACTU) | — |
| notacredito.dbf | Anulaciones pendientes | PENDIENTE_ = '2' + TIPO_MOVIM = '2' |
| motivonota.dbf | Motivos de anulacion | — |

**Flags que escribe el Motor:**

| Valor | Significado |
|---|---|
| '3' | Enviado y confirmado (Motor escribe) |
| '4' | Error — pendiente reintento (Motor escribe) |

> Pendiente: verificar si sistema legacy bloquea DBF durante escritura simultanea.
> Si hay bloqueo → solo SQLite controla, no se escribe al DBF.

---

## 6. CONTROL DE ENVIOS — todas las fuentes

SQLite es la fuente de verdad. Antes de procesar cualquier comprobante
el Motor verifica si ya existe REMITIDO para ese serie+numero+ruc.

**Estados SQLite:**

| Estado | Cuando |
|---|---|
| LEIDO | Comprobante leido desde fuente |
| NORMALIZADO | Convertido a estructura CPE |
| GENERADO | Archivo .txt/.json generado |
| REMITIDO | Enviado al endpoint exitosamente |
| ERROR | Fallo en algún punto |
| IGNORADO | Serie no permitida o duplicado |

**Reenvio forzado:** UI historial → seleccionar → Reenviar.
Motor ignora SQLite y DBF, fuerza reproceso.
Util para falsos positivos o errores de conexion.

**write_flag() en BaseAdapter:**
Metodo opcional. Cada adaptador lo implementa si su fuente permite escritura.
Si no puede escribir, retorna silenciosamente sin error.

---

## 7. DRIVERS DE BASE DE DATOS

| Motor | Driver | Estado |
|---|---|---|
| SQL Server | pyodbc | Activo — base |
| DBF | dbfread | Activo — base |
| Excel / XLSX | openpyxl | Activo — base |
| CSV | nativo Python | Sin dependencia |
| MySQL / MariaDB | mysql-connector-python | requirements-mysql.txt |
| PostgreSQL | psycopg2-binary | requirements-postgres.txt |
| Access | pyodbc + Access Engine | Requiere instalacion manual |

---

## 8. ESTRUCTURA DEL PROYECTO

```
disateq-motor-cpe-v5/
├── main.py                          # entry point CLI + UI
├── requirements.txt                 # dependencias base
├── requirements-mysql.txt           # perfil MySQL/MariaDB
├── requirements-postgres.txt        # perfil PostgreSQL
│
├── src/
│   ├── adapters/
│   │   ├── base_adapter.py          # write_flag() aqui
│   │   ├── adapter_factory.py       # detecta contrato_path
│   │   └── generic_adapter.py       # adaptador universal
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
│   │   └── client_loader.py
│   │
│   ├── database/
│   │   ├── schema.py                # TASK-003 — crear
│   │   └── cpe_logger.py
│   │
│   ├── licenses/
│   │   └── validator.py
│   │
│   ├── tools/
│   │   ├── source_explorer.py
│   │   ├── smart_mapper.py
│   │   ├── contract_validator.py    # TASK-007 — crear
│   │   └── autocontract_service.py  # TASK-009 — crear
│   │
│   ├── motor.py
│   ├── scheduler.py
│   │
│   └── ui/
│       ├── api.py                   # TASK-004 — clase DisateQAPI
│       ├── app.py                   # TASK-004 — arranque PyWebView
│       └── frontend/
│           ├── index.html
│           ├── wizard.html
│           ├── css/
│           └── js/
│
├── config/
│   ├── clientes/
│   │   └── farmacias_fas.yaml
│   └── contratos/
│       └── farmacias_fas.yaml
│
└── docs/
    └── manual_vivo.md
```

---

## 9. PLAN DE TRABAJO — ESTADO ACTUAL

### FASE 1 — BASE SOLIDA (EN CURSO)

| Task | Descripcion | Estado |
|---|---|---|
| TASK-001 | Migrar DbfFarmaciaAdapter → contrato YAML farmacias_fas | PENDIENTE |
| TASK-001B | Control anti-duplicado y reenvio — todas las fuentes | PENDIENTE |
| TASK-002 | Eliminar XlsxAdapter (POS) | PENDIENTE |
| TASK-003 | SQLite — inicializacion en arranque | PENDIENTE |
| TASK-004 | Migrar UI Eel → PyWebView | PENDIENTE |

### FASE 2 — FUNCIONALIDAD COMPLETA

| Task | Descripcion | Estado |
|---|---|---|
| TASK-005 | Wizard end-to-end — 6 pasos completos | PENDIENTE |
| TASK-006 | Guardar series desde UI al YAML | PENDIENTE |
| TASK-007 | Validador de contrato con score confianza | PENDIENTE |
| TASK-008 | Credenciales APIFAS — primer envio real | PENDIENTE |
| TASK-009 | Autocontrato — flujo Caso 2 completo | PENDIENTE |

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

## 10. FLUJO DE TRABAJO — DISATEQ FLOW OPS v1

```
inicio → input → analisis → plan → ejecucion → revision → validacion → commit
```

**Etapa actual: EJECUCION (Etapa 4)**
Herramienta: Claude Code en VS Code
Siguiente tarea: TASK-001

**Reglas activas:**
- Sin GO humano no hay codigo
- 1 tarea = 1 resultado verificable
- Sin input completo no se avanza
- Ningun commit sin pasar checklist de validacion
- Formato commit: feat|fix|refactor|docs|security: descripcion

---

## 11. RETROALIMENTACION PENDIENTE PARA FLOW OPS + ECOSYSTEM

Para pasar al equipo que mantiene los documentos:

**FLOW OPS v1:**
- Etapa 4 define estructura de capas para FastAPI/web.
  Agregar variante: Estructura de capas — Motor de escritorio (PyWebView)
  con separacion: motor.py / ui/api.py / adapters / generators / sender

**ECOSYSTEM v1:**
- Reemplazar Eel por PyWebView en el stack.
  Nota: WebView2 nativo Windows 10/11 — sin dependencia de Chrome.
  Empaquetado limpio con PyInstaller.
- disateq-init.ps1 aun no existe — agregar como pendiente antes del
  siguiente proyecto piloto.

---

## 12. ARCHIVOS GENERADOS EN ESTA SESION

Guardar en `D:\disateq\Proyectos\disateq-motor-cpe-v5\docs\` o en
la carpeta `/1_raw` del proyecto segun FLOW OPS:

| Archivo | Contenido |
|---|---|
| 2_ANALISIS_MOTOR_CPE_v5.md | Analisis formal Etapa 2 |
| 3_PLAN_MOTOR_CPE_v5.md | Plan completo Etapa 3 con todas las tasks |
| CONTEXTO_MAESTRO_MOTOR_CPE_v5.md | Este archivo |

---

*DisateQ™ Motor CPE v5.0 — Contexto Maestro — 2026-04-29*
*Generado al cierre de sesion para continuidad del desarrollo*
