# Ejemplos Prácticos — Motor CPE DisateQ™ v3.0

## 📝 Casos de Uso Reales

---

## 1. Integración con DisateQ POS™ (Excel)

### **Escenario**

Cliente tiene DisateQ POS™ funcionando en Excel. Cada venta genera una fila en el worksheet \_CPE\ con los datos listos para envío.

### **Código Completo**

\\\python
# enviar_desde_pos.py
from adapters.xlsx_adapter import XlsxAdapter
from normalizer import normalizar
from signer import cargar_llave_privada, firmar_json
from sender import enviar_cpe
import sys

# Configuración
ARCHIVO_VENTAS = 'D:/DisateQ/ventas_hoy.xlsx'
CERTIFICADO = 'D:/DATA/disateq_private.pem'
RUC_EMISOR = '20123456789'
RAZON_SOCIAL = 'MI EMPRESA SAC'

def main():
    # 1. Conectar al Excel
    print("Conectando a DisateQ POS™...")
    adapter = XlsxAdapter(ARCHIVO_VENTAS)
    adapter.connect()
    
    # 2. Leer comprobantes pendientes
    pendientes = adapter.read_pending()
    print(f"Encontrados {len(pendientes)} comprobantes pendientes")
    
    if not pendientes:
        print("No hay comprobantes pendientes.")
        return
    
    # 3. Procesar cada comprobante
    enviados = 0
    errores = 0
    
    for comp in pendientes:
        try:
            # Leer ítems
            items = adapter.read_items(comp)
            
            # Normalizar
            cpe = normalizar(comp, items, RUC_EMISOR, RAZON_SOCIAL)
            
            # Enviar a SUNAT
            exito, mensaje = enviar_cpe(cpe, CERTIFICADO)
            
            if exito:
                print(f"✓ {cpe['serie']}-{cpe['numero']:08d}: {mensaje}")
                enviados += 1
            else:
                print(f"✗ {cpe['serie']}-{cpe['numero']:08d}: {mensaje}")
                errores += 1
                
        except Exception as e:
            print(f"✗ Error procesando comprobante: {e}")
            errores += 1
    
    # 4. Resumen
    print(f"\nResumen: {enviados} enviados, {errores} errores")
    adapter.disconnect()

if __name__ == '__main__':
    main()
\\\

### **Ejecución**

\\\powershell
python enviar_desde_pos.py
\\\

**Salida esperada:**
\\\
Conectando a DisateQ POS™...
Encontrados 5 comprobantes pendientes
✓ B001-00000123: Aceptado por SUNAT
✓ B001-00000124: Aceptado por SUNAT
✗ B001-00000125: Error validación - Total no coincide
✓ B001-00000126: Aceptado por SUNAT
✓ B001-00000127: Aceptado por SUNAT

Resumen: 4 enviados, 1 errores
\\\

---

## 2. Migración desde FoxPro Legacy

### **Escenario**

Farmacia con sistema FoxPro antiguo. Tienen DBF con ventas pero nunca enviaron a SUNAT electrónicamente.

### **Paso 1: Explorar la estructura**

\\\ash
python tools/source_explorer.py --source C:/Sistemas/data/ventas.dbf --verbose
\\\

**Salida:**
\\\
═══════════════════════════════════════
Source Explorer — DisateQ™
═══════════════════════════════════════

Fuente: ventas.dbf
Tipo:   DBF (FoxPro)

Campos encontrados: 15

NOMBRE              TIPO     LONGITUD  MUESTRA
──────────────────────────────────────────────
TIPO_DOC            C        1         B
SERIE               C        4         001
NUMERO              N        8         123
FECHA               D        8         2024-03-27
RUC_CLI             C        11        12345678901
NOMBRE_CLI          C        100       CLIENTE EJEMPLO
TOTAL_GRAV          N        12,2      100.00
TOTAL_IGV           N        12,2      18.00
TOTAL               N        12,2      118.00
FLAG_ENVIO          N        1         0
...
\\\

### **Paso 2: Código de integración**

