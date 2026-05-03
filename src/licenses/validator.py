"""
validator.py
============
Sistema de Licencias Offline RSA — Motor CPE DisateQ™ v5.0
TASK-016: busqueda en raiz proyecto y exe, metodo cargar_licencia()

Validacion de licencias sin conexion a internet.
Cifrado RSA-2048 para seguridad maxima.

Flujo:
    1. DisateQ genera par de claves RSA (una vez)
    2. Cliente instala Motor + clave publica
    3. DisateQ genera licencia firmada con clave privada
    4. Motor valida licencia con clave publica local
"""

import json
import base64
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


def _raiz_proyecto() -> Path:
    """Sube hasta encontrar main.py o config/ — funciona en dev y exe."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    aqui = Path(__file__).resolve()
    for p in [aqui.parent.parent.parent, aqui.parent.parent]:
        if (p / 'main.py').exists() or (p / 'config').is_dir():
            return p
    return aqui.parent.parent.parent


class LicenseValidator:
    """
    Validador de licencias offline con cifrado RSA.

    Busca archivos en este orden:
      1. C:\\Program Files\\DisateQ\\Motor CPE\\  (produccion instalada)
      2. {raiz_proyecto}/src/licenses/client_licenses/  (desarrollo)
      3. {raiz_proyecto}/  (exe o raiz)
    """

    LICENSE_FILE    = "disateq_motor.lic"
    PUBLIC_KEY_FILE = "disateq_public.pem"

    def __init__(self, license_dir: Optional[Path] = None):
        raiz = _raiz_proyecto()

        if license_dir is not None:
            license_dir = Path(license_dir)
            keys_dir    = license_dir
        else:
            # Buscar en candidatos en orden de prioridad
            candidatos = [
                # 1. Produccion instalada
                Path(r"C:\Program Files\DisateQ\Motor CPE"),
                # 2. Desarrollo organizado
                Path(__file__).parent / "client_licenses",
                # 3. Raiz del proyecto / exe
                raiz,
            ]
            license_dir = None
            keys_dir    = None
            for c in candidatos:
                if (c / self.LICENSE_FILE).exists():
                    license_dir = c
                    break

            if license_dir is None:
                license_dir = Path(__file__).parent / "client_licenses"
                license_dir.mkdir(parents=True, exist_ok=True)

            # Buscar clave publica
            keys_candidatos = [
                Path(r"C:\Program Files\DisateQ\Motor CPE"),
                Path(__file__).parent / "keys",
                raiz / "src" / "licenses" / "keys",
                raiz,
            ]
            for c in keys_candidatos:
                if (c / self.PUBLIC_KEY_FILE).exists():
                    keys_dir = c
                    break

            if keys_dir is None:
                keys_dir = Path(__file__).parent / "keys"

        self.license_dir  = Path(license_dir)
        self.license_path = self.license_dir / self.LICENSE_FILE
        self.pubkey_path  = Path(keys_dir) / self.PUBLIC_KEY_FILE
        self.public_key   = None
        self._load_public_key()

    def _load_public_key(self):
        try:
            if not self.pubkey_path.exists():
                raise FileNotFoundError(
                    f"Clave publica no encontrada: {self.pubkey_path}"
                )
            with open(self.pubkey_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(), backend=default_backend()
                )
        except Exception as e:
            raise RuntimeError(f"Error cargando clave publica: {e}")

    def validate(self) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida la licencia actual.
        Returns: (es_valida, mensaje, datos_licencia)
        """
        if not self.license_path.exists():
            return False, "Licencia no encontrada. Contacte a DisateQ™", None

        try:
            with open(self.license_path, 'r', encoding='utf-8') as f:
                license_data = json.load(f)

            if not all(k in license_data for k in ['data', 'signature']):
                return False, "Licencia corrupta (campos faltantes)", None

            # Verificar firma RSA
            data_str  = json.dumps(license_data['data'], sort_keys=True)
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
                return False, "Licencia invalida (firma alterada)", None

            # Verificar vencimiento
            data   = license_data['data']
            expiry = datetime.fromisoformat(data['expiry_date'])
            now    = datetime.now()

            if now > expiry:
                dias = (now - expiry).days
                return False, f"Licencia vencida hace {dias} dias", data

            dias_restantes = (expiry - now).days
            return True, f"Licencia valida ({dias_restantes} dias restantes)", data

        except json.JSONDecodeError:
            return False, "Licencia corrupta (formato invalido)", None
        except Exception as e:
            return False, f"Error validando licencia: {e}", None

    def get_license_info(self) -> Optional[Dict]:
        """Retorna datos de la licencia sin validar firma."""
        if not self.license_path.exists():
            return None
        try:
            with open(self.license_path, 'r', encoding='utf-8') as f:
                return json.load(f).get('data')
        except Exception:
            return None

    def cargar_licencia(self, ruta_origen: str) -> Tuple[bool, str]:
        """
        TASK-016 — Copia un archivo .lic al directorio de licencias
        y lo valida antes de activarlo.

        Args:
            ruta_origen: Ruta al archivo .lic seleccionado por el usuario

        Returns:
            (exito, mensaje)
        """
        origen = Path(ruta_origen)
        if not origen.exists():
            return False, f"Archivo no encontrado: {ruta_origen}"
        if origen.suffix.lower() != '.lic':
            return False, "El archivo debe tener extension .lic"

        # Validar antes de copiar
        try:
            with open(origen, 'r', encoding='utf-8') as f:
                license_data = json.load(f)

            if not all(k in license_data for k in ['data', 'signature']):
                return False, "Archivo de licencia invalido (campos faltantes)"

            data_str  = json.dumps(license_data['data'], sort_keys=True)
            signature = base64.b64decode(license_data['signature'])
            self.public_key.verify(
                signature,
                data_str.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            # Verificar vencimiento
            expiry = datetime.fromisoformat(license_data['data']['expiry_date'])
            if datetime.now() > expiry:
                return False, "La licencia ya esta vencida"

        except json.JSONDecodeError:
            return False, "Archivo de licencia con formato invalido"
        except Exception:
            return False, "Licencia invalida — firma no verificada"

        # Copiar al directorio de licencias
        try:
            self.license_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(origen), str(self.license_path))
            data      = license_data['data']
            cliente   = data.get('client_name', '')
            vencimiento = data.get('expiry_date', '')[:10]
            return True, f"Licencia activada para {cliente} — valida hasta {vencimiento}"
        except Exception as e:
            return False, f"Error copiando licencia: {e}"


