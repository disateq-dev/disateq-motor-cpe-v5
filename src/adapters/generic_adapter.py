# src/adapters/generic_adapter.py
# DisateQ Motor CPE v5.0
# FIX-DBF-01: SafeFieldParser — parseN + parseF para floats nulos b'\x00\x00'
# TASK-008: encoding cp850, _norm_num para NUMERO_FAC en todos los caches
# ─────────────────────────────────────────────────────────────────────────────

import os
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from src.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

TIPO_CPE_MAP = {
    'F': '1',
    'B': '2',
}

DOC_MOD_TIPO_MAP = {
    'F': '1',
    'B': '2',
}

CLIENTE_TIPO_DOC_MAP = {
    0: '-',
    1: '1',
    6: '6',
}


def _norm_num(numero: str) -> str:
    """
    Normaliza NUMERO_FAC quitando ceros a la izquierda.
    Resuelve mismatch entre tablas:
      enviosffee:    '00016377'   (8 chars)
      factura:       '0000016377' (10 chars)
      detalleventa:  '0000016377' (10 chars)
    Normalizando a '16377' en todos los caches el join matchea.
    """
    return numero.lstrip('0') or '0'


def _safe_read_dbf(path: str, encoding: str = 'cp850') -> List[Dict]:
    """
    Lee un DBF completo con manejo de fechas, enteros y floats nulos.
    Retorna lista de dicts. Nunca lanza excepción.
    """
    from dbfread import DBF as _DBF, FieldParser

    class SafeFieldParser(FieldParser):

        def parseD(self, field, data):
            """Fecha: retorna None si el valor es nulo o inválido."""
            try:
                if not data or data.strip() == b'' or b'\x00' in data:
                    return None
                return super().parseD(field, data)
            except Exception:
                return None

        def parseN(self, field, data):
            """Entero/decimal: retorna None si el valor es nulo o vacío."""
            try:
                if not data or data.strip() == b'' or b'\x00' in data:
                    return None
                return super().parseN(field, data)
            except Exception:
                return None

        def parseF(self, field, data):
            """Float: retorna None si el valor es nulo (b'\\x00\\x00' o vacío)."""
            try:
                if not data or data.strip() == b'' or b'\x00' in data:
                    return None
                return super().parseF(field, data)
            except Exception:
                return None

    registros = []
    try:
        tabla = _DBF(
            path,
            encoding=encoding,
            parserclass=SafeFieldParser,
            ignore_missing_memofile=True,
            raw=False,
        )
        for r in tabla:
            try:
                registros.append(dict(r))
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"[DBF] Error leyendo {path}: {e}")
    return registros


