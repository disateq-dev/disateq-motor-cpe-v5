content = open('src/ui/frontend/js/app.js', encoding='utf-8').read()

# Card del Scheduler a insertar
scheduler_card = """
        '<div class="card" style="margin-bottom:1rem;"><div class="card-header">' +
        '<h3>&#9201; Procesamiento Automático</h3>' +
        '<span style="font-size:0.72rem;color:#22c55e;background:#dcfce7;padding:2px 8px;border-radius:10px;">Editable</span>' +
        '</div><div class="card-body">' +
        '<div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:1rem;">' +
        '<div>' +
        '<label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.35rem;">MODO</label>' +
        '<div style="display:flex;gap:0.5rem;">' +
        '<label style="display:flex;align-items:center;gap:0.4rem;cursor:pointer;font-size:0.875rem;padding:0.5rem 1rem;border:2px solid #d1d5db;border-radius:6px;" id="lbl-modo-manual">' +
        '<input type="radio" name="sched-modo" id="sched-modo-manual" value="manual" onchange="onSchedModoChange()"> Manual</label>' +
        '<label style="display:flex;align-items:center;gap:0.4rem;cursor:pointer;font-size:0.875rem;padding:0.5rem 1rem;border:2px solid #d1d5db;border-radius:6px;" id="lbl-modo-auto">' +
        '<input type="radio" name="sched-modo" id="sched-modo-auto" value="automatico" onchange="onSchedModoChange()"> Automático</label>' +
        '</div></div>' +
        '<div id="sched-intervalo-box" style="display:none;">' +
        '<label style="font-size:0.72rem;color:#6b7280;display:block;margin-bottom:0.35rem;">INTERVALO BOLETAS</label>' +
        '<select id="sched-intervalo" style="padding:0.45rem 0.75rem;border:1px solid #d1d5db;border-radius:6px;font-size:0.875rem;">' +
        '<option value="5">Cada 5 minutos</option>' +
        '<option value="10">Cada 10 minutos</option>' +
        '<option value="15">Cada 15 minutos</option>' +
        '<option value="30">Cada 30 minutos</option>' +
        '</select></div>' +
        '</div>' +
        '<div style="font-size:0.78rem;color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:0.75rem;">' +
        '&#8505; <strong>Manual:</strong> el operador presiona "Procesar" cuando desea enviar. ' +
        '<strong>Automático:</strong> el Motor envía boletas cada X minutos y facturas de forma inmediata, sin intervención.' +
        '</div></div></div>' +"""

# Insertar antes de la card Clave del Instalador
old = """        '<div class="card" style="margin-bottom:1rem;"><div class="card-header">' +
        '<h3>&#128273; Clave del Instalador</h3>' +"""

new = scheduler_card + """
        '<div class="card" style="margin-bottom:1rem;"><div class="card-header">' +
        '<h3>&#128273; Clave del Instalador</h3>' +"""

if old in content:
    content = content.replace(old, new)
    open('src/ui/frontend/js/app.js', 'w', encoding='utf-8').write(content)
    print('OK — card scheduler insertada')
else:
    print('NO ENCONTRADO')
    idx = content.find('Clave del Instalador')
    print(repr(content[idx-100:idx+50]))
