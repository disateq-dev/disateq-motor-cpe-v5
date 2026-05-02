"""
smart_mapper.py
===============
Mapeador inteligente de campos — DisateQ CPE™ v5.0
TASK-009: agrega generar(fuente) → entry point desde api.py wizard_generar_contrato_auto()

Usa Claude API para sugerir mapeo de campos del sistema origen
a la estructura estándar del Motor CPE.

Con internet  → Claude API sugiere mapeo automático (~90% precisión)
Sin internet  → Heurísticas mejoradas + campos candidatos ordenados
"""

import json
import re
from typing import Dict, List, Optional
from datetime import datetime


# ================================================================
# ESTRUCTURA ESTÁNDAR CPE — Lo que el Motor necesita
# ================================================================

CAMPOS_CPE = {
    'comprobantes': {
        'tipo_doc':         {'descripcion': 'Tipo de comprobante (B=Boleta, F=Factura)', 'requerido': True, 'tipo_dato': 'texto'},
        'serie':            {'descripcion': 'Serie del comprobante (ej: 001, B001)',      'requerido': True, 'tipo_dato': 'texto'},
        'numero':           {'descripcion': 'Número correlativo del comprobante',          'requerido': True, 'tipo_dato': 'numero'},
        'fecha':            {'descripcion': 'Fecha de emisión del comprobante',            'requerido': True, 'tipo_dato': 'fecha'},
        'total':            {'descripcion': 'Importe total incluido IGV',                  'requerido': True, 'tipo_dato': 'decimal'},
        'ruc_cliente':      {'descripcion': 'RUC o DNI del cliente',                       'requerido': False, 'tipo_dato': 'texto'},
        'nombre_cliente':   {'descripcion': 'Nombre o razón social del cliente',           'requerido': False, 'tipo_dato': 'texto'},
        'direccion':        {'descripcion': 'Dirección del cliente',                       'requerido': False, 'tipo_dato': 'texto'},
        'subtotal':         {'descripcion': 'Base imponible (sin IGV)',                    'requerido': False, 'tipo_dato': 'decimal'},
        'igv':              {'descripcion': 'Monto de IGV',                                'requerido': False, 'tipo_dato': 'decimal'},
        'estado_pendiente': {'descripcion': 'Campo flag de pendiente de envío',            'requerido': True,  'tipo_dato': 'texto'},
    },
    'items': {
        'codigo':      {'descripcion': 'Código del producto',           'requerido': False, 'tipo_dato': 'texto'},
        'descripcion': {'descripcion': 'Nombre o descripción',          'requerido': True,  'tipo_dato': 'texto'},
        'cantidad':    {'descripcion': 'Cantidad vendida',               'requerido': True,  'tipo_dato': 'decimal'},
        'precio':      {'descripcion': 'Precio unitario con IGV',        'requerido': True,  'tipo_dato': 'decimal'},
        'subtotal':    {'descripcion': 'Valor de venta sin IGV',         'requerido': True,  'tipo_dato': 'decimal'},
        'igv':         {'descripcion': 'IGV del item',                   'requerido': True,  'tipo_dato': 'decimal'},
        'total':       {'descripcion': 'Total del item con IGV',         'requerido': True,  'tipo_dato': 'decimal'},
        'campo_union': {'descripcion': 'Campo que une items con comprobantes', 'requerido': True, 'tipo_dato': 'texto'},
    },
    'anulaciones': {
        'tipo_doc':      {'descripcion': 'Tipo de comprobante a anular',    'requerido': True, 'tipo_dato': 'texto'},
        'serie':         {'descripcion': 'Serie del comprobante a anular',  'requerido': True, 'tipo_dato': 'texto'},
        'numero':        {'descripcion': 'Número del comprobante a anular', 'requerido': True, 'tipo_dato': 'numero'},
        'fecha_emision': {'descripcion': 'Fecha de emisión original',       'requerido': True, 'tipo_dato': 'fecha'},
        'motivo':        {'descripcion': 'Motivo de anulación',             'requerido': True, 'tipo_dato': 'texto'},
    }
}


