# ANALISIS — DisateQ Motor CPE v5.0
**Etapa 2 — DISATEQ FLOW OPS**
**Fecha:** 2026-04-29
**Arquitecto:** Claude (chat)
**Revisión pendiente:** Fernando Hernán Tejada — DisateQ DEV

---

## 1. DESCRIPCION DEL SISTEMA

Motor generador y enrutador universal de Comprobantes de Pago Electrónicos (CPE)
para SUNAT Perú. Lee datos desde sistemas legacy o modernos de cualquier cliente,
genera archivos TXT/JSON y los envía a servicios de validación tercerizados (OSE/PSE/SEE).

### Dos casos de uso principales

**Caso 1 — Contrato manual (cliente con programador)**
El programador conoce su sistema. Completa un contrato YAML indicando exactamente
dónde están los datos. El Motor lo lee y procesa sin intervención adicional.

**Caso 2 — Contrato auto-generado (cliente sin programador)**
El Motor escanea la carpeta del sistema legacy con source_explorer + smart_mapper (IA).
Genera un contrato YAML borrador con score de confianza.
Si confianza >= 0.80 → procede automático.
Si confianza < 0.80 → UI muestra solo los campos faltantes al tecnico.

---

## 2. QUE FUNCIONA HOY (conservar intacto)

| Componente | Estado | Notas |
|---|---|---|
| `GenericAdapter` | Funcional | DBF, SQL Server, MySQL, PostgreSQL, XLSX, CSV |
| `XlsxAdapter` | Funcional | Contrato POS v1.2 (29 campos) |
| `TxtGenerator` | Funcional | Probado con datos farmacia real |
| `AnulacionGenerator` | Funcional | Comunicaciones de baja |
| `UniversalSender` | Funcional | Multi-endpoint, TXT y JSON |
| `ClientLoader` | Funcional | Carga YAML de clientes |
| `CpeLogger` | Funcional | SQLite, estados completos |
| `source_explorer` | Funcional | Escaneo de fuentes |
| `smart_mapper` | Parcial | Genera contrato borrador con IA |
| Logica SUNAT | Funcional | Campos TXT, afectaciones IGV, UNSPSC |
| Sistema licencias RSA | Funcional | Trial 24h + licencias permanentes |

---

## 3. QUE ESTA MAL (cambiar con criterio)

### 3.1 Capa UI — Eel → PyWebView
**Decision tomada:** Migrar de Eel a PyWebView.
- Eel sin mantenimiento activo desde 2022
- Requiere Chrome instalado (dependencia externa)
- PyInstaller problemático con Eel
- PyWebView usa WebView2 nativo de Windows 10/11
- app.py tiene 898 lineas — necesita partirse en módulos

### 3.2 Motor no conecta bien con AdapterFactory
- `motor.py` llama a `get_adapter(config)` pero `adapter_factory.py`
  buscaba `contrato_path` solo bajo `adaptador`, no bajo `fuente`.
- Resultado: caia al DbfFarmaciaAdapter hardcoded en vez de GenericAdapter.

### 3.3 Inconsistencias de versión en docs
- ESTADO.md decia v3.0, GUIA_TECNICA.md decia v3.0 — ya corregido a v5.0.
- Arquitectura documentada en ARQUITECTURA_CARPETAS.md no coincide
  con la estructura real del repo.

### 3.4 main.py era un stub
- Solo imprimia un mensaje — ya corregido, ahora es funcional.

### 3.5 DbfFarmaciaAdapter hardcoded
- `dbf_farmacia_adapter.py` tiene logica especifica para un solo cliente.
- Debe quedar como legacy/fallback con DeprecationWarning.
- Todos los clientes nuevos deben usar GenericAdapter + contrato YAML.

### 3.6 SQLite no implementada operativamente
- Schema diseñado pero la base de datos no se inicializa en el arranque.
- CpeLogger existe pero no garantiza que la DB esté creada.

---

## 4. ARQUITECTURA OBJETIVO v5.0

### Capas del sistema

```
[UI PyWebView]          ← ventana nativa Windows, HTML/CSS/JS
      ↓ API Bridge (clase Python expuesta)
[API Layer]             ← metodos Python que responden al frontend
      ↓
[Motor / Orquestador]   ← flujo completo por cliente
      ↓
[AdapterFactory]        ← detecta tipo de fuente, instancia adaptador
      ↓
[GenericAdapter]        ← lee cualquier fuente via contrato YAML
[XlsxAdapter]          ← fuente DisateQ POS™ (contrato fijo v1.2)
[DbfFarmaciaAdapter]   ← legacy, solo si no hay contrato YAML
      ↓
[Generators]            ← TxtGenerator / JsonGenerator / AnulacionGenerator
      ↓
[UniversalSender]       ← envia a APIFAS, Nubefact, DisateQ Platform
      ↓
[CpeLogger + SQLite]    ← persistencia offline, historial completo
```

### Estructura de carpetas objetivo

