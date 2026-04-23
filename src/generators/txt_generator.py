"""
txt_generator.py
================
Generador de archivos TXT formato APIFAS — Motor CPE DisateQ™ v3.0

Genera archivos de texto plano con el formato requerido por APIFAS.
"""

from decimal import Decimal
from typing import Dict, List
from pathlib import Path


class TxtGenerator:
    """
    Genera archivos TXT en formato APIFAS.
    
    Formato:
    - Línea 1: Cabecera del comprobante
    - Líneas siguientes: Items del comprobante
    - Separador: pipe (|)
    """
    
    @staticmethod
    def generate(cpe: Dict, output_dir: str = "output") -> str:
        """
        Genera archivo TXT para un CPE normalizado.
        
        Args:
            cpe: Comprobante normalizado (desde XlsxAdapter.normalize)
            output_dir: Directorio donde guardar el archivo
        
        Returns:
            Ruta del archivo generado
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Nombre del archivo: SERIE-NUMERO.txt
        filename = f"{cpe['serie']}-{cpe['numero']:08d}.txt"
        filepath = output_path / filename
        
        # Generar contenido
        lines = []
        
        # LÍNEA 1: CABECERA
        cabecera = TxtGenerator._generar_cabecera(cpe)
        lines.append(cabecera)
        
        # LÍNEAS 2+: ITEMS
        for item in cpe['items']:
            item_line = TxtGenerator._generar_item(item)
            lines.append(item_line)
        
        # Guardar archivo
        content = "\n".join(lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(filepath)
    
    @staticmethod
    def _generar_cabecera(cpe: Dict) -> str:
        """
        Genera línea de cabecera del comprobante.
        
        Formato APIFAS (campos separados por |):
        tipo_doc|serie|numero|fecha|moneda|cliente_tipo_doc|cliente_num_doc|
        cliente_nombre|cliente_direccion|gravada|exonerada|inafecta|igv|
        icbper|total|forma_pago
        """
        cliente = cpe['cliente']
        totales = cpe['totales']
        
        campos = [
            cpe['tipo_doc'],                           # 01=Factura, 03=Boleta
            cpe['serie'],                              # F001, B001
            str(cpe['numero']),                        # 1, 2, 3...
            cpe['fecha_str'],                          # DD-MM-YYYY
            cpe['moneda'],                             # PEN, USD
            cliente['tipo_doc'],                       # 1=DNI, 6=RUC
            cliente['numero_doc'],                     # 12345678, 20123456789
            cliente['denominacion'],                   # CLIENTE S.A.C.
            cliente.get('direccion', '-'),             # Dirección o -
            TxtGenerator._format_decimal(totales['gravada']),      # 100.00
            TxtGenerator._format_decimal(totales['exonerada']),    # 0.00
            TxtGenerator._format_decimal(totales['inafecta']),     # 0.00
            TxtGenerator._format_decimal(totales['igv']),          # 18.00
            TxtGenerator._format_decimal(totales.get('icbper', 0)),  # 0.00
            TxtGenerator._format_decimal(totales['total']),        # 118.00
            cpe.get('forma_pago', 'Contado'),          # Contado, Credito
        ]
        
        return "|".join(campos)
    
    @staticmethod
    def _generar_item(item: Dict) -> str:
        """
        Genera línea de item del comprobante.
        
        Formato APIFAS (campos separados por |):
        codigo|descripcion|unspsc|unidad|cantidad|precio_sin_igv|
        precio_con_igv|subtotal_sin_igv|igv|total|afectacion_igv
        """
        campos = [
            item['codigo'],                                    # PROD001
            item['descripcion'],                               # Producto X
            item.get('unspsc', '10000000'),                   # Código UNSPSC
            item['unidad'],                                    # NIU, ZZ
            TxtGenerator._format_decimal(item['cantidad']),    # 2.00
            TxtGenerator._format_decimal(item['precio_sin_igv']),  # 10.00
            TxtGenerator._format_decimal(item['precio_con_igv']),  # 11.80
            TxtGenerator._format_decimal(item['subtotal_sin_igv']),  # 20.00
            TxtGenerator._format_decimal(item['igv']),         # 3.60
            TxtGenerator._format_decimal(item['total']),       # 23.60
            item.get('afectacion_igv', '10'),                 # 10=Gravado
        ]
        
        return "|".join(campos)
    
    @staticmethod
    def _format_decimal(value) -> str:
        """
        Formatea valores decimales a 2 decimales.
        
        Args:
            value: Decimal, float, int o string
        
        Returns:
            String con formato "0.00"
        """
        if isinstance(value, (Decimal, float, int)):
            return f"{float(value):.2f}"
        return "0.00"


# ========================================
# LECTOR DE TXT (para pruebas)
# ========================================

class TxtReader:
    """Lee archivos TXT formato APIFAS (útil para debugging)"""
    
    @staticmethod
    def read(filepath: str) -> Dict:
        """
        Lee un archivo TXT APIFAS y retorna estructura normalizada.
        
        Args:
            filepath: Ruta al archivo .txt
        
        Returns:
            Dict con estructura similar a XlsxAdapter.normalize()
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            raise ValueError("Archivo TXT vacío")
        
        # Línea 1: Cabecera
        cabecera = lines[0].strip().split('|')
        
        cpe = {
            'tipo_doc': cabecera[0],
            'serie': cabecera[1],
            'numero': int(cabecera[2]),
            'fecha_str': cabecera[3],
            'moneda': cabecera[4],
            'cliente': {
                'tipo_doc': cabecera[5],
                'numero_doc': cabecera[6],
                'denominacion': cabecera[7],
                'direccion': cabecera[8] if len(cabecera) > 8 else '-',
            },
            'totales': {
                'gravada': Decimal(cabecera[9]),
                'exonerada': Decimal(cabecera[10]),
                'inafecta': Decimal(cabecera[11]),
                'igv': Decimal(cabecera[12]),
                'icbper': Decimal(cabecera[13]) if len(cabecera) > 13 else Decimal('0'),
                'total': Decimal(cabecera[14]) if len(cabecera) > 14 else Decimal('0'),
            },
            'forma_pago': cabecera[15] if len(cabecera) > 15 else 'Contado',
            'items': []
        }
        
        # Líneas 2+: Items
        for line in lines[1:]:
            if not line.strip():
                continue
            
            campos = line.strip().split('|')
            item = {
                'codigo': campos[0],
                'descripcion': campos[1],
                'unspsc': campos[2] if len(campos) > 2 else '10000000',
                'unidad': campos[3] if len(campos) > 3 else 'NIU',
                'cantidad': float(campos[4]) if len(campos) > 4 else 0,
                'precio_sin_igv': Decimal(campos[5]) if len(campos) > 5 else Decimal('0'),
                'precio_con_igv': Decimal(campos[6]) if len(campos) > 6 else Decimal('0'),
                'subtotal_sin_igv': Decimal(campos[7]) if len(campos) > 7 else Decimal('0'),
                'igv': Decimal(campos[8]) if len(campos) > 8 else Decimal('0'),
                'total': Decimal(campos[9]) if len(campos) > 9 else Decimal('0'),
                'afectacion_igv': campos[10] if len(campos) > 10 else '10',
            }
            cpe['items'].append(item)
        
        return cpe


