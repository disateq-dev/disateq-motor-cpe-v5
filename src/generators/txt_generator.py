"""
txt_generator.py — DisateQ Integrador CPE™ v5.0
Formato APIFAS: string continuo sin saltos de linea.
Decimales: 4 cifras (formato legacy confirmado).
"""

from pathlib import Path

TIPO_IGV_MAP = {
    1: '1',   # Gravado
    2: '8',   # Exonerado
    3: '9',   # Inafecto
    4: '16',  # Exportacion
}


def _fd(value, d=4):
    try:
        return f"{float(value):.{d}f}"
    except (TypeError, ValueError):
        return f"0.{'0' * d}"


def _fecha(val):
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


class TxtGenerator:

    @staticmethod
    def generate(cpe: dict, output_dir: str = "output") -> str:
        p = Path(output_dir)
        p.mkdir(parents=True, exist_ok=True)
        serie  = str(cpe.get('serie', '') or '')
        numero = int(cpe.get('numero', 0) or 0)
        ruc    = str(cpe.get('ruc_emisor', '') or '')
        tipo   = str(cpe.get('tipo_de_comprobante', '02') or '02').zfill(2)
        fp     = p / f"{ruc}-{tipo}-{serie}-{numero:08d}.txt"
        fp.write_text(TxtGenerator._contenido(cpe), encoding='latin-1', newline='')
        return str(fp)

    @staticmethod
    def _contenido(cpe: dict) -> str:
        parts = []

        def f(k, v=''):
            parts.append(f"{k}|{v}|")

        # Cabecera
        tipo_comp = str(cpe.get('tipo_comprobante', '') or cpe.get('tipo_de_comprobante', '2') or '2')
        serie     = str(cpe.get('serie',  '') or '')
        numero    = int(cpe.get('numero', 0)  or 0)
        fecha_emi = _fecha(cpe.get('fecha_de_emision', '') or cpe.get('fecha_emision', ''))
        fecha_vto = _fecha(cpe.get('fecha_de_vencimiento', '') or cpe.get('fecha_vencimiento', ''))
        cli_tipo  = str(cpe.get('cliente_tipo_doc',   '-')            or '-')
        cli_doc   = str(cpe.get('cliente_num_doc',    '00000000')     or '00000000')
        cli_nom   = str(cpe.get('cliente_nombre',     'CLIENTE VARIOS') or 'CLIENTE VARIOS')
        cli_dir   = str(cpe.get('cliente_direccion',  '-')            or '-')
        cli_email = str(cpe.get('cliente_email',      '')             or '')
        gr        = float(cpe.get('total_gravada',         0) or 0)
        ex        = float(cpe.get('total_exonerada',        0) or 0)
        ina       = float(cpe.get('total_inafecta',         0) or 0)
        ig        = float(cpe.get('total_igv',              0) or 0)
        icb       = float(cpe.get('total_impuestos_bolsas', 0) or 0)
        tot       = float(cpe.get('total',                  0) or 0)
        doc_tipo  = str(cpe.get('doc_mod_tipo',        '') or '')
        doc_serie = str(cpe.get('doc_mod_serie',       '') or '')
        doc_num   = str(cpe.get('doc_mod_numero',      '') or '')
        tipo_nc   = str(cpe.get('tipo_nota_credito',   '') or '')

        f('operacion',                          'generar_comprobante')
        f('tipo_de_comprobante',                tipo_comp)
        f('serie',                              serie)
        f('numero',                             str(numero))
        f('sunat_transaction',                  '1')
        f('cliente_tipo_de_documento',          cli_tipo)
        f('cliente_numero_de_documento',        cli_doc)
        f('cliente_denominacion',               cli_nom)
        f('cliente_direccion',                  cli_dir)
        f('cliente_email',                      cli_email)
        f('cliente_email_1')
        f('cliente_email_2')
        f('fecha_de_emision',                   fecha_emi)
        f('fecha_de_vencimiento',               fecha_vto)
        f('moneda',                             '1')
        f('tipo_de_cambio')
        f('porcentaje_de_igv',                  '18.00')
        f('descuento_global')
        f('total_descuento')
        f('total_anticipo')
        f('total_gravada',                      _fd(gr))
        f('total_inafecta',                     _fd(ina) if ina else '')
        f('total_exonerada',                    _fd(ex))
        f('total_igv',                          _fd(ig))
        f('total_impuestos_bolsas',             _fd(icb))
        f('total_gratuita',                     '0.0000')
        f('total_otros_cargos')
        f('total',                              _fd(tot))
        f('percepcion_tipo')
        f('percepcion_base_imponible')
        f('total_percepcion')
        f('total_incluido_percepcion')
        f('detraccion',                         'false')
        f('observaciones')
        f('documento_que_se_modifica_tipo',     doc_tipo)
        f('documento_que_se_modifica_serie',    doc_serie)
        f('documento_que_se_modifica_numero',   doc_num)
        f('tipo_de_nota_de_credito',            tipo_nc)
        f('tipo_de_nota_de_debito')
        f('enviar_automaticamente_a_la_sunat',  'false')
        f('enviar_automaticamente_al_cliente',  'false')
        f('condiciones_de_pago')
        f('medio_de_pago')
        f('placa_vehiculo')
        f('orden_compra_servicio')
        f('detraccion_tipo')
        f('detraccion_total')
        f('ubigeo_origen')
        f('direccion_origen')
        f('ubigeo_destino')
        f('direccion_destino')
        f('detalle_viaje')
        f('val_ref_serv_trans')
        f('val_ref_carga_efec')
        f('val_ref_carga_util')
        f('formato_de_pdf')
        f('generado_por_contingencia')

        # Items
        for item in cpe.get('items', []):
            unidad      = str(item.get('unidad',          'NIU') or 'NIU')
            codigo      = str(item.get('codigo',          '')    or '')
            descripcion = str(item.get('descripcion',     '')    or codigo)
            cantidad    = float(item.get('cantidad',      0)     or 0)
            val_unit    = float(item.get('valor_unitario',0)     or 0)
            pre_unit    = float(item.get('precio_unitario',0)    or 0)
            subtotal    = float(item.get('valor_total',   0)     or 0)
            tipo_igv_n  = int(item.get('tipo_igv',        1)     or 1)
            igv_item    = float(item.get('igv',           0)     or 0)
            total_item  = float(item.get('total',         0)     or 0)
            cod_sunat   = str(item.get('cod_sunat', '10000000')  or '10000000')
            afectacion  = TIPO_IGV_MAP.get(tipo_igv_n, '1')
            cant_str    = str(int(cantidad)) if cantidad == int(cantidad) else _fd(cantidad)

            parts.append(
                f"item|{unidad}|{codigo}|{descripcion}"
                f"|{cant_str}|{_fd(val_unit, 8)}|{_fd(pre_unit, 8)}"
                f"||{_fd(subtotal)}|{afectacion}|{_fd(igv_item)}"
                f"|{_fd(total_item)}|false|||{cod_sunat}|||||"
            )

        return "".join(parts)

    @staticmethod
    def _format_decimal(value):
        return _fd(value, 2)
