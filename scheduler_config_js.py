content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

js_functions = """
// ================================================================
// SCHEDULER CONFIG
// ================================================================

async function cargarSchedulerConfig() {
    try {
        var result = await eel.get_scheduler_status()();
        if (!result.exito) return;
        var s = result.status;

        var modoManual = document.getElementById('sched-modo-manual');
        var modoAuto   = document.getElementById('sched-modo-auto');
        var intervalBox = document.getElementById('sched-intervalo-box');
        var intervalo  = document.getElementById('sched-intervalo');

        if (!modoManual) return;

        if (s.modo === 'automatico') {
            modoAuto.checked = true;
            if (intervalBox) intervalBox.style.display = 'block';
            document.getElementById('lbl-modo-auto').style.borderColor = '#22c55e';
            document.getElementById('lbl-modo-manual').style.borderColor = '#d1d5db';
        } else {
            modoManual.checked = true;
            if (intervalBox) intervalBox.style.display = 'none';
            document.getElementById('lbl-modo-manual').style.borderColor = '#22c55e';
            document.getElementById('lbl-modo-auto').style.borderColor = '#d1d5db';
        }

        if (intervalo) {
            intervalo.value = String(s.intervalo_minutos || 10);
        }
    } catch(e) { console.error('Error cargando scheduler:', e); }
}

function onSchedModoChange() {
    var modo = document.querySelector('input[name="sched-modo"]:checked');
    if (!modo) return;
    var intervalBox = document.getElementById('sched-intervalo-box');
    var lblManual = document.getElementById('lbl-modo-manual');
    var lblAuto   = document.getElementById('lbl-modo-auto');

    if (modo.value === 'automatico') {
        if (intervalBox) intervalBox.style.display = 'block';
        if (lblAuto)   lblAuto.style.borderColor   = '#22c55e';
        if (lblManual) lblManual.style.borderColor = '#d1d5db';
    } else {
        if (intervalBox) intervalBox.style.display = 'none';
        if (lblManual) lblManual.style.borderColor = '#22c55e';
        if (lblAuto)   lblAuto.style.borderColor   = '#d1d5db';
    }
}

// Exponer callback del scheduler para notificaciones de ciclo
eel.expose(scheduler_ciclo_completado);
function scheduler_ciclo_completado(resultados) {
    showToast('⏱️ Ciclo automático: ' + resultados.enviados + ' enviados, ' + resultados.errores + ' errores', 'info');
    cargarDashboard();
}
"""

# Insertar antes del bloque de CONFIGURACION
marker = '// ================================================================\n// CONFIGURACION\n// ================================================================'
if marker in content:
    content = content.replace(marker, js_functions + '\n' + marker)
    open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)
    print('OK — funciones scheduler agregadas')
else:
    print('NO ENCONTRADO')
