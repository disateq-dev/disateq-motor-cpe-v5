"""
smart_mapper.py
===============
Mapeador inteligente de campos — DisateQ CPE™ v4.0

Usa Claude API para sugerir mapeo de campos del sistema origen
a la estructura estándar del Motor CPE.

Con internet  → Claude API sugiere mapeo automático (~90% precisión)
Sin internet  → Heurísticas mejoradas + campos candidatos ordenados

Uso:
    from src.tools.smart_mapper import SmartMapper
    mapper = SmartMapper()
    mapeo  = mapper.mapear(reporte, tabla_comp='enviosffee', tabla_items='detalleventa')
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
        'tipo_doc': {
            'descripcion': 'Tipo de comprobante (B=Boleta, F=Factura)',
            'requerido': True,
            'ejemplo_sunat': '01=Factura, 03=Boleta',
            'tipo_dato': 'texto'
        },
        'serie': {
            'descripcion': 'Serie del comprobante (ej: 001, B001)',
            'requerido': True,
            'tipo_dato': 'texto'
        },
        'numero': {
            'descripcion': 'Número correlativo del comprobante',
            'requerido': True,
            'tipo_dato': 'numero'
        },
        'fecha': {
            'descripcion': 'Fecha de emisión del comprobante',
            'requerido': True,
            'tipo_dato': 'fecha',
            'formatos': 'YYYYMMDD, DD/MM/YYYY, YYYY-MM-DD'
        },
        'total': {
            'descripcion': 'Importe total del comprobante incluido IGV',
            'requerido': True,
            'tipo_dato': 'decimal'
        },
        'ruc_cliente': {
            'descripcion': 'RUC o DNI del cliente (vacío para clientes varios)',
            'requerido': False,
            'tipo_dato': 'texto'
        },
        'nombre_cliente': {
            'descripcion': 'Nombre o razón social del cliente',
            'requerido': False,
            'tipo_dato': 'texto'
        },
        'direccion': {
            'descripcion': 'Dirección del cliente',
            'requerido': False,
            'tipo_dato': 'texto'
        },
        'subtotal': {
            'descripcion': 'Base imponible (sin IGV)',
            'requerido': False,
            'tipo_dato': 'decimal'
        },
        'igv': {
            'descripcion': 'Monto de IGV',
            'requerido': False,
            'tipo_dato': 'decimal'
        },
        'estado_pendiente': {
            'descripcion': 'Valor que indica que el comprobante está pendiente de envío',
            'requerido': True,
            'tipo_dato': 'texto',
            'nota': 'Necesario para el filtro de pendientes'
        }
    },
    'items': {
        'codigo': {
            'descripcion': 'Código del producto',
            'requerido': False,
            'tipo_dato': 'texto'
        },
        'descripcion': {
            'descripcion': 'Nombre o descripción del producto',
            'requerido': True,
            'tipo_dato': 'texto'
        },
        'cantidad': {
            'descripcion': 'Cantidad vendida',
            'requerido': True,
            'tipo_dato': 'decimal'
        },
        'precio': {
            'descripcion': 'Precio unitario con IGV',
            'requerido': True,
            'tipo_dato': 'decimal'
        },
        'subtotal': {
            'descripcion': 'Valor de venta sin IGV',
            'requerido': True,
            'tipo_dato': 'decimal'
        },
        'igv': {
            'descripcion': 'IGV del item',
            'requerido': True,
            'tipo_dato': 'decimal'
        },
        'total': {
            'descripcion': 'Total del item con IGV',
            'requerido': True,
            'tipo_dato': 'decimal'
        },
        'campo_union': {
            'descripcion': 'Campo que une esta tabla con la tabla de comprobantes',
            'requerido': True,
            'tipo_dato': 'texto',
            'nota': 'Ej: NUMERO_FAC, COD_FACTURA, ID_VENTA'
        }
    },
    'anulaciones': {
        'tipo_doc': {
            'descripcion': 'Tipo de comprobante a anular',
            'requerido': True,
            'tipo_dato': 'texto'
        },
        'serie': {
            'descripcion': 'Serie del comprobante a anular',
            'requerido': True,
            'tipo_dato': 'texto'
        },
        'numero': {
            'descripcion': 'Número del comprobante a anular',
            'requerido': True,
            'tipo_dato': 'numero'
        },
        'fecha_emision': {
            'descripcion': 'Fecha de emisión del comprobante original',
            'requerido': True,
            'tipo_dato': 'fecha'
        },
        'motivo': {
            'descripcion': 'Motivo de anulación',
            'requerido': True,
            'tipo_dato': 'texto'
        }
    }
}


class SmartMapper:
    """
    Mapeador inteligente de campos.
    Usa Claude API si hay internet, heurísticas si no.
    """

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: API key de Anthropic. Si None, usa heurísticas.
        """
        self.api_key   = api_key
        self._tiene_ia = False
        self._verificar_ia()

    def _verificar_ia(self):
        """Verifica si hay conexión y API key disponible."""
        if not self.api_key:
            # Intentar leer desde config o variable de entorno
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
        """Lee API key desde config/disateq.yaml si existe."""
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
    # ENTRY POINT
    # ================================================================

    def mapear(self,
               reporte: Dict,
               tabla_comp: str = None,
               tabla_items: str = None,
               tabla_anulaciones: str = None) -> Dict:
        """
        Genera mapeo inteligente de campos.

        Returns:
            {
                'metodo': 'ia' | 'heuristica',
                'confianza': 0.0-1.0,
                'comprobantes': {...},
                'items': {...},
                'anulaciones': {...},
                'transformaciones': {...},
                'advertencias': [...]
            }
        """
        tablas = reporte.get('tablas', {})

        # Auto-detectar tablas si no se especifican
        if not tabla_comp:
            tabla_comp = self._detectar_tabla_comp(tablas)
        if not tabla_items:
            tabla_items = self._detectar_tabla_items(tablas)
        if not tabla_anulaciones:
            tabla_anulaciones = self._detectar_tabla_anulaciones(tablas)

        print(f"\n🧠 SmartMapper iniciando...")
        print(f"   Tabla comprobantes: {tabla_comp}")
        print(f"   Tabla items:        {tabla_items}")
        print(f"   Tabla anulaciones:  {tabla_anulaciones}")

        if self._tiene_ia:
            print(f"   Modo: IA (Claude API) ✅")
            return self._mapear_con_ia(reporte, tabla_comp, tabla_items, tabla_anulaciones)
        else:
            print(f"   Modo: Heurísticas 🔍")
            return self._mapear_heuristica(reporte, tabla_comp, tabla_items, tabla_anulaciones)

    # ================================================================
    # MAPEO CON IA
    # ================================================================

    def _mapear_con_ia(self, reporte, tabla_comp, tabla_items, tabla_anulaciones) -> Dict:
        """Usa Claude API para sugerir mapeo."""
        import urllib.request

        # Preparar contexto para Claude
        contexto = self._preparar_contexto_ia(reporte, tabla_comp, tabla_items, tabla_anulaciones)

        prompt = f"""Eres un experto en sistemas de facturación electrónica SUNAT (Perú).

Analiza esta estructura de base de datos de un sistema de ventas y mapea sus campos 
a la estructura estándar del Motor CPE DisateQ™.

ESTRUCTURA DEL SISTEMA:
{json.dumps(contexto, ensure_ascii=False, indent=2)}

ESTRUCTURA ESTÁNDAR CPE REQUERIDA:
{json.dumps(CAMPOS_CPE, ensure_ascii=False, indent=2)}

Responde SOLO con un JSON válido con esta estructura exacta:
{{
  "comprobantes": {{
    "tipo_doc": "NOMBRE_CAMPO_ORIGEN o null",
    "serie": "NOMBRE_CAMPO_ORIGEN o null",
    "numero": "NOMBRE_CAMPO_ORIGEN o null",
    "fecha": "NOMBRE_CAMPO_ORIGEN o null",
    "total": "NOMBRE_CAMPO_ORIGEN o null",
    "ruc_cliente": "NOMBRE_CAMPO_ORIGEN o null",
    "nombre_cliente": "NOMBRE_CAMPO_ORIGEN o null",
    "direccion": "NOMBRE_CAMPO_ORIGEN o null",
    "subtotal": "NOMBRE_CAMPO_ORIGEN o null",
    "igv": "NOMBRE_CAMPO_ORIGEN o null",
    "estado_pendiente": "NOMBRE_CAMPO_ORIGEN o null",
    "valor_pendiente": "VALOR que indica pendiente (ej: 2, P, N)"
  }},
  "items": {{
    "codigo": "NOMBRE_CAMPO_ORIGEN o null",
    "descripcion": "NOMBRE_CAMPO_ORIGEN o null",
    "cantidad": "NOMBRE_CAMPO_ORIGEN o null",
    "precio": "NOMBRE_CAMPO_ORIGEN o null",
    "subtotal": "NOMBRE_CAMPO_ORIGEN o null",
    "igv": "NOMBRE_CAMPO_ORIGEN o null",
    "total": "NOMBRE_CAMPO_ORIGEN o null",
    "campo_union": "NOMBRE_CAMPO que une items con comprobantes"
  }},
  "anulaciones": {{
    "tipo_doc": "NOMBRE_CAMPO_ORIGEN o null",
    "serie": "NOMBRE_CAMPO_ORIGEN o null",
    "numero": "NOMBRE_CAMPO_ORIGEN o null",
    "fecha_emision": "NOMBRE_CAMPO_ORIGEN o null",
    "motivo": "NOMBRE_CAMPO_ORIGEN o null"
  }},
  "transformaciones": {{
    "tipo_doc": {{"B": "03", "F": "01"}},
    "fecha_formato": "YYYYMMDD",
    "moneda": "PEN"
  }},
  "confianza": 0.85,
  "advertencias": ["lista de campos que no se pudieron mapear con certeza"]
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

                # Limpiar posibles backticks
                texto = re.sub(r'^```json\s*', '', texto)
                texto = re.sub(r'\s*```$', '', texto)

                mapeo = json.loads(texto)
                mapeo['metodo'] = 'ia'
                mapeo['tablas'] = {
                    'comprobantes': tabla_comp,
                    'items':        tabla_items,
                    'anulaciones':  tabla_anulaciones
                }
                print(f"   ✅ Mapeo IA completado — confianza: {mapeo.get('confianza', 0):.0%}")
                return mapeo

        except Exception as e:
            print(f"   ⚠️  Error IA: {e} — usando heurísticas")
            return self._mapear_heuristica(reporte, tabla_comp, tabla_items, tabla_anulaciones)

    def _preparar_contexto_ia(self, reporte, tabla_comp, tabla_items, tabla_anulaciones) -> Dict:
        """Prepara contexto resumido para Claude (no enviar todo el reporte)."""
        tablas = reporte.get('tablas', {})
        ctx = {}

        for nombre_tabla in [tabla_comp, tabla_items, tabla_anulaciones]:
            if nombre_tabla and nombre_tabla in tablas:
                t = tablas[nombre_tabla]
                ctx[nombre_tabla] = {
                    'campos':   [c['nombre'] for c in t.get('campos', [])],
                    'muestra':  t.get('muestra', [])[:2],
                    'registros': t.get('total_registros', 0)
                }
        return ctx

    # ================================================================
    # MAPEO HEURÍSTICO (sin IA)
    # ================================================================

    def _mapear_heuristica(self, reporte, tabla_comp, tabla_items, tabla_anulaciones) -> Dict:
        """Mapeo por heurísticas mejoradas."""
        tablas = reporte.get('tablas', {})

        mapeo_comp  = self._mapear_tabla_heuristica(tablas.get(tabla_comp, {}), 'comprobantes')
        mapeo_items = self._mapear_tabla_heuristica(tablas.get(tabla_items, {}), 'items')
        mapeo_anul  = self._mapear_tabla_heuristica(tablas.get(tabla_anulaciones, {}), 'anulaciones')

        # Detectar transformaciones desde muestra de datos
        transf = self._detectar_transformaciones(tablas.get(tabla_comp, {}), mapeo_comp)

        advertencias = self._generar_advertencias(mapeo_comp, mapeo_items, mapeo_anul)

        confianza = self._calcular_confianza(mapeo_comp, mapeo_items)

        return {
            'metodo':    'heuristica',
            'confianza': confianza,
            'tablas': {
                'comprobantes': tabla_comp,
                'items':        tabla_items,
                'anulaciones':  tabla_anulaciones
            },
            'comprobantes':     mapeo_comp,
            'items':            mapeo_items,
            'anulaciones':      mapeo_anal if (mapeo_anal := mapeo_anul) else {},
            'transformaciones': transf,
            'advertencias':     advertencias
        }

    def _mapear_tabla_heuristica(self, tabla_info: Dict, tipo: str) -> Dict:
        """Mapea campos de una tabla usando heurísticas mejoradas."""
        if not tabla_info:
            return {}

        campos = [c['nombre'] for c in tabla_info.get('campos', [])]
        campos_lower = {c.lower(): c for c in campos}
        muestra = tabla_info.get('muestra', [])

        # Patrones extendidos por campo CPE
        PATRONES = {
            'comprobantes': {
                'tipo_doc':       ['tipo_factu', 'tipo_doc', 'tipo_comp', 'tipo_compr', 'tip_doc', 'tipo', 'cod_tipo', 'tipo_cpe'],
                'serie':          ['serie_fact', 'serie_fac', 'serie', 'num_serie', 'cod_serie', 'serie_cpe'],
                'numero':         ['numero_fac', 'numero_doc', 'nro_doc', 'num_doc', 'numero', 'nrodoc', 'correlat'],
                'fecha':          ['fecha_fact', 'fecha_doc', 'fecha_emi', 'fec_emis', 'fecha_docu', 'fecha_venta', 'fec_venta'],
                'total':          ['total_fact', 'total_doc', 'monto_tot', 'importe_t', 'total_venta', 'tot_venta', 'total_pag'],
                'ruc_cliente':    ['ruc_client', 'num_doc_cl', 'ruc', 'documento', 'doc_cliente', 'num_ruc'],
                'nombre_cliente': ['nombre_cli', 'razon_soci', 'nom_client', 'cliente', 'denominac'],
                'direccion':      ['direccion', 'dir_client', 'domicilio', 'direccion_'],
                'subtotal':       ['subtotal', 'val_venta', 'valor_ven', 'base_impo', 'sub_total'],
                'igv':            ['igv', 'monto_igv', 'importe_i', 'igv_total'],
                'estado_pendiente': ['flag_envio', 'estado', 'flag_cpe', 'enviado', 'estado_env', 'flag']
            },
            'items': {
                'codigo':      ['codigo_pro', 'cod_prod', 'cod_articu', 'codigo', 'cod_item'],
                'descripcion': ['descripcio', 'descripcion', 'nombre_pro', 'nom_prod', 'detalle', 'producto'],
                'cantidad':    ['cantidad_p', 'cantidad', 'cant_venta', 'cant', 'fraccion_p', 'cantidad_v'],
                'precio':      ['precio_uni', 'precio_con', 'precio_ven', 'precio', 'p_unitario'],
                'subtotal':    ['monto_pedi', 'subtotal', 'val_venta', 'importe', 'sub_total'],
                'igv':         ['igv_pedido', 'igv_item', 'igv', 'monto_igv'],
                'total':       ['real_pedid', 'total_item', 'total', 'precio_tot', 'importe_t'],
                'campo_union': ['numero_fac', 'nro_doc', 'cod_factur', 'id_factura', 'numero_doc']
            },
            'anulaciones': {
                'tipo_doc':      ['tipo_factu', 'tipo_doc', 'tipo'],
                'serie':         ['serie_nota', 'serie_fact', 'serie'],
                'numero':        ['numero_not', 'numero_fac', 'numero'],
                'fecha_emision': ['fecha_nota', 'fecha_fact', 'fecha_emi', 'fecha'],
                'motivo':        ['tipo_motiv', 'motivo', 'descripcion', 'razon']
            }
        }

        resultado = {}
        patrones_tipo = PATRONES.get(tipo, {})

        for campo_cpe, candidatos in patrones_tipo.items():
            encontrado = None
            for candidato in candidatos:
                if candidato in campos_lower:
                    encontrado = campos_lower[candidato]
                    break

            # Si no encontró, buscar por substring
            if not encontrado:
                for candidato in candidatos:
                    for campo_orig in campos_lower:
                        if candidato[:6] in campo_orig or campo_orig[:6] in candidato:
                            encontrado = campos_lower[campo_orig]
                            break
                    if encontrado:
                        break

            resultado[campo_cpe] = encontrado

        # Detectar valor de estado pendiente desde muestra
        if tipo == 'comprobantes' and resultado.get('estado_pendiente') and muestra:
            campo_estado = resultado['estado_pendiente']
            valores = list(set([str(r.get(campo_estado, '')) for r in muestra if r.get(campo_estado)]))
            resultado['_valores_estado'] = valores[:5]

        return resultado

    def _detectar_transformaciones(self, tabla_info: Dict, mapeo: Dict) -> Dict:
        """Detecta formato de fecha y valores de tipo_doc desde muestra."""
        muestra  = tabla_info.get('muestra', [])
        transf   = {'moneda': 'PEN'}

        # Detectar formato de fecha
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
                elif val and val[4] == '-':
                    transf['fecha_formato'] = 'YYYY-MM-DD'
                    break

        # Detectar mapeo tipo_doc desde muestra
        campo_tipo = mapeo.get('tipo_doc')
        if campo_tipo and muestra:
            valores = list(set([str(row.get(campo_tipo, '')).strip() for row in muestra if row.get(campo_tipo)]))
            tipo_map = {}
            for v in valores:
                if v in ('B', 'BOL', 'BOLETA', '03', '3'):
                    tipo_map[v] = '03'
                elif v in ('F', 'FAC', 'FACTURA', '01', '1'):
                    tipo_map[v] = '01'
                else:
                    tipo_map[v] = '__COMPLETAR (03=Boleta, 01=Factura)'
            if tipo_map:
                transf['tipo_doc'] = tipo_map

        if 'tipo_doc' not in transf:
            transf['tipo_doc'] = {'B': '03', 'F': '01'}

        return transf

    def _calcular_confianza(self, mapeo_comp: Dict, mapeo_items: Dict) -> float:
        """Calcula nivel de confianza del mapeo."""
        campos_req_comp  = ['tipo_doc', 'serie', 'numero', 'fecha', 'total']
        campos_req_items = ['descripcion', 'cantidad', 'precio', 'total']

        encontrados_comp  = sum(1 for c in campos_req_comp if mapeo_comp.get(c))
        encontrados_items = sum(1 for c in campos_req_items if mapeo_items.get(c))

        conf_comp  = encontrados_comp / len(campos_req_comp)
        conf_items = encontrados_items / len(campos_req_items) if mapeo_items else 0.5

        return round((conf_comp * 0.7 + conf_items * 0.3), 2)

    def _generar_advertencias(self, comp, items, anul) -> List[str]:
        """Genera lista de advertencias sobre campos no mapeados."""
        advertencias = []
        campos_req = ['tipo_doc', 'serie', 'numero', 'fecha', 'total']
        for c in campos_req:
            if not comp.get(c):
                advertencias.append(f"Campo requerido no encontrado en comprobantes: {c}")
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
                      'lineas', 'detalles', 'factura_det', 'det_venta', 'det_factura']
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
    # GENERAR DOCUMENTOS
    # ================================================================

    def generar_contrato_motor(self, mapeo: Dict, config_cliente: Dict = None) -> Dict:
        """
        Genera contrato YAML para el GenericAdapter del Motor.
        Uso interno — técnico DisateQ.
        """
        tablas = mapeo.get('tablas', {})
        transf = mapeo.get('transformaciones', {})

        return {
            'version': '1.0',
            'generado': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metodo_mapeo': mapeo.get('metodo', 'heuristica'),
            'confianza': mapeo.get('confianza', 0),

            'fuente': config_cliente or {},

            'comprobantes': {
                'tabla':  tablas.get('comprobantes', ''),
                'filtro': {
                    'campo': mapeo['comprobantes'].get('estado_pendiente', ''),
                    'valor': mapeo['comprobantes'].get('valor_pendiente', '__COMPLETAR')
                },
                'campos': {k: v for k, v in mapeo.get('comprobantes', {}).items()
                          if not k.startswith('_') and k != 'valor_pendiente'}
            },

            'items': {
                'tabla': tablas.get('items', ''),
                'join':  mapeo.get('items', {}).get('campo_union', '__COMPLETAR'),
                'campos': {k: v for k, v in mapeo.get('items', {}).items()
                          if k != 'campo_union'}
            } if tablas.get('items') else None,

            'anulaciones': {
                'tabla':  tablas.get('anulaciones', ''),
                'campos': mapeo.get('anulaciones', {})
            } if tablas.get('anulaciones') else None,

            'transformaciones': transf,
            'advertencias': mapeo.get('advertencias', [])
        }

    def generar_contrato_programador(self, mapeo: Dict, nombre_sistema: str = 'Sistema') -> str:
        """
        Genera documento legible para el programador del sistema legacy.
        Sin jerga técnica, en español claro.
        Returns: string YAML con comentarios explicativos
        """
        tablas  = mapeo.get('tablas', {})
        comp    = mapeo.get('comprobantes', {})
        items   = mapeo.get('items', {})
        transf  = mapeo.get('transformaciones', {})
        advert  = mapeo.get('advertencias', [])

        lineas = [
            "# ============================================================",
            f"# CONTRATO DE DATOS — DisateQ CPE™",
            f"# Sistema: {nombre_sistema}",
            f"# Fecha: {datetime.now().strftime('%d/%m/%Y')}",
            "# ============================================================",
            "#",
            "# INSTRUCCIONES PARA EL PROGRAMADOR:",
            "# Este documento describe qué información necesita el Motor CPE",
            "# de su sistema para generar comprobantes electrónicos.",
            "#",
            "# Por cada campo marcado con [COMPLETAR], indique el nombre",
            "# exacto del campo en su base de datos.",
            "#",
            "# Si tiene dudas, contáctenos: soporte@disateq.com",
            "# ============================================================",
            "",
            "# ── TABLA DE COMPROBANTES ──────────────────────────────────",
            "tabla_comprobantes: " + str(tablas.get('comprobantes', '[COMPLETAR: nombre de tabla]')),
            "",
            "campos_comprobantes:",
        ]

        campos_info = CAMPOS_CPE['comprobantes']
        for campo, info in campos_info.items():
            valor = comp.get(campo)
            req   = "REQUERIDO" if info['requerido'] else "opcional"
            lineas.append(f"")
            lineas.append(f"  # {info['descripcion']} ({req})")
            if 'nota' in info:
                lineas.append(f"  # Nota: {info['nota']}")
            if valor:
                lineas.append(f"  {campo}: {valor}  # <- detectado automáticamente")
            else:
                lineas.append(f"  {campo}: '[COMPLETAR]'")

        lineas += [
            "",
            "",
            "# ── TABLA DE ITEMS / DETALLE ────────────────────────────────",
            "tabla_items: " + str(tablas.get('items', '[COMPLETAR: nombre de tabla]')),
            "",
            "campos_items:",
        ]

        campos_items_info = CAMPOS_CPE['items']
        for campo, info in campos_items_info.items():
            valor = items.get(campo)
            req   = "REQUERIDO" if info['requerido'] else "opcional"
            lineas.append(f"")
            lineas.append(f"  # {info['descripcion']} ({req})")
            if valor:
                lineas.append(f"  {campo}: {valor}  # <- detectado automáticamente")
            else:
                lineas.append(f"  {campo}: '[COMPLETAR]'")

        lineas += [
            "",
            "",
            "# ── VALORES Y FORMATOS ──────────────────────────────────────",
            "",
            "# Formato de fecha en su sistema:",
            f"formato_fecha: '{transf.get('fecha_formato', '[COMPLETAR: YYYYMMDD | DD/MM/YYYY | YYYY-MM-DD]')}'",
            "",
            "# Valores que usa su sistema para el tipo de comprobante:",
            "# Indique qué valor representa Boleta y qué valor representa Factura",
        ]

        tipo_map = transf.get('tipo_doc', {})
        if tipo_map:
            for val_orig, val_sunat in tipo_map.items():
                if not val_orig.startswith('_'):
                    lineas.append(f"  '{val_orig}': '{val_sunat}'  # <- detectado")
        else:
            lineas.append("  '[valor_boleta]': '03'   # <- COMPLETAR")
            lineas.append("  '[valor_factura]': '01'  # <- COMPLETAR")

        lineas += [
            "",
            "# Valor que indica que un comprobante está PENDIENTE de envío:",
            f"estado_pendiente: '{comp.get('estado_pendiente', '[COMPLETAR]')}'",
            f"valor_pendiente:  '[COMPLETAR: ej: 2, P, N, PENDIENTE]'",
        ]

        if advert:
            lineas += ["", "", "# ── CAMPOS NO DETECTADOS AUTOMÁTICAMENTE ───────────────────"]
            for a in advert:
                lineas.append(f"# ⚠️  {a}")

        lineas += [
            "",
            "",
            "# ── CONTACTO ────────────────────────────────────────────────",
            "# Una vez completado este documento, envíelo a:",
            "# soporte@disateq.com | WhatsApp: +51 XXX XXX XXX",
            "# ============================================================",
        ]

        return '\n'.join(lineas)
