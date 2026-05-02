# PLAN — DisateQ Motor CPE v5.0
**Etapa 3 — DISATEQ FLOW OPS**
**Fecha:** 2026-04-29
**Estado:** Aprobado — GO por Fernando Hernán Tejada

---

## DECISIONES DE ARQUITECTURA VIGENTES

| Decision | Detalle |
|---|---|
| PyWebView reemplaza Eel | WebView2 nativo Windows 10/11, sin Chrome |
| GenericAdapter unico adaptador | DBF, Excel, SQL, CSV via contrato YAML |
| XlsxAdapter (POS™) eliminado | Proyecto POS cerrado definitivamente |
| DbfFarmaciaAdapter → farmacias_fas | Migrar mapeo hardcoded a contrato YAML |
| Un solo flujo para todas las fuentes | AdapterFactory → GenericAdapter → Motor |
| Ruta de fuente en YAML del cliente | No hardcoded en codigo |
| Score confianza 0.80 para autocontrato | Por debajo → UI muestra solo campos faltantes |
| SQLite es fuente de verdad de envios | Controla duplicados y reenvios para cualquier fuente |
| Marca en fuente es opcional | DBF/SQL/Excel si permiten escritura, sino solo SQLite |
| Requirements opcionales por perfil | mysql y postgres comentados, se activan por perfil |

---

## ARCHIVOS DBF — farmacias_fas

Ubicacion: `C:\sistemas\data`

| Archivo | Uso | Flag de lectura |
|---|---|---|
| `enviosffee.dbf` | Comprobantes pendientes | `FLAG_ENVIO = '2'` |
| `detalleventa.dbf` | Items de cada comprobante | — |
| `productox.dbf` | Catalogo productos | — |
| `factura.dbf` | Totales reales | — |
| `notacredito.dbf` | Anulaciones pendientes | `PENDIENTE_ = '2'` + `TIPO_MOVIM = '2'` |
| `motivonota.dbf` | Motivos de anulacion | — |

**Flags de estado que escribe el Motor:**

| Valor | Significado | Quien lo escribe |
|---|---|---|
| `'2'` | Listo para enviar | Sistema del cliente |
| `'3'` | Enviado y confirmado | Motor CPE |
| `'4'` | Error — pendiente reintento | Motor CPE |

> Pendiente verificar si sistema legacy bloquea DBF durante escritura simultanea.

---

## CONTROL DE ENVIOS — todas las fuentes

```
Cualquier fuente (DBF, Excel, SQL, CSV...)
        ↓
Motor verifica en SQLite:
¿Ya existe REMITIDO para este serie+numero+ruc?
    Si → salta (IGNORADO - duplicado)
    No → procesa
        ↓
    Envia al endpoint
        ↓
    Exitoso → REMITIDO en SQLite + intenta marcar en fuente
    Fallido → ERROR en SQLite + intenta marcar en fuente
```

**Marca en fuente por tipo:**

| Fuente | Marca posible | Como |
|---|---|---|
| DBF | Si — si no hay bloqueo | FLAG_ENVIO = '3' o '4' |
| Excel | Si | Columna ESTADO_CPE |
| SQL Server / MySQL / PostgreSQL | Si | UPDATE SET flag='3' |
| CSV | No | Solo SQLite controla |
| Access | Si — si no hay bloqueo | Similar a DBF |

**Reenvio forzado desde UI:**
- Historial → seleccionar comprobante → Reenviar
- Motor ignora SQLite y DBF, fuerza reproceso
- Util para falsos positivos o errores de conexion

---

## DRIVERS DE BASE DE DATOS

| Motor | Driver | Estado en requirements |
|---|---|---|
| SQL Server | pyodbc | Activo — base |
| DBF | dbfread | Activo — base |
| Excel / XLSX | openpyxl | Activo — base |
| CSV | nativo Python | Sin dependencia |
| MySQL / MariaDB | mysql-connector-python | requirements-mysql.txt |
| PostgreSQL | psycopg2-binary | requirements-postgres.txt |
| Access | pyodbc + Access Engine | Requiere instalacion manual |