# ========================================
# CLI
# ========================================

def main():
    """CLI para generar TXT desde Excel"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Generador TXT APIFAS desde Excel DisateQ POS™"
    )
    parser.add_argument('excel_file', help='Archivo Excel de entrada')
    parser.add_argument('-o', '--output', default='output', help='Directorio de salida')
    
    args = parser.parse_args()
    
    try:
        # Importar adapter
        sys.path.insert(0, str(Path(__file__).parent))
        from adapters.xlsx_adapter import XlsxAdapter
        
        # Leer Excel
        print(f"📖 Leyendo Excel: {args.excel_file}")
        adapter = XlsxAdapter(args.excel_file)
        adapter.connect()
        
        comprobantes = adapter.read_pending()
        print(f"   ✅ {len(comprobantes)} comprobantes encontrados\n")
        
        # Generar TXT para cada comprobante
        for comp in comprobantes:
            items = adapter.read_items(comp)
            cpe = adapter.normalize(comp, items)
            
            filepath = TxtGenerator.generate(cpe, args.output)
            print(f"   ✅ {cpe['serie']}-{cpe['numero']:08d}.txt → {filepath}")
        
        adapter.disconnect()
        
        print(f"\n✅ {len(comprobantes)} archivos TXT generados en: {args.output}\n")
    
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