```
disateq-motor-cpe-v5/
├── main.py                          # entry point (CLI + UI)
├── requirements.txt
├── pyproject.toml
│
├── src/
│   ├── adapters/
│   │   ├── base_adapter.py
│   │   ├── adapter_factory.py       # detecta contrato_path → GenericAdapter
│   │   ├── generic_adapter.py       # adaptador universal (CONSERVAR)
│   │   ├── xlsx_adapter.py          # DisateQ POS™ (CONSERVAR)
│   │   └── dbf_farmacia_adapter.py  # legacy fallback
│   │
│   ├── generators/
│   │   ├── txt_generator.py         # CONSERVAR
│   │   ├── json_generator.py        # CONSERVAR
│   │   └── anulacion_generator.py   # CONSERVAR
│   │
│   ├── sender/
│   │   └── universal_sender.py      # CONSERVAR
│   │
│   ├── config/
│   │   └── client_loader.py         # CONSERVAR
│   │
│   ├── database/
│   │   ├── schema.py                # crear/verificar tablas SQLite
│   │   └── cpe_logger.py            # CONSERVAR + conectar a schema
│   │
│   ├── licenses/
│   │   └── validator.py             # CONSERVAR
│   │
│   ├── tools/
│   │   ├── source_explorer.py       # CONSERVAR
│   │   └── smart_mapper.py          # CONSERVAR + validador confianza
│   │
│   ├── motor.py                     # CONSERVAR + ajustar imports
│   ├── scheduler.py                 # CONSERVAR
│   │
│   └── ui/
│       ├── api.py                   # NUEVO — clase API expuesta a PyWebView
│       ├── app.py                   # NUEVO — arranque PyWebView (reemplaza Eel)
│       └── frontend/                # HTML/CSS/JS (CONSERVAR estructura)
│           ├── index.html
│           ├── wizard.html
│           ├── css/
│           └── js/
│
├── config/
│   ├── clientes/                    # YAML por cliente
│   └── contratos/                   # YAML de mapeo por cliente
│
├── docs/                            # actualizar con arquitectura real
├── tests/
└── tools/
```

### Separacion de responsabilidades en UI

```python
# ui/app.py — solo arranca PyWebView
import webview
from src.ui.api import DisateQAPI

def start_app():
    api = DisateQAPI()
    window = webview.create_window(
        'DisateQ Motor CPE v5',
        'src/ui/frontend/index.html',
        js_api=api,
        width=1200, height=800
    )
    webview.start()

# ui/api.py — metodos expuestos al frontend (antes era app.py monolitico)
class DisateQAPI:
    def get_empresa_info(self): ...
    def get_dashboard_stats(self): ...
    def procesar_comprobantes(self, alias, limit=None): ...
    def guardar_config_series(self, alias, series): ...
    def explorar_fuente(self, ruta): ...
    # etc.
```

---

## 5. FLUJO DE CONTRATO (Caso 1 y Caso 2 unificados)

```
Nuevo cliente
      ↓
¿Tiene contrato_path en YAML cliente?
      Sí → GenericAdapter(contrato_path) → Motor
      No  → source_explorer(ruta_sistema)
              → smart_mapper (IA)
              → validar_contrato()
                    ↓
              score >= 0.80?
                Sí → guardar contrato → GenericAdapter → Motor
                No → UI muestra solo campos faltantes
                          → tecnico completa
                          → guardar contrato → GenericAdapter → Motor
```

---

## 6. PENDIENTES PRIORIZADOS

### FASE 1 — Base solida (antes de cualquier feature)
1. Corregir `adapter_factory.py` — detectar `contrato_path` bajo `fuente`
2. Inicializar SQLite en arranque — `database/schema.py`
3. Migrar UI de Eel a PyWebView — `ui/app.py` + `ui/api.py`
4. Partir `app.py` monolitico en modulos de la clase API

### FASE 2 — Completar funcionalidad critica
5. Wizard end-to-end — Paso 5 endpoints con nueva estructura
6. Guardar series desde UI al YAML del cliente
7. Credenciales APIFAS — primer envio real a produccion
8. Validador de contrato con score de confianza (Caso 2)

### FASE 3 — UI/UX
9. Colores de pestanas — corregir CSS
10. Tabla Procesar — agregar columna Tipo (B/F)
11. Dashboard — corregir advertencia stepSize chart.js
12. `_setFuenteLabel` — mostrar ruta real, no "Cargando..."

### FASE 4 — Infraestructura
13. Instaladores v5 — build.ps1 actualizado con PyWebView
14. SQL Server — prueba real con cliente
15. Flujo completo de licenciamiento desde UI

### FASE 5 — Roadmap futuro
16. Generador XML UBL 2.1
17. DisateQ Platform API propia
18. WhatsApp notifier
19. Resumen de Cierre Diario (RC)

---

## 7. DECISIONES DE ARQUITECTURA REGISTRADAS

| Decision | Razon |
|---|---|
| PyWebView en lugar de Eel | Nativo Windows 10/11, sin Chrome, mejor empaquetado |
| GenericAdapter como unico adaptador | Un solo codigo para DBF/SQL/XLSX/CSV via contrato YAML |
| DbfFarmaciaAdapter como legacy | No romper clientes existentes, deprecar gradualmente |
| Score de confianza 0.80 para Caso 2 | Equilibrio entre automatismo y precision |
| Contrato YAML como contrato de datos | Programador o IA lo generan, Motor lo consume igual |

---

## 8. RETROALIMENTACION PARA DISATEQ FLOW OPS + ECOSYSTEM

### FLOW OPS v1:
- Etapa 4 define estructura de capas para FastAPI/web.
  Agregar variante **"Estructura de capas — Motor de escritorio (PyWebView)"**
  con separacion: `motor.py` / `ui/api.py` / `adapters/` / `generators/` / `sender/`

### ECOSYSTEM v1:
- Reemplazar **Eel** por **PyWebView** en el stack de herramientas.
  Nota: *"WebView2 nativo de Windows 10/11 — sin dependencia de Chrome.
  Empaquetado limpio con PyInstaller."*
- `disateq-init.ps1` aun no existe — agregar en ECOSYSTEM como pendiente
  de crear antes del siguiente proyecto piloto.

---

**Pendiente de revision y GO por Fernando Hernán Tejada — DisateQ DEV**

---
*DisateQ™ Motor CPE v5.0 — Análisis Etapa 2 — 2026-04-29*
