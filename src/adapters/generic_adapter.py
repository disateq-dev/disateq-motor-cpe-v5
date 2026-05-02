# src/adapters/generic_adapter.py
# DisateQ Motor CPE v5.0
# ─────────────────────────────────────────────────────────────────────────────

import os
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from src.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

# ─── MAPEOS GLOBALES ──────────────────────────────────────────────────────────

TIPO_CPE_MAP = {
    'F': '1',   # Factura
    'B': '2',   # Boleta de venta
}

DOC_MOD_TIPO_MAP = {
    'F': '1',
    'B': '2',
}

CLIENTE_TIPO_DOC_MAP = {
    0: '-',     # cliente varios
    1: '1',     # DNI
    6: '6',     # RUC
}


class GenericAdapter(BaseAdapter):
    """
    Adaptador universal — lee cualquier fuente via contrato YAML.

    DBF (dbfread) → ACTIVO — farmacias_fas verificado
    Excel / CSV / SQL → estructura lista, implementacion pendiente
    """

    def __init__(self, contrato: dict, config_cliente: dict):
        super().__init__(contrato, config_cliente)
        self.source_type = contrato['source']['type'].lower()
        self.source_path = contrato['source']['path']
        self.encoding    = contrato['source'].get('encoding', 'latin-1')

        self._cache_factura:   Optional[Dict] = None
        self._cache_productos: Optional[Dict] = None
        self._cache_motivos:   Optional[Dict] = None

    # ═════════════════════════════════════════════════════════════════════════
    # INTERFAZ PUBLICA — BaseAdapter
    # ═════════════════════════════════════════════════════════════════════════

    def read_pending(self) -> List[Dict[str, Any]]:
        if self.source_type == 'dbf':
            return self._read_pending_dbf()
        raise NotImplementedError(f"read_pending: fuente '{self.source_type}' no implementada")

    def read_items(self, comprobante: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.source_type == 'dbf':
            return self._read_items_dbf(comprobante)
        raise NotImplementedError(f"read_items: fuente '{self.source_type}' no implementada")

    def normalize(
        self,
        comprobante: Dict[str, Any],
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        tipo = comprobante.get('_tipo_registro', 'comprobante')
        if tipo == 'comprobante':
            return self._normalize_comprobante(comprobante, items)
        return self._normalize_nota(comprobante, items)

    def write_flag(self, comprobante: Dict[str, Any], estado: str) -> None:
        if self.source_type != 'dbf':
            return
        if comprobante.get('_tipo_registro') == 'comprobante':
            self._write_flag_enviosffee(comprobante, estado)

    # ═════════════════════════════════════════════════════════════════════════
    # DBF — READ PENDING
    # ═════════════════════════════════════════════════════════════════════════

    def _read_pending_dbf(self) -> List[Dict[str, Any]]:
        from dbfread import DBF as _DBF

        comprobantes = self._read_pending_comprobantes_dbf(_DBF)

        # Notas son opcionales — si no hay seccion 'notas' en contrato, omitir
        notas = []
        if 'notas' in self.contrato:
            try:
                notas = self._read_pending_notas_dbf(_DBF)
            except Exception as e:
                logger.warning(f"[GenericAdapter] No se pudieron leer notas: {e}")

        total = len(comprobantes) + len(notas)
        logger.info(
            f"[{self.contrato['cliente_id']}] Pendientes: "
            f"{len(comprobantes)} comprobantes + {len(notas)} notas = {total}"
        )
        return comprobantes + notas

    def _read_pending_comprobantes_dbf(self, DBF) -> List[Dict[str, Any]]:
        cfg        = self.contrato['comprobantes']
        tabla_path = self._tabla_path(cfg['tabla'])
        flag_campo = cfg['flag_lectura']['campo']
        flag_valor = cfg['flag_lectura']['valor']

        pendientes = []
        for r in DBF(tabla_path, encoding=self.encoding, raw=False):
            if r.get(flag_campo) == flag_valor:
                rec = dict(r)
                rec['_tipo_registro'] = 'comprobante'
                rec['_tabla_origen']  = cfg['tabla']
                pendientes.append(rec)
        return pendientes

    def _read_pending_notas_dbf(self, DBF) -> List[Dict[str, Any]]:
        cfg        = self.contrato['notas']
        tabla_path = self._tabla_path(cfg['tabla'])
        fl         = cfg['flag_lectura']

        campo_pend  = fl['campo_pendiente']
        valor_pend  = str(fl['valor_pendiente'])
        campo_movim = fl['campo_tipo_movim']
        valor_movim = fl['valor_tipo_movim']

        pendientes = []
        for r in DBF(tabla_path, encoding=self.encoding, raw=False):
            if (str(r.get(campo_pend, '')).strip() == valor_pend and
                    r.get(campo_movim) == valor_movim):
                rec = dict(r)
                rec['_tipo_registro'] = 'nota'
                rec['_tabla_origen']  = cfg['tabla']
                pendientes.append(rec)
        return pendientes

    # ═════════════════════════════════════════════════════════════════════════
    # DBF — READ ITEMS
    # ═════════════════════════════════════════════════════════════════════════

    def _read_items_dbf(self, comprobante: Dict[str, Any]) -> List[Dict[str, Any]]:
        from dbfread import DBF as _DBF

        tipo   = str(comprobante['TIPO_FACTU']).strip()
        serie  = str(comprobante['SERIE_FACT']).strip()
        numero = str(comprobante['NUMERO_FAC']).strip()

        cfg        = self.contrato['items']
        tabla_path = self._tabla_path(cfg['tabla'])

        items = []
        for r in _DBF(tabla_path, encoding=self.encoding, raw=False):
            if (str(r['TIPO_FACTU']).strip() == tipo and
                    str(r['SERIE_FACT']).strip() == serie and
                    str(r['NUMERO_FAC']).strip() == numero):
                items.append(dict(r))

        items.sort(key=lambda x: x.get('ITEM_FACTU', 0))
        return items

    # ═════════════════════════════════════════════════════════════════════════
    # NORMALIZE — COMPROBANTE NORMAL
    # ═════════════════════════════════════════════════════════════════════════

    def _normalize_comprobante(
        self,
        raw: Dict[str, Any],
        items_raw: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        tipo_factu = str(raw['TIPO_FACTU']).strip()
        serie_fact = str(raw['SERIE_FACT']).strip()
        numero_raw = str(raw['NUMERO_FAC']).strip()

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
            'tipo_comprobante': tipo_cpe,
            'serie':            serie_completa,
            'numero':           numero_limpio,
            'es_nota':          False,
            'es_anulacion':     False,
            'ruc_emisor':       self.config_cliente.get('ruc', ''),
            'razon_social':     self.config_cliente.get('razon_social', ''),
            'cliente_tipo_doc': cliente_tipo_doc,
            'cliente_num_doc':  cliente_num_doc,
            'cliente_nombre':   cliente_nombre,
            'cliente_direccion': '',
            'cliente_email':    str(fac.get('EMAIL_CLIE', '') or '').strip(),
            'fecha_emision':    fecha_emision,
            'fecha_vencimiento': '',
            'total_gravada':          round(total_gravada,   8),
            'total_exonerada':        round(total_exonerada, 8),
            'total_inafecta':         0.0,
            'total_igv':              round(total_igv,       8),
            'total_impuestos_bolsas': round(icbper,          8),
            'total_gratuita':         0.0,
            'total':                  round(total_real,      8),
            'items':            items_norm,
            'doc_mod_tipo':     None,
            'doc_mod_serie':    None,
            'doc_mod_numero':   None,
            'tipo_nota_credito': None,
            'fecha_anulacion':  None,
            'motivo_baja':      None,
            '_raw':             raw,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # NORMALIZE — NOTA / ANULACION
    # ═════════════════════════════════════════════════════════════════════════

    def _normalize_nota(
        self,
        raw: Dict[str, Any],
        items_raw: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        cfg_notas        = self.contrato['notas']
        tipo_registro_nota = cfg_notas.get('tipo_registro', 'anulacion')
        es_anulacion     = (tipo_registro_nota == 'anulacion')

        tipo_factu_mod = str(raw['TIPO_FACTU']).strip()
        serie_mod_raw  = str(raw['SERIE_FACT']).strip()
        numero_mod_raw = str(raw['NUMERO_FAC']).strip()

        serie_doc_orig  = f"{tipo_factu_mod}{serie_mod_raw}"
        numero_doc_orig = numero_mod_raw.lstrip('0') or '0'

        prefijos       = cfg_notas.get('serie_prefijos', {})
        prefijo        = prefijos.get(tipo_factu_mod, 'BC')
        serie_nota_raw = str(raw.get('SERIE_NOTA', '')).strip()
        serie_nota     = f"{prefijo}{serie_nota_raw}"
        numero_nota    = str(raw.get('NUMERO_NOT', '')).strip().lstrip('0') or '0'

        tipo_cpe = cfg_notas['tipo_comprobante_map'].get(tipo_factu_mod, '2')

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
            'tipo_comprobante': tipo_cpe,
            'serie':            serie_nota      if not es_anulacion else serie_doc_orig,
            'numero':           numero_nota     if not es_anulacion else numero_doc_orig,
            'es_nota':          not es_anulacion,
            'es_anulacion':     es_anulacion,
            'ruc_emisor':       self.config_cliente.get('ruc', ''),
            'razon_social':     self.config_cliente.get('razon_social', ''),
            'cliente_tipo_doc': cliente_tipo_doc,
            'cliente_num_doc':  cliente_num_doc,
            'cliente_nombre':   cliente_nombre,
            'cliente_direccion': '-',
            'cliente_email':    '',
            'fecha_emision':    fecha_emision_orig,
            'fecha_anulacion':  fecha_nota,
            'fecha_vencimiento': '',
            'total_gravada':          round(total_base,      8),
            'total_exonerada':        round(total_exonerada, 8),
            'total_inafecta':         0.0,
            'total_igv':              round(total_igv,       8),
            'total_impuestos_bolsas': 0.0,
            'total_gratuita':         0.0,
            'total':                  round(total_real,      8),
            'items':            items_norm,
            'doc_mod_tipo':     DOC_MOD_TIPO_MAP.get(tipo_factu_mod, '2'),
            'doc_mod_serie':    serie_doc_orig,
            'doc_mod_numero':   numero_doc_orig,
            'tipo_nota_credito': tipo_nc,
            'motivo_baja':      motivo_baja,
            '_raw':             raw,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # NORMALIZE — ITEM
    # ═════════════════════════════════════════════════════════════════════════

    def _normalize_item(
        self,
        raw: Dict[str, Any],
        productos: Dict[str, Any],
        factura_ex: int
    ) -> Dict[str, Any]:

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
            tipo   = str(comprobante['TIPO_FACTU']).strip()
            serie  = str(comprobante['SERIE_FACT']).strip()
            numero = str(comprobante['NUMERO_FAC']).strip()
            logger.info(
                f"[write_flag] {cfg['tabla']} "
                f"TIPO={tipo} SERIE={serie} NUM={numero} "
                f"→ {flag_campo}={nuevo_val} ({estado}) "
                f"[PENDIENTE: escritura DBF real]"
            )
        except Exception as e:
            logger.warning(f"[write_flag] Error: {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # CACHE — TABLAS DE REFERENCIA
    # ═════════════════════════════════════════════════════════════════════════

    def _load_factura_cache(self) -> Dict:
        if self._cache_factura is not None:
            return self._cache_factura
        from dbfread import DBF as _DBF
        cfg        = self.contrato['totales']
        tabla_path = self._tabla_path(cfg['tabla'])
        self._cache_factura = {}
        for r in _DBF(tabla_path, encoding=self.encoding, raw=False):
            key = (
                str(r['TIPO_FACTU']).strip(),
                str(r['SERIE_FACT']).strip(),
                str(r['NUMERO_FAC']).strip(),
            )
            self._cache_factura[key] = dict(r)
        logger.debug(f"Cache factura: {len(self._cache_factura)} registros")
        return self._cache_factura

    def _load_productos_cache(self) -> Dict:
        if self._cache_productos is not None:
            return self._cache_productos
        from dbfread import DBF as _DBF
        cfg        = self.contrato['productos']
        tabla_path = self._tabla_path(cfg['tabla'])
        join_campo = cfg['join_campo']
        self._cache_productos = {}
        for r in _DBF(tabla_path, encoding=self.encoding, raw=False):
            key = str(r[join_campo]).strip()
            self._cache_productos[key] = dict(r)
        logger.debug(f"Cache productos: {len(self._cache_productos)} registros")
        return self._cache_productos

    def _load_motivos_cache(self) -> Dict:
        if self._cache_motivos is not None:
            return self._cache_motivos
        from dbfread import DBF as _DBF
        cfg        = self.contrato['motivos']
        tabla_path = self._tabla_path(cfg['tabla'])
        self._cache_motivos = {}
        for r in _DBF(tabla_path, encoding=self.encoding, raw=False):
            key = str(r['CODIGO']).strip()
            self._cache_motivos[key] = dict(r)
        logger.debug(f"Cache motivos: {len(self._cache_motivos)} registros")
        return self._cache_motivos

    # ═════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═════════════════════════════════════════════════════════════════════════

    def _tabla_path(self, nombre_tabla: str) -> str:
        """
        Construye la ruta completa al archivo DBF.
        Agrega extensión .dbf si no la tiene.
        """
        nombre = nombre_tabla.strip()
        if not nombre.lower().endswith('.dbf'):
            nombre = nombre + '.dbf'
        return os.path.join(self.source_path, nombre)

    def _get_factura(self, tipo: str, serie: str, numero: str) -> Dict:
        cache = self._load_factura_cache()
        return cache.get((tipo.strip(), serie.strip(), numero.strip()), {})

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
        resultado = ''.join(c for c in resultado if c.isalnum())
        return resultado or 'ANULACION'
