# CONTEXTO MAESTRO — DisateQ Motor CPE v5.5
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
Etapa actual: EJECUCION — TASK-009
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
TxtGenerator / AnulacionGenerator → archivo .txt
        ↓
UniversalSender — envia a endpoints activos
    APIFAS (sin credenciales, endpoint directo) ✓
        ↓
Respuesta SUNAT — CDR
        ↓
CpeLogger — registra estado en SQLite
write_flag() — marca en fuente (pendiente python-dbf)
```

---

## 3. DOS CASOS DE USO

**Caso 1 — Cliente con programador**
Programador llena contrato YAML. Motor lo lee y procesa.

**Caso 2 — Cliente sin programador**
source_explorer + smart_mapper (IA) genera contrato YAML.
Score >= 0.80 → procede automatico.
Score < 0.80  → UI muestra campos faltantes al tecnico.

---

## 4. DECISIONES DE ARQUITECTURA VIGENTES

| Decision | Detalle |
|---|---|
| PyWebView reemplaza Eel | WebView2 nativo Windows 10/11 |
| GenericAdapter unico | DBF, Excel, SQL, CSV via contrato YAML |
| Encoding DBF | cp850 (no latin-1) — confirmado con datos reales |
| NUMERO_FAC normalizado | _norm_num() strip leading zeros en todos los caches |
| TxtGenerator v5 | Estructura CPE plana, TIPO_IGV_MAP, campos correctos |
| AnulacionGenerator v5 | Estructura CPE plana, motivo_baja, fecha_anulacion |
| APIFAS sin credenciales | Endpoints directos funcionan sin usuario/token |
| Velocidad envio | ~620ms/comprobante — aceptable para lotes diarios |
| SQLite fuente de verdad | cliente_id = file stem (no empresa.alias) |
| SafeFieldParser completo | parseD + parseN + parseF |
| sort_keys=False en YAML | Preserva orden, filtra series vacias |
| flag_lectura anidado | GenericAdapter espera estructura anidada |
| write_flag DBF | dbfread read-only — pendiente python-dbf |

---

## 5. CLIENTE ACTIVO — farmacia_central

**YAML cliente:** config/clientes/farmacia_central.yaml
**YAML contrato:** config/contratos/farmacia_central.yaml
**Ruta datos PROD:** D:\FFEESUNAT\Test
**Tipo fuente:** DBF (FoxPro) | **Encoding:** cp850

**Campos DBF confirmados con datos reales:**

| Tabla | Campos clave | Nota |
|---|---|---|
| enviosffee | TIPO_FACTU, SERIE_FACT, NUMERO_FAC, FLAG_ENVIO=2 | pendientes |
| factura | TIPO_FACTU, SERIE_FACT, NUMERO_FAC, REAL_FACTU, MONTO_FACT | totales |
| detalleventa | TIPO_FACTU, SERIE_FACT, NUMERO_FAC, CANTIDAD_P, MONTO_PEDI | items |
| productox | CODIGO_PRO, DESCRIPCIO, PRESENTA_P, CODIGO_UNS | catalogo |
| notacredito | PENDIENTE_='2', TIPO_MOVIM=2 | anulaciones |
| motivonota | CODIGO, MOTIVO | motivos |

**NUMERO_FAC — mismatch resuelto:**
- enviosffee: `'00016377'` (8 chars)
- factura/detalleventa: `'0000016377'` (10 chars)
- Solucion: `_norm_num()` strip leading zeros en todos los caches

**Resultado prueba real 2026-05-02:**
- 10/10 comprobantes enviados a APIFAS ✓
- ~620ms por comprobante
- TXT con totales, items, encoding correcto

---

## 6. ESTRUCTURA DEL PROYECTO

```
disateq-motor-cpe-v5/
├── src/
│   ├── adapters/
│   │   └── generic_adapter.py     — cp850, _norm_num, SafeFieldParser ✓
│   ├── generators/
│   │   ├── txt_generator.py       — CPE plano v5, TIPO_IGV_MAP ✓
│   │   └── anulacion_generator.py — CPE plano v5 ✓
│   ├── sender/
│   │   └── universal_sender.py    — sin credenciales OK ✓
│   ├── config/
│   │   └── client_loader.py       — robusto v5 ✓
│   ├── tools/
│   │   ├── wizard_mapper.py       — heuristica DBF→CPE ✓
│   │   ├── wizard_service.py      — flag_lectura anidado ✓
│   │   ├── contract_validator.py  — TASK-007 score=1.0 ✓
│   │   └── autocontract_service.py — TASK-009 pendiente
│   ├── motor.py                   — alias = file stem ✓
│   └── ui/
│       ├── api.py                 — _cliente_stem, validar_contrato ✓
│       └── frontend/
│           ├── index.html         — TASK-013 ruta real ✓
│           ├── css/
│           │   └── layout.css     — FIX-UI-01/02/03 ✓
│           └── js/
│               ├── app.js
│               ├── dashboard.js   — actualizarStatPendientes ✓
│               ├── processor.js   — TASK-011 Tipo B/F, TASK-013 ✓
│               └── wizard.js
├── config/
│   ├── clientes/farmacia_central.yaml
│   └── contratos/farmacia_central.yaml
└── docs/
    └── CONTEXTO_MAESTRO_MOTOR_CPE_v5_5.md
