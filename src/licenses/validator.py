import json, base64, hashlib, shutil, sys, uuid, platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


def _raiz_proyecto() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    aqui = Path(__file__).resolve()
    for p in [aqui.parent.parent.parent, aqui.parent.parent]:
        if (p / 'main.py').exists() or (p / 'config').is_dir():
            return p
    return aqui.parent.parent.parent


def _get_hardware_id() -> str:
    mac = str(uuid.getnode())
    cpu = platform.processor() or 'UNKNOWN_CPU'
    raw = f"{mac}|{cpu}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16].upper()


# Estados posibles de licencia
LIC_OK      = 'ok'
LIC_GRACIA  = 'gracia'
LIC_VENCIDA = 'vencida'
LIC_INVALIDA = 'invalida'


class LicenseValidator:
    """
    Validador de licencias offline con cifrado RSA.
    validate() retorna Tuple[str, str, Optional[Dict]]
      estado: 'ok' | 'gracia' | 'vencida' | 'invalida'
    """

    LICENSE_FILE    = "disateq_motor.lic"
    PUBLIC_KEY_FILE = "disateq_public.pem"

    def __init__(self, license_dir: Optional[Path] = None):
        raiz = _raiz_proyecto()

        if license_dir is not None:
            license_dir = Path(license_dir)
            keys_dir    = license_dir
        else:
            candidatos = [
                Path(r"C:\Program Files\DisateQ\Motor CPE\licenses"),
                Path(__file__).parent / "client_licenses",
                raiz,
            ]
            license_dir = None
            for c in candidatos:
                if (c / self.LICENSE_FILE).exists():
                    license_dir = c
                    break
            if license_dir is None:
                license_dir = Path(__file__).parent / "client_licenses"
                license_dir.mkdir(parents=True, exist_ok=True)

            keys_candidatos = [
                Path(r"C:\Program Files\DisateQ\Motor CPE\licenses"),
                Path(__file__).parent / "keys",
                raiz / "src" / "licenses" / "keys",
                raiz,
            ]
            keys_dir = None
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
                raise FileNotFoundError(f"Clave publica no encontrada: {self.pubkey_path}")
            with open(self.pubkey_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(f.read(), backend=default_backend())
        except Exception as e:
            raise RuntimeError(f"Error cargando clave publica: {e}")

    def validate(self) -> Tuple[str, str, Optional[Dict]]:
        """
        Valida la licencia actual.
        Returns: (estado, mensaje, datos_licencia)
          estado: 'ok' | 'gracia' | 'vencida' | 'invalida'
        """
        if not self.license_path.exists():
            return LIC_INVALIDA, "Licencia no encontrada. Contacte a DisateQ", None

        try:
            with open(self.license_path, 'r', encoding='utf-8') as f:
                license_file = json.load(f)

            if not all(k in license_file for k in ['data', 'signature']):
                return LIC_INVALIDA, "Licencia corrupta (campos faltantes)", None

            # Verificar firma RSA
            data_str  = json.dumps(license_file['data'], sort_keys=True)
            signature = base64.b64decode(license_file['signature'])
            try:
                self.public_key.verify(
                    signature,
                    data_str.encode('utf-8'),
                    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                    hashes.SHA256()
                )
            except Exception:
                return LIC_INVALIDA, "Licencia invalida (firma alterada)", None

            data = license_file['data']
            now  = datetime.now()

            # Verificar hardware_id
            lic_hw = data.get('hardware_id', '')
            if lic_hw:
                if lic_hw != _get_hardware_id():
                    return LIC_INVALIDA, "Licencia no valida para este equipo. Contacte a DisateQ.", None

            # Verificar vencimiento
            expiry       = datetime.fromisoformat(data['expiry_date'])
            grace_days   = int(data.get('grace_days', 0))

            if now <= expiry:
                dias_restantes = (expiry - now).days
                return LIC_OK, f"Licencia valida ({dias_restantes} dias restantes)", data

            dias_vencida = (now - expiry).days

            if grace_days > 0 and dias_vencida <= grace_days:
                return LIC_GRACIA, f"Periodo de gracia: {dias_vencida}/{grace_days} dias. Renueve su licencia.", data

            return LIC_VENCIDA, f"Licencia vencida hace {dias_vencida} dias. Contacte a DisateQ.", data

        except json.JSONDecodeError:
            return LIC_INVALIDA, "Licencia corrupta (formato invalido)", None
        except Exception as e:
            return LIC_INVALIDA, f"Error validando licencia: {e}", None

    def get_license_info(self) -> Optional[Dict]:
        if not self.license_path.exists():
            return None
        try:
            with open(self.license_path, 'r', encoding='utf-8') as f:
                return json.load(f).get('data')
        except Exception:
            return None

    def cargar_licencia(self, ruta_origen: str) -> Tuple[bool, str]:
        origen = Path(ruta_origen)
        if not origen.exists():
            return False, f"Archivo no encontrado: {ruta_origen}"
        if origen.suffix.lower() != '.lic':
            return False, "El archivo debe tener extension .lic"

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
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )

            # En gracia se puede recargar, vencida no
            expiry     = datetime.fromisoformat(license_data['data']['expiry_date'])
            now        = datetime.now()
            grace_days = int(license_data['data'].get('grace_days', 0))
            if now > expiry:
                dias_vencida = (now - expiry).days
                if not (grace_days > 0 and dias_vencida <= grace_days):
                    return False, "La licencia ya esta vencida"

            lic_hw = license_data['data'].get('hardware_id', '')
            if lic_hw and lic_hw != _get_hardware_id():
                return False, "Esta licencia no corresponde a este equipo."

        except json.JSONDecodeError:
            return False, "Archivo de licencia con formato invalido"
        except Exception:
            return False, "Licencia invalida — firma no verificada"

        try:
            self.license_dir.mkdir(parents=True, exist_ok=True)
            if Path(origen).resolve() != Path(self.license_path).resolve():
                shutil.copy2(str(origen), str(self.license_path))
            data        = license_data['data']
            cliente     = data.get('client_name', '')
            vencimiento = data.get('expiry_date', '')[:10]
            return True, f"Licencia activada para {cliente} — valida hasta {vencimiento}"
        except Exception as e:
            return False, f"Error copiando licencia: {e}"


