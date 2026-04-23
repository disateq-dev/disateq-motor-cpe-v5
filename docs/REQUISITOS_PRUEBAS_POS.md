# Requisitos para Pruebas de Integración

**Motor CPE v3.0** ← **DisateQ POS™ Excel**

---

## 📦 Archivo Requerido

- **Nombre:** ventas_test.xlsx
- **Ubicación:** D:/DisateQ/test/
- **Fecha entrega:** [A DEFINIR]

---

## 📋 Contenido del Worksheet _CPE

### Configuración
- **Nombre:** _CPE
- **Visibilidad:** xlVeryHidden
- **Protección:** Desactivada (para pruebas)

### Estructura
Fila 1: Headers (según contrato v1.1)
Fila 2: 1 comprobante de prueba completo

---

## 🧾 Datos del Comprobante de Prueba

### Cabecera
| Campo | Valor |
|-------|-------|
| tipo_doc | 03 (Boleta) |
| serie | B001 |
| numero | 1 |
| fecha_emision | 2024-04-20 |
| moneda | PEN |

### Cliente
| Campo | Valor |
|-------|-------|
| cliente_tipo_doc | 1 (DNI) |
| cliente_numero_doc | 12345678 |
| cliente_denominacion | CLIENTE PRUEBA |
| cliente_direccion | AV TEST 123 |

### Ítem
| Campo | Valor |
|-------|-------|
| item_codigo | PROD001 |
| item_descripcion | PRODUCTO TEST |
| item_cantidad | 2.0 |
| item_unidad | NIU |
| item_precio_unitario | 10.00 |
| item_valor_unitario | 8.47 |
| item_subtotal_sin_igv | 16.95 |
| item_igv | 3.05 |
| item_total | 20.00 |
| item_afectacion_igv | 10 (Gravado) |
| item_unspsc | 10000000 |

### Totales
| Campo | Valor |
|-------|-------|
| total_gravada | 16.95 |
| total_exonerada | 0.00 |
| total_igv | 3.05 |
| total | 20.00 |

**CRÍTICO:** total = gravada + igv (20.00 = 16.95 + 3.05)

---

## ✅ Checklist de Validación

- [ ] Archivo .xlsx creado
- [ ] Worksheet _CPE existe y está oculto
- [ ] Fila 1 tiene headers
- [ ] Fila 2 tiene comprobante completo
- [ ] tipo_doc = "03"
- [ ] serie = "B001"
- [ ] numero = 1
- [ ] Fecha formato YYYY-MM-DD
- [ ] Cliente con DNI 8 dígitos
- [ ] Ítem completo con todos los campos
- [ ] item_afectacion_igv = "10"
- [ ] total = gravada + igv
- [ ] No hay celdas vacías
- [ ] Decimales con punto (16.95 no 16,95)

---

## 🧪 Proceso de Pruebas

**Nivel 1:** Lectura (~2 min)  
**Nivel 2:** Generación TXT (~3 min)  
**Nivel 3:** Envío Real APIFAS (~5 min)

**Total:** ~10 minutos

---

**Motor CPE v3.0** | DisateQ™
