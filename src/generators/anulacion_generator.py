"""
anulacion_generator.py
======================
Generador TXT formato APIFAS para anulaciones (Comunicacion de Baja)
Motor CPE DisateQ™ v4.0

Formato:
tipo_de_comprobante|N|
serie|XXXX|
numero|NNNNNN|
fecha_de_emision|DD-MM-YYYY|
fecha_de_anulacion|DD-MM-YYYY|
motivo_de_baja|DESCRIPCION|
"""

from pathlib import Path
from typing import Dict


class AnulacionGenerator:

    @staticmethod
    def generate(cpe: Dict, ruc: str, output_dir: str = "output/anulaciones") -> str:
        """
        Genera archivo TXT de anulacion formato APIFAS.

        Args:
            cpe:        Resultado de normalize_anulacion()
            ruc:        RUC del emisor
            output_dir: Directorio de salida

        Returns:
            Ruta del archivo generado
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        cab    = cpe['comprobante']
        serie  = cab['serie']
        numero = int(cab['numero'])

        # Nombre: A-RUC-tipo-serie-numero.txt
        tipo_num = '2' if cab['tipo_doc'] == '03' else '1'
        filename = f"A-{ruc}-{tipo_num}-{serie}-{numero:08d}.txt"
        filepath = output_path / filename

        lines = [
            f"tipo_de_comprobante|{tipo_num}|",
            f"serie|{serie}|",
            f"numero|{numero}|",
            f"fecha_de_emision|{cab['fecha_emision']}|",
            f"fecha_de_anulacion|{cab['fecha_anulacion']}|",
            f"motivo_de_baja|{cab['motivo']}|",
        ]

        filepath.write_text("\n".join(lines) + "\n", encoding='utf-8')
        return str(filepath)