---

## RESUMEN DE FASES

| Fase | Nombre | Tareas | Prioridad |
|---|---|---|---|
| FASE 1 | Base solida | 5 | Critica |
| FASE 2 | Funcionalidad completa | 5 | Alta |
| FASE 3 | UI/UX | 4 | Media |
| FASE 4 | Infraestructura | 3 | Media |
| FASE 5 | Roadmap futuro | 4 | Baja |

---

## FASE 1 — BASE SOLIDA

> Sin esta fase no hay Motor funcional. Ejecutar en orden.

---

### TASK-001: Migrar DbfFarmaciaAdapter a contrato YAML — farmacias_fas

**OBJETIVO:**
Eliminar DbfFarmaciaAdapter. Convertir su mapeo hardcoded en contrato YAML
completo para farmacias_fas. El cliente sigue funcionando igual.

**CONTEXTO:**
- Existe `src/adapters/dbf_farmacia_adapter.py` con mapeo hardcoded
- Cliente renombrado de farmacia_central a farmacias_fas
- Ruta real del cliente: `C:\sistemas\data`
- GenericAdapter ya soporta DBF via dbfread

**ACCION:**
1. Renombrar todos los archivos y referencias de farmacia_central a farmacias_fas
2. Leer `dbf_farmacia_adapter.py` y extraer todos los campos mapeados
3. Completar `config/contratos/farmacias_fas.yaml` con ese mapeo completo
4. Verificar que GenericAdapter produce el mismo resultado
5. Eliminar `dbf_farmacia_adapter.py`
6. Actualizar `adapter_factory.py` — quitar rama DBF legacy
7. Configurar ruta `C:\sistemas\data` en `config/clientes/farmacias_fas.yaml`

**OUTPUT:**
- `config/contratos/farmacias_fas.yaml` completo y verificado
- `config/clientes/farmacias_fas.yaml` con ruta correcta
- `dbf_farmacia_adapter.py` eliminado
- `adapter_factory.py` sin rama legacy

**ARCHIVOS:**
- `src/adapters/dbf_farmacia_adapter.py` — eliminar
- `src/adapters/adapter_factory.py` — modificar
- `config/contratos/farmacias_fas.yaml` — crear
- `config/clientes/farmacias_fas.yaml` — renombrar y actualizar

**CRITERIO:**
`python main.py --cli farmacias_fas --mock --limit 3` completa sin errores.
Los 3 comprobantes generados tienen los mismos campos que antes.

---

### TASK-001B: Control de envios — anti-duplicado y reenvio

**OBJETIVO:**
Implementar mecanismo de control de envios para todas las fuentes.
SQLite como fuente de verdad. Marca en la fuente cuando sea posible.

**CONTEXTO:**
- Sin este control el Motor puede reenviar duplicados en cada ejecucion
- Aplica a DBF, Excel, SQL, CSV y cualquier fuente futura
- El reenvio forzado desde UI debe ser posible para falsos positivos

**ACCION:**
1. Motor verifica SQLite antes de procesar cada comprobante
2. Si ya existe REMITIDO → salta con IGNORADO (motivo: duplicado)
3. Si envio exitoso → REMITIDO en SQLite + llama write_flag() del adaptador
4. Si envio fallido → ERROR en SQLite + llama write_flag() del adaptador
5. Definir metodo `write_flag(serie, numero, flag)` en BaseAdapter
   — cada adaptador lo implementa si su fuente lo permite
   — si no puede escribir, retorna silenciosamente sin error
6. UI: boton Reenviar en historial — fuerza reproceso ignorando check SQLite
7. Verificar bloqueo de DBF en farmacias_fas antes de implementar write_flag

**OUTPUT:**
- `src/adapters/base_adapter.py` — metodo write_flag()
- `src/adapters/generic_adapter.py` — implementacion write_flag por tipo
- `src/motor.py` — verificacion SQLite antes de procesar
- UI historial con boton Reenviar funcional

