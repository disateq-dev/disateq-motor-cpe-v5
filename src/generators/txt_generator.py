"""
txt_generator.py — Motor CPE DisateQ™ v3.0
Formato APIFAS: clave|valor| por linea + item|... al final
"""
from decimal import Decimal
from pathlib import Path

def _get(cpe, *keys):
    for key in keys:
        if key in cpe: return cpe[key]
    for s in ('comprobante','cliente','totales'):
        sub = cpe.get(s,{})
        for key in keys:
            if key in sub: return sub[key]
    return None

def _fmt_fecha(val):
    if not val: return ''
    v = str(val).strip()
    if len(v)==10 and v[4]=='-': return f"{v[8:10]}-{v[5:7]}-{v[:4]}"
    if len(v)==8 and v.isdigit(): return f"{v[6:8]}-{v[4:6]}-{v[:4]}"
    return v

def _fd(value, d=8):
    try: return f"{float(value):.{d}f}"
    except: return f"0.{'0'*d}"

def _tipo_comp(tipo_doc):
    return {'01':'1','03':'2','07':'3','08':'4'}.get(str(tipo_doc).zfill(2),'2')

def _cli_tipo(tipo_doc, tipo_comp):
    t = str(tipo_doc).strip()
    if tipo_comp=='2' and t in ('','1','-'): return '-'
    return t if t else '6'

class TxtGenerator:

    @staticmethod
    def generate(cpe, output_dir="output"):
        p = Path(output_dir)
        p.mkdir(parents=True, exist_ok=True)
        serie  = str(_get(cpe,'serie') or '')
        numero = int(_get(cpe,'numero') or 0)
        fp = p / f"{serie}-{numero:08d}.txt"
        fp.write_text(TxtGenerator._contenido(cpe), encoding='utf-8')
        return str(fp)

    @staticmethod
    def _contenido(cpe):
        cl = cpe.get('cliente',{})
        to = cpe.get('totales',{})
        it = cpe.get('items',[])
        td  = str(_get(cpe,'tipo_doc') or '03')
        tc  = _tipo_comp(td)
        ser = str(_get(cpe,'serie') or '')
        num = int(_get(cpe,'numero') or 0)
        mon = '1' if str(_get(cpe,'moneda') or 'PEN')=='PEN' else '2'
        fec = _fmt_fecha(str(_get(cpe,'fecha_str','fecha_emision') or ''))
        ct  = _cli_tipo(cl.get('tipo_doc',''), tc)
        cd  = cl.get('numero_doc','00000000') or '00000000'
        cn  = cl.get('denominacion','CLIENTE VARIOS') or 'CLIENTE VARIOS'
        cdi = cl.get('direccion','-') or '-'
        gr  = float(to.get('gravada',0) or 0)
        ex  = float(to.get('exonerada',0) or 0)
        ina = float(to.get('inafecta',0) or 0)
        ig  = float(to.get('igv',0) or 0)
        icb = float(to.get('icbper',0) or 0)
        tot = float(to.get('total',0) or 0)
        L = []
        def l(k,v=''): L.append(f"{k}|{v}|")
        l('operacion','generar_comprobante')
        l('tipo_de_comprobante',tc)
        l('serie',ser); l('numero',str(num))
        l('sunat_transaction','1')
        l('cliente_tipo_de_documento',ct)
        l('cliente_numero_de_documento',cd)
        l('cliente_denominacion',cn)
        l('cliente_direccion',cdi)
        l('cliente_email'); l('cliente_email_1'); l('cliente_email_2')
        l('fecha_de_emision',fec); l('fecha_de_vencimiento')
        l('moneda',mon); l('tipo_de_cambio')
        l('porcentaje_de_igv','18.00')
        l('descuento_global'); l('total_descuento'); l('total_anticipo')
        l('total_gravada',_fd(gr))
        l('total_inafecta',_fd(ina) if ina else '')
        l('total_exonerada',_fd(ex))
        l('total_igv',_fd(ig))
        l('total_impuestos_bolsas',_fd(icb))
        l('total_gratuita','0.00000000'); l('total_otros_cargos')
        l('total',_fd(tot))
        l('percepcion_tipo'); l('percepcion_base_imponible')
        l('total_percepcion'); l('total_incluido_percepcion')
        l('detraccion','false'); l('observaciones')
        l('documento_que_se_modifica_tipo'); l('documento_que_se_modifica_serie')
        l('documento_que_se_modifica_numero')
        l('tipo_de_nota_de_credito'); l('tipo_de_nota_de_debito')
        l('enviar_automaticamente_a_la_sunat','false')
        l('enviar_automaticamente_al_cliente','false')
        l('condiciones_de_pago'); l('medio_de_pago'); l('placa_vehiculo')
        l('orden_compra_servicio'); l('detraccion_tipo'); l('detraccion_total')
        l('ubigeo_origen'); l('direccion_origen')
        l('ubigeo_destino'); l('direccion_destino')
        l('detalle_viaje'); l('val_ref_serv_trans')
        l('val_ref_carga_efec'); l('val_ref_carga_util')
        l('formato_de_pdf'); l('generado_por_contingencia')
        for i in it:
            u  = i.get('unidad','NIU')
            co = i.get('codigo','')
            de = i.get('descripcion','')
            ca = float(i.get('cantidad',0) or 0)
            ps = float(i.get('precio_sin_igv') or i.get('valor_unitario') or 0)
            pc = float(i.get('precio_con_igv') or i.get('precio_unitario') or 0)
            su = float(i.get('subtotal_sin_igv',0) or 0)
            af = i.get('afectacion_igv','10')
            ig2= float(i.get('igv',0) or 0)
            ti = float(i.get('total',0) or 0)
            un = i.get('unspsc','10000000')
            L.append(f"item|{u}|{co}|{de}|{_fd(ca)}|{_fd(ps)}|{_fd(pc)}||{_fd(su)}|{af}|{_fd(ig2)}|{_fd(ti)}|false|||{un}|||||")
        return "\n".join(L)+"\n"

    @staticmethod
    def _format_decimal(value):
        return _fd(value, 2)
