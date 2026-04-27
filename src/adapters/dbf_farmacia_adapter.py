"""
dbf_farmacia_adapter.py
=======================
Adaptador DBF para sistema legacy de farmacia
"""

from dbfread import DBF
from pathlib import Path
from typing import List, Dict
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.base_adapter import BaseAdapter


class DbfFarmaciaAdapter(BaseAdapter):

    def __init__(self, data_path: str):
        super().__init__()
        self.data_path      = Path(data_path)
        self.envios_path    = self.data_path / 'enviosffee.dbf'
        self.detalle_path   = self.data_path / 'detalleventa.dbf'
        self.productos_path = self.data_path / 'productox.dbf'
        self.factura_path   = self.data_path / 'factura.dbf'
        self.productos_cache = {}
        self.detalle_cache   = {}
        self.factura_cache   = {}   # key: (TIPO_FACTU, SERIE_FACT, NUMERO_FAC) -> row

    def _decode(self, val) -> str:
        if val is None:
            return ''
        if isinstance(val, bytes):
            return val.decode('latin1').strip()
        return str(val).strip()

    def connect(self):
        for p in [self.envios_path, self.detalle_path, self.productos_path]:
            if not p.exists():
                raise FileNotFoundError(f"No existe: {p}")
        self._cargar_productos()
        self._cargar_detalles()
        self._cargar_facturas()
        print(f"✅ Conectado a DBFs farmacia")
        print(f"   Productos: {len(self.productos_cache)}")
        print(f"   Detalles: {len(self.detalle_cache)}")

    def disconnect(self):
        self.productos_cache.clear()
        self.detalle_cache.clear()
        self.factura_cache.clear()

    def _cargar_productos(self):
        dbf = DBF(str(self.productos_path), encoding='latin1', ignore_missing_memofile=True, raw=True)
        for record in dbf:
            try:
                codigo = self._decode(record.get('CODIGO_PRO', '')).strip()
                if codigo:
                    self.productos_cache[codigo] = {
                        'descripcion':  self._decode(record.get('DESCRIPCIO', '')),
                        'presentacion': self._decode(record.get('PRESENTA_P', '')),
                        'unspsc':       self._decode(record.get('UNSPSC', '10000000')) or '10000000'
                    }
            except (ValueError, KeyError):
                continue

    def _cargar_detalles(self):
        dbf = DBF(str(self.detalle_path), encoding='latin1', ignore_missing_memofile=True, raw=True)
        for record in dbf:
            try:
                tipo   = self._decode(record.get('TIPO_FACTU', ''))
                serie  = self._decode(record.get('SERIE_FACT', ''))
                numero = self._decode(record.get('NUMERO_FAC', ''))
                key = (tipo, serie, numero)
                if key not in self.detalle_cache:
                    self.detalle_cache[key] = []
                self.detalle_cache[key].append(record)
            except (ValueError, KeyError):
                continue

    def _cargar_facturas(self):
        """Carga factura.dbf en memoria para JOIN con enviosffee."""
        if not self.factura_path.exists():
            return
        try:
            dbf = DBF(str(self.factura_path), encoding='latin1', ignore_missing_memofile=True, raw=True)
            for record in dbf:
                try:
                    tipo   = self._decode(record.get('TIPO_FACTU', ''))
                    serie  = self._decode(record.get('SERIE_FACT', ''))
                    numero = self._decode(record.get('NUMERO_FAC', ''))
                    key = (tipo, serie, numero)
                    self.factura_cache[key] = record
                except (ValueError, KeyError):
                    continue
        except Exception as e:
            print(f"⚠️  No se pudo cargar factura.dbf: {e}")

    def _get_total_factura(self, tipo: str, serie: str, numero: str) -> float:
        """
        Obtiene el total real del comprobante desde factura.dbf.
        Usa REAL_FACTU (total con IGV) como campo principal.
        """
        key = (tipo, serie, numero)
        row = self.factura_cache.get(key)
        if not row:
            return 0.0
        # REAL_FACTU = total con IGV (precio de venta al público)
        # MONTO_FACT = monto sin IGV
        # PAGO_FACTU = monto pagado
        for campo in ('REAL_FACTU', 'PAGO_FACTU', 'MONTO_FACT'):
            val = row.get(campo)
            if val is not None:
                try:
                    v = float(self._decode(val))
                    if v > 0:
                        return round(v, 2)
                except (ValueError, TypeError):
                    continue
        return 0.0

    def read_pending(self) -> List[Dict]:
        dbf = DBF(str(self.envios_path), encoding='latin1', ignore_missing_memofile=True, raw=True)
        pendientes = []
        for record in dbf:
            try:
                flag = self._decode(record.get('FLAG_ENVIO', b'0'))
                if flag == '2':
                    decoded = {k: self._decode(v) for k, v in record.items()}
                    # Enriquecer con total desde factura.dbf
                    tipo   = decoded.get('TIPO_FACTU', '')
                    serie  = decoded.get('SERIE_FACT', '')
                    numero = decoded.get('NUMERO_FAC', '')
                    decoded['_TOTAL_REAL'] = self._get_total_factura(tipo, serie, numero)
                    pendientes.append(decoded)
            except (ValueError, KeyError):
                continue
        print(f"📋 Pendientes encontrados: {len(pendientes)}")
        return pendientes

    def read_items(self, comprobante: Dict) -> List[Dict]:
        tipo   = comprobante.get('TIPO_FACTU', '').strip()
        serie  = comprobante.get('SERIE_FACT', '').strip()
        numero = comprobante.get('NUMERO_FAC', '').strip()
        key    = (tipo, serie, numero)
        items  = self.detalle_cache.get(key, [])
        items_enriquecidos = []
        for item in items:
            codigo   = self._decode(item.get('CODIGO_PRO', '')).strip()
            producto = self.productos_cache.get(codigo, {})
            item_dec = {k: self._decode(v) for k, v in item.items()}
            item_dec['_producto_desc'] = producto.get('descripcion', 'PRODUCTO SIN DESCRIPCION')
            item_dec['_producto_pres'] = producto.get('presentacion', '')
            item_dec['_unspsc']        = producto.get('unspsc', '10000000')
            items_enriquecidos.append(item_dec)
        return items_enriquecidos

    def normalize(self, source_data: Dict, source_items: List[Dict]) -> Dict:
        tipo_dbf = source_data.get('TIPO_FACTU', 'B').strip().upper()
        tipo_cpe = '03' if tipo_dbf == 'B' else '01'
        serie    = source_data.get('SERIE_FACT', '').strip()
        numero   = self._safe_int(source_data.get('NUMERO_FAC', '0'))

        fecha = ''
        if source_items:
            fecha = self._fmt_fecha(source_items[0].get('FECHA_FACT', ''))
        if not fecha:
            fecha = self._fmt_fecha(source_data.get('FECHA_DOCU', ''))

        cli_tipo   = source_data.get('TIPO_DOCUM', '1').strip() or '1'
        cli_doc    = source_data.get('NUMERO_DOC', '00000000').strip() or '00000000'
        cli_nombre = source_data.get('RAZON_SOCI', 'CLIENTES VARIOS').strip() or 'CLIENTES VARIOS'

        items_normalizados = []
        total_gravada = total_exonerada = total_igv = total_general = 0.0

        for idx, item in enumerate(source_items, 1):
            cantidad_p  = self._safe_float(item.get('CANTIDAD_P', '0'))
            fraccion_p  = self._safe_float(item.get('FRACCION_P', '0'))
            cantidad    = cantidad_p if cantidad_p > 0 else fraccion_p
            unidad_item = 'NIU' if cantidad_p > 0 else 'TAB'
            precio_unit = self._safe_float(item.get('PRECIO_UNI', '0'))
            monto_item  = self._safe_float(item.get('MONTO_PEDI', '0'))
            igv_item_r  = self._safe_float(item.get('IGV_PEDIDO', '0'))
            total_item  = self._safe_float(item.get('REAL_PEDID', '0'))

            prod_e_raw = item.get('PRODUCTO_E', '0')
            try:
                prod_e_val = float(prod_e_raw.strip()) if prod_e_raw.strip() else 0.0
            except:
                prod_e_val = 0.0
            es_exonerado = prod_e_val > 0
            afectacion   = '20' if es_exonerado else '10'

            if es_exonerado:
                total_exonerada += total_item
            else:
                total_gravada += monto_item
                total_igv     += igv_item_r
            total_general += total_item

            valor_unit       = round(monto_item / cantidad, 8) if cantidad else 0.0
            precio_unit_real = round(total_item / cantidad, 8) if cantidad else precio_unit

            items_normalizados.append({
                'item':            idx,
                'codigo':          item.get('CODIGO_PRO', '').strip(),
                'descripcion':     item.get('_producto_desc', 'PRODUCTO'),
                'cantidad':        cantidad,
                'unidad':          unidad_item,
                'precio_unitario': precio_unit_real,
                'valor_unitario':  valor_unit,
                'subtotal_sin_igv': round(monto_item, 2),
                'igv':             round(igv_item_r, 2),
                'total':           round(total_item, 2),
                'afectacion_igv':  afectacion,
                'unspsc':          item.get('_unspsc', '10000000')
            })

        return {
            'comprobante': {
                'tipo_doc':      tipo_cpe,
                'serie':         serie,
                'numero':        numero,
                'fecha_emision': fecha,
                'moneda':        'PEN'
            },
            'cliente': {
                'tipo_doc':    cli_tipo,
                'numero_doc':  cli_doc,
                'denominacion': cli_nombre,
                'direccion':   source_data.get('DIRECCION', '').strip()
            },
            'totales': {
                'gravada':    round(total_gravada, 2),
                'exonerada':  round(total_exonerada, 2),
                'inafecta':   0.0,
                'igv':        round(total_igv, 2),
                'total':      round(total_general, 2)
            },
            'items': items_normalizados
        }

    def _fmt_fecha(self, val: str) -> str:
        v = val.strip()
        if len(v) == 8 and v.isdigit():
            return f"{v[6:8]}-{v[4:6]}-{v[:4]}"
        if len(v) == 10 and v[4] == '-':
            return f"{v[8:10]}-{v[5:7]}-{v[:4]}"
        return v

    def _safe_str(self, val) -> str:
        return self._decode(val)

    def _safe_int(self, val) -> int:
        try:
            return int(self._decode(val)) if val else 0
        except:
            return 0

    def _safe_float(self, val) -> float:
        try:
            return float(self._decode(val)) if val else 0.0
        except:
            return 0.0

    def read_pending_anulaciones(self):
        anulaciones_path = self.data_path / 'notacredito.dbf'
        if not anulaciones_path.exists():
            print("Advertencia: notacredito.dbf no encontrado")
            return []
        motivos = {}
        try:
            mot_path = self.data_path / 'motivonota.dbf'
            if mot_path.exists():
                from dbfread import DBF as _DBF
                for r in _DBF(str(mot_path), encoding='latin1', ignore_missing_memofile=True, raw=True):
                    codigo = self._decode(r.get('CODIGO', '')).strip()
                    motivo = self._decode(r.get('MOTIVO', '')).strip()
                    motivos[codigo] = motivo
        except:
            pass
        motivos.setdefault('01', 'Anulacion de la operacion')
        from dbfread import DBF as _DBF2
        dbf = _DBF2(str(anulaciones_path), encoding='latin1', ignore_missing_memofile=True, raw=True)
        pendientes = []
        for record in dbf:
            try:
                pendiente = self._decode(record.get('PENDIENTE_', b'0'))
                tipo_mov  = self._decode(record.get('TIPO_MOVIM', b'0'))
                if pendiente == '2' and tipo_mov == '2':
                    dec = {k: self._decode(v) for k, v in record.items()}
                    codigo_motivo      = dec.get('TIPO_MOTIV', '01').strip()
                    dec['_motivo_desc'] = motivos.get(codigo_motivo, 'Anulacion de la operacion')
                    pendientes.append(dec)
            except:
                continue
        print(f"Anulaciones pendientes: {len(pendientes)}")
        return pendientes

    def normalize_anulacion(self, record) -> dict:
        tipo_dbf  = record.get('TIPO_FACTU', 'B').strip().upper()
        tipo_cpe  = '03' if tipo_dbf == 'B' else '01'
        serie_raw = record.get('SERIE_NOTA', '').strip()
        prefijo   = {'01': 'F', '03': 'B'}.get(tipo_cpe, 'B')
        serie     = prefijo + serie_raw
        numero    = self._safe_int(record.get('NUMERO_NOT', '0'))
        fecha_raw = record.get('FECHA_NOTA', '').strip()
        fecha     = self._fmt_fecha(fecha_raw)
        motivo    = record.get('_motivo_desc', 'Anulacion de la operacion')
        serie_orig  = record.get('SERIE_FACT', '').strip()
        numero_orig = self._safe_int(record.get('NUMERO_FAC', '0'))
        from datetime import date
        return {
            'tipo': 'anulacion',
            'comprobante': {
                'tipo_doc':        tipo_cpe,
                'serie':           serie,
                'numero':          numero,
                'fecha_emision':   fecha,
                'fecha_anulacion': date.today().strftime('%d-%m-%Y'),
                'motivo':          motivo,
                'serie_original':  serie_orig,
                'numero_original': numero_orig,
            }
        }
