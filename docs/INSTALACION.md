# Guía de Instalación — Motor CPE DisateQ™ v3.0

## 📋 Requisitos Previos

### **Sistema Operativo**
- Windows 10/11 o Windows Server 2016+
- Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)

### **Software Base**
- Python 3.10 o superior
- Git (para clonar repositorio)

### **Certificado Digital**
- Certificado SUNAT (.PFX o .PEM)
- RUC del emisor
- Clave SOL (para homologación)

---

## 🚀 Instalación Básica

### **1. Clonar Repositorio**

\\\ash
# Via SSH (recomendado)
git clone git@github.com:DisateQ/disateq-cpe-envio.git

# Via HTTPS
git clone https://github.com/DisateQ/disateq-cpe-envio.git

cd disateq-cpe-envio
\\\

### **2. Crear Entorno Virtual**

**Windows:**
\\\powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
\\\

**Linux:**
\\\ash
python3 -m venv venv
source venv/bin/activate
\\\

### **3. Instalar Dependencias**

\\\ash
pip install --upgrade pip
pip install -r requirements.txt
\\\

**Contenido de requirements.txt:**
\\\
dbfread==2.0.7          # DBF (FoxPro)
openpyxl==3.1.2         # Excel
pyodbc==5.0.1           # SQL universal
PyYAML==6.0.1           # Mapeo YAML
requests==2.31.0        # HTTP
pytest==7.4.3           # Testing
\\\

### **4. Configurar Certificado Digital**

**Opción A: Convertir .PFX a .PEM**

\\\ash
# Extraer llave privada
openssl pkcs12 -in certificado_sunat.pfx -nocerts -out private_encrypted.pem
# Contraseña del PFX: [ingresar]
# PEM pass phrase: [ingresar nueva]

# Quitar contraseña de la llave (opcional pero recomendado)
openssl rsa -in private_encrypted.pem -out disateq_private.pem
# Enter pass phrase: [ingresar la del paso anterior]
\\\

**Opción B: Ya tienes .PEM**

Solo copiar a ubicación segura.

**Ubicaciones recomendadas:**

| Sistema | Path | Permisos |
|---------|------|----------|
| Windows Dev | \D:\DATA\disateq_private.pem\ | Usuario actual |
| Windows Prod | \C:\ProgramData\DisateQ\certs\private.pem\ | Admin only |
| Linux Prod | \/etc/disateq/certs/private.pem\ | \chmod 600\ |

⚠️ **NUNCA commitear la llave privada al repositorio**

### **5. Verificar Instalación**

\\\ash
# Ejecutar tests
pytest tests/ -v

# Debe mostrar: 30 passed
\\\

---

## 🔧 Configuración por Tipo de Fuente

### **A. Excel (DisateQ POS™)**

**No requiere configuración adicional.**

El \XlsxAdapter\ lee directamente del worksheet \_CPE\ con estructura fija.

**Uso:**
\\\python
from adapters.xlsx_adapter import XlsxAdapter

adapter = XlsxAdapter('ventas.xlsx')
adapter.connect()
comprobantes = adapter.read_pending()
\\\

---

### **B. FoxPro (DBF)**

**Instalar driver ODBC (opcional):**

Solo necesario si los archivos DBF están en servidor remoto.

