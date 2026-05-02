"""
txt_generator.py — Motor CPE DisateQ™ v5.0
TASK-008: reescrito para estructura CPE plana de GenericAdapter v5

Estructura CPE plana (normalize() de GenericAdapter):
    cpe['tipo_comprobante']   — '1'=factura, '2'=boleta
    cpe['serie']              — 'B001', 'F001'
    cpe['numero']             — '16377'
    cpe['cliente_tipo_doc']   — '-', '1', '6'
    cpe['cliente_num_doc']    — '00000000' / DNI / RUC
    cpe['cliente_nombre']     — 'CLIENTE VARIOS'
    cpe['cliente_direccion']  — ''
    cpe['cliente_email']      — ''
    cpe['fecha_emision']      — 'DD-MM-YYYY'
    cpe['total_gravada']      — float
    cpe['total_exonerada']    — float
    cpe['total_inafecta']     — float
    cpe['total_igv']          — float
    cpe['total_impuestos_bolsas'] — float
    cpe['total']              — float
    cpe['items']              — lista de dicts planos
        item['unidad']        — 'NIU'
        item['codigo']        — str
        item['descripcion']   — str
        item['cantidad']      — float
        item['valor_unitario'] — float (sin IGV)
        item['precio_unitario'] — float (con IGV)
        item['valor_total']   — float (subtotal sin IGV)
        item['tipo_igv']      — 1=gravado, 2=exonerado
        item['igv']           — float
        item['total']         — float (con IGV)
        item['cod_sunat']     — str UNSPSC
        item['icbper']        — float

Formato APIFAS: clave|valor| por linea, items al final.
"""

from pathlib import Path


# Mapa tipo_igv interno → codigo SUNAT afectacion IGV
TIPO_IGV_MAP = {
    1: '10',   # Gravado — Operacion Onerosa
    2: '20',   # Exonerado — Operacion Onerosa
    3: '30',   # Inafecto — Operacion Onerosa
    4: '40',   # Exportacion
}


def _fd(value, d=8):
    """Formatea decimal con d cifras."""
    try:
        return f"{float(value):.{d}f}"
    except (TypeError, ValueError):
        return f"0.{'0' * d}"


def _fecha(val):
    """Normaliza fecha a DD-MM-YYYY."""
    if not val:
        return ''
    v = str(val).strip()
    # Ya en formato DD-MM-YYYY
    if len(v) == 10 and v[2] == '-' and v[5] == '-':
        return v
    # YYYY-MM-DD → DD-MM-YYYY
    if len(v) == 10 and v[4] == '-':
        return f"{v[8:10]}-{v[5:7]}-{v[:4]}"
    # YYYYMMDD → DD-MM-YYYY
    if len(v) == 8 and v.isdigit():
        return f"{v[6:8]}-{v[4:6]}-{v[:4]}"
    return v


