# Guía Técnica — Adaptador Universal v3.0

## Para técnicos instaladores

### Flujo de configuración

1. **Explorar la fuente de datos del cliente**
```bash
   python tools/source_explorer.py --source C:\Cliente\ventas.dbf
   # O para SQL:
   python tools/source_explorer.py --source VENTAS \
     --connection "Driver={SQL Server};Server=SRV;Database=ERP"
```

2. **Copiar plantilla de mapeo**
```bash
   copy docs\mapping_examples\ejemplo_completo_sql.yaml \
        src\adapters\mappings\cliente_abc.yaml
```

3. **Editar YAML con nombres reales**
   - Usar nombres exactos del source_explorer
   - Ajustar transformaciones según necesidad
   - Configurar relaciones cabecera-detalle

4. **Probar mapeo**
```python
   from adapters.sql_adapter import SQLAdapter
   
   adapter = SQLAdapter('src/adapters/mappings/cliente_abc.yaml')
   adapter.connect()
   pendientes = adapter.read_pending()
   
   if pendientes:
       comp = pendientes[0]
       items = adapter.read_items(comp)
       resultado = adapter.normalize(comp, items)
       print(resultado)
```

5. **Validar y ajustar**
   - Verificar que los totales calculan correctamente
   - Confirmar afectación IGV por ítem
   - Validar formato de fechas

## Sistemas soportados

### Legacy (ODBC)
- FoxPro DBF
- Access MDB
- SQL Server 2000-2008

### Moderno (SQL nativo)
- SQL Server 2012+
- PostgreSQL
- MySQL
- Oracle

## Troubleshooting

### Error: "Campo no encontrado"
→ Ejecutar source_explorer.py y copiar nombre EXACTO

### Error: "Transformación fallida"
→ Revisar sintaxis del transform en YAML

### Error: "Totales no cuadran"
→ Verificar afectacion_igv y cálculo de valor_unitario

---

**DisateQ™** — Motor CPE v3.0
