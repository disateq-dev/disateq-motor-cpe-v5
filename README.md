# DisateQ™ Motor CPE v5.0

**Generador y enrutador universal de comprobantes electrónicos con soporte multi-endpoint para PSE/OSE, SEE-Contribuyente, y plataforma propia futura.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-4.0.0-green.svg)](CHANGELOG.md)

---

## 🎯 Descripción

Motor CPE DisateQ™ v5.0 es un sistema profesional para generación y envío de Comprobantes de Pago Electrónicos (CPE) a SUNAT (Perú).

**Características principales:**
- 🔌 **Multi-endpoint**: Envío a PSE/OSE, SEE-Contribuyente, DisateQ Platform
- 📊 **Multi-fuente**: Excel, DBF (FoxPro), SQL Server, PostgreSQL, MySQL
- 🔄 **Formatos múltiples**: JSON (estándar), TXT (legacy), XML UBL 2.1 (futuro)
- 🎨 **UI moderna**: Interfaz Eel (Python + HTML/CSS/JS)
- 🗄️ **Offline-first**: SQLite, funciona sin internet
- 🔐 **Licenciamiento RSA-2048**: Trial 24h + licencias permanentes

---

## 🚀 Inicio Rápido

### **Instalación**

```powershell
# Clonar repositorio
git clone git@github.com:fhertejadaDEV/disateq-motor-cpe-v4.git
cd disateq-motor-cpe-v4

# Instalar dependencias
pip install -r requirements.txt

# Iniciar aplicación
python -m src.ui.backend.app
```

### **Uso Básico**

```python
from src.adapters.xlsx_adapter import XlsxAdapter
from src.generators.json_generator import JsonGenerator
from src.sender.universal_sender import UniversalSender

# 1. Leer desde Excel
adapter = XlsxAdapter('ventas.xlsx')
adapter.connect()

# 2. Procesar comprobantes
comprobantes = adapter.read_pending()
for comp in comprobantes:
    items = adapter.read_items(comp)
    cpe = adapter.normalize(comp, items)
    
    # 3. Generar JSON
    json_file = JsonGenerator.generate(cpe, 'output/json')
    
    # 4. Enviar a endpoint
    sender = UniversalSender(config_path='config/endpoints.yaml')
    exito, respuesta = sender.enviar(json_file, cpe)
    
    print(f"CPE {cpe['serie']}-{cpe['numero']}: {'✅' if exito else '❌'}")
```

---

## 📋 Requisitos

**Sistema:**
- Windows 10/11 o Server 2016+
- 500 MB espacio en disco
- .NET Framework 4.8+

**Python:**
- Python 3.11+
- Ver `requirements.txt` para dependencias

**Opcional:**
- Access Database Engine (para .mdb/.accdb)
- ODBC Driver 17 (para SQL Server)

---

## 🏗️ Arquitectura

```
Usuario → Fuente Datos → Motor CPE → Endpoint → SUNAT
          (Excel/DBF)    (Normaliza)  (APIFAS)
                         ↓
                      JSON/TXT
```

**Componentes:**

1. **Adapters**: Leen datos desde múltiples fuentes
2. **Generators**: Generan archivos TXT/JSON/XML
3. **Sender**: Envía a endpoints configurables
4. **Database**: Persistencia SQLite offline
5. **UI**: Interfaz Eel (Python ↔ HTML/JS)

Ver [ARQUITECTURA.md](docs/ARQUITECTURA.md) para detalles.

---

## 🔌 Endpoints Soportados

| Endpoint | Tipo | Formato | Estado |
|----------|------|---------|--------|
| APIFAS PSE/OSE | Tercero | TXT/JSON | ✅ Activo |
| APIFAS SEE | SUNAT Directo | JSON | ✅ Activo |
| Nubefact | Tercero | JSON | ✅ Disponible |
| DisateQ Platform | Propio | JSON | 🔄 Desarrollo |

---

## 📊 Fuentes de Datos Soportadas

| Fuente | Extensión | Estado | Notas |
|--------|-----------|--------|-------|
| Excel | `.xlsx`, `.xls` | ✅ Funcional | Contrato POS™ v1.2 |
| FoxPro | `.dbf` | ✅ Funcional | Farmacia (hardcoded) |
| SQL Server | Conexión | ⏳ Futuro | v4.1 |
| PostgreSQL | Conexión | ⏳ Futuro | v4.1 |
| MySQL | Conexión | ⏳ Futuro | v4.1 |
| Access | `.mdb`, `.accdb` | ⏳ Futuro | v4.1 |
| CSV | `.csv` | ⏳ Futuro | v4.1 |
| JSON | `.json` | ⏳ Futuro | v4.2 |

---

## 📚 Documentación

- [Arquitectura](docs/ARQUITECTURA.md)
- [Instalación](docs/INSTALACION.md)
- [API Reference](docs/API.md)
- [Ejemplos](docs/EJEMPLOS.md)
- [Guía Técnica](docs/GUIA_TECNICA.md)
- [Roadmap Autocontrato](docs/ROADMAP_AUTOCONTRATO.md)

---

## 🧪 Testing

```bash
# Ejecutar tests
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=src --cov-report=html

# Test específico
pytest tests/test_adapters.py::test_xlsx_adapter -v
```

---

## 🗺️ Roadmap

### **v5.0 (Actual)** ✅
- [x] Adaptadores Excel y DBF
- [x] Generadores JSON y TXT
- [x] UniversalSender multi-endpoint
- [x] Sistema licencias RSA-2048
- [x] Configuración YAML

### **v4.1 (Q2 2026)** 🔄
- [ ] UI Eel completa
- [ ] Sistema Autocontrato Universal
- [ ] Scanners multi-fuente
- [ ] SqlAdapter universal
- [ ] Base de datos SQLite

### **v4.2 (Q3 2026)** 📝
- [ ] Generador XML UBL 2.1
- [ ] Envío directo SUNAT SEE
- [ ] DisateQ Platform
- [ ] Portal web licencias

---

## 📄 Licencia

**Propietario** — DisateQ™ / @fhertejadaDEV

Todos los derechos reservados. Este software es propiedad de DisateQ™ y no puede ser distribuido, modificado o utilizado sin autorización expresa.

---

## 👨‍💻 Autor

**Fernando Hernán Tejada Quevedo**  
[@fhertejadaDEV](https://github.com/fhertejadaDEV) | DisateQ™

**Contacto:**
- Email: soporte@disateq.com
- GitHub: [fhertejadaDEV](https://github.com/fhertejadaDEV)

---

## 🆘 Soporte

- **Issues**: [GitHub Issues](https://github.com/fhertejadaDEV/disateq-motor-cpe-v4/issues)
- **Documentación**: [docs/](docs/)
- **Email**: soporte@disateq.com

---

## 🙏 Agradecimientos

Desarrollado con ❤️ en Perú para la transformación digital de PYMEs.

---

**DisateQ™** — Soluciones empresariales para facturación electrónica.
# Test