```

---

## 7. ENTORNO DE DESARROLLO

| Item | Valor |
|---|---|
| OS | Windows 10/11 |
| Python | 3.14 |
| Ruta proyecto | D:\DisateQ\Proyectos\disateq-motor-cpe-v5 |
| Ruta descargas | D:\DATA\Downloads |
| Ruta datos test | D:\FFEESUNAT\Test |
| Encoding DBF | cp850 |
| APIFAS prod | https://apifas.disateq.com/produccion_text.php |
| APIFAS anul | https://apifas.disateq.com/anulacion_text.php |

**Deploy estandar:**
```powershell
Copy-Item D:\DATA\Downloads\archivo destino -Force
git add ... && git commit -m "..."
python main.py
```
**1-2 archivos → comandos directos. 3+ → .ps1**
**NUNCA parches — siempre reescritura completa.**

---

## 8. PLAN DE TRABAJO — ESTADO ACTUAL

### FASE 1 — COMPLETA ✅
TASK-001 al TASK-004 — base solida, SQLite, PyWebView.

### FASE 2 — EN CURSO

| Task | Descripcion | Estado |
|---|---|---|
| TASK-005 | Wizard 6 pasos | ✅ |
| TASK-006 | Series YAML + historial/logs | ✅ |
| TASK-007 | contract_validator score=1.0 | ✅ |
| TASK-008 | Envio real APIFAS 10/10 ✓ | ✅ |
| TASK-009 | Autocontrato IA (smart_mapper) | PROXIMA |

### FASE 3 — UI/UX

| Task | Descripcion | Estado |
|---|---|---|
| TASK-010 | Colores pestanas CSS | PENDIENTE |
| TASK-011 | Columna Tipo B/F en Procesar | ✅ |
| TASK-012 | stepSize chart.js | PENDIENTE |
| TASK-013 | Fuente label ruta real | ✅ |

### FASE 4 — INFRAESTRUCTURA

| Task | Descripcion | Estado |
|---|---|---|
| TASK-014 | Build PyWebView + installer | PENDIENTE |
| TASK-015 | SQL Server prueba real | PENDIENTE |
| TASK-016 | Licenciamiento desde UI | PENDIENTE |

### FIXES PENDIENTES

| Fix | Descripcion |
|---|---|
| FIX-WIZ-01 | Wizard contrato Excel descargable/subible |

---

## 9. NOTAS TECNICAS CRITICAS

**Encoding:**
```python
# CORRECTO — cp850 para DBF FoxPro peruanos
encoding: cp850
# MAL — latin-1 causa PA¥AL en lugar de PAÑAL
```

**_norm_num — normalizar NUMERO_FAC:**
```python
def _norm_num(numero: str) -> str:
    return numero.lstrip('0') or '0'
# Usar en: _load_factura_cache, _load_items_cache, _read_items_dbf, _get_factura
```

**TxtGenerator — TIPO_IGV_MAP:**
```python
TIPO_IGV_MAP = {1: '10', 2: '20', 3: '30', 4: '40'}
# tipo_igv int del CPE → codigo SUNAT afectacion
```

**cliente_id:**
```python
cliente_id = getattr(self, '_cliente_stem', None)  # 'farmacia_central'
# NO: self._client_config.alias  → 'LOCAL PRINCIPAL' no matchea SQLite
```

**Contrato YAML flag_lectura:**
```yaml
comprobantes:
  flag_lectura:
    campo: FLAG_ENVIO
    valor: 2
  flag_escritura:
    campo: FLAG_ENVIO
    enviado: 3
    error: 4
```

**APIFAS — envio sin credenciales:**
```python
# UniversalSender omite usuario/token si estan vacios
# Endpoint responde 200 directamente con el TXT
```

**PyWebView JS:**
```javascript
window.pywebview.api.metodo(params).then(callback)
```

---

*DisateQ™ Motor CPE v5.0 — Contexto Maestro v5.5 — 2026-05-02*
*Envio real APIFAS 10/10 exitosos — TXT correcto — Historial/Logs funcionando*
*Continuar en TASK-009 — Autocontrato IA (smart_mapper completo)*
