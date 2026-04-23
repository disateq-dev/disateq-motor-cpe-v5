"""
validador_licencias.py
======================
Sistema de Licencias Offline RSA — Motor CPE DisateQ™ v3.0

Validación de licencias sin conexión a internet.
Cifrado RSA-2048 para seguridad máxima.

Autor: Fernando Hernán Tejada (@fhertejada™)
Empresa: DisateQ™
"""

import json
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


class LicenseValidator:
    """
    Validador de licencias offline con cifrado RSA.
    
    Flujo:
        1. DisateQ genera par de claves RSA (una vez)
        2. Cliente instala Motor + clave pública
        3. DisateQ genera licencia firmada con clave privada
        4. Motor valida licencia con clave pública
    """
    
    # Configuración
    LICENSE_FILE = "disateq_motor.lic"
    PUBLIC_KEY_FILE = "disateq_public.pem"
    
    def __init__(self, license_dir: Optional[Path] = None):
        """
        Inicializa validador.
        
        Args:
            license_dir: Directorio donde buscar archivos de licencia.
                        Por defecto: auto-detecta ubicación
        """
        if license_dir is None:
            # Auto-detectar ubicación
            script_dir = Path(__file__).parent  # licenses/
            
            # CASO 1: Producción - C:\Program Files\DisateQ\Motor CPE\
            prod_dir = Path(r"C:\Program Files\DisateQ\Motor CPE")
            if prod_dir.exists() and (prod_dir / self.PUBLIC_KEY_FILE).exists():
                license_dir = prod_dir
                keys_dir = prod_dir
            # CASO 2: Desarrollo organizado - licenses/ (este script está en licenses/)
            elif script_dir.name == "licenses":
                license_dir = script_dir / "client_licenses"
                keys_dir = script_dir / "keys"
            # CASO 3: Desarrollo sin organizar - raíz
            else:
                license_dir = script_dir
                keys_dir = script_dir
        else:
            license_dir = Path(license_dir)
            # Buscar keys relativo a licenses
            if (license_dir.parent / "keys").exists():
                keys_dir = license_dir.parent / "keys"
            else:
                keys_dir = license_dir
        
        self.license_dir = Path(license_dir)
        self.license_path = self.license_dir / self.LICENSE_FILE
        self.pubkey_path = keys_dir / self.PUBLIC_KEY_FILE
        self.public_key = None
        self._load_public_key()
    
    def _load_public_key(self):
        """Carga clave pública desde archivo PEM."""
        try:
            if not self.pubkey_path.exists():
                raise FileNotFoundError(
                    f"Clave pública no encontrada: {self.pubkey_path}"
                )
            
            with open(self.pubkey_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
        except Exception as e:
            raise RuntimeError(f"Error cargando clave pública: {e}")
    
    def validate(self) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida licencia actual.
        
        Returns:
            (es_valida, mensaje, datos_licencia)
        
        Verificaciones:
            1. Archivo de licencia existe
            2. Formato JSON válido
            3. Firma RSA válida (integridad)
            4. Fecha de expiración vigente
        """
        # 1. Verificar archivo existe
        if not self.license_path.exists():
            return False, "Licencia no encontrada. Contacte a DisateQ™", None
        
        try:
            # 2. Leer y parsear licencia
            with open(self.license_path, 'r', encoding='utf-8') as f:
                license_data = json.load(f)
            
            # Verificar campos requeridos
            required = ['data', 'signature']
            if not all(k in license_data for k in required):
                return False, "Licencia corrupta (campos faltantes)", None
            
            # 3. Verificar firma RSA
            data_str = json.dumps(license_data['data'], sort_keys=True)
            signature = base64.b64decode(license_data['signature'])
            
            try:
                self.public_key.verify(
                    signature,
                    data_str.encode('utf-8'),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            except Exception:
                return False, "Licencia inválida (firma alterada)", None
            
            # 4. Verificar fecha de expiración
            data = license_data['data']
            expiry = datetime.fromisoformat(data['expiry_date'])
            now = datetime.now()
            
            if now > expiry:
                dias_vencida = (now - expiry).days
                return False, f"Licencia vencida hace {dias_vencida} días", data
            
            # ✅ Licencia válida
            dias_restantes = (expiry - now).days
            
            return True, f"Licencia válida ({dias_restantes} días restantes)", data
        
        except json.JSONDecodeError:
            return False, "Licencia corrupta (formato inválido)", None
        except Exception as e:
            return False, f"Error validando licencia: {str(e)}", None
    
    def get_license_info(self) -> Optional[Dict]:
        """
        Obtiene información de la licencia sin validar firma.
        Útil para mostrar info al usuario.
        
        Returns:
            Dict con datos de licencia o None si no existe
        """
        if not self.license_path.exists():
            return None
        
        try:
            with open(self.license_path, 'r', encoding='utf-8') as f:
                license_data = json.load(f)
                return license_data.get('data')
        except:
            return None


# ========================================
# GENERADOR DE LICENCIAS (DisateQ™ uso interno)
# ========================================

class LicenseGenerator:
    """
    Generador de licencias RSA — Solo para uso interno DisateQ™
    
    NO distribuir este código al cliente.
    Solo distribuir: LicenseValidator + clave pública.
    """
    
    PRIVATE_KEY_FILE = "disateq_private.pem"
    PUBLIC_KEY_FILE = "disateq_public.pem"
    
    @staticmethod
    def generate_keypair(key_dir: Path = Path(".")):
        """
        Genera par de claves RSA-2048 (una sola vez).
        
        Genera:
            - disateq_private.pem (MANTENER SECRETO)
            - disateq_public.pem (distribuir con Motor)
        """
        key_dir = Path(key_dir)
        private_path = key_dir / LicenseGenerator.PRIVATE_KEY_FILE
        public_path = key_dir / LicenseGenerator.PUBLIC_KEY_FILE
        
        # Generar par de claves
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        # Guardar clave privada
        with open(private_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Guardar clave pública
        with open(public_path, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        
        print(f"✅ Par de claves generado:")
        print(f"   Privada: {private_path} (MANTENER SEGURA)")
        print(f"   Pública: {public_path} (distribuir con Motor)")
    
    @staticmethod
    def create_license(
        client_name: str,
        client_ruc: str,
        expiry_days: int,
        max_docs_month: int = 999999,  # Ilimitado por defecto
        private_key_path: Path = Path("disateq_private.pem"),
        output_path: Path = Path("disateq_motor.lic")
    ) -> Dict:
        """
        Crea licencia firmada para un cliente.
        
        Args:
            client_name: Nombre del cliente
            client_ruc: RUC del cliente
            expiry_days: Días de validez desde hoy
            max_docs_month: Máximo documentos por mes (999999 = ilimitado)
            private_key_path: Ruta a clave privada DisateQ
            output_path: Dónde guardar la licencia
        
        Returns:
            Dict con datos de la licencia generada
        """
        # Cargar clave privada
        with open(private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        # Crear datos de licencia
        now = datetime.now()
        expiry = now + timedelta(days=expiry_days)
        
        license_data = {
            'client_name': client_name,
            'client_ruc': client_ruc,
            'product': 'Motor CPE DisateQ™ v3.0',
            'issue_date': now.isoformat(),
            'expiry_date': expiry.isoformat(),
            'max_docs_month': max_docs_month,
            'version': '3.0',
        }
        
        # Firmar con RSA
        data_str = json.dumps(license_data, sort_keys=True)
        signature = private_key.sign(
            data_str.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Crear licencia completa
        license_file = {
            'data': license_data,
            'signature': base64.b64encode(signature).decode('utf-8')
        }
        
        # Guardar
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(license_file, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Licencia generada: {output_path}")
        print(f"   Cliente: {client_name} ({client_ruc})")
        print(f"   Válida hasta: {expiry.strftime('%Y-%m-%d')}")
        max_docs_str = "ilimitado" if max_docs_month >= 999999 else str(max_docs_month)
        print(f"   Máx docs/mes: {max_docs_str}")
        
        return license_data


# ========================================
# INTERFAZ CLI
# ========================================

def main():
    """CLI para validar licencia o generar claves."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sistema de Licencias DisateQ™ Motor CPE v3.0"
    )
    parser.add_argument(
        'action',
        choices=['validate', 'generate-keys', 'create-license'],
        help='Acción a realizar'
    )
    parser.add_argument('--client-name', help='Nombre del cliente')
    parser.add_argument('--client-ruc', help='RUC del cliente')
    parser.add_argument('--days', type=int, default=365, help='Días de validez')
    parser.add_argument('--max-docs', type=int, default=999999, help='Docs/mes (999999=ilimitado)')
    
    args = parser.parse_args()
    
    if args.action == 'validate':
        # Validar licencia actual
        validator = LicenseValidator()
        valida, mensaje, datos = validator.validate()
        
        print("\n" + "="*60)
        print("VALIDACIÓN DE LICENCIA")
        print("="*60)
        
        if valida:
            print(f"✅ {mensaje}")
            max_docs = datos['max_docs_month']
            max_docs_str = "ilimitado" if max_docs >= 999999 else str(max_docs)
            print(f"\nCliente: {datos['client_name']}")
            print(f"RUC: {datos['client_ruc']}")
            print(f"Vencimiento: {datos['expiry_date'][:10]}")
            print(f"Máx docs/mes: {max_docs_str}")
        else:
            print(f"❌ {mensaje}")
        
        print("="*60 + "\n")
        
        return 0 if valida else 1
    
    elif args.action == 'generate-keys':
        # Generar par de claves RSA
        print("\n⚠️  Generando par de claves RSA-2048...")
        print("   Solo hacerlo UNA VEZ para DisateQ™\n")
        
        LicenseGenerator.generate_keypair()
        print("\n⚠️  IMPORTANTE:")
        print("   - Guardar disateq_private.pem en lugar SEGURO")
        print("   - Distribuir disateq_public.pem con el Motor\n")
    
    elif args.action == 'create-license':
        # Crear licencia para cliente
        if not args.client_name or not args.client_ruc:
            print("❌ Error: --client-name y --client-ruc requeridos")
            return 1
        
        LicenseGenerator.create_license(
            client_name=args.client_name,
            client_ruc=args.client_ruc,
            expiry_days=args.days,
            max_docs_month=args.max_docs
        )


if __name__ == '__main__':
    import sys
    sys.exit(main())