\\\python
# migrar_foxpro.py
from adapters.dbf_adapter import DbfAdapter
from normalizer import normalizar
from sender import enviar_cpe
from datetime import datetime

# Configuración
DATA_PATH = 'C:/Sistemas/data'
CERTIFICADO = 'D:/DATA/disateq_private.pem'
RUC_EMISOR = '20987654321'
RAZON_SOCIAL = 'FARMACIA DEL PUEBLO SAC'

def main():
    adapter = DbfAdapter(DATA_PATH)
    adapter.connect()
    
    # Solo comprobantes del mes actual
    hoy = datetime.now()
    
    pendientes = adapter.read_pending()
    # Filtrar por mes
    pendientes_mes = [
        p for p in pendientes 
        if p['fecha_emision'].month == hoy.month
    ]
    
    print(f"Comprobantes del mes {hoy.month}: {len(pendientes_mes)}")
    
    for comp in pendientes_mes:
        items = adapter.read_items(comp)
        cpe = normalizar(comp, items, RUC_EMISOR, RAZON_SOCIAL)
        
        exito, msg = enviar_cpe(cpe, CERTIFICADO)
        
        if exito:
            # Marcar como enviado en el DBF
            adapter.marcar_enviado(comp)
            print(f"✓ {cpe['serie']}-{cpe['numero']:08d}")
        else:
            print(f"✗ {cpe['serie']}-{cpe['numero']:08d}: {msg}")

if __name__ == '__main__':
    main()
\\\

---

## 3. Sistema ERP con SQL Server

### **Escenario**

Empresa con ERP en SQL Server 2019. Necesitan enviar facturas automáticamente.

### **Paso 1: Explorar tablas**

\\\ash
python tools/source_explorer.py \
  --source VEN_CABECERA \
  --connection "Driver={ODBC Driver 17 for SQL Server};Server=SRV01;Database=ERP_PRODUCCION;UID=cpe_user;PWD=secret123"
\\\

### **Paso 2: Crear mapeo YAML**

\\\yaml
# src/adapters/mappings/empresa_xyz.yaml

source:
  type: sqlserver
  connection: "Driver={ODBC Driver 17 for SQL Server};Server=SRV01;Database=ERP_PRODUCCION;UID=cpe_user;PWD=secret123"
  table: VEN_CABECERA

comprobante:
  tipo_doc:
    field: TIPO_COMPROBANTE
    transform: "map({'FAC': '01', 'BOL': '03'})"
  
  serie:
    field: SERIE_DOCUMENTO
    transform: "strip().upper()"
  
  numero:
    field: NRO_DOCUMENTO
    transform: "int()"
  
  fecha_emision:
    field: FECHA_EMISION
    transform: "to_date('%Y-%m-%d')"
  
  moneda:
    field: MONEDA
    default: "PEN"

cliente:
  tipo_doc:
    field: TIPO_DOC_CLIENTE
    transform: "map({'1': '1', '6': '6'})"
  
  numero_doc:
    field: NRO_DOC_CLIENTE
  
  denominacion:
    field: RAZON_SOCIAL_CLIENTE
    transform: "upper().strip()"

items:
  source_table: VEN_DETALLE
  relation:
    ID_DOCUMENTO: ID_DOCUMENTO
  
  fields:
    codigo:
      field: COD_PRODUCTO
    
    descripcion:
      field: DES_PRODUCTO
      transform: "upper()"
    
    cantidad:
      field: CANTIDAD
      transform: "float()"
    
    precio_unitario:
      field: PRECIO_UNIT
      transform: "float()"
    
    afectacion_igv:
      field: AFECTACION_IGV
      transform: "map({'1': '10', '2': '20'})"

business_rules:
  filter:
    - field: ESTADO_SUNAT
      equals: 'PENDIENTE'
  
  ignore_if:
    - field: ANULADO
      equals: 1
\\\

### **Paso 3: Script automatizado**

\\\python
# envio_automatico.py
from adapters.sql_adapter import SQLAdapter
from sender import enviar_cpe
import time

