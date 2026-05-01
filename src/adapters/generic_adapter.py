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

# TIPO_FACTU DBF → tipo_de_comprobante SUNAT (comprobante normal)
TIPO_CPE_MAP = {
    'F': '1',   # Factura
    'B': '2',   # Boleta de venta
}

# Tipo doc modificado en nota/anulacion (para documento_que_se_modifica_tipo)
DOC_MOD_TIPO_MAP = {
    'F': '1',
    'B': '2',
}

# TIPO_CLIEN factura.dbf → cliente_tipo_de_documento SUNAT
CLIENTE_TIPO_DOC_MAP = {
    0: '-',     # cliente varios
    1: '1',     # DNI
    6: '6',     # RUC
}


class GenericAdapter(BaseAdapter):
    """
    Adaptador universal — lee cualquier fuente via contrato YAML.

    Estado actual:
        DBF (dbfread)   → ACTIVO — farmacias_fas verificado
        Excel (openpyxl)→ Estructura lista — implementacion pendiente
        CSV (nativo)    → Estructura lista — implementacion pendiente
        SQL Server      → Estructura lista — implementacion pendiente
        MySQL           → Estructura lista — implementacion pendiente
        PostgreSQL      → Estructura lista — implementacion pendiente

    El contrato YAML define QUE leer. Este adaptador define COMO leerlo.
    """

    def __init__(self, contrato: dict, config_cliente: dict):
        super().__init__(contrato, config_cliente)
        self.source_type = contrato['source']['type'].lower()
        self.source_path = contrato['source']['path']
        self.encoding = contrato['source'].get('encoding', 'latin-1')

        # Cache de tablas de referencia (cargadas una sola vez por sesion)
        self._cache_factura:  Optional[Dict] = None
        self._cache_productos: Optional[Dict] = None
        self._cache_motivos:  Optional[Dict] = None

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
        """
        Escribe FLAG_ENVIO en enviosffee.dbf.
        estado: 'enviado' → 3 | 'error' → 4

        dbfread es solo lectura. Escritura real pendiente con python-dbf
        una vez confirmado que el sistema legacy no bloquea el archivo.
        Hasta entonces: log de intencion + SQLite controla.
        """
        if self.source_type != 'dbf':
            return
        if comprobante.get('_tipo_registro') == 'comprobante':
            self._write_flag_enviosffee(comprobante, estado)
        # Notas: pendiente — notacredito.dbf escritura no implementada aun

    # ═════════════════════════════════════════════════════════════════════════
    # DBF — READ PENDING
    # ═════════════════════════════════════════════════════════════════════════

    def _read_pending_dbf(self) -> List[Dict[str, Any]]:
        from dbfread import DBF as _DBF  # import local — dbfread opcional en perfil base

        comprobantes = self._read_pending_comprobantes_dbf(_DBF)
        notas = self._read_pending_notas_dbf(_DBF)
        total = len(comprobantes) + len(notas)
        logger.info(
            f"[{self.contrato['cliente_id']}] Pendientes: "
            f"{len(comprobantes)} comprobantes + {len(notas)} notas = {total}"
        )
        return comprobantes + notas

    def _read_pending_comprobantes_dbf(self, DBF) -> List[Dict[str, Any]]:
        cfg = self.contrato['comprobantes']
        tabla_path = self._tabla_path(cfg['tabla'])
        flag_campo = cfg['flag_lectura']['campo']
        flag_valor = cfg['flag_lectura']['valor']   # integer 2

        pendientes = []
        for r in DBF(tabla_path, encoding=self.encoding, raw=False):
            if r.get(flag_campo) == flag_valor:
                rec = dict(r)
                rec['_tipo_registro'] = 'comprobante'
                rec['_tabla_origen'] = cfg['tabla']
                pendientes.append(rec)
        return pendientes

    def _read_pending_notas_dbf(self, DBF) -> List[Dict[str, Any]]:
        cfg = self.contrato['notas']
        tabla_path = self._tabla_path(cfg['tabla'])
        fl = cfg['flag_lectura']

        campo_pend  = fl['campo_pendiente']
        valor_pend  = str(fl['valor_pendiente'])      # string "2"
        campo_movim = fl['campo_tipo_movim']
        valor_movim = fl['valor_tipo_movim']           # integer 2

        pendientes = []
        for r in DBF(tabla_path, encoding=self.encoding, raw=False):
            if (str(r.get(campo_pend, '')).strip() == valor_pend and
                    r.get(campo_movim) == valor_movim):
                rec = dict(r)
                rec['_tipo_registro'] = 'nota'
                rec['_tabla_origen'] = cfg['tabla']
                pendientes.append(rec)
        return pendientes

    # ═════════════════════════════════════════════════════════════════════════
    # DBF — READ ITEMS
    # ═════════════════════════════════════════════════════════════════════════

    def _read_items_dbf(self, comprobante: Dict[str, Any]) -> List[Dict[str, Any]]:
        from dbfread import DBF as _DBF

        tipo_registro = comprobante.get('_tipo_registro', 'comprobante')

        if tipo_registro == 'comprobante':
            tipo   = str(comprobante['TIPO_FACTU']).strip()
            serie  = str(comprobante['SERIE_FACT']).strip()
            numero = str(comprobante['NUMERO_FAC']).strip()
        else:
            # Nota/anulacion: items del comprobante ORIGINAL
            tipo   = str(comprobante['TIPO_FACTU']).strip()
            serie  = str(comprobante['SERIE_FACT']).strip()
            numero = str(comprobante['NUMERO_FAC']).strip()

        cfg = self.contrato['items']
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
    # NORMALIZE — COMPROBANTE NORMAL (Factura / Boleta)
    # ═════════════════════════════════════════════════════════════════════════

    def _normalize_comprobante(
        self,
        raw: Dict[str, Any],
        items_raw: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        tipo_factu = str(raw['TIPO_FACTU']).strip()
        serie_fact = str(raw['SERIE_FACT']).strip()
        numero_raw = str(raw['NUMERO_FAC']).strip()

        # Datos reales desde factura.dbf
        fac = self._get_factura(tipo_factu, serie_fact, numero_raw)

        # Identificacion
        serie_completa  = f"{tipo_factu}{serie_fact}"           # B001, F013
        tipo_cpe        = TIPO_CPE_MAP.get(tipo_factu, '2')
        numero_limpio   = numero_raw.lstrip('0') or '0'

        # Cliente
        cliente_tipo_doc, cliente_num_doc, cliente_nombre = self._cliente_data(fac)

        # Fechas
        fecha_emision = self._fmt_date(raw.get('FECHA_DOCU'))

        # Importes desde factura.dbf (fuente de verdad)
        factura_ex    = int(raw.get('FACTURA_EX') or 0)
        total_real    = float(fac.get('REAL_FACTU') or 0)
        total_gravada = float(fac.get('MONTO_FACT') or 0)
        total_igv     = float(fac.get('IGV_FACTUR') or 0)
        icbper        = float(fac.get('IMPORTE_IC') or 0)

        if factura_ex == 1:                 # comprobante exonerado total
            total_exonerada = total_real
            total_gravada   = 0.0
            total_igv       = 0.0
        else:
            total_exonerada = 0.0

        # Items
        productos = self._load_productos_cache()
        items_norm = [
            self._normalize_item(i, productos, factura_ex)
            for i in items_raw
        ]

        return {
            # Identificacion
            'tipo_comprobante': tipo_cpe,
            'serie':            serie_completa,
            'numero':           numero_limpio,
            'es_nota':          False,
            'es_anulacion':     False,

            # Emisor
            'ruc_emisor':   self.config_cliente.get('ruc', ''),
            'razon_social': self.config_cliente.get('razon_social', ''),

            # Cliente
            'cliente_tipo_doc': cliente_tipo_doc,
            'cliente_num_doc':  cliente_num_doc,
            'cliente_nombre':   cliente_nombre,
            'cliente_direccion': '',
            'cliente_email':     str(fac.get('EMAIL_CLIE', '') or '').strip(),

            # Fechas
            'fecha_emision':    fecha_emision,
            'fecha_vencimiento': '',

            # Importes
            'total_gravada':          round(total_gravada,   8),
            'total_exonerada':        round(total_exonerada, 8),
            'total_inafecta':         0.0,
            'total_igv':              round(total_igv,       8),
            'total_impuestos_bolsas': round(icbper,          8),
            'total_gratuita':         0.0,
            'total':                  round(total_real,      8),

            # Items
            'items': items_norm,

            # Nota/Anulacion (vacio en comprobante normal)
            'doc_mod_tipo':     None,
            'doc_mod_serie':    None,
            'doc_mod_numero':   None,
            'tipo_nota_credito': None,
            'fecha_anulacion':  None,
            'motivo_baja':      None,

            '_raw': raw,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # NORMALIZE — NOTA / ANULACION
    # ═════════════════════════════════════════════════════════════════════════

    def _normalize_nota(
        self,
        raw: Dict[str, Any],
        items_raw: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        cfg_notas = self.contrato['notas']
        tipo_registro_nota = cfg_notas.get('tipo_registro', 'anulacion')
        es_anulacion = (tipo_registro_nota == 'anulacion')

        tipo_factu_mod  = str(raw['TIPO_FACTU']).strip()  # tipo doc ORIGINAL
        serie_mod_raw   = str(raw['SERIE_FACT']).strip()
        numero_mod_raw  = str(raw['NUMERO_FAC']).strip()

        # Serie y numero del doc ORIGINAL
        serie_doc_orig   = f"{tipo_factu_mod}{serie_mod_raw}"   # B001, F013
        numero_doc_orig  = numero_mod_raw.lstrip('0') or '0'

        # Serie de la nota/anulacion
        prefijos        = cfg_notas.get('serie_prefijos', {})
        prefijo         = prefijos.get(tipo_factu_mod, 'BC')
        serie_nota_raw  = str(raw.get('SERIE_NOTA', '')).strip()
        serie_nota      = f"{prefijo}{serie_nota_raw}"          # BC001, FC001

        numero_nota     = str(raw.get('NUMERO_NOT', '')).strip().lstrip('0') or '0'

        # tipo_de_comprobante para el TXT = tipo del doc ORIGINAL
        tipo_cpe = cfg_notas['tipo_comprobante_map'].get(tipo_factu_mod, '2')

        # Motivo
        tipo_motiv      = str(raw.get('TIPO_MOTIV', '01')).strip()
        tipo_nc         = tipo_motiv.lstrip('0') or '1'  # '01' → '1'

        # Cliente
        cliente_tipo_doc, cliente_num_doc, cliente_nombre = self._cliente_data(raw)

        # Fechas
        fecha_nota = self._fmt_date(raw.get('FECHA_NOTA'))

        # Fecha original del doc modificado — desde factura.dbf
        fac_orig = self._get_factura(tipo_factu_mod, serie_mod_raw, numero_mod_raw)
        fecha_emision_orig = self._fmt_date(fac_orig.get('FECHA_FACT')) or fecha_nota

        # Importes
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

        # Items del comprobante ORIGINAL
        productos = self._load_productos_cache()
        items_norm = [
            self._normalize_item(i, productos, factura_ex)
            for i in items_raw
        ]

        # Motivo baja legible para TXT anulacion
        motivos    = self._load_motivos_cache()
        motivo_obj = motivos.get(tipo_motiv, {})
        motivo_baja = self._sanitize_motivo(
            str(motivo_obj.get('MOTIVO', 'ANULACION'))
        )

        return {
            # Identificacion
            'tipo_comprobante': tipo_cpe,
            'serie':            serie_nota      if not es_anulacion else serie_doc_orig,
            'numero':           numero_nota     if not es_anulacion else numero_doc_orig,
            'es_nota':          not es_anulacion,
            'es_anulacion':     es_anulacion,

            # Emisor
            'ruc_emisor':   self.config_cliente.get('ruc', ''),
            'razon_social': self.config_cliente.get('razon_social', ''),

            # Cliente
            'cliente_tipo_doc': cliente_tipo_doc,
            'cliente_num_doc':  cliente_num_doc,
            'cliente_nombre':   cliente_nombre,
            'cliente_direccion': '-',
            'cliente_email':     '',

            # Fechas
            'fecha_emision':    fecha_emision_orig,
            'fecha_anulacion':  fecha_nota,
            'fecha_vencimiento': '',

            # Importes
            'total_gravada':          round(total_base,      8),
            'total_exonerada':        round(total_exonerada, 8),
            'total_inafecta':         0.0,
            'total_igv':              round(total_igv,       8),
            'total_impuestos_bolsas': 0.0,
            'total_gratuita':         0.0,
            'total':                  round(total_real,      8),

            # Items
            'items': items_norm,

            # Para nota de credito (es_anulacion=False)
            'doc_mod_tipo':     DOC_MOD_TIPO_MAP.get(tipo_factu_mod, '2'),
            'doc_mod_serie':    serie_doc_orig,
            'doc_mod_numero':   numero_doc_orig,
            'tipo_nota_credito': tipo_nc,

            # Para anulacion (es_anulacion=True)
            'motivo_baja': motivo_baja,

            '_raw': raw,
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

        codigo      = str(raw.get('CODIGO_PRO', '')).strip()
        producto    = productos.get(codigo, {})

        cantidad    = float(raw.get('CANTIDAD_P') or 0)
        monto_pedi  = float(raw.get('MONTO_PEDI') or 0)   # subtotal SIN IGV
        igv_pedido  = float(raw.get('IGV_PEDIDO') or 0)
        real_pedid  = float(raw.get('REAL_PEDID') or 0)   # total CON IGV
        precio_uni  = float(raw.get('PRECIO_UNI') or 0)   # precio unit CON IGV
        icbper      = float(raw.get('ICBPER')     or 0)

        # valor unitario sin IGV = monto_pedi / cantidad
        valor_unit  = round(monto_pedi / cantidad, 8) if cantidad else 0.0

        # Descripcion: DESCRIPCIO + PRESENTA_P
        desc     = str(producto.get('DESCRIPCIO', '') or '').strip()
        presenta = str(producto.get('PRESENTA_P', '') or '').strip()
        if presenta:
            desc = f"{desc}   {presenta}"

        # Codigo SUNAT UNSPSC
        cod_sunat = str(producto.get('CODIGO_UNS', '') or '').strip()
        if not cod_sunat or len(cod_sunat) < 8:
            cod_sunat = '10000000'

        # Tipo IGV
        exonerado = bool(producto.get('EXONERADO_', False))
        if factura_ex == 1 or exonerado:
            tipo_igv = 2    # exonerado
        else:
            tipo_igv = 1    # gravado normal

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
        """
        PENDIENTE escritura real — dbfread es solo lectura.
        Implementar con python-dbf una vez confirmado que el sistema
        legacy no bloquea enviosffee.dbf durante escritura simultanea.
        Hasta entonces: solo log + SQLite controla el estado.
        """
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
            logger.warning(f"[write_flag] Error preparando escritura DBF: {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # CACHE — TABLAS DE REFERENCIA
    # ═════════════════════════════════════════════════════════════════════════

    def _load_factura_cache(self) -> Dict:
        if self._cache_factura is not None:
            return self._cache_factura

        from dbfread import DBF as _DBF
        cfg = self.contrato['totales']
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
        cfg = self.contrato['productos']
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
        cfg = self.contrato['motivos']
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
        return os.path.join(self.source_path, nombre_tabla)

    def _get_factura(self, tipo: str, serie: str, numero: str) -> Dict:
        """Busca en cache de factura.dbf. Retorna dict vacio si no encuentra."""
        cache = self._load_factura_cache()
        return cache.get((tipo.strip(), serie.strip(), numero.strip()), {})

    def _cliente_data(self, record: Dict) -> tuple:
        """
        Extrae y normaliza datos de cliente desde un registro (factura o nota).
        Retorna (tipo_doc, num_doc, nombre).
        """
        cfg_varios = self.contrato.get('cliente_varios', {})

        tipo_clien   = record.get('TIPO_CLIEN', 0) or 0
        try:
            tipo_clien = int(tipo_clien)
        except (ValueError, TypeError):
            tipo_clien = 0

        tipo_doc = CLIENTE_TIPO_DOC_MAP.get(tipo_clien, '-')
        num_doc  = str(record.get('RUC_CLIENT', '') or '').strip()
        nombre   = str(record.get('NOMBRE_CLI', '') or '').strip()

        # Si num_doc es '0', vacio o no existe → cliente varios
        if not num_doc or num_doc == '0':
            tipo_doc = cfg_varios.get('tipo_doc', '-')
            num_doc  = cfg_varios.get('num_doc',  '00000000')
            nombre   = cfg_varios.get('nombre',   'CLIENTE VARIOS')

        return tipo_doc, num_doc, nombre

    @staticmethod
    def _fmt_date(fecha) -> str:
        """Convierte date/datetime DBF → string dd-mm-yyyy para TXT."""
        if fecha is None:
            return ''
        if isinstance(fecha, datetime):
            return fecha.strftime('%d-%m-%Y')
        if isinstance(fecha, date):
            return fecha.strftime('%d-%m-%Y')
        return str(fecha)

    @staticmethod
    def _sanitize_motivo(motivo: str) -> str:
        """
        Limpia motivo de baja para el TXT de anulacion.
        Elimina tildes, espacios y caracteres especiales.
        Ej: 'Anulación de la operación' → 'ANULACIONDELAOPERACION'
        """
        reemplazos = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'ñ': 'n', 'Ñ': 'N',
        }
        resultado = motivo.upper().strip()
        for original, reemplazo in reemplazos.items():
            resultado = resultado.replace(original, reemplazo)
        # Solo alfanumericos — sin espacios ni puntuacion
        resultado = ''.join(c for c in resultado if c.isalnum())
        return resultado or 'ANULACION'
