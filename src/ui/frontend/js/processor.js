// processor.js - DisateQ™ Motor CPE v4.0

// ============================================================
// VARIABLES GLOBALES
// ============================================================

let comprobantesPreview = [];
let archivoSeleccionado = null;

// ============================================================
// SELECCIONAR ARCHIVO
// ============================================================

async function seleccionarArchivo() {
    try {
        const archivo = await eel.seleccionar_archivo()();
        
        if (!archivo) {
            return;
        }
        
        archivoSeleccionado = archivo;
        document.getElementById('fuente-archivo').value = archivo;
        
        // Conectar y obtener preview
        await conectarYPreview();
        
    } catch (error) {
        console.error('Error seleccionando archivo:', error);
        showToast('Error al seleccionar archivo', 'error');
    }
}

// ============================================================
// CONECTAR Y MOSTRAR PREVIEW
// ============================================================

async function conectarYPreview() {
    const tipo = document.getElementById('fuente-tipo').value;
    const archivo = document.getElementById('fuente-archivo').value;
    
    if (!archivo) {
        showToast('Selecciona un archivo primero', 'warning');
        return;
    }
    
    const statusDiv = document.getElementById('fuente-status');
    statusDiv.innerHTML = '<p>⏳ Conectando...</p>';
    statusDiv.className = 'alert alert-info';
    statusDiv.style.display = 'block';
    
    try {
        const resultado = await eel.conectar_fuente(tipo, archivo)();
        
        if (resultado.exito) {
            statusDiv.innerHTML = `
                <p>✅ Conectado exitosamente</p>
                <p><strong>${resultado.pendientes}</strong> comprobantes pendientes encontrados</p>
            `;
            statusDiv.className = 'alert alert-success';
            
            // Guardar y mostrar preview
            comprobantesPreview = resultado.comprobantes;
            mostrarPreview(comprobantesPreview);
            
            showToast(`${resultado.pendientes} comprobantes encontrados`, 'success');
        } else {
            statusDiv.innerHTML = `<p>❌ Error: ${resultado.error}</p>`;
            statusDiv.className = 'alert alert-error';
            
            document.getElementById('preview-container').style.display = 'none';
        }
        
    } catch (error) {
        console.error('Error conectando:', error);
        statusDiv.innerHTML = `<p>❌ Error: ${error}</p>`;
        statusDiv.className = 'alert alert-error';
    }
}

// ============================================================
// MOSTRAR PREVIEW
// ============================================================