MAPPING = 'src/adapters/mappings/empresa_xyz.yaml'
CERTIFICADO = 'D:/DATA/disateq_private.pem'

def procesar_pendientes():
    adapter = SQLAdapter(MAPPING)
    adapter.connect()
    
    try:
        pendientes = adapter.read_pending()
        
        for comp in pendientes:
            items = adapter.read_items(comp)
            cpe = adapter.normalize(comp, items)
            
            exito, msg = enviar_cpe(cpe, CERTIFICADO)
            
            if exito:
                # Actualizar estado en BD
                adapter.actualizar_estado(comp, 'ENVIADO', msg)
            else:
                adapter.actualizar_estado(comp, 'ERROR', msg)
            
            # Delay para no saturar SUNAT
            time.sleep(2)
            
    finally:
        adapter.disconnect()

if __name__ == '__main__':
    # Ejecutar cada 5 minutos
    while True:
        try:
            procesar_pendientes()
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(300)  # 5 minutos
\\\

### **Paso 4: Configurar como servicio Windows**

Ver [docs/INSTALACION.md](INSTALACION.md#servidor-windows-servicio)

---

## 4. Validación y Testing

### **Test unitario de adaptador**

\\\python
# tests/test_custom_adapter.py
import pytest
from adapters.sql_adapter import SQLAdapter

@pytest.fixture
def adapter():
    return SQLAdapter('tests/fixtures/test_mapping.yaml')

def test_conexion(adapter):
    adapter.connect()
    assert adapter.is_connected()

def test_lectura_pendientes(adapter):
    adapter.connect()
    pendientes = adapter.read_pending()
    
    assert len(pendientes) > 0
    assert 'tipo_doc' in pendientes[0]
    assert 'serie' in pendientes[0]

def test_normalizacion(adapter):
    adapter.connect()
    comp = adapter.read_pending()[0]
    items = adapter.read_items(comp)
    
    cpe = adapter.normalize(comp, items)
    
    # Validar estructura
    assert cpe['tipo_doc'] in ['01', '03']
    assert cpe['totales']['total'] > 0
    assert len(cpe['items']) > 0
\\\

---

## 5. Manejo de Errores

### **Reintentos automáticos**

\\\python
# envio_con_reintentos.py
from sender import enviar_cpe
import time

def enviar_con_reintentos(cpe, certificado, max_intentos=3):
    """
    Envía CPE con reintentos exponenciales.
    """
    for intento in range(1, max_intentos + 1):
        try:
            exito, msg = enviar_cpe(cpe, certificado)
            
            if exito:
                return True, msg
            
            # Si es error de validación, no reintentar
            if 'validación' in msg.lower():
                return False, msg
            
            # Si es error de conexión, reintentar
            if intento < max_intentos:
                espera = 2 ** intento  # 2s, 4s, 8s
                print(f"Reintento {intento}/{max_intentos} en {espera}s...")
                time.sleep(espera)
                
        except Exception as e:
            if intento == max_intentos:
                return False, f"Error tras {max_intentos} intentos: {e}"
            time.sleep(2 ** intento)
    
    return False, "Reintentos agotados"

# Uso
exito, mensaje = enviar_con_reintentos(cpe, CERTIFICADO, max_intentos=3)
\\\

### **Logging detallado**

\\\python
# config_logging.py
import logging
from datetime import datetime

def configurar_logging(nivel=logging.INFO):
    """
    Configura logging para el motor CPE.
    """
    log_file = f"cpe_motor_{datetime.now():%Y%m%d}.log"
    
    logging.basicConfig(
        level=nivel,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

# Uso en script principal
configurar_logging(logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("Iniciando procesamiento")
logger.debug(f"Comprobante: {cpe}")
logger.error(f"Error en envío: {error}")
\\\

---

## 6. Batch Processing

### **Procesar lote de 100 comprobantes**

\\\python
# batch_processor.py
from adapters.xlsx_adapter import XlsxAdapter
from sender import enviar_cpe
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

CERTIFICADO = 'D:/DATA/disateq_private.pem'
MAX_WORKERS = 5  # Threads simultáneos

def enviar_uno(cpe_data):
    """Envía un CPE individual."""
    comp, items, ruc, razon = cpe_data
    
    from normalizer import normalizar
    cpe = normalizar(comp, items, ruc, razon)
    
    exito, msg = enviar_cpe(cpe, CERTIFICADO)
    
    return {
        'serie': cpe['serie'],
        'numero': cpe['numero'],
        'exito': exito,
        'mensaje': msg
    }

def procesar_lote(archivo_excel, ruc, razon):
    adapter = XlsxAdapter(archivo_excel)
    adapter.connect()
    
    pendientes = adapter.read_pending()
    
    # Preparar datos para threads
    lote = []
    for comp in pendientes[:100]:  # Máximo 100
        items = adapter.read_items(comp)
        lote.append((comp, items, ruc, razon))
    
    # Procesar en paralelo
    resultados = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(enviar_uno, data): data for data in lote}
        
        for future in as_completed(futures):
            resultado = future.result()
            resultados.append(resultado)
            
            if resultado['exito']:
                print(f"✓ {resultado['serie']}-{resultado['numero']:08d}")
            else:
                print(f"✗ {resultado['serie']}-{resultado['numero']:08d}: {resultado['mensaje']}")
    
    adapter.disconnect()
    return resultados

# Uso
resultados = procesar_lote('ventas.xlsx', '20123456789', 'MI EMPRESA SAC')
enviados = sum(1 for r in resultados if r['exito'])
print(f"\nTotal enviados: {enviados}/{len(resultados)}")
\\\

---

## 7. Dashboard de Monitoreo

### **Script simple para monitoreo**

\\\python
# dashboard.py
from adapters.sql_adapter import SQLAdapter
from datetime import datetime, timedelta

def generar_reporte_dia(mapping_path):
    adapter = SQLAdapter(mapping_path)
    adapter.connect()
    
    # Stats del día
    hoy = datetime.now().date()
    
    query = f"""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN ESTADO_SUNAT='ENVIADO' THEN 1 ELSE 0 END) as enviados,
        SUM(CASE WHEN ESTADO_SUNAT='ERROR' THEN 1 ELSE 0 END) as errores,
        SUM(CASE WHEN ESTADO_SUNAT='PENDIENTE' THEN 1 ELSE 0 END) as pendientes,
        SUM(TOTAL) as monto_total
    FROM VEN_CABECERA
    WHERE CAST(FECHA_EMISION AS DATE) = '{hoy}'
    """
    
    stats = adapter.execute_query(query)[0]
    
    print(f"""
    ═══════════════════════════════════════
    REPORTE CPE — {hoy:%d/%m/%Y}
    ═══════════════════════════════════════
    
    Total comprobantes: {stats['total']}
    Enviados:           {stats['enviados']} ({stats['enviados']/stats['total']*100:.1f}%)
    Errores:            {stats['errores']}
    Pendientes:         {stats['pendientes']}
    
    Monto total:        S/ {stats['monto_total']:,.2f}
    ═══════════════════════════════════════
    """)
    
    adapter.disconnect()

# Uso
generar_reporte_dia('src/adapters/mappings/empresa_xyz.yaml')
\\\

---

## 8. Integración con Webhook

### **Notificar a sistema externo tras envío**

\\\python
# webhook_integration.py
import requests
from sender import enviar_cpe

WEBHOOK_URL = 'https://mi-sistema.com/api/webhook/cpe'

def enviar_con_notificacion(cpe, certificado):
    # Enviar a SUNAT
    exito, mensaje = enviar_cpe(cpe, certificado)
    
    # Notificar al sistema
    payload = {
        'tipo_doc': cpe['tipo_doc'],
        'serie': cpe['serie'],
        'numero': cpe['numero'],
        'exito': exito,
        'mensaje': mensaje,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Warning: No se pudo notificar al webhook: {e}")
    
    return exito, mensaje
\\\

---

**DisateQ™** — Motor CPE v3.0