**ARCHIVOS:**
- `src/adapters/base_adapter.py` — agregar write_flag()
- `src/adapters/generic_adapter.py` — implementar write_flag
- `src/motor.py` — logica anti-duplicado
- `src/ui/api.py` — metodo reenviar_comprobante()

**CRITERIO:**
Correr Motor dos veces seguidas — segundo ciclo no reenvía nada (IGNORADO).
Desde UI, forzar reenvio de un comprobante REMITIDO — se reenvía correctamente.

---

### TASK-002: Eliminar XlsxAdapter (POS™)

**OBJETIVO:**
Remover XlsxAdapter del proyecto. Excel usa GenericAdapter + contrato YAML.

**ACCION:**
1. Verificar que ningun cliente YAML referencia XlsxAdapter
2. Eliminar `src/adapters/xlsx_adapter.py`
3. Quitar rama xlsx de `adapter_factory.py`
4. Limpiar imports en todo el proyecto

**ARCHIVOS:**
- `src/adapters/xlsx_adapter.py` — eliminar
- `src/adapters/adapter_factory.py` — modificar
- `src/adapters/__init__.py` — limpiar

**CRITERIO:**
`grep -r "xlsx_adapter\|XlsxAdapter" src/` devuelve cero resultados.

---

### TASK-003: Implementar SQLite — inicializacion en arranque

**OBJETIVO:**
Garantizar que SQLite se crea y verifica cada vez que el Motor arranca.

**ACCION:**
1. Crear `src/database/schema.py` con `init_db(db_path)`
2. Definir todas las tablas: log_envios, comprobantes, config
3. Usar `CREATE TABLE IF NOT EXISTS` — idempotente
4. Conectar `cpe_logger.py` para llamar `init_db()` antes de operar
5. Llamar `init_db()` en `main.py` al arranque

**ARCHIVOS:**
- `src/database/schema.py` — crear
- `src/logger/cpe_logger.py` — modificar
- `main.py` — agregar init_db()

**CRITERIO:**
Borrar `disateq.db`, correr Motor. El archivo se crea automaticamente
con todas las tablas correctas.

---

### TASK-004: Migrar UI de Eel a PyWebView

**OBJETIVO:**
Reemplazar Eel por PyWebView. Partir `app.py` de 900 lineas en modulos limpios.

**ACCION:**
1. Instalar pywebview — agregar a `requirements.txt`, quitar eel
2. Crear `src/ui/api.py` — clase DisateQAPI con todos los metodos
3. Crear `src/ui/app.py` limpio — solo arranca PyWebView
4. Actualizar frontend JS — cambiar `eel.funcion()` por `pywebview.api.funcion()`
5. Eliminar `src/ui/backend/app.py`
6. Verificar que las 5 pantallas cargan y responden

**ARCHIVOS:**
- `src/ui/api.py` — crear
- `src/ui/app.py` — crear
- `src/ui/backend/app.py` — eliminar
- `src/ui/frontend/js/*.js` — actualizar llamadas
- `requirements.txt` — actualizar

**CRITERIO:**
`python main.py` abre ventana PyWebView. Las 5 pantallas cargan.
Sin errores en consola.

---

## FASE 2 — FUNCIONALIDAD COMPLETA

---

### TASK-005: Wizard end-to-end — flujo completo 6 pasos

**OBJETIVO:**
Completar el wizard de configuracion de nuevo cliente.
Paso 5 (endpoints) con nueva estructura. Al finalizar genera YAML del cliente.

**CRITERIO:**
Wizard completo crea cliente nuevo. Motor lo procesa sin errores.

---

### TASK-006: Guardar series desde UI al YAML del cliente

**OBJETIVO:**
Series editadas desde UI persisten en YAML. Motor las usa en siguiente proceso.

**CRITERIO:**
Cambiar serie en UI, cerrar y reabrir. La serie nueva esta activa.

---

### TASK-007: Validador de contrato con score de confianza

