content = open('src/ui/frontend/index.html', encoding='utf-8').read()

# 1. Reemplazar input+Examinar+Cargar por barra informativa + botón Cargar
old = '''                        <div style="display:grid;grid-template-columns:1fr auto;gap:1rem;align-items:end;margin-bottom:1rem;">
                            <div>
                                <label style="font-size:0.8rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;">Fuente de Datos (DBF)</label>
                                <div style="display:flex;gap:0.5rem;margin-top:0.25rem;">
                                    <input type="text" id="archivo-seleccionado"
                                           placeholder="Seleccionar carpeta DBF..."
                                           readonly
                                           style="flex:1;padding:0.5rem 0.75rem;border:1px solid var(--border-medium);border-radius:var(--radius-md);font-size:0.875rem;background:var(--bg-input-disabled);">
                                    <button class="btn btn-secondary" onclick="seleccionarArchivo()">
                                        <i data-feather="folder"></i> Examinar
                                    </button>
                                </div>
                            </div>
                            <button class="btn btn-primary" onclick="cargarPendientes()" id="btn-cargar">
                                <i data-feather="refresh-cw"></i> Cargar
                            </button>
                        </div>'''

new = '''                        <!-- Barra informativa fuente — solo lectura -->
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;gap:1rem;">
                            <div style="flex:1;display:flex;align-items:center;gap:0.75rem;padding:0.6rem 1rem;background:var(--bg-table-head);border:1px solid var(--border-light);border-radius:var(--radius-md);">
                                <i data-feather="database" style="width:15px;height:15px;color:var(--text-muted);flex-shrink:0;"></i>
                                <div style="min-width:0;">
                                    <div style="font-size:0.68rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:1px;">Fuente configurada</div>
                                    <div id="archivo-seleccionado" style="font-size:0.82rem;color:var(--text-primary);font-family:var(--font-mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">—</div>
                                </div>
                            </div>
                            <button class="btn btn-primary" onclick="cargarPendientes()" id="btn-cargar">
                                <i data-feather="refresh-cw"></i> Cargar
                            </button>
                        </div>

                        <!-- Spinner overlay -->
                        <div id="proc-spinner" style="display:none;position:absolute;inset:0;background:rgba(255,255,255,0.82);z-index:50;border-radius:var(--radius-lg);align-items:center;justify-content:center;flex-direction:column;gap:0.75rem;">
                            <div style="width:36px;height:36px;border:3px solid var(--border-medium);border-top-color:var(--primary);border-radius:50%;animation:spin 0.7s linear infinite;"></div>
                            <div id="proc-spinner-msg" style="font-size:0.82rem;color:var(--text-muted);font-weight:500;">Cargando...</div>
                        </div>'''

if old in content:
    # Agregar position:relative al card-body de procesar
    content = content.replace(old, new)
    # Agregar position:relative al card-body contenedor
    content = content.replace(
        '<div class="card-body">\n                        <!-- Barra informativa',
        '<div class="card-body" style="position:relative;">\n                        <!-- Barra informativa'
    )
    print('OK 1/1 — HTML Procesar actualizado')
else:
    print('NO ENCONTRADO')
    idx = content.find('Examinar')
    print(repr(content[idx-200:idx+100]))

open('src/ui/frontend/index.html', 'w', encoding='utf-8').write(content)