class TxtGenerator:
    """Genera archivos TXT formato APIFAS desde estructura CPE plana v5."""

    @staticmethod
    def generate(cpe: dict, output_dir: str = "output") -> str:
        """
        Genera el archivo TXT y retorna su ruta.
        """
        p = Path(output_dir)
        p.mkdir(parents=True, exist_ok=True)

        serie  = str(cpe.get('serie', '') or '')
        numero = int(cpe.get('numero', 0) or 0)
        fp     = p / f"{serie}-{numero:08d}.txt"
        fp.write_text(TxtGenerator._contenido(cpe), encoding='utf-8')
        return str(fp)

    @staticmethod
    def _contenido(cpe: dict) -> str:
        lines = []

        def l(k, v=''):
            lines.append(f"{k}|{v}|")

        # ── Cabecera ──────────────────────────────────────────────
        tipo_comp = str(cpe.get('tipo_comprobante', '2') or '2')
        serie     = str(cpe.get('serie',  '') or '')
        numero    = int(cpe.get('numero', 0)  or 0)
        moneda    = '1'  # PEN por defecto

        fecha_emi = _fecha(cpe.get('fecha_emision', ''))
        fecha_vto = _fecha(cpe.get('fecha_vencimiento', ''))

        # Cliente
        cli_tipo  = str(cpe.get('cliente_tipo_doc', '-') or '-')
        cli_doc   = str(cpe.get('cliente_num_doc',  '00000000') or '00000000')
        cli_nom   = str(cpe.get('cliente_nombre',   'CLIENTE VARIOS') or 'CLIENTE VARIOS')
        cli_dir   = str(cpe.get('cliente_direccion', '-') or '-')
        cli_email = str(cpe.get('cliente_email', '')     or '')

        # Totales
        gr  = float(cpe.get('total_gravada',          0) or 0)
        ex  = float(cpe.get('total_exonerada',         0) or 0)
        ina = float(cpe.get('total_inafecta',          0) or 0)
        ig  = float(cpe.get('total_igv',               0) or 0)
        icb = float(cpe.get('total_impuestos_bolsas',  0) or 0)
        tot = float(cpe.get('total',                   0) or 0)

        # Nota credito/debito
        doc_mod_tipo   = str(cpe.get('doc_mod_tipo',   '') or '')
        doc_mod_serie  = str(cpe.get('doc_mod_serie',  '') or '')
        doc_mod_numero = str(cpe.get('doc_mod_numero', '') or '')
        tipo_nc        = str(cpe.get('tipo_nota_credito', '') or '')

        l('operacion', 'generar_comprobante')
        l('tipo_de_comprobante', tipo_comp)
        l('serie', serie)
        l('numero', str(numero))
        l('sunat_transaction', '1')
        l('cliente_tipo_de_documento', cli_tipo)
        l('cliente_numero_de_documento', cli_doc)
        l('cliente_denominacion', cli_nom)
        l('cliente_direccion', cli_dir)
        l('cliente_email', cli_email)
        l('cliente_email_1')
        l('cliente_email_2')
        l('fecha_de_emision', fecha_emi)
        l('fecha_de_vencimiento', fecha_vto)
        l('moneda', moneda)
        l('tipo_de_cambio')
        l('porcentaje_de_igv', '18.00')
        l('descuento_global')
        l('total_descuento')
        l('total_anticipo')
        l('total_gravada',           _fd(gr))
        l('total_inafecta',          _fd(ina) if ina else '')
        l('total_exonerada',         _fd(ex))
        l('total_igv',               _fd(ig))
        l('total_impuestos_bolsas',  _fd(icb))
        l('total_gratuita',          '0.00000000')
        l('total_otros_cargos')
        l('total',                   _fd(tot))
        l('percepcion_tipo')
        l('percepcion_base_imponible')
        l('total_percepcion')
        l('total_incluido_percepcion')
        l('detraccion', 'false')
        l('observaciones')
        l('documento_que_se_modifica_tipo',   doc_mod_tipo)
        l('documento_que_se_modifica_serie',  doc_mod_serie)
        l('documento_que_se_modifica_numero', doc_mod_numero)
        l('tipo_de_nota_de_credito', tipo_nc)
        l('tipo_de_nota_de_debito')
        l('enviar_automaticamente_a_la_sunat', 'false')
        l('enviar_automaticamente_al_cliente', 'false')
        l('condiciones_de_pago')
        l('medio_de_pago')
        l('placa_vehiculo')
        l('orden_compra_servicio')
        l('detraccion_tipo')
        l('detraccion_total')
        l('ubigeo_origen')
        l('direccion_origen')
        l('ubigeo_destino')
        l('direccion_destino')
        l('detalle_viaje')
        l('val_ref_serv_trans')
        l('val_ref_carga_efec')
        l('val_ref_carga_util')
        l('formato_de_pdf')
        l('generado_por_contingencia')

        # ── Items ─────────────────────────────────────────────────
        for item in cpe.get('items', []):
            unidad     = str(item.get('unidad',      'NIU')       or 'NIU')
            codigo     = str(item.get('codigo',      '')          or '')
            descripcion = str(item.get('descripcion', '')         or '')
            cantidad   = float(item.get('cantidad',       0)      or 0)
            val_unit   = float(item.get('valor_unitario', 0)      or 0)   # sin IGV
            pre_unit   = float(item.get('precio_unitario', 0)     or 0)   # con IGV
            subtotal   = float(item.get('valor_total',    0)      or 0)   # sin IGV
            tipo_igv_n = int(item.get('tipo_igv', 1)              or 1)
            igv_item   = float(item.get('igv',  0)                or 0)
            total_item = float(item.get('total', 0)               or 0)
            cod_sunat  = str(item.get('cod_sunat', '10000000')    or '10000000')
            icbper_i   = float(item.get('icbper', 0)              or 0)

            afectacion = TIPO_IGV_MAP.get(tipo_igv_n, '10')

            lines.append(
                f"item|{unidad}|{codigo}|{descripcion}"
                f"|{_fd(cantidad)}|{_fd(val_unit)}|{_fd(pre_unit)}"
                f"||{_fd(subtotal)}|{afectacion}|{_fd(igv_item)}"
                f"|{_fd(total_item)}|false|||{cod_sunat}|||||"
            )

        return "\n".join(lines) + "\n"

    @staticmethod
    def _format_decimal(value):
        return _fd(value, 2)
