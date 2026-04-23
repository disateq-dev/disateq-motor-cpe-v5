# Sistema de Licencias Offline RSA — Motor CPE DisateQ™ v3.0

Sistema de validación de licencias sin conexión a internet usando cifrado RSA-2048.

---

## 📦 Archivos del Sistema

### Archivos Core
- `validador_licencias.py` — Módulo principal (validator + generator)
- `main.py` — Motor CPE con validación integrada

### Scripts de Uso
- `generar_claves_disateq.py` — Generar par de claves RSA (una sola vez)
- `crear_licencia_cliente.py` — Crear licencias para clientes
- `test_licencias.py` — Tests del sistema completo

### Archivos de Licencia
- `disateq_private.pem` — Clave privada DisateQ (MANTENER SEGURA)
- `disateq_public.pem` — Clave pública (distribuir con Motor)
- `disateq_motor.lic` — Archivo de licencia firmado (cliente)

---

## 🚀 Uso DisateQ™ (Interno)

### 1. Primera vez: Generar claves maestras

```bash
python generar_claves_disateq.py
```

**Resultado:**
- `disateq_private.pem` → Guardar en lugar SEGURO DisateQ
- `disateq_public.pem` → Distribuir con cada instalación del Motor

⚠️ **Solo hacer UNA VEZ. Backup de ambas claves.**

### 2. Crear licencia para cliente

```bash
python crear_licencia_cliente.py
```

**Interactivo:**
```
Nombre cliente: Distribuidora ABC S.A.C.
RUC cliente: 20123456789
Días de validez: 365
Máx documentos/mes: 5000
```

**Resultado:**
- `disateq_motor.lic` → Enviar al cliente

### 3. Entregar al cliente

**Archivos a entregar:**
1. Motor CPE v3.0 (.exe o instalador)
2. `disateq_motor.lic` (licencia firmada)
3. `disateq_public.pem` (clave pública)

**Ubicación:** Los 3 archivos deben estar en el mismo directorio.

---

## 💻 Uso Cliente

### Validar licencia actual

```bash
python validador_licencias.py validate
```

**Salida ejemplo:**
```
============================================================
VALIDACIÓN DE LICENCIA
============================================================
✅ Licencia válida (312 días restantes)

Cliente: Distribuidora ABC S.A.C.
RUC: 20123456789
Vencimiento: 2027-04-20
Máx docs/mes: 5000
============================================================
```

### Ejecutar Motor CPE

```bash
python main.py
```

El Motor validará la licencia automáticamente al iniciar.

---

## 🔐 Seguridad

### Arquitectura RSA-2048

1. **DisateQ** genera par de claves (una sola vez)
2. **Cliente** instala Motor + clave pública
3. **DisateQ** genera licencia firmada con clave privada
4. **Motor** valida licencia con clave pública

### Protecciones

✅ **Offline**: No requiere internet
✅ **Cifrado RSA-2048**: Imposible falsificar sin clave privada
✅ **Firma digital**: Cualquier alteración invalida la licencia
✅ **Fecha de expiración**: Verificación automática
✅ **Hardware ID**: Opcional (futuro)

### Qué NO pueden hacer los clientes

❌ Modificar fecha de expiración
❌ Cambiar límite de documentos
❌ Generar licencias propias (requiere clave privada)
❌ Transferir licencia a otro equipo (futuro: hardware ID)

---

## 🧪 Testing

### Ejecutar tests completos

```bash
python test_licencias.py
```

**Tests incluidos:**
1. ✅ Generar claves RSA
2. ✅ Crear licencia válida
3. ✅ Validar licencia correcta
4. ✅ Detectar licencia vencida
5. ✅ Detectar licencia alterada
6. ✅ Detectar archivo faltante

---

## 📊 Estructura de Licencia

```json
{
  "data": {
    "client_name": "Distribuidora ABC S.A.C.",
    "client_ruc": "20123456789",
    "product": "Motor CPE DisateQ™ v3.0",
    "issue_date": "2026-04-20T10:30:00",
    "expiry_date": "2027-04-20T10:30:00",
    "max_docs_month": 5000,
    "version": "3.0"
  },
  "signature": "aGVsbG8gd29ybGQK..." // Base64(RSA signature)
}
```

---

## 🔄 Renovación de Licencias

### Cliente solicita renovación

1. Cliente contacta a DisateQ™
2. DisateQ genera nueva licencia con:
   - Nueva fecha de expiración
   - Mismo o nuevo límite de documentos
3. Envía nuevo `disateq_motor.lic`
4. Cliente reemplaza archivo y reinicia Motor

**No requiere reinstalación del Motor.**

---

## 🆘 Solución de Problemas

### Error: "Licencia no encontrada"

**Causa**: Archivo `disateq_motor.lic` faltante
**Solución**: Contactar a DisateQ™ para obtener licencia

### Error: "Clave pública no encontrada"

**Causa**: Archivo `disateq_public.pem` faltante
**Solución**: Reinstalar Motor o descargar clave pública

### Error: "Licencia vencida hace X días"

**Causa**: Fecha de expiración alcanzada
**Solución**: Contactar a DisateQ™ para renovar licencia

### Error: "Licencia inválida (firma alterada)"

**Causa**: Archivo de licencia corrupto o modificado
**Solución**: Solicitar nueva licencia a DisateQ™

---

## 📝 Integración con Motor CPE

### En main.py

```python
from validador_licencias import LicenseValidator

def main():
    # Validar licencia antes de continuar
    validator = LicenseValidator()
    valida, mensaje, datos = validator.validate()
    
    if not valida:
        print(f"❌ {mensaje}")
        return 1
    
    # Continuar con lógica del Motor...
```

### Compilar a .exe (PyInstaller)

```bash
pip install pyinstaller

pyinstaller --onefile --name "MotorCPE_DisateQ_v3.0" main.py
```

**Incluir en distribución:**
- `MotorCPE_DisateQ_v3.0.exe`
- `disateq_public.pem`
- `disateq_motor.lic` (licencia del cliente)

---

## 📞 Contacto DisateQ™

**Soporte técnico:**
- Email: soporte@disateq.com
- WhatsApp: +51 999 999 999

**Renovación de licencias:**
- Email: ventas@disateq.com

---

**DisateQ™** — Motor CPE v3.0
© 2026 DisateQ™ | @fhertejada™