class SmartMapper:
    """
    Mapeador inteligente de campos.
    Usa Claude API si hay internet, heurísticas si no.
    """

    def __init__(self, api_key: str = None):
        self.api_key   = api_key
        self._tiene_ia = False
        self._verificar_ia()

    def _verificar_ia(self):
        if not self.api_key:
            import os
            self.api_key = os.environ.get('ANTHROPIC_API_KEY') or self._leer_api_key_config()
        if self.api_key:
            try:
                import urllib.request
                urllib.request.urlopen('https://api.anthropic.com', timeout=3)
                self._tiene_ia = True
            except Exception:
                self._tiene_ia = False

    def _leer_api_key_config(self) -> Optional[str]:
        try:
            import yaml
            from pathlib import Path
            cfg_path = Path('config/disateq.yaml')
            if cfg_path.exists():
                with open(cfg_path, encoding='utf-8') as f:
                    cfg = yaml.safe_load(f)
                return cfg.get('anthropic', {}).get('api_key')
        except Exception:
            pass
        return None

    # ================================================================
    # TASK-009 — ENTRY POINT DESDE API.PY
    # ================================================================

    def generar(self, fuente: dict) -> dict:
        """
        TASK-009 — Entry point desde api.py wizard_generar_contrato_auto().

        fuente: {tipo, ruta} del wizard paso 2

        Flujo:
          1. SourceExplorer.explorar_rapido() → reporte de estructura DBF
          2. self.mapear(reporte)             → mapeo heurístico o IA con scores
          3. _mapeo_a_contrato(mapeo)         → contrato formato GenericAdapter v5

        Retorna:
          { score: float, contrato: dict }
          score >= 0.80 → wizard avanza automático (sin input manual)
          score <  0.80 → wizard muestra campos pendientes al técnico
        """
        from src.tools.source_explorer import SourceExplorer

        tipo = fuente.get("tipo", "dbf").lower()
        ruta = fuente.get("ruta", "")

        try:
            explorer = SourceExplorer()
            if tipo in ("dbf", "excel", "csv", "access"):
                reporte = explorer.explorar_rapido(tipo=tipo, ruta=ruta)
            else:
                reporte = explorer.explorar(
                    tipo       = tipo,
                    servidor   = fuente.get("host", ""),
                    base_datos = fuente.get("database", ""),
                    usuario    = fuente.get("usuario", ""),
                    clave      = fuente.get("password", ""),
                    puerto     = fuente.get("puerto"),
                )
        except Exception as exc:
            return {"score": 0.0, "contrato": {}, "error": str(exc)}

        mapeo    = self.mapear(reporte)
        score    = float(mapeo.get("confianza", 0))
        contrato = self._mapeo_a_contrato(mapeo, fuente)

        return {"score": score, "contrato": contrato}

    def _mapeo_a_contrato(self, mapeo: dict, fuente: dict) -> dict:
        """
        Convierte el dict de mapeo SmartMapper al formato contrato
        que GenericAdapter v5 y wizard_service._build_contrato_yaml() esperan.

        Estructura destino (igual que buildContratoActual() en wizard.js):
          tabla, flag_campo, flag_valor, flag_tipo, campos{}, items{}
        """
        tablas = mapeo.get("tablas", {})
        comp   = mapeo.get("comprobantes", {})
        items  = mapeo.get("items", {})

        # ── Flag de pendiente ─────────────────────────────────────
        flag_campo = comp.get("estado_pendiente", "")
        flag_valor = comp.get("valor_pendiente", "2")

        # Detectar tipo del valor del flag
        try:
            int(str(flag_valor).strip())
            flag_tipo = "integer"
        except (ValueError, TypeError):
            flag_tipo = "string"

        # ── Campos de comprobante (filtrar no resueltos) ───────────
        campos_comp = {
            "numero":         comp.get("numero"),
            "serie":          comp.get("serie"),
            "tipo_doc":       comp.get("tipo_doc"),
            "fecha":          comp.get("fecha"),
            "ruc_cliente":    comp.get("ruc_cliente"),
            "nombre_cliente": comp.get("nombre_cliente"),
            "total":          comp.get("total"),
        }
        campos_comp = {
            k: v for k, v in campos_comp.items()
            if v and not str(v).startswith("__")
        }

        # ── Items (filtrar no resueltos) ───────────────────────────
        items_out = {
            "tabla":       tablas.get("items", ""),
            "join_campo":  items.get("campo_union", ""),
            "codigo":      items.get("codigo", ""),
            "descripcion": items.get("descripcion", ""),
            "cantidad":    items.get("cantidad", ""),
            "precio":      items.get("precio", ""),
        }
        items_out = {
            k: v for k, v in items_out.items()
            if v and not str(v).startswith("__")
        }

        return {
            "tabla":      tablas.get("comprobantes", ""),
            "flag_campo": flag_campo,
            "flag_valor": flag_valor,
            "flag_tipo":  flag_tipo,
            "campos":     campos_comp,
            "items":      items_out,
        }

    # ================================================================
    # ENTRY POINT — mapear(reporte)
    # ================================================================

    def mapear(self,
               reporte: Dict,
               tabla_comp: str = None,
               tabla_items: str = None,
               tabla_anulaciones: str = None) -> Dict:
        """
        Genera mapeo inteligente de campos desde un reporte de SourceExplorer.
        """
        tablas = reporte.get('tablas', {})

        if not tabla_comp:
            tabla_comp = self._detectar_tabla_comp(tablas)
        if not tabla_items:
            tabla_items = self._detectar_tabla_items(tablas)
        if not tabla_anulaciones:
            tabla_anulaciones = self._detectar_tabla_anulaciones(tablas)

        if self._tiene_ia:
            return self._mapear_con_ia(reporte, tabla_comp, tabla_items, tabla_anulaciones)
        else:
            return self._mapear_heuristica(reporte, tabla_comp, tabla_items, tabla_anulaciones)

    # ================================================================
    # MAPEO CON IA
    # ================================================================

    def _mapear_con_ia(self, reporte, tabla_comp, tabla_items, tabla_anulaciones) -> Dict:
        import urllib.request

        contexto = self._preparar_contexto_ia(reporte, tabla_comp, tabla_items, tabla_anulaciones)

        prompt = f"""Eres un experto en sistemas de facturación electrónica SUNAT (Perú).

Analiza esta estructura de base de datos y mapea sus campos a la estructura estándar del Motor CPE DisateQ™.

ESTRUCTURA DEL SISTEMA:
{json.dumps(contexto, ensure_ascii=False, indent=2)}

ESTRUCTURA ESTÁNDAR CPE REQUERIDA:
{json.dumps(CAMPOS_CPE, ensure_ascii=False, indent=2)}

Responde SOLO con un JSON válido con esta estructura exacta:
{{
  "comprobantes": {{
    "tipo_doc": "NOMBRE_CAMPO o null",
    "serie": "NOMBRE_CAMPO o null",
    "numero": "NOMBRE_CAMPO o null",
    "fecha": "NOMBRE_CAMPO o null",
    "total": "NOMBRE_CAMPO o null",
    "ruc_cliente": "NOMBRE_CAMPO o null",
    "nombre_cliente": "NOMBRE_CAMPO o null",
    "subtotal": "NOMBRE_CAMPO o null",
    "igv": "NOMBRE_CAMPO o null",
    "estado_pendiente": "NOMBRE_CAMPO o null",
    "valor_pendiente": "VALOR que indica pendiente"
  }},
  "items": {{
    "codigo": "NOMBRE_CAMPO o null",
    "descripcion": "NOMBRE_CAMPO o null",
    "cantidad": "NOMBRE_CAMPO o null",
    "precio": "NOMBRE_CAMPO o null",
    "subtotal": "NOMBRE_CAMPO o null",
    "igv": "NOMBRE_CAMPO o null",
    "total": "NOMBRE_CAMPO o null",
    "campo_union": "NOMBRE_CAMPO que une items con comprobantes"
  }},
  "anulaciones": {{
    "tipo_doc": "NOMBRE_CAMPO o null",
    "serie": "NOMBRE_CAMPO o null",
    "numero": "NOMBRE_CAMPO o null",
    "fecha_emision": "NOMBRE_CAMPO o null",
    "motivo": "NOMBRE_CAMPO o null"
  }},
  "transformaciones": {{
    "tipo_doc": {{"B": "03", "F": "01"}},
    "fecha_formato": "YYYYMMDD",
    "moneda": "PEN"
  }},
  "confianza": 0.85,
  "advertencias": []
}}

Solo devuelve el JSON, sin texto adicional."""

        try:
            data = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            }).encode('utf-8')

            req = urllib.request.Request(
                'https://api.anthropic.com/v1/messages',
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': self.api_key,
                    'anthropic-version': '2023-06-01'
                }
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                texto  = result['content'][0]['text'].strip()
                texto  = re.sub(r'^```json\s*', '', texto)
                texto  = re.sub(r'\s*```$', '', texto)

                mapeo = json.loads(texto)
                mapeo['metodo'] = 'ia'
                mapeo['tablas'] = {
                    'comprobantes': tabla_comp,
                    'items':        tabla_items,
                    'anulaciones':  tabla_anulaciones,
                }
                return mapeo

        except Exception as e:
            return self._mapear_heuristica(reporte, tabla_comp, tabla_items, tabla_anulaciones)

    def _preparar_contexto_ia(self, reporte, tabla_comp, tabla_items, tabla_anulaciones) -> Dict:
        tablas = reporte.get('tablas', {})
        ctx = {}
        for nombre_tabla in [tabla_comp, tabla_items, tabla_anulaciones]:
            if nombre_tabla and nombre_tabla in tablas:
                t = tablas[nombre_tabla]
                ctx[nombre_tabla] = {
                    'campos':    [c['nombre'] for c in t.get('campos', [])],
                    'muestra':   t.get('muestra', [])[:2],
                    'registros': t.get('total_registros', 0),
                }
        return ctx

    # ================================================================
    # MAPEO HEURÍSTICO (sin IA)
    # ================================================================

    def _mapear_heuristica(self, reporte, tabla_comp, tabla_items, tabla_anulaciones) -> Dict:
        tablas = reporte.get('tablas', {})

        mapeo_comp  = self._mapear_tabla_heuristica(tablas.get(tabla_comp,  {}), 'comprobantes')
        mapeo_items = self._mapear_tabla_heuristica(tablas.get(tabla_items, {}), 'items')
        mapeo_anul  = self._mapear_tabla_heuristica(tablas.get(tabla_anulaciones, {}), 'anulaciones')

        transf      = self._detectar_transformaciones(tablas.get(tabla_comp, {}), mapeo_comp)
        advertencias = self._generar_advertencias(mapeo_comp, mapeo_items, mapeo_anul)
        confianza   = self._calcular_confianza(mapeo_comp, mapeo_items)

        return {
            'metodo':    'heuristica',
            'confianza': confianza,
            'tablas': {
                'comprobantes': tabla_comp,
                'items':        tabla_items,
                'anulaciones':  tabla_anulaciones,
            },
            'comprobantes':     mapeo_comp,
            'items':            mapeo_items,
            'anulaciones':      mapeo_anul,
            'transformaciones': transf,
            'advertencias':     advertencias,
        }

    def _mapear_tabla_heuristica(self, tabla_info: Dict, tipo: str) -> Dict:
        if not tabla_info:
            return {}

        campos       = [c['nombre'] for c in tabla_info.get('campos', [])]
        campos_lower = {c.lower(): c for c in campos}
        muestra      = tabla_info.get('muestra', [])

        PATRONES = {
            'comprobantes': {
                'tipo_doc':         ['tipo_factu', 'tipo_doc', 'tipo_comp', 'tipo', 'cod_tipo'],
                'serie':            ['serie_fact', 'serie_fac', 'serie', 'num_serie'],
                'numero':           ['numero_fac', 'numero_doc', 'nro_doc', 'num_doc', 'numero', 'correlat'],
                'fecha':            ['fecha_fact', 'fecha_doc', 'fecha_emi', 'fec_emis', 'fecha_docu', 'fecha_venta'],
                'total':            ['total_fact', 'total_doc', 'monto_tot', 'importe_t', 'total_venta', 'real_factu'],
                'ruc_cliente':      ['ruc_client', 'num_doc_cl', 'ruc', 'documento', 'doc_cliente'],
                'nombre_cliente':   ['nombre_cli', 'razon_soci', 'nom_client', 'cliente'],
                'direccion':        ['direccion', 'dir_client', 'domicilio'],
                'subtotal':         ['subtotal', 'val_venta', 'valor_ven', 'base_impo', 'monto_fact'],
                'igv':              ['igv', 'monto_igv', 'importe_i', 'igv_factur'],
                'estado_pendiente': ['flag_envio', 'estado', 'flag_cpe', 'enviado', 'flag'],
            },
            'items': {
                'codigo':      ['codigo_pro', 'cod_prod', 'cod_articu', 'codigo', 'cod_item'],
                'descripcion': ['descripcio', 'descripcion', 'nombre_pro', 'nom_prod', 'detalle'],
                'cantidad':    ['cantidad_p', 'cantidad', 'cant_venta', 'cant', 'fraccion_p'],
                'precio':      ['precio_uni', 'precio_con', 'precio_ven', 'precio'],
                'subtotal':    ['monto_pedi', 'subtotal', 'val_venta', 'importe'],
                'igv':         ['igv_pedido', 'igv_item', 'igv'],
                'total':       ['real_pedid', 'total_item', 'total'],
                'campo_union': ['numero_fac', 'nro_doc', 'cod_factur', 'numero_doc'],
            },
            'anulaciones': {
                'tipo_doc':      ['tipo_factu', 'tipo_doc', 'tipo'],
                'serie':         ['serie_nota', 'serie_fact', 'serie'],
                'numero':        ['numero_not', 'numero_fac', 'numero'],
                'fecha_emision': ['fecha_nota', 'fecha_fact', 'fecha_emi', 'fecha'],
                'motivo':        ['tipo_motiv', 'motivo', 'descripcion'],
            },
        }

        resultado = {}
        for campo_cpe, candidatos in PATRONES.get(tipo, {}).items():
            encontrado = None
            for candidato in candidatos:
                if candidato in campos_lower:
                    encontrado = campos_lower[candidato]
                    break
            if not encontrado:
                for candidato in candidatos:
                    for campo_orig in campos_lower:
                        if candidato[:6] in campo_orig or campo_orig[:6] in candidato:
                            encontrado = campos_lower[campo_orig]
                            break
                    if encontrado:
                        break
            resultado[campo_cpe] = encontrado

        # Detectar valor del flag desde muestra
        if tipo == 'comprobantes' and resultado.get('estado_pendiente') and muestra:
            campo_estado = resultado['estado_pendiente']
            valores = list(set([
                str(r.get(campo_estado, '')) for r in muestra
                if r.get(campo_estado) is not None
            ]))
            resultado['_valores_estado'] = valores[:5]
            # Intentar detectar valor pendiente conocido
            for v in valores:
                if str(v).strip() in ('2', 'P', 'PENDIENTE', '0', 'N'):
                    resultado['valor_pendiente'] = str(v).strip()
                    break

        return resultado

    def _detectar_transformaciones(self, tabla_info: Dict, mapeo: Dict) -> Dict:
        muestra = tabla_info.get('muestra', [])
        transf  = {'moneda': 'PEN'}

        campo_fecha = mapeo.get('fecha')
        if campo_fecha and muestra:
            for row in muestra:
                val = str(row.get(campo_fecha, ''))
                if val and len(val) == 8 and val.isdigit():
                    transf['fecha_formato'] = 'YYYYMMDD'
                    break
                elif val and '/' in val:
                    transf['fecha_formato'] = 'DD/MM/YYYY'
                    break
                elif val and len(val) >= 10 and val[4] == '-':
                    transf['fecha_formato'] = 'YYYY-MM-DD'
                    break

        campo_tipo = mapeo.get('tipo_doc')
        if campo_tipo and muestra:
            valores = list(set([
                str(row.get(campo_tipo, '')).strip()
                for row in muestra if row.get(campo_tipo)
            ]))
            tipo_map = {}
            for v in valores:
                if v in ('B', 'BOL', 'BOLETA', '03', '3'):
                    tipo_map[v] = '03'
                elif v in ('F', 'FAC', 'FACTURA', '01', '1'):
                    tipo_map[v] = '01'
                elif v in ('T', 'TK', 'TICKET'):
                    tipo_map[v] = '03'
                else:
                    tipo_map[v] = '__COMPLETAR'
            if tipo_map:
                transf['tipo_doc'] = tipo_map

        if 'tipo_doc' not in transf:
            transf['tipo_doc'] = {'B': '03', 'F': '01'}

        return transf

    def _calcular_confianza(self, mapeo_comp: Dict, mapeo_items: Dict) -> float:
        campos_req_comp  = ['tipo_doc', 'serie', 'numero', 'fecha', 'total', 'estado_pendiente']
        campos_req_items = ['descripcion', 'cantidad', 'total', 'campo_union']

        enc_comp  = sum(1 for c in campos_req_comp  if mapeo_comp.get(c) and not str(mapeo_comp[c]).startswith('__'))
        enc_items = sum(1 for c in campos_req_items if mapeo_items.get(c) and not str(mapeo_items[c]).startswith('__'))

        conf_comp  = enc_comp  / len(campos_req_comp)
        conf_items = enc_items / len(campos_req_items) if mapeo_items else 0.5

        return round(conf_comp * 0.7 + conf_items * 0.3, 2)

    def _generar_advertencias(self, comp, items, anul) -> List[str]:
        advertencias = []
        for c in ['tipo_doc', 'serie', 'numero', 'fecha', 'total', 'estado_pendiente']:
            if not comp.get(c) or str(comp.get(c, '')).startswith('__'):
                advertencias.append(f"Campo requerido no detectado en comprobantes: {c}")
        if items and not items.get('campo_union'):
            advertencias.append("No se detectó campo de unión entre items y comprobantes")
        return advertencias

    # ================================================================
    # DETECCIÓN DE TABLAS
    # ================================================================

    def _detectar_tabla_comp(self, tablas: Dict) -> Optional[str]:
        candidatos = ['enviosffee', 'facturas', 'ventas', 'comprobantes',
                      'factura', 'venta', 'documento', 'cabecera', 'cab_venta']
        for c in candidatos:
            if c in tablas:
                return c
        return max(tablas.keys(), key=lambda t: tablas[t].get('total_registros', 0)) if tablas else None

    def _detectar_tabla_items(self, tablas: Dict) -> Optional[str]:
        candidatos = ['detalleventa', 'detalle_ventas', 'items', 'detalle',
                      'lineas', 'detalles', 'factura_det', 'det_venta']
        for c in candidatos:
            if c in tablas:
                return c
        return None

    def _detectar_tabla_anulaciones(self, tablas: Dict) -> Optional[str]:
        candidatos = ['notacredito', 'anulaciones', 'bajas', 'nota_credito',
                      'anulacion', 'baja', 'cancelaciones']
        for c in candidatos:
            if c in tablas:
                return c
        return None

    # ================================================================
    # GENERAR DOCUMENTOS (legacy — no modificados)
    # ================================================================

    def generar_contrato_motor(self, mapeo: Dict, config_cliente: Dict = None) -> Dict:
        tablas = mapeo.get('tablas', {})
        transf = mapeo.get('transformaciones', {})
        return {
            'version': '1.0',
            'generado': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metodo_mapeo': mapeo.get('metodo', 'heuristica'),
            'confianza': mapeo.get('confianza', 0),
            'fuente': config_cliente or {},
            'comprobantes': {
                'tabla': tablas.get('comprobantes', ''),
                'filtro': {
                    'campo': mapeo['comprobantes'].get('estado_pendiente', ''),
                    'valor': mapeo['comprobantes'].get('valor_pendiente', '__COMPLETAR'),
                },
                'campos': {k: v for k, v in mapeo.get('comprobantes', {}).items()
                           if not k.startswith('_') and k != 'valor_pendiente'},
            },
            'items': {
                'tabla': tablas.get('items', ''),
                'join':  mapeo.get('items', {}).get('campo_union', '__COMPLETAR'),
                'campos': {k: v for k, v in mapeo.get('items', {}).items() if k != 'campo_union'},
            } if tablas.get('items') else None,
            'anulaciones': {
                'tabla':  tablas.get('anulaciones', ''),
                'campos': mapeo.get('anulaciones', {}),
            } if tablas.get('anulaciones') else None,
            'transformaciones': transf,
            'advertencias': mapeo.get('advertencias', []),
        }

    def generar_contrato_programador(self, mapeo: Dict, nombre_sistema: str = 'Sistema') -> str:
        """Genera documento legible para el programador del sistema legacy."""
        tablas = mapeo.get('tablas', {})
        comp   = mapeo.get('comprobantes', {})
        items  = mapeo.get('items', {})
        transf = mapeo.get('transformaciones', {})
        advert = mapeo.get('advertencias', [])

        lineas = [
            "# ============================================================",
            f"# CONTRATO DE DATOS — DisateQ CPE™",
            f"# Fecha: {datetime.now().strftime('%d/%m/%Y')}",
            "# ============================================================",
            "",
            "tabla_comprobantes: " + str(tablas.get('comprobantes', '[COMPLETAR]')),
            "",
            "campos_comprobantes:",
        ]

        for campo, info in CAMPOS_CPE['comprobantes'].items():
            valor = comp.get(campo)
            req   = "REQUERIDO" if info['requerido'] else "opcional"
            lineas.append(f"  # {info['descripcion']} ({req})")
            if valor and not str(valor).startswith('__'):
                lineas.append(f"  {campo}: {valor}  # detectado")
            else:
                lineas.append(f"  {campo}: '[COMPLETAR]'")
            lineas.append("")

        if advert:
            lineas += ["", "# CAMPOS NO DETECTADOS:"]
            for a in advert:
                lineas.append(f"# ⚠  {a}")

        return '\n'.join(lineas)
