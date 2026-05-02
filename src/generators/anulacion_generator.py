"""
anulacion_generator.py — Motor CPE DisateQ™ v5.0
TASK-008: reescrito para estructura CPE plana de GenericAdapter v5

Estructura CPE plana de anulacion (normalize() de GenericAdapter):
    cpe['tipo_comprobante']  — '1'=factura, '2'=boleta
    cpe['serie']             — 'B001'
    cpe['numero']            — '16377'
    cpe['fecha_emision']     — 'DD-MM-YYYY'  (fecha del doc original)
    cpe['fecha_anulacion']   — 'DD-MM-YYYY'
    cpe['motivo_baja']       — str (sanitizado, sin tildes)
    cpe['es_anulacion']      — True

Formato APIFAS anulacion: clave|valor| por linea.
"""

from pathlib import Path
from typing import Dict


def _fecha(val: str) -> str:
    """Normaliza fecha a DD-MM-YYYY."""
    if not val:
        return ''
    v = str(val).strip()
    if len(v) == 10 and v[2] == '-' and v[5] == '-':
        return v
    if len(v) == 10 and v[4] == '-':
        return f"{v[8:10]}-{v[5:7]}-{v[:4]}"
    if len(v) == 8 and v.isdigit():
        return f"{v[6:8]}-{v[4:6]}-{v[:4]}"
    return v


class AnulacionGenerator:
    """Genera archivos TXT de anulacion formato APIFAS desde CPE plano v5."""

    @staticmethod
    def generate(cpe: Dict, ruc: str, output_dir: str = "output/anulaciones") -> str:
        """
        Genera archivo TXT de anulacion y retorna su ruta.

        Args:
            cpe:        CPE plano normalizado con es_anulacion=True
            ruc:        RUC del emisor
            output_dir: Directorio de salida
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        tipo_comp = str(cpe.get('tipo_comprobante', '2') or '2')
        serie     = str(cpe.get('serie',  '') or '')
        numero    = int(cpe.get('numero', 0)  or 0)

        # Nombre: A-RUC-tipo-serie-numero.txt
        filename = f"A-{ruc}-{tipo_comp}-{serie}-{numero:08d}.txt"
        filepath = output_path / filename

        fecha_emi  = _fecha(cpe.get('fecha_emision',  ''))
        fecha_anul = _fecha(cpe.get('fecha_anulacion', ''))
        motivo     = str(cpe.get('motivo_baja', 'ANULACION') or 'ANULACION')

        lines = [
            f"tipo_de_comprobante|{tipo_comp}|",
            f"serie|{serie}|",
            f"numero|{numero}|",
            f"fecha_de_emision|{fecha_emi}|",
            f"fecha_de_anulacion|{fecha_anul}|",
            f"motivo_de_baja|{motivo}|",
        ]

        filepath.write_text("\n".join(lines) + "\n", encoding='utf-8')
        return str(filepath)