class GenericAdapter(BaseAdapter):
    """
    Adaptador universal — lee cualquier fuente via contrato YAML.
    DBF optimizado: items en cache, parser de fechas y floats robusto.
    """

    def __init__(self, contrato: dict, config_cliente: dict):
        super().__init__(contrato, config_cliente)
        self.source_type = contrato['source']['type'].lower()
        self.source_path = contrato['source']['path']
        self.encoding    = contrato['source'].get('encoding', 'latin-1')

        # Caches — se cargan una sola vez por sesión
        self._cache_factura:   Optional[Dict] = None
        self._cache_productos: Optional[Dict] = None
        self._cache_motivos:   Optional[Dict] = None
        self._cache_items:     Optional[Dict] = None

    # ═════════════════════════════════════════════════════════════════════════
    # INTERFAZ PUBLICA
    # ═════════════════════════════════════════════════════════════════════════

    def read_pending(self) -> List[Dict[str, Any]]:
        if self.source_type == 'dbf':
            return self._read_pending_dbf()
        if self.source_type == 'sqlite':
            return self._read_pending_sqlite()
        raise NotImplementedError(f"read_pending: '{self.source_type}' no implementado")

    def read_items(self, comprobante: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.source_type == 'dbf':
            return self._read_items_dbf(comprobante)
        if self.source_type == 'sqlite':
            return self._read_items_sqlite(comprobante)
        raise NotImplementedError(f"read_items: '{self.source_type}' no implementado")

    def normalize(self, comprobante: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
        tipo = comprobante.get('_tipo_registro', 'comprobante')
        if tipo == 'comprobante':
            return self._normalize_comprobante(comprobante, items)
        return self._normalize_nota(comprobante, items)

    def write_flag(self, comprobante: Dict[str, Any], estado: str) -> None:
        if self.source_type == 'sqlite':
            self._write_flag_sqlite(comprobante, estado)
            return
        if self.source_type != 'dbf':
            return
        if comprobante.get('_tipo_registro') == 'comprobante':
            self._write_flag_enviosffee(comprobante, estado)

    # ═════════════════════════════════════════════════════════════════════════
    # DBF — READ PENDING
    # ═════════════════════════════════════════════════════════════════════════

    def _read_pending_dbf(self) -> List[Dict[str, Any]]:
        comprobantes = self._read_pending_comprobantes_dbf()
        notas = []
        if 'notas' in self.contrato:
            try:
                notas = self._read_pending_notas_dbf()
            except Exception as e:
                logger.warning(f"[GenericAdapter] notas: {e}")
        total = len(comprobantes) + len(notas)
        logger.info(f"[{self.contrato['cliente_id']}] Pendientes: {len(comprobantes)} comp + {len(notas)} notas = {total}")
        return comprobantes + notas

    def _read_pending_comprobantes_dbf(self) -> List[Dict[str, Any]]:
        cfg        = self.contrato['comprobantes']
        tabla_path = self._tabla_path(cfg['tabla'])
        flag_campo = cfg['flag_lectura']['campo']
        flag_valor = cfg['flag_lectura']['valor']

        pendientes = []
        for r in _safe_read_dbf(tabla_path, self.encoding):
            if r.get(flag_campo) == flag_valor:
                r['_tipo_registro'] = 'comprobante'
                r['_tabla_origen']  = cfg['tabla']
                pendientes.append(r)
        return pendientes

    def _read_pending_notas_dbf(self) -> List[Dict[str, Any]]:
        cfg        = self.contrato['notas']
        tabla_path = self._tabla_path(cfg['tabla'])
        fl         = cfg['flag_lectura']
        campo_pend  = fl['campo_pendiente']
        valor_pend  = str(fl['valor_pendiente'])
        campo_movim = fl['campo_tipo_movim']
        valor_movim = fl['valor_tipo_movim']

        pendientes = []
        for r in _safe_read_dbf(tabla_path, self.encoding):
            if (str(r.get(campo_pend, '')).strip() == valor_pend and
                    r.get(campo_movim) == valor_movim):
                r['_tipo_registro'] = 'nota'
                r['_tabla_origen']  = cfg['tabla']
                pendientes.append(r)
        return pendientes

    # ═════════════════════════════════════════════════════════════════════════
    # DBF — READ ITEMS (con cache)
    # ═════════════════════════════════════════════════════════════════════════

    def _read_items_dbf(self, comprobante: Dict[str, Any]) -> List[Dict[str, Any]]:
        tipo   = str(comprobante.get('TIPO_FACTU', '')).strip()
        serie  = str(comprobante.get('SERIE_FACT', '')).strip()
        numero = _norm_num(str(comprobante.get('NUMERO_FAC', '')).strip())

        cache = self._load_items_cache()
        items = cache.get((tipo, serie, numero), [])
        return sorted(items, key=lambda x: x.get('ITEM_FACTU', 0))

    def _load_items_cache(self) -> Dict:
        """
        Carga TODOS los items de detalleventa.dbf una sola vez
        y los indexa por (TIPO_FACTU, SERIE_FACT, NUMERO_FAC).
        """
        if self._cache_items is not None:
            return self._cache_items

        cfg        = self.contrato['items']
        tabla_path = self._tabla_path(cfg['tabla'])

        self._cache_items = {}
        total = 0
        for r in _safe_read_dbf(tabla_path, self.encoding):
            tipo   = str(r.get('TIPO_FACTU', '')).strip()
            serie  = str(r.get('SERIE_FACT', '')).strip()
            numero = _norm_num(str(r.get('NUMERO_FAC', '')).strip())
            key    = (tipo, serie, numero)
            if key not in self._cache_items:
                self._cache_items[key] = []
            self._cache_items[key].append(r)
            total += 1

        logger.info(f"Cache items: {total} registros → {len(self._cache_items)} grupos")
        return self._cache_items

    # ═════════════════════════════════════════════════════════════════════════
    # NORMALIZE — COMPROBANTE
    # ═════════════════════════════════════════════════════════════════════════

    def _normalize_comprobante(self, raw: Dict[str, Any], items_raw: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.source_type == 'sqlite':
            return self._normalize_comprobante_sqlite(raw, items_raw)

        tipo_factu = str(raw.get('TIPO_FACTU', '')).strip()
        serie_fact = str(raw.get('SERIE_FACT', '')).strip()
        numero_raw = str(raw.get('NUMERO_FAC', '')).strip()

        fac = self._get_factura(tipo_factu, serie_fact, numero_raw)

        serie_completa = f"{tipo_factu}{serie_fact}"
        tipo_cpe       = TIPO_CPE_MAP.get(tipo_factu, '2')
        numero_limpio  = numero_raw.lstrip('0') or '0'

        cliente_tipo_doc, cliente_num_doc, cliente_nombre = self._cliente_data(fac)
        fecha_emision = self._fmt_date(raw.get('FECHA_DOCU'))

        factura_ex    = int(raw.get('FACTURA_EX') or 0)
        total_real    = float(fac.get('REAL_FACTU') or 0)
        total_gravada = float(fac.get('MONTO_FACT') or 0)
        total_igv     = float(fac.get('IGV_FACTUR') or 0)
        icbper        = float(fac.get('IMPORTE_IC') or 0)

        if factura_ex == 1:
            total_exonerada = total_real
            total_gravada   = 0.0
            total_igv       = 0.0
        else:
            total_exonerada = 0.0

        productos  = self._load_productos_cache()
        items_norm = [self._normalize_item(i, productos, factura_ex) for i in items_raw]

        return {
            'tipo_comprobante':  tipo_cpe,
            'serie':             serie_completa,
            'numero':            numero_limpio,
            'es_nota':           False,
            'es_anulacion':      False,
            'ruc_emisor':        self.config_cliente.get('ruc', ''),
            'razon_social':      self.config_cliente.get('razon_social', ''),
            'cliente_tipo_doc':  cliente_tipo_doc,
            'cliente_num_doc':   cliente_num_doc,
            'cliente_nombre':    cliente_nombre,
            'cliente_direccion': '',
            'cliente_email':     str(fac.get('EMAIL_CLIE', '') or '').strip(),
            'fecha_emision':     fecha_emision,
            'fecha_vencimiento': '',
            'total_gravada':          round(total_gravada,   8),
            'total_exonerada':        round(total_exonerada, 8),
            'total_inafecta':         0.0,
            'total_igv':              round(total_igv,       8),
            'total_impuestos_bolsas': round(icbper,          8),
            'total_gratuita':         0.0,
            'total':                  round(total_real,      8),
            'items':             items_norm,
            'doc_mod_tipo':      None,
            'doc_mod_serie':     None,
            'doc_mod_numero':    None,
            'tipo_nota_credito': None,
            'fecha_anulacion':   None,
            'motivo_baja':       None,
            '_raw':              raw,
        }

    def _normalize_comprobante_sqlite(self, raw: Dict[str, Any], items_raw: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Normaliza un comprobante desde SQLite usando campos del contrato."""
        campos = self.contrato['comprobantes'].get('campos', {})

        def g(campo_cpe, default=''):
            campo_real = campos.get(campo_cpe, campo_cpe)
            return raw.get(campo_real, raw.get(campo_cpe, default))

        tipo_raw   = str(g('tipo_doc', 'B')).strip()
        serie      = str(g('serie', '')).strip()
        numero_raw = str(g('numero', '0')).strip()

        # Mapear tipo local a codigo SUNAT
        tipo_map  = {'F': '1', 'B': '2', 'f': '1', 'b': '2',
                     '01': '1', '03': '2', '1': '1', '2': '2'}
        tipo_cpe  = tipo_map.get(tipo_raw, '2')
        numero    = numero_raw.lstrip('0') or '0'

        factura_ex    = int(raw.get(campos.get('exonerado', 'exonerado'), 0) or 0)
        total_real    = float(g('total', 0) or 0)
        total_gravada = float(g('subtotal', 0) or 0)
        total_igv     = float(g('igv', 0) or 0)

        if factura_ex == 1:
            total_exonerada = total_real
            total_gravada   = 0.0
            total_igv       = 0.0
        else:
            total_exonerada = 0.0

        # Cliente
        tipo_cli_raw = int(raw.get(campos.get('tipo_cliente', 'tipo_cli'), 0) or 0)
        cli_tipo_map = {0: '-', 1: '1', 6: '6'}
        cli_tipo_doc = cli_tipo_map.get(tipo_cli_raw, '-')
        cli_num_doc  = str(g('ruc_cliente', '') or '').strip()
        cli_nombre   = str(g('nombre_cliente', '') or '').strip()

        cfg_varios = self.contrato.get('cliente_varios', {})
        if not cli_num_doc or cli_num_doc == '0':
            cli_tipo_doc = cfg_varios.get('tipo_doc', '-')
            cli_num_doc  = cfg_varios.get('num_doc', '00000000')
            cli_nombre   = cfg_varios.get('nombre', 'CLIENTE VARIOS')

        fecha_emision = self._fmt_date(g('fecha', ''))

        productos  = self._load_productos_cache()
        items_norm = [self._normalize_item_sqlite(i, productos, factura_ex) for i in items_raw]

        return {
            'tipo_comprobante':       tipo_cpe,
            'serie':                  serie,
            'numero':                 numero,
            'es_nota':                False,
            'es_anulacion':           False,
            'ruc_emisor':             self.config_cliente.get('ruc', ''),
            'razon_social':           self.config_cliente.get('razon_social', ''),
            'cliente_tipo_doc':       cli_tipo_doc,
            'cliente_num_doc':        cli_num_doc,
            'cliente_nombre':         cli_nombre,
            'cliente_direccion':      '',
            'cliente_email':          '',
            'fecha_emision':          fecha_emision,
            'fecha_vencimiento':      '',
            'total_gravada':          round(total_gravada,   8),
            'total_exonerada':        round(total_exonerada, 8),
            'total_inafecta':         0.0,
            'total_igv':              round(total_igv,       8),
            'total_impuestos_bolsas': 0.0,
            'total_gratuita':         0.0,
            'total':                  round(total_real,      8),
            'items':                  items_norm,
            'doc_mod_tipo':           None,
            'doc_mod_serie':          None,
            'doc_mod_numero':         None,
            'tipo_nota_credito':      None,
            'fecha_anulacion':        None,
            'motivo_baja':            None,
            '_raw':                   raw,
        }

    def _normalize_item_sqlite(self, raw: Dict[str, Any], productos: Dict, factura_ex: int) -> Dict[str, Any]:
        """Normaliza un item desde SQLite."""
        codigo      = str(raw.get('cod_prod', '') or '').strip()
        producto    = productos.get(codigo, {})

        cantidad    = float(raw.get('cantidad',    0) or 0)
        subtotal    = float(raw.get('subtotal',    0) or 0)
        igv_item    = float(raw.get('igv',         0) or 0)
        total_item  = float(raw.get('total',       0) or 0)
        precio_igv  = float(raw.get('precio_igv',  0) or 0)
        precio_uni  = float(raw.get('precio_uni',  0) or 0)

        val_unit    = round(subtotal / cantidad, 8) if cantidad else 0.0

        desc        = str(raw.get('descripcion', '') or producto.get('descripcion', '')).strip()
        cod_sunat   = str(producto.get('cod_sunat', '10000000') or '10000000').strip()
        if len(cod_sunat) < 8:
            cod_sunat = '10000000'

        exonerado   = int(raw.get('exonerado', 0) or producto.get('exonerado', 0) or 0)
        tipo_igv    = 2 if (factura_ex == 1 or exonerado == 1) else 1

        return {
            'unidad':          'NIU',
            'codigo':          codigo,
            'descripcion':     desc,
            'cantidad':        cantidad,
            'valor_unitario':  val_unit,
            'precio_unitario': precio_igv or precio_uni,
            'valor_total':     round(subtotal,   8),
            'tipo_igv':        tipo_igv,
            'igv':             round(igv_item,   8),
            'total':           round(total_item, 8),
            'cod_sunat':       cod_sunat,
            'icbper':          0.0,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # NORMALIZE — NOTA / ANULACION
    # ═════════════════════════════════════════════════════════════════════════

    def _normalize_nota(self, raw: Dict[str, Any], items_raw: List[Dict[str, Any]]) -> Dict[str, Any]:
        cfg_notas          = self.contrato['notas']
        tipo_registro_nota = cfg_notas.get('tipo_registro', 'anulacion')
        es_anulacion       = (tipo_registro_nota == 'anulacion')

        tipo_factu_mod = str(raw.get('TIPO_FACTU', '')).strip()
        serie_mod_raw  = str(raw.get('SERIE_FACT', '')).strip()
        numero_mod_raw = str(raw.get('NUMERO_FAC', '')).strip()

        serie_doc_orig  = f"{tipo_factu_mod}{serie_mod_raw}"
        numero_doc_orig = numero_mod_raw.lstrip('0') or '0'

        prefijos       = cfg_notas.get('serie_prefijos', {})
        prefijo        = prefijos.get(tipo_factu_mod, 'BC')
        serie_nota_raw = str(raw.get('SERIE_NOTA', '')).strip()
        serie_nota     = f"{prefijo}{serie_nota_raw}"
        numero_nota    = str(raw.get('NUMERO_NOT', '')).strip().lstrip('0') or '0'

        tipo_cpe   = cfg_notas['tipo_comprobante_map'].get(tipo_factu_mod, '2')
        tipo_motiv = str(raw.get('TIPO_MOTIV', '01')).strip()
        tipo_nc    = tipo_motiv.lstrip('0') or '1'

        cliente_tipo_doc, cliente_num_doc, cliente_nombre = self._cliente_data(raw)
        fecha_nota = self._fmt_date(raw.get('FECHA_NOTA'))

        fac_orig           = self._get_factura(tipo_factu_mod, serie_mod_raw, numero_mod_raw)
        fecha_emision_orig = self._fmt_date(fac_orig.get('FECHA_FACT')) or fecha_nota

        factura_ex    = int(raw.get('FACTURA_EX') or 0)
        total_real    = float(raw.get('REAL_NOTA')  or 0)
        total_base    = float(raw.get('MONTO_NOTA') or 0)
        total_igv     = float(raw.get('IGV_NOTA')   or 0)

        if factura_ex == 1:
            total_exonerada = total_real
            total_base      = 0.0
            total_igv       = 0.0
        else:
            total_exonerada = 0.0

        productos  = self._load_productos_cache()
        items_norm = [self._normalize_item(i, productos, factura_ex) for i in items_raw]

        motivos     = self._load_motivos_cache()
        motivo_obj  = motivos.get(tipo_motiv, {})
        motivo_baja = self._sanitize_motivo(str(motivo_obj.get('MOTIVO', 'ANULACION')))

        return {
            'tipo_comprobante':  tipo_cpe,
            'serie':             serie_nota      if not es_anulacion else serie_doc_orig,
            'numero':            numero_nota     if not es_anulacion else numero_doc_orig,
            'es_nota':           not es_anulacion,
            'es_anulacion':      es_anulacion,
            'ruc_emisor':        self.config_cliente.get('ruc', ''),
            'razon_social':      self.config_cliente.get('razon_social', ''),
            'cliente_tipo_doc':  cliente_tipo_doc,
            'cliente_num_doc':   cliente_num_doc,
            'cliente_nombre':    cliente_nombre,
            'cliente_direccion': '-',
            'cliente_email':     '',
            'fecha_emision':     fecha_emision_orig,
            'fecha_anulacion':   fecha_nota,
            'fecha_vencimiento': '',
            'total_gravada':          round(total_base,      8),
            'total_exonerada':        round(total_exonerada, 8),
            'total_inafecta':         0.0,
            'total_igv':              round(total_igv,       8),
            'total_impuestos_bolsas': 0.0,
            'total_gratuita':         0.0,
            'total':                  round(total_real,      8),
            'items':             items_norm,
            'doc_mod_tipo':      DOC_MOD_TIPO_MAP.get(tipo_factu_mod, '2'),
            'doc_mod_serie':     serie_doc_orig,
            'doc_mod_numero':    numero_doc_orig,
            'tipo_nota_credito': tipo_nc,
            'motivo_baja':       motivo_baja,
            '_raw':              raw,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # NORMALIZE — ITEM
    # ═════════════════════════════════════════════════════════════════════════

    def _normalize_item(self, raw: Dict[str, Any], productos: Dict[str, Any], factura_ex: int) -> Dict[str, Any]:
        codigo     = str(raw.get('CODIGO_PRO', '')).strip()
        producto   = productos.get(codigo, {})

        cantidad   = float(raw.get('CANTIDAD_P') or 0)
        monto_pedi = float(raw.get('MONTO_PEDI') or 0)
        igv_pedido = float(raw.get('IGV_PEDIDO') or 0)
        real_pedid = float(raw.get('REAL_PEDID') or 0)
        precio_uni = float(raw.get('PRECIO_UNI') or 0)
        icbper     = float(raw.get('ICBPER')     or 0)

        valor_unit = round(monto_pedi / cantidad, 8) if cantidad else 0.0

        desc     = str(producto.get('DESCRIPCIO', '') or '').strip()
        presenta = str(producto.get('PRESENTA_P', '') or '').strip()
        if presenta:
            desc = f"{desc}   {presenta}"

        cod_sunat = str(producto.get('CODIGO_UNS', '') or '').strip()
        if not cod_sunat or len(cod_sunat) < 8:
            cod_sunat = '10000000'

        exonerado = bool(producto.get('EXONERADO_', False))
        tipo_igv  = 2 if (factura_ex == 1 or exonerado) else 1

        return {
            'unidad':          'NIU',
            'codigo':          codigo,
            'descripcion':     desc,
            'cantidad':        cantidad,
            'valor_unitario':  valor_unit,
            'precio_unitario': precio_uni,
            'valor_total':     round(monto_pedi,  8),
            'tipo_igv':        tipo_igv,
            'igv':             round(igv_pedido,  8),
            'total':           round(real_pedid,  8),
            'cod_sunat':       cod_sunat,
            'icbper':          icbper,
        }


    # ═════════════════════════════════════════════════════════════════════════
    # SQLITE — READ PENDING + ITEMS + WRITE FLAG
    # ═════════════════════════════════════════════════════════════════════════

    def _safe_read_sqlite(self, query: str, params: tuple = ()) -> List[Dict]:
        """Lee filas de SQLite y retorna lista de dicts. Nunca lanza excepcion."""
        import sqlite3 as _sqlite3
        try:
            conn = _sqlite3.connect(self.source_path)
            conn.row_factory = _sqlite3.Row
            cur  = conn.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            logger.warning(f"[SQLite] Error: {e}")
            return []

    def _read_pending_sqlite(self) -> List[Dict[str, Any]]:
        cfg        = self.contrato['comprobantes']
        tabla      = cfg['tabla']
        flag_c     = cfg['flag_lectura']['campo']
        flag_v     = cfg['flag_lectura']['valor']

        query = f"SELECT * FROM {tabla} WHERE {flag_c} = ?"
        rows  = self._safe_read_sqlite(query, (flag_v,))
        for r in rows:
            r['_tipo_registro'] = 'comprobante'
            r['_tabla_origen']  = tabla
        logger.info(f"[SQLite] Pendientes: {len(rows)}")
        return rows

    def _read_items_sqlite(self, comprobante: Dict[str, Any]) -> List[Dict[str, Any]]:
        cfg        = self.contrato.get('items', {})
        tabla      = cfg.get('tabla', '')
        join_campo = cfg.get('join_campo', '')
        if not tabla or not join_campo:
            return []

        numero = str(comprobante.get('numero', '')).strip()
        query  = f"SELECT * FROM {tabla} WHERE {join_campo} = ?"
        return self._safe_read_sqlite(query, (numero,))

    def _write_flag_sqlite(self, comprobante: Dict[str, Any], estado: str) -> None:
        """Actualiza el flag en SQLite — a diferencia de DBF, SQLite es escribible."""
        import sqlite3 as _sqlite3
        try:
            cfg        = self.contrato['comprobantes']
            tabla      = cfg['tabla']
            flag_c     = cfg['flag_escritura']['campo']
            nuevo_val  = (
                cfg['flag_escritura']['enviado'] if estado == 'enviado'
                else cfg['flag_escritura']['error']
            )
            join_campo = cfg.get('campos', {}).get('numero', 'numero')
            numero     = str(comprobante.get('numero', '')).strip()

            conn = _sqlite3.connect(self.source_path)
            conn.execute(
                f"UPDATE {tabla} SET {flag_c} = ? WHERE {join_campo} = ?",
                (nuevo_val, numero)
            )
            conn.commit()
            conn.close()
            logger.info(f"[SQLite] write_flag {tabla} {numero} → {flag_c}={nuevo_val}")
        except Exception as e:
            logger.warning(f"[SQLite] write_flag error: {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # WRITE FLAG
    # ═════════════════════════════════════════════════════════════════════════

    def _write_flag_enviosffee(self, comprobante: Dict, estado: str) -> None:
        try:
            cfg        = self.contrato['comprobantes']
            flag_campo = cfg['flag_escritura']['campo']
            nuevo_val  = (
                cfg['flag_escritura']['enviado'] if estado == 'enviado'
                else cfg['flag_escritura']['error']
            )
            tipo   = str(comprobante.get('TIPO_FACTU', '')).strip()
            serie  = str(comprobante.get('SERIE_FACT', '')).strip()
            numero = str(comprobante.get('NUMERO_FAC', '')).strip()
            logger.info(f"[write_flag] {cfg['tabla']} {tipo}{serie}-{numero} → {flag_campo}={nuevo_val} [PENDIENTE]")
        except Exception as e:
            logger.warning(f"[write_flag] {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # CACHES — TABLAS DE REFERENCIA
    # ═════════════════════════════════════════════════════════════════════════

    def _load_factura_cache(self) -> Dict:
        if self._cache_factura is not None:
            return self._cache_factura
        self._cache_factura = {}
        if self.source_type == 'sqlite':
            # SQLite: totales en la misma tabla de comprobantes
            cfg   = self.contrato.get('totales', self.contrato['comprobantes'])
            tabla = cfg['tabla']
            for r in self._safe_read_sqlite(f"SELECT * FROM {tabla}"):
                campos = self.contrato['comprobantes'].get('campos', {})
                serie  = str(r.get(campos.get('serie',  'serie'),  '')).strip()
                numero = _norm_num(str(r.get(campos.get('numero', 'numero'), '')).strip())
                key    = (serie, numero)
                self._cache_factura[key] = r
        else:
            cfg        = self.contrato['totales']
            tabla_path = self._tabla_path(cfg['tabla'])
            for r in _safe_read_dbf(tabla_path, self.encoding):
                key = (
                    str(r.get('TIPO_FACTU', '')).strip(),
                    str(r.get('SERIE_FACT', '')).strip(),
                    _norm_num(str(r.get('NUMERO_FAC', '')).strip()),
                )
                self._cache_factura[key] = r
        logger.info(f"Cache factura: {len(self._cache_factura)} registros")
        return self._cache_factura

    def _load_productos_cache(self) -> Dict:
        if self._cache_productos is not None:
            return self._cache_productos
        self._cache_productos = {}
        cfg        = self.contrato.get('productos', {})
        join_campo = cfg.get('join_campo', '')
        if not cfg or not cfg.get('tabla'):
            return self._cache_productos
        if self.source_type == 'sqlite':
            tabla = cfg['tabla']
            for r in self._safe_read_sqlite(f"SELECT * FROM {tabla}"):
                key = str(r.get(join_campo, '')).strip()
                self._cache_productos[key] = r
        else:
            tabla_path = self._tabla_path(cfg['tabla'])
            for r in _safe_read_dbf(tabla_path, self.encoding):
                key = str(r.get(join_campo, '')).strip()
                self._cache_productos[key] = r
        logger.info(f"Cache productos: {len(self._cache_productos)} registros")
        return self._cache_productos

    def _load_motivos_cache(self) -> Dict:
        if self._cache_motivos is not None:
            return self._cache_motivos
        cfg        = self.contrato.get('motivos', {})
        if not cfg:
            return {}
        tabla_path = self._tabla_path(cfg['tabla'])
        self._cache_motivos = {}
        for r in _safe_read_dbf(tabla_path, self.encoding):
            key = str(r.get('CODIGO', '')).strip()
            self._cache_motivos[key] = r
        logger.info(f"Cache motivos: {len(self._cache_motivos)} registros")
        return self._cache_motivos

    # ═════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═════════════════════════════════════════════════════════════════════════

    def _tabla_path(self, nombre_tabla: str) -> str:
        nombre = nombre_tabla.strip()
        if not nombre.lower().endswith('.dbf'):
            nombre = nombre + '.dbf'
        return os.path.join(self.source_path, nombre)

    def _get_factura(self, tipo: str, serie: str, numero: str) -> Dict:
        cache = self._load_factura_cache()
        if self.source_type == 'sqlite':
            # SQLite: clave por (serie, numero)
            return cache.get((serie.strip(), _norm_num(numero.strip())), {})
        return cache.get(
            (tipo.strip(), serie.strip(), _norm_num(numero.strip())), {}
        )

    def _cliente_data(self, record: Dict) -> tuple:
        cfg_varios = self.contrato.get('cliente_varios', {})
        tipo_clien = record.get('TIPO_CLIEN', 0) or 0
        try:
            tipo_clien = int(tipo_clien)
        except (ValueError, TypeError):
            tipo_clien = 0
        tipo_doc = CLIENTE_TIPO_DOC_MAP.get(tipo_clien, '-')
        num_doc  = str(record.get('RUC_CLIENT', '') or '').strip()
        nombre   = str(record.get('NOMBRE_CLI', '') or '').strip()
        if not num_doc or num_doc == '0':
            tipo_doc = cfg_varios.get('tipo_doc', '-')
            num_doc  = cfg_varios.get('num_doc',  '00000000')
            nombre   = cfg_varios.get('nombre',   'CLIENTE VARIOS')
        return tipo_doc, num_doc, nombre

    @staticmethod
    def _fmt_date(fecha) -> str:
        if fecha is None:
            return ''
        if isinstance(fecha, datetime):
            return fecha.strftime('%d-%m-%Y')
        if isinstance(fecha, date):
            return fecha.strftime('%d-%m-%Y')
        return str(fecha)

    @staticmethod
    def _sanitize_motivo(motivo: str) -> str:
        reemplazos = {
            'á':'a','é':'e','í':'i','ó':'o','ú':'u',
            'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U',
            'ñ':'n','Ñ':'N',
        }
        resultado = motivo.upper().strip()
        for orig, rep in reemplazos.items():
            resultado = resultado.replace(orig, rep)
        return ''.join(c for c in resultado if c.isalnum()) or 'ANULACION'
