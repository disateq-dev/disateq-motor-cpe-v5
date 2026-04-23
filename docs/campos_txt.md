# Referencia de campos TXT — APIFAS

Formato de archivo TXT para APIFAS (API para DisateQ).
Cada línea tiene el formato: `campo|valor|`

## Endpoints APIFAS

| Modalidad | Operación | URL |
|---|---|---|
| OSE / PSE | Envío | https://apifas.disateq.com/ose_produccion.php |
| OSE / PSE | Anulación | https://apifas.disateq.com/ose_anular.php |
| SEE SUNAT | Envío | https://apifas.disateq.com/produccion_text.php |
| SEE SUNAT | Anulación | https://apifas.disateq.com/produccion_anular.php |

## Cabecera del comprobante

| Campo | Valor | Notas |
|---|---|---|
| `operacion` | `generar_comprobante` | Fijo |
| `tipo_de_comprobante` | `1` factura / `2` boleta | |
| `serie` | `F001`, `B001`, etc. | |
| `numero` | Correlativo numérico | Sin ceros a la izquierda |
| `sunat_transaction` | `1` | Fijo |
| `cliente_tipo_de_documento` | `1` DNI / `6` RUC / `-` varios | |
| `cliente_numero_de_documento` | Número de documento | `00000000` si es varios |
| `cliente_denominacion` | Nombre del cliente | `CLIENTE VARIOS` si no aplica |
| `fecha_de_emision` | `DD-MM-YYYY` | |
| `moneda` | `1` PEN / `2` USD | |
| `porcentaje_de_igv` | `18.00` | |
| `total_gravada` | Monto sin IGV | 8 decimales |
| `total_exonerada` | Monto exonerado | 8 decimales |
| `total_igv` | Monto IGV | 8 decimales |
| `total_impuestos_bolsas` | ICBPER | 8 decimales |
| `total` | Total con IGV | 8 decimales |
| `condiciones_de_pago` | `Contado` / `Credito` | Desde `FORMA_FACT` |

## Línea de ítem

```
item|UNIDAD|CODIGO|DESCRIPCION|CANTIDAD|PRECIO_SIN_IGV|PRECIO_CON_IGV||SUBTOTAL_SIN_IGV|AFECTACION|IGV|TOTAL|false||UNSPSC|||||
```

| Posición | Campo | Notas |
|---|---|---|
| 1 | Unidad | `NIU` bien / `ZZ` servicio |
| 2 | Código del producto | Código interno del sistema |
| 3 | Descripción | MAYÚSCULAS — desde `productox.DESCRIPCIO + PRESENTA_P` |
| 4 | Cantidad | `CANTIDAD_P` o `TABLETA_PE` si CANTIDAD_P = 0 |
| 5 | Precio sin IGV | `PRECIO_UNI/1.18` o `PRECIO_FRA/1.18` |
| 6 | Precio con IGV | `PRECIO_UNI` o `PRECIO_FRA` |
| 7 | (vacío) | |
| 8 | Subtotal sin IGV | `MONTO_PEDI` |
| 9 | Afectación IGV | `10` gravado / `20` exonerado / `30` inafecto |
| 10 | IGV del ítem | `IGV_PEDIDO` |
| 11 | Total del ítem | `REAL_PEDID` |
| 12 | `false` | Fijo |
| 13-14 | (vacíos) | |
| 15 | Código UNSPSC | 8 dígitos — desde `productox.CODIGO_UNS` |

## Códigos de afectación IGV

| Código | Descripción | Condición en DBF |
|---|---|---|
| `10` | Gravado — Operación Onerosa | `PRODUCTO_E=0` y `ICBPER=0` |
| `20` | Exonerado — Operación Onerosa | `PRODUCTO_E=1` o `ICBPER=1` |
| `30` | Inafecto — Operación Onerosa | (no usado actualmente) |

## Nombre del archivo TXT

```
{RUC}-02-{SERIE}{NUMERO_3_DIGITOS}-{NUMERO_8_DIGITOS}.txt
Ejemplo: 10405206710-02-B001-00023168.txt
```

## Errores del sistema FoxPro original corregidos

| Problema | Campo afectado | Corrección |
|---|---|---|
| Afectación IGV siempre `1` | Ítem posición 9 | Verificar `PRODUCTO_E` e `ICBPER` |
| Exonerados suman a gravada | `total_gravada` | Calcular por tipo de ítem |
| ICBPER en campo incorrecto | `total_gratuita` | Usar `total_impuestos_bolsas` |
| Forma de pago vacía | `condiciones_de_pago` | Leer `FORMA_FACT` |
| Descripción solo código | Ítem posición 3 | Cruzar con `productox` |
| UNSPSC hardcodeado | Ítem posición 15 | Leer `productox.CODIGO_UNS` |
| Fechas nulas (`\x00`) | `FECHA_DOCU` | `_SafeFieldParser` en `dbf_reader.py` |