function mostrarPreview(comprobantes) {
    const previewList = document.getElementById('preview-list');
    const container = document.getElementById('preview-container');
    
    if (!comprobantes || comprobantes.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    previewList.innerHTML = comprobantes.map((comp, index) => `
        <div class="preview-item">
            <input type="checkbox" 
                   id="check-${index}" 
                   value="${index}" 
                   checked>
            <div class="preview-item-content">
                <div class="preview-item-serie">${comp.serie}-${String(comp.numero).padStart(8, '0')}</div>
                <div class="preview-item-cliente">${escapeHtml(comp.cliente)}</div>
                <div class="preview-item-total">${formatCurrency(comp.total)}</div>
            </div>
        </div>
    `).join('');
    
    container.style.display = 'block';
    
    // Evento para "Seleccionar todos"
    const selectAll = document.getElementById('select-all');
    selectAll.checked = true;
    selectAll.onchange = (e) => {
        document.querySelectorAll('.preview-item input[type="checkbox"]').forEach(cb => {
            cb.checked = e.target.checked;
        });
    };
}

// ============================================================
// PROCESAR SELECCIONADOS
// ============================================================

async function procesarSeleccionados() {
    const archivo = document.getElementById('fuente-archivo').value;
    const endpoint = document.querySelector('input[name="endpoint"]:checked').value;
    
    // Obtener índices seleccionados
    const checkboxes = document.querySelectorAll('.preview-item input[type="checkbox"]:checked');
    const indicesSeleccionados = Array.from(checkboxes).map(cb => parseInt(cb.value));
    
    if (indicesSeleccionados.length === 0) {
        showToast('Selecciona al menos un comprobante', 'warning');
        return;
    }
    
    if (!confirm(`¿Procesar ${indicesSeleccionados.length} comprobante(s)?`)) {
        return;
    }
    
    // Ocultar preview, mostrar progress
    document.getElementById('preview-container').style.display = 'none';
    document.getElementById('progress-container').style.display = 'block';
    
    try {
        const resultado = await eel.procesar_comprobantes(archivo, endpoint, indicesSeleccionados)();
        
        if (resultado.exito) {
            showToast(
                `Procesamiento completado: ${resultado.exitosos} exitosos, ${resultado.fallidos} fallidos`,
                resultado.fallidos > 0 ? 'warning' : 'success'
            );
            
            // Mostrar resultados
            mostrarResultados(resultado);
        } else {
            showToast(`Error: ${resultado.error}`, 'error');
        }
        
    } catch (error) {
        console.error('Error procesando:', error);
        showToast('Error durante el procesamiento', 'error');
    } finally {
        document.getElementById('progress-container').style.display = 'none';
        
        // Refrescar dashboard
        if (typeof cargarDashboard === 'function') {
            cargarDashboard();
        }
    }
}

// ============================================================
// MOSTRAR RESULTADOS
// ============================================================

function mostrarResultados(resultado) {
    const html = `
        <div class="card">
            <div class="card-header">
                <h3>✅ Procesamiento Completado</h3>
            </div>
            <div class="card-body">
                <div class="stats-grid" style="grid-template-columns: repeat(3, 1fr);">
                    <div class="stat-card">
                        <div class="stat-content">
                            <div class="stat-label">Total Procesados</div>
                            <div class="stat-value">${resultado.procesados}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-content">
                            <div class="stat-label">Exitosos</div>
                            <div class="stat-value" style="color: var(--success);">${resultado.exitosos}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-content">
                            <div class="stat-label">Fallidos</div>
                            <div class="stat-value" style="color: var(--error);">${resultado.fallidos}</div>
                        </div>
                    </div>
                </div>
                
                <h4 class="mb-2">Detalle:</h4>
                <div style="max-height: 300px; overflow-y: auto;">
                    ${resultado.resultados.map(r => `
                        <div class="alert ${r.exito ? 'alert-success' : 'alert-error'}" style="margin-bottom: 0.5rem;">
                            <strong>${r.comprobante}</strong>: ${r.mensaje}
                        </div>
                    `).join('')}
                </div>
                
                <div style="margin-top: 1.5rem; display: flex; gap: 1rem;">
                    <button class="btn btn-primary" onclick="volverAProcesar()">
                        Procesar Más
                    </button>
                    <button class="btn btn-secondary" onclick="navigateTo('dashboard')">
                        Volver al Dashboard
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('progress-container').innerHTML = html;
    document.getElementById('progress-container').style.display = 'block';
}

// ============================================================
// VOLVER A PROCESAR
// ============================================================

function volverAProcesar() {
    document.getElementById('progress-container').style.display = 'none';
    document.getElementById('progress-container').innerHTML = `
        <div class="card">
            <div class="card-body">
                <h4>Procesando...</h4>
                <div class="progress">
                    <div id="progress-bar" class="progress-bar" style="width: 0%"></div>
                </div>
                <p id="progress-text">0/0 (0%)</p>
            </div>
        </div>
    `;
    
    // Reconectar
    if (archivoSeleccionado) {
        conectarYPreview();
    }
}

// ============================================================
// UPDATE PROGRESS (llamado desde Python)
// ============================================================

eel.expose(update_progress);
function update_progress(current, total) {
    const percentage = Math.round((current / total) * 100);
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        progressBar.textContent = `${percentage}%`;
    }
    
    if (progressText) {
        progressText.textContent = `${current}/${total} (${percentage}%)`;
    }
}

// ============================================================
// EVENTOS
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // Evento cambio de tipo
    const fuenteTipo = document.getElementById('fuente-tipo');
    if (fuenteTipo) {
        fuenteTipo.addEventListener('change', () => {
            document.getElementById('fuente-archivo').value = '';
            archivoSeleccionado = null;
            document.getElementById('preview-container').style.display = 'none';
            document.getElementById('fuente-status').style.display = 'none';
        });
    }
});
