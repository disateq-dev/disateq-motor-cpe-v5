# Arquitectura de Carpetas — Motor CPE DisateQ™ v3.0

## 🎯 Principio: Separación Programas vs Datos

Siguiendo estándar Windows profesional:
- **Programas** → `C:\Program Files\` (archivos binarios, librerías, inmutables)
- **Datos** → `D:\` (configuración, logs, archivos generados, mutables)

---

## 📁 Estructura en Producción (Cliente)

### C:\Program Files\DisateQ\Motor CPE\
**Contenido:** Programas y archivos inmutables
```
C:\Program Files\DisateQ\Motor CPE\
├── MotorCPE_DisateQ_v3.0.0.exe    # Ejecutable principal
├── disateq_public.pem             # Clave pública RSA
└── disateq_motor.lic              # Licencia del cliente
```

**Permisos:** Solo lectura para usuarios estándar

---

### D:\FFEESUNAT\CPE DisateQ\
**Contenido:** Datos, configuración y archivos generados
```
D:\FFEESUNAT\CPE DisateQ\
├── config\
│   └── motor_config.yaml          # Configuración del Motor
│
├── logs\
│   └── motor_cpe_YYYY-MM-DD.log   # Logs diarios
│
├── output\
│   ├── txt\                       # TXT para APIFAS
│   ├── xml\                       # XML UBL 2.1
│   └── json\                      # JSON (futuro)
│
└── backup\
    └── YYYY-MM-DD\                # Backups automáticos
```

**Permisos:** Lectura/escritura para usuario del Motor

---

## 📁 Estructura en Desarrollo (DisateQ)

### D:\DATA\_DEV_\repos\disateq-cpe-envio\
**Contenido:** Código fuente completo
```
disateq-cpe-envio/
├── main.py                        # Punto de entrada
├── requirements.txt               # Dependencias Python
├── .gitignore                     # Exclusiones Git
├── README.md                      # Documentación principal
│
├── src/                           # Código fuente
│   └── adapters/                  # Adaptadores de fuentes
│       ├── base_adapter.py
│       ├── xlsx_adapter.py
│       ├── dbf_adapter.py
│       ├── sql_adapter.py
│       ├── yaml_mapper.py
│       └── mappings/              # YAML configs por cliente
│
├── licenses/                      # Sistema de licencias
│   ├── validador_licencias.py
│   ├── generar_claves_disateq.py
│   ├── crear_licencia_cliente.py
│   ├── test_licencias.py
│   ├── README.md
│   ├── keys/                      # Claves RSA DisateQ
│   │   ├── disateq_private.pem   # ⚠️ NUNCA COMPARTIR
│   │   └── disateq_public.pem
│   └── client_licenses/           # Licencias generadas
│       └── *.lic
│
├── config/                        # Configs de ejemplo
│   └── motor_config.yaml
│
├── docs/                          # Documentación
│   ├── README.md
│   ├── README_LICENCIAS.md
│   ├── ESTADO.md
│   └── ...
│
├── tests/                         # Tests unitarios
│   └── test_*.py
│
├── tools/                         # Herramientas auxiliares
│   └── source_explorer.py
│
├── logs/                          # Logs de desarrollo
├── output/                        # Salidas de prueba
├── backup/                        # Backups de prueba
│
└── dist/                          # ⭐ PRODUCTOS FINALES
    ├── README.md
    ├── windows/                   # Ejecutables compilados
    │   └── MotorCPE_DisateQ_v3.0.0.exe
    └── installers/                # Paquetes para clientes
        └── MotorCPE_v3.0.0_Instalador_2026-04-20.zip
```

---

## 🔄 Flujo de Archivos

### Desarrollo → Distribución → Producción

```
1. DESARROLLO
   D:\DATA\_DEV_\repos\disateq-cpe-envio\
   ├── Código Python (.py)
   ├── Tests
   └── Documentación

   ↓ Compilar (PyInstaller)

2. DISTRIBUCIÓN
   disateq-cpe-envio\dist\installers\
   └── MotorCPE_v3.0.0_Instalador.zip
       ├── INSTALAR.bat
       ├── MotorCPE_DisateQ_v3.0.0.exe
       ├── disateq_public.pem
       └── carpetas vacías (config, logs, output, backup)

   ↓ Enviar al cliente

3. PRODUCCIÓN (Cliente)
   C:\Program Files\DisateQ\Motor CPE\     ← Programas
   D:\FFEESUNAT\CPE DisateQ\               ← Datos
```

---

## 🔐 Seguridad y Git

### ✅ Incluir en Git:
- Código fuente (.py)
- Documentación (.md)
- Configuraciones de ejemplo
- Tests
- Scripts de compilación
- Clave pública (disateq_public.pem)

### ❌ EXCLUIR de Git (.gitignore):
- Clave privada (disateq_private.pem) ← **CRÍTICO**
- Licencias de clientes (*.lic)
- Ejecutables compilados (dist/)
- Logs (logs/)
- Datos de prueba (output/, backup/)
- Cache Python (__pycache__)

---

## 📝 Auto-detección de Rutas

El Motor detecta automáticamente su entorno:

**Producción** (instalado):
```python
# Busca en C:\Program Files\DisateQ\Motor CPE\
# Configuración en D:\FFEESUNAT\CPE DisateQ\config\
```

**Desarrollo** (repositorio):
```python
# Busca relativo al script
# Estructura src/, licenses/, config/
```

---

## 🛠️ Scripts de Organización

### organizar_motor_cpe.ps1
- Crea estructura completa en repositorio
- Mueve archivos a carpetas correctas
- Genera .gitignore y READMEs

### compilar_producto_final.ps1
- Compila .exe con PyInstaller
- Crea instalador ZIP
- Separa archivos para C: y D:

---

## 📞 Contacto

**DisateQ™**
- Repositorio: D:\DATA\_DEV_\repos\disateq-cpe-envio (privado)
- Email: soporte@disateq.com

---

© 2026 DisateQ™ | Motor CPE v3.0
