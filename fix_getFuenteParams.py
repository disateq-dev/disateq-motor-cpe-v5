content = open('src/ui/frontend/js/wizard.js', encoding='utf-8').read()

get_fuente_params = """
function getFuenteParams() {
    var esSql = (_tipoActual === 'sqlserver' || _tipoActual === 'mysql' || _tipoActual === 'postgres');
    if (esSql) {
        var servidor = document.getElementById('sql-servidor').value.trim();
        var db       = document.getElementById('sql-db').value.trim();
        if (!servidor || !db) {
            showAlert('fuente-alert', 'error', 'Servidor y base de datos son obligatorios.'); return null;
        }
        return {
            tipo:       _tipoActual,
            servidor:   servidor,
            base_datos: db,
            usuario:    document.getElementById('sql-usuario').value.trim(),
            clave:      document.getElementById('sql-clave').value,
            puerto:     parseInt(document.getElementById('sql-puerto').value) || 1433
        };
    } else {
        var ruta = document.getElementById('fuente-ruta-input').value.trim();
        if (!ruta) {
            showAlert('fuente-alert', 'error', 'Selecciona la ruta de los datos.'); return null;
        }
        return { tipo: _tipoActual, ruta: ruta };
    }
}
"""

# Insertar antes de explorarFuente
old = 'async function explorarFuente()'
if old in content:
    content = content.replace(old, get_fuente_params + '\n' + old)
    open('src/ui/frontend/js/wizard.js', 'w', encoding='utf-8').write(content)
    print('OK — getFuenteParams restaurada')
else:
    print('NO ENCONTRADO')