**OBJETIVO:**
Validar autocontrato generado por smart_mapper.
Score >= 0.80 → automatico. Score < 0.80 → UI muestra campos faltantes.

**ARCHIVOS:**
- `src/tools/contract_validator.py` — crear
- `src/motor.py` — integrar validacion

**CRITERIO:**
Contrato con campos null lanza error claro.
Contrato completo con score >= 0.80 pasa sin intervencion.

---

### TASK-008: Credenciales APIFAS — primer envio real

**OBJETIVO:**
Configurar credenciales reales de APIFAS para farmacias_fas
y ejecutar el primer envio real a produccion.

**CRITERIO:**
CDR con estado ACEPTADO guardado en SQLite.
Credenciales no aparecen en ningun log.

---

### TASK-009: Autocontrato — flujo Caso 2 completo

**OBJETIVO:**
source_explorer + smart_mapper + contract_validator integrados.
Boton Escanear fuente en UI. Flujo completo sin intervencion si score >= 0.80.

**ARCHIVOS:**
- `src/tools/autocontract_service.py` — crear

**CRITERIO:**
Apuntar a carpeta DBF de prueba. Motor genera autocontrato
y procesa 3 comprobantes sin intervencion manual.

---

## FASE 3 — UI / UX

### TASK-010: Corregir colores de pestanas y estilos CSS
**CRITERIO:** Las 5 pestanas muestran colores correctos.

### TASK-011: Tabla Procesar — agregar columna Tipo (B/F)
**CRITERIO:** Columna Tipo visible con valores B o F.

### TASK-012: Dashboard — corregir advertencia stepSize chart.js
**CRITERIO:** Consola sin warnings al cargar el dashboard.

### TASK-013: Fuente label — mostrar ruta real
**CRITERIO:** Ruta del cliente aparece correcta al cargar la UI.

---

## FASE 4 — INFRAESTRUCTURA

---

### TASK-014: Build PyWebView — instalador y requirements por perfil

**OBJETIVO:**
Generar ejecutable .exe con PyWebView usando PyInstaller.
Implementar requirements opcionales por perfil de base de datos.

**ACCION:**
1. Actualizar `build.ps1` para PyWebView + PyInstaller
2. Actualizar `installer.nsi` para v5
3. Crear `requirements-mysql.txt` — mysql-connector-python
4. Crear `requirements-postgres.txt` — psycopg2-binary
5. Documentar como instalar segun perfil del cliente

**CRITERIO:**
.exe generado corre en maquina limpia sin Python instalado.
Perfil MySQL instala solo lo necesario para MySQL.

---

### TASK-015: SQL Server — prueba real con cliente

**OBJETIVO:**
Verificar GenericAdapter con SQL Server real.
Documentar contrato YAML de ejemplo para este tipo de fuente.

**CRITERIO:**
Motor procesa 3 comprobantes desde SQL Server real.

---

### TASK-016: Flujo completo de licenciamiento desde UI

**OBJETIVO:**
Activar, validar y renovar licencia desde la UI.
Sin licencia valida el Motor no procesa.

**CRITERIO:**
Trial 24h funciona. Licencia permanente activa el Motor.

---

## FASE 5 — ROADMAP FUTURO

| Task | Descripcion |
|---|---|
| TASK-017 | Generador XML UBL 2.1 — envio directo SUNAT SEE |
| TASK-018 | DisateQ Platform API — endpoint propio |
| TASK-019 | WhatsApp notifier — alertas de envio |
| TASK-020 | Resumen de Cierre Diario (RC) |

---

## REGLAS DE AVANCE

- No se inicia FASE 2 sin FASE 1 completamente validada
- Cada TASK tiene un unico resultado verificable
- Si una TASK falla → documentar en `docs/manual_vivo.md` y reintentar
- Ningun commit sin pasar checklist ETAPA 6 del FLOW OPS
- Formato commit: `feat|fix|refactor|docs|security: descripcion`

---

*DisateQ™ Motor CPE v5.0 — Plan Etapa 3 — 2026-04-29*