# ================================================================
# GENERADOR DE LICENCIAS (DisateQ™ — uso interno)
# ================================================================

class LicenseGenerator:
    """
    Generador de licencias RSA — Solo para uso interno DisateQ™
    NO distribuir al cliente.
    """

    PRIVATE_KEY_FILE = "disateq_private.pem"
    PUBLIC_KEY_FILE  = "disateq_public.pem"

    @staticmethod
    def generate_keypair(key_dir: Path = Path(".")):
        key_dir      = Path(key_dir)
        private_path = key_dir / LicenseGenerator.PRIVATE_KEY_FILE
        public_path  = key_dir / LicenseGenerator.PUBLIC_KEY_FILE

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        with open(private_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        with open(public_path, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))

        print(f"Par de claves generado:")
        print(f"   Privada: {private_path} (MANTENER SEGURA)")
        print(f"   Publica: {public_path} (distribuir con Motor)")

    @staticmethod
    def create_license(
        client_name: str,
        client_ruc: str,
        expiry_days: int,
        max_docs_month: int = 999999,
        private_key_path: Path = Path("disateq_private.pem"),
        output_path: Path = Path("disateq_motor.lic")
    ) -> Dict:
        with open(private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

        now    = datetime.now()
        expiry = now + timedelta(days=expiry_days)

        license_data = {
            'client_name':     client_name,
            'client_ruc':      client_ruc,
            'product':         'Motor CPE DisateQ™ v5.0',
            'issue_date':      now.isoformat(),
            'expiry_date':     expiry.isoformat(),
            'max_docs_month':  max_docs_month,
            'version':         '5.0',
        }

        data_str  = json.dumps(license_data, sort_keys=True)
        signature = private_key.sign(
            data_str.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        license_file = {
            'data':      license_data,
            'signature': base64.b64encode(signature).decode('utf-8'),
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(license_file, f, indent=2, ensure_ascii=False)

        print(f"Licencia generada: {output_path}")
        print(f"   Cliente: {client_name} ({client_ruc})")
        print(f"   Valida hasta: {expiry.strftime('%Y-%m-%d')}")
        max_str = "ilimitado" if max_docs_month >= 999999 else str(max_docs_month)
        print(f"   Max docs/mes: {max_str}")

        return license_data


# ================================================================
# CLI
# ================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Licencias DisateQ™ Motor CPE v5.0")
    parser.add_argument('action', choices=['validate', 'generate-keys', 'create-license'])
    parser.add_argument('--client-name')
    parser.add_argument('--client-ruc')
    parser.add_argument('--days',     type=int, default=365)
    parser.add_argument('--max-docs', type=int, default=999999)
    args = parser.parse_args()

    if args.action == 'validate':
        v = LicenseValidator()
        valida, mensaje, datos = v.validate()
        print(f"\n{'OK' if valida else 'ERROR'}: {mensaje}")
        if datos:
            print(f"Cliente: {datos['client_name']} ({datos['client_ruc']})")
            print(f"Vence: {datos['expiry_date'][:10]}")
        return 0 if valida else 1

    elif args.action == 'generate-keys':
        LicenseGenerator.generate_keypair()

    elif args.action == 'create-license':
        if not args.client_name or not args.client_ruc:
            print("Error: --client-name y --client-ruc requeridos")
            return 1
        LicenseGenerator.create_license(
            client_name=args.client_name, client_ruc=args.client_ruc,
            expiry_days=args.days, max_docs_month=args.max_docs
        )


if __name__ == '__main__':
    import sys
    sys.exit(main())
