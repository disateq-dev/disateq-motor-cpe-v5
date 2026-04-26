content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

# 1. Agregar scheduler al payload de guardarConfig
old = """    var payload = {
        nombre_comercial: document.getElementById('cfg-nombre-comercial') ? document.getElementById('cfg-nombre-comercial').value : '',
        alias:            document.getElementById('cfg-alias')             ? document.getElementById('cfg-alias').value             : '',
        endpoints:        endpoints,
        series:           series,
        clave_nueva:      nueva || null
    };"""

new = """    // Leer config scheduler
    var schedModo = document.querySelector('input[name="sched-modo"]:checked');
    var schedIntervalo = document.getElementById('sched-intervalo');
    var schedulerPayload = null;
    if (schedModo) {
        schedulerPayload = {
            modo: schedModo.value,
            intervalo_boletas: schedIntervalo ? parseInt(schedIntervalo.value) : 10
        };
    }

    var payload = {
        nombre_comercial: document.getElementById('cfg-nombre-comercial') ? document.getElementById('cfg-nombre-comercial').value : '',
        alias:            document.getElementById('cfg-alias')             ? document.getElementById('cfg-alias').value             : '',
        endpoints:        endpoints,
        series:           series,
        clave_nueva:      nueva || null
    };"""

if old in content:
    content = content.replace(old, new)
    print('OK 1/3 — scheduler leído en guardarConfig')
else:
    print('NO ENCONTRADO 1/3')

# 2. Agregar guardado del scheduler después de guardar config principal
old2 = """    var result = await eel.guardar_config(payload)();
    msg.style.display = 'block';"""

new2 = """    // Guardar scheduler si hay cambios
    if (schedulerPayload) {
        await eel.guardar_config_scheduler(schedulerPayload)();
    }

    var result = await eel.guardar_config(payload)();
    msg.style.display = 'block';"""

if old2 in content:
    content = content.replace(old2, new2)
    print('OK 2/3 — scheduler guardado en guardarConfig')
else:
    print('NO ENCONTRADO 2/3')

# 3. Llamar cargarSchedulerConfig() al mostrar config completa
old3 = """    page.querySelector('.card-body').innerHTML = html;
}

function agregarSerie"""

new3 = """    page.querySelector('.card-body').innerHTML = html;
    // Cargar estado actual del scheduler
    setTimeout(cargarSchedulerConfig, 100);
}

function agregarSerie"""

if old3 in content:
    content = content.replace(old3, new3)
    print('OK 3/3 — cargarSchedulerConfig() llamado al abrir config')
else:
    print('NO ENCONTRADO 3/3')

open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)