# ================================================================
# GENERADOR DE LICENCIAS (DisateQ — uso interno)
# ================================================================

class LicenseGenerator:
    PRIVATE_KEY_FILE = "disateq_private.pem"
    PUBLIC_KEY_FILE  = "disateq_public.pem"

    @staticmethod
    def generate_keypair(key_dir: Path = Path(".")):
        key_dir      = Path(key_dir)
        private_path = key_dir / LicenseGenerator.PRIVATE_KEY_FILE
        public_path  = key_dir / LicenseGenerator.PUBLIC_KEY_FILE
        private_key  = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        public_key   = private_key.public_key()
        with open(private_path, 'wb') as f:
            f.write(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        with open(public_path, 'wb') as f:
            f.write(public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))


# ================================================================
# CLI
# ================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Licencias DisateQ Motor CPE v5.0")
    parser.add_argument('action', choices=['validate', 'generate-keys'])
    args = parser.parse_args()

    if args.action == 'validate':
        v = LicenseValidator()
        estado, mensaje, datos = v.validate()
        print(f"\n{estado.upper()}: {mensaje}")
        if datos:
            print(f"Cliente: {datos['client_name']} ({datos['client_ruc']})")
            print(f"Vence:   {datos['expiry_date'][:10]}")
            print(f"Gracia:  {datos.get('grace_days', 0)} dias")
        return 0 if estado in (LIC_OK, LIC_GRACIA) else 1

    elif args.action == 'generate-keys':
        LicenseGenerator.generate_keypair()


if __name__ == '__main__':
    sys.exit(main())