**Windows:**
- Descargar [Visual FoxPro ODBC Driver](https://www.microsoft.com/download)
- Instalar ejecutable
- Configurar DSN en Panel de Control → Orígenes de datos ODBC

**Uso:**
\\\python
from adapters.dbf_adapter import DbfAdapter

adapter = DbfAdapter('C:\\Sistemas\\data')
adapter.connect()
comprobantes = adapter.read_pending()
\\\

---

### **C. SQL Server**

**Instalar driver ODBC:**

**Windows:**
- Generalmente ya incluido en el sistema
- Si no: [Microsoft ODBC Driver 17](https://docs.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)

**Linux:**
\\\ash
# Ubuntu/Debian
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17

# CentOS/RHEL
curl https://packages.microsoft.com/config/rhel/8/prod.repo > /etc/yum.repos.d/mssql-release.repo
yum remove unixODBC-utf16 unixODBC-utf16-devel
ACCEPT_EULA=Y yum install -y msodbcsql17
\\\

**Configurar YAML:**

1. Explorar estructura:
\\\ash
python tools/source_explorer.py --source VENTAS \\
  --connection "Driver={ODBC Driver 17 for SQL Server};Server=SRV01;Database=ERP;UID=user;PWD=pass"
\\\

2. Copiar plantilla:
\\\ash
cp docs/mapping_examples/ejemplo_completo_sql.yaml \\
   src/adapters/mappings/cliente_abc.yaml
\\\

3. Editar con campos reales del explorer

4. Probar:
\\\python
from adapters.sql_adapter import SQLAdapter

adapter = SQLAdapter('src/adapters/mappings/cliente_abc.yaml')
adapter.connect()
print(adapter.read_pending())
\\\

---

### **D. PostgreSQL**

**Instalar driver:**
\\\ash
pip install psycopg2-binary
\\\

**YAML connection string:**
\\\yaml
source:
  type: postgresql
  connection: "host=localhost port=5432 dbname=erp user=postgres password=secret"
\\\

---

### **E. MySQL**

**Instalar driver:**
\\\ash
pip install mysql-connector-python
\\\

**YAML connection string:**
\\\yaml
source:
  type: mysql
  connection: "host=localhost;user=root;password=secret;database=erp"
\\\

---

### **F. Oracle**

**Instalar Oracle Instant Client:**

**Windows:**
1. Descargar [Instant Client](https://www.oracle.com/database/technologies/instant-client/downloads.html)
2. Descomprimir en \C:\oracle\instantclient_21_3\
3. Agregar al PATH

**Linux:**
\\\ash
# Descargar y descomprimir
wget https://download.oracle.com/otn_software/linux/instantclient/215000/instantclient-basic-linux.x64-21.5.0.0.0dbru.zip
unzip instantclient-basic-linux.x64-21.5.0.0.0dbru.zip -d /opt/oracle
export LD_LIBRARY_PATH=/opt/oracle/instantclient_21_5:\
\\\

**Instalar driver Python:**
\\\ash
pip install cx-Oracle
\\\

**YAML connection string:**
\\\yaml
source:
  type: oracle
  connection: "user/password@hostname:1521/service_name"
\\\

---

## 🏭 Instalación en Producción

### **Servidor Linux (Ubuntu/Debian)**

\\\ash
# 1. Instalar dependencias del sistema
sudo apt-get update
sudo apt-get install -y python3.10 python3-pip python3-venv git

# 2. Crear usuario de servicio
sudo useradd -r -m -s /bin/bash disateq
sudo su - disateq

# 3. Clonar y configurar
git clone git@github.com:DisateQ/disateq-cpe-envio.git
cd disateq-cpe-envio
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Copiar certificado
sudo mkdir -p /etc/disateq/certs
sudo cp disateq_private.pem /etc/disateq/certs/
sudo chown disateq:disateq /etc/disateq/certs/disateq_private.pem
sudo chmod 600 /etc/disateq/certs/disateq_private.pem

# 5. Crear servicio systemd
sudo nano /etc/systemd/system/disateq-cpe.service
\\\

**Contenido del servicio:**
\\\ini
[Unit]
Description=Motor CPE DisateQ
After=network.target

[Service]
Type=simple
User=disateq
WorkingDirectory=/home/disateq/disateq-cpe-envio
Environment="PATH=/home/disateq/disateq-cpe-envio/venv/bin"
ExecStart=/home/disateq/disateq-cpe-envio/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
\\\

**Activar servicio:**
\\\ash
sudo systemctl daemon-reload
sudo systemctl enable disateq-cpe
sudo systemctl start disateq-cpe
sudo systemctl status disateq-cpe
\\\

---

### **Servidor Windows (Servicio)**

**Usando NSSM (Non-Sucking Service Manager):**

\\\powershell
# 1. Descargar NSSM
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile nssm.zip
Expand-Archive nssm.zip -DestinationPath C:\Tools
Move-Item C:\Tools\nssm-2.24\win64\nssm.exe C:\Windows\System32\

# 2. Instalar servicio
nssm install DisateQCPE "D:\DisateQ\disateq-cpe-envio\venv\Scripts\python.exe"
nssm set DisateQCPE AppParameters "src\main.py"
nssm set DisateQCPE AppDirectory "D:\DisateQ\disateq-cpe-envio"
nssm set DisateQCPE DisplayName "Motor CPE DisateQ"
nssm set DisateQCPE Description "Motor de Comprobantes Electrónicos SUNAT"
nssm set DisateQCPE Start SERVICE_AUTO_START

# 3. Iniciar servicio
nssm start DisateQCPE
\\\

---

## 🔍 Verificación Post-Instalación

### **1. Test de Conexión a Fuente**

\\\python
# test_conexion.py
from adapters.sql_adapter import SQLAdapter

adapter = SQLAdapter('src/adapters/mappings/tu_cliente.yaml')
try:
    adapter.connect()
    print("✓ Conexión exitosa")
    pendientes = adapter.read_pending()
    print(f"✓ Encontrados {len(pendientes)} comprobantes pendientes")
except Exception as e:
    print(f"✗ Error: {e}")
\\\

### **2. Test de Certificado**

\\\python
# test_certificado.py
from signer import cargar_llave_privada, firmar_json

try:
    llave = cargar_llave_privada('D:/DATA/disateq_private.pem')
    print("✓ Certificado cargado correctamente")
    
    # Test de firma
    test_data = {"test": "data"}
    firma = firmar_json(test_data, llave)
    print(f"✓ Firma generada: {firma[:50]}...")
except Exception as e:
    print(f"✗ Error: {e}")
\\\

### **3. Test End-to-End**

\\\ash
# Ejecutar test completo
pytest tests/test_e2e.py -v
\\\

---

## 🐛 Troubleshooting

### **Error: "No module named 'pyodbc'"**

**Solución:**
\\\ash
pip install pyodbc

# Si falla en Linux:
sudo apt-get install unixodbc-dev
pip install pyodbc
\\\

---

### **Error: "SSL: CERTIFICATE_VERIFY_FAILED"**

**Solución:**
\\\ash
pip install --upgrade certifi
\\\

---

### **Error: "OperationalError: [HY000]"**

**Causa:** Driver ODBC no encontrado

**Solución:**
\\\ash
# Listar drivers instalados
odbcinst -q -d

# Si SQL Server no aparece, instalar:
# Ver sección "C. SQL Server" arriba
\\\

---

### **Error: "Access denied for user"**

**Causa:** Credenciales incorrectas en connection string

**Solución:**
1. Verificar usuario/password en YAML
2. Verificar permisos en base de datos
3. Probar conexión con cliente GUI (DBeaver, SSMS)

---

### **Error: "Could not load private key"**

**Causa:** Formato de certificado incorrecto

**Solución:**
\\\ash
# Verificar formato
openssl rsa -in disateq_private.pem -check

# Debe mostrar: "RSA key ok"
\\\

---

## 📊 Logs y Monitoreo

### **Ubicación de Logs**

| Sistema | Path |
|---------|------|
| Windows | \D:\DisateQ\logs\cpe_motor.log\ |
| Linux | \/var/log/disateq/cpe_motor.log\ |

### **Configurar Rotación de Logs**

**Linux (logrotate):**
\\\ash
sudo nano /etc/logrotate.d/disateq-cpe
\\\

\\\
/var/log/disateq/cpe_motor.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 disateq disateq
}
\\\

---

## 🔐 Seguridad en Producción

### **Checklist**

- [ ] Certificado en ubicación segura con permisos 600
- [ ] Connection strings sin contraseñas en texto plano
- [ ] Firewall permitiendo solo puerto SUNAT (443)
- [ ] Usuario de servicio sin privilegios admin
- [ ] Logs rotando para evitar llenado de disco
- [ ] Backups automáticos de configuración

---

**DisateQ™** — Motor CPE v3.0
