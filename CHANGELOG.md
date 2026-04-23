# Changelog

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [4.0.0] - 2026-04-23

### 🎉 Lanzamiento Inicial v4.0

Primera versión pública del Motor CPE DisateQ™ v4.0.

### ✅ Agregado

**Core:**
- Sistema de adaptadores universales para múltiples fuentes de datos
- `XlsxAdapter`: Soporte completo para Excel con contrato POS™ v1.2
- `DbfAdapter`: Soporte para archivos FoxPro (farmacia)
- `JsonGenerator`: Generador de JSON estándar DisateQ
- `TxtGenerator`: Generador TXT formato APIFAS legacy
- `UniversalSender`: Sistema de envío multi-endpoint

**Endpoints:**
- APIFAS PSE/OSE (TXT multipart)
- APIFAS SEE-Contribuyente (JSON + credenciales SUNAT)
- Nubefact (JSON)
- Mock local para pruebas

**Licenciamiento:**
- Sistema RSA-2048 offline
- Trial 24 horas con límite de 10 documentos
- Licencias permanentes con validación local

**Configuración:**
- `motor_config.yaml`: Configuración general del motor
- `endpoints.yaml`: Configuración multi-endpoint
- Soporte para múltiples ambientes (producción/homologación)

**Documentación:**
- Arquitectura completa del sistema
- Guía de instalación paso a paso
- API Reference con ejemplos
- Roadmap de autocontrato universal
- Diseño UI Eel

### 🔧 Técnico

**Stack:**
- Python 3.11
- Eel 0.16.0 (preparado para UI)
- SQLite 3.40+ (schema diseñado)
- SQLAlchemy 2.0 (preparado)

**Dependencias:**
- openpyxl: Lectura/escritura Excel
- dbfread: Lectura DBF FoxPro
- PyYAML: Configuración YAML
- requests: HTTP para envío
- cryptography: RSA para licencias

**Estructura:**
- Código modular y escalable
- Separación clara backend/frontend
- Preparado para empaquetado PyInstaller

### 📋 Contrato de Datos

**DisateQ POS™ v1.2:**
- 29 campos estandarizados
- Worksheet `_CPE`
- Soporte para:
  - Cabecera (5 campos)
  - Cliente (4 campos)
  - Items (11 campos)
  - Totales (6 campos)
  - Pago (2 campos)
  - Estado (1 campo)

### ⚠️ Conocido

**Limitaciones actuales:**
- DbfAdapter solo funciona con estructura de farmacia (hardcoded)
- UI Eel no implementada (solo diseño)
- Base de datos SQLite no implementada (solo schema)
- SqlAdapter no implementado
- Sistema autocontrato no implementado

**Por implementar (v4.1):**
- UI Eel completa
- Base de datos persistente
- Sistema autocontrato universal
- Scanners multi-fuente
- FieldMappers inteligentes

### 🔒 Seguridad

- Licencias firmadas digitalmente (RSA-2048)
- Credenciales en YAML (pendiente: encriptación DPAPI)
- Validación offline sin internet

---

## [Unreleased]

### 🔄 En Desarrollo

**v4.1 (Próximo):**
- [ ] Interfaz Eel completa
- [ ] Base de datos SQLite operativa
- [ ] Dashboard en tiempo real
- [ ] Gestión visual de comprobantes
- [ ] Sistema de logs integrado
- [ ] Configuración visual (sin editar YAML)

**v4.2 (Futuro):**
- [ ] Sistema autocontrato universal
- [ ] Scanners para Access, CSV, JSON
- [ ] FieldMappers inteligentes con IA
- [ ] Wizard interactivo
- [ ] SqlAdapter universal

**v4.3 (Futuro):**
- [ ] Generador XML UBL 2.1
- [ ] Firma digital con certificado
- [ ] Envío directo SUNAT SEE
- [ ] DisateQ Platform API

---

## Tipos de Cambios

- `Agregado`: Nuevas características
- `Cambiado`: Cambios en funcionalidad existente
- `Obsoleto`: Características que serán removidas
- `Removido`: Características removidas
- `Arreglado`: Corrección de bugs
- `Seguridad`: Vulnerabilidades corregidas

---

**Autor:** Fernando Hernán Tejada Quevedo (@fhertejadaDEV)  
**Proyecto:** DisateQ™ Motor CPE v4.0  
**Licencia:** Propietario
