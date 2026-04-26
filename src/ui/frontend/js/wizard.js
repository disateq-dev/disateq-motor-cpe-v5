/**
 * wizard.js — DisateQ CPE™ v4.0
 * Lógica del asistente de instalación (6 pasos)
 */

// ================================================================
// ESTADO GLOBAL
// ================================================================

var WZ = {
    paso:        1,
    modo:        'nuevo',   // 'nuevo' | 'reconfigurar'
    licencia:    { valida: false, tipo: 'Trial', codigo: '' },
    empresa:     { ruc: '', alias: '', razon_social: '', nombre_comercial: '' },
    fuente:      { tipo: 'dbf', ruta: '', servidor: '', base_datos: '', usuario: '', clave: '', puerto: '' },
    explorado:   false,
    contrato:    null,
    series:      { boleta: [], factura: [], nota_credito: [], nota_debito: [] },
    endpoint:    { nombre: 'APIFAS', url: 'https://apifas.disateq.com/produccion_text.php', usuario: '', token: '' },
    prueba_ok:   false
};

var PASOS = [
    { num: 1, label: 'Licencia'  },
    { num: 2, label: 'Empresa'   },
    { num: 3, label: 'Fuente'    },
    { num: 4, label: 'Series'    },
    { num: 5, label: 'Endpoint'  },
    { num: 6, label: 'Prueba'    }
];

// ================================================================
// INIT
// ================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Detectar modo reconfigurar desde URL
    var params = new URLSearchParams(window.location.search);
    if (params.get('modo') === 'reconfigurar') {
        WZ.modo = 'reconfigurar';
        cargarConfigExistente();
    }
    renderStepper();
    renderSeriesDefault();
});

function renderStepper() {
    var html = '';
    for (var i = 0; i < PASOS.length; i++) {
        var p = PASOS[i];
        var cls = p.num === WZ.paso ? 'active' : (p.num < WZ.paso ? 'done' : '');
        html += '<div class="wz-step ' + cls + '">' +
            '<div class="wz-step-dot">' + (p.num < WZ.paso ? '✓' : p.num) + '</div>' +
            '<div class="wz-step-label">' + p.label + '</div>' +
            '</div>';
        if (i < PASOS.length - 1) {
            html += '<div class="wz-step-line ' + (p.num < WZ.paso ? 'done' : '') + '"></div>';
        }
    }
    document.getElementById('stepper').innerHTML = html;
}

function irPaso(n) {
    document.getElementById('page-' + WZ.paso).classList.remove('active');
    WZ.paso = n;
    var page = document.getElementById('page-' + n);
    if (page) page.classList.add('active');
    renderStepper();
    window.scrollTo(0, 0);

    // Acciones al entrar a cada paso
    if (n === 4) initSeries();
}

// ================================================================
// PASO 1 — LICENCIA
// ================================================================

function formatLicCode(input) {
    var v = input.value.replace(/[^A-Z0-9]/gi, '').toUpperCase().substring(0, 16);
    var parts = [];
    for (var i = 0; i < v.length; i += 4) parts.push(v.substring(i, i + 4));
    input.value = parts.join('-');
}

async function validarLicencia() {
    var codigo = document.getElementById('lic-codigo').value.replace(/-/g, '');
    if (codigo.length < 16) {
        showAlert('lic-alert', 'warn', '⚠️ El código debe tener 16 caracteres (XXXX-XXXX-XXXX-XXXX)');
        return;
    }
    var alert = document.getElementById('lic-alert');
    alert.className = 'wz-alert neutral';
    alert.style.display = 'flex';
    alert.innerHTML = '<span class="spinner"></span> Validando licencia...';

    try {
        var result = await eel.wz_validar_licencia(codigo)();
        if (result.valida) {
            WZ.licencia = { valida: true, tipo: result.tipo || 'Full', codigo: codigo };
            showAlert('lic-alert', 'info', '✅ Licencia válida — ' + WZ.licencia.tipo);
            setTimeout(function() { irPaso(2); }, 800);
        } else {
            showAlert('lic-alert', 'error', '❌ Licencia inválida o expirada. Verifica el código o continúa en Trial.');
        }
    } catch(e) {
        showAlert('lic-alert', 'error', '❌ No se pudo contactar el servidor de licencias. Continúa en Trial.');
    }
}

function usarTrial() {
    WZ.licencia = { valida: true, tipo: 'Trial 30 días', codigo: 'TRIAL' };
    showAlert('lic-alert', 'warn', '⚠️ Modo Trial activado — 30 días de uso.');
    setTimeout(function() { irPaso(2); }, 600);
}

// ================================================================
// PASO 2 — EMPRESA
// ================================================================

function validarEmpresa() {
    var ruc   = document.getElementById('emp-ruc').value.trim();
    var alias = document.getElementById('emp-alias').value.trim();
    var razon = document.getElementById('emp-razon').value.trim();

    if (ruc.length !== 11) {
        showAlert('emp-alert', 'error', '❌ El RUC debe tener exactamente 11 dígitos.'); return;
    }
    if (!alias) {
        showAlert('emp-alert', 'error', '❌ El alias es obligatorio (ej: farmacia_central).'); return;
    }
    if (!razon) {
        showAlert('emp-alert', 'error', '❌ La razón social es obligatoria.'); return;
    }

    // Normalizar alias
    alias = alias.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    document.getElementById('emp-alias').value = alias;

    WZ.empresa = {
        ruc:              ruc,
        alias:            alias,
        razon_social:     razon,
        nombre_comercial: document.getElementById('emp-nombre').value.trim() || razon
    };

    hideAlert('emp-alert');
    irPaso(3);
}

// ================================================================
// PASO 3 — FUENTE DE DATOS
// ================================================================

var _tipoActual = 'dbf';

function selTipo(tipo) {
    _tipoActual = tipo;
    document.querySelectorAll('.tipo-card').forEach(function(c) { c.classList.remove('selected'); });
    document.getElementById('tipo-' + tipo).classList.add('selected');

    var esSql = (tipo === 'sqlserver' || tipo === 'mysql' || tipo === 'postgres');
    document.getElementById('fuente-ruta').style.display = esSql ? 'none' : 'block';
    document.getElementById('fuente-sql').style.display  = esSql ? 'block' : 'none';

    // Reset explorer
    document.getElementById('explorer-status').style.display = 'none';
    document.getElementById('explorer-result').style.display = 'none';
    WZ.explorado = false;
}

async function seleccionarCarpeta() {
    try {
        var carpeta = await eel.seleccionar_carpeta()();
        if (carpeta) document.getElementById('fuente-ruta-input').value = carpeta;
    } catch(e) { toast('No se pudo abrir el explorador'); }
}


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

async function explorarFuente() {
    var status = document.getElementById('explorer-status');
    var result_div = document.getElementById('explorer-result');
    var btn = document.getElementById('btn-explorar');

    var params = getFuenteParams();
    if (!params) return;

    status.style.display = 'block';
    status.innerHTML = '<span class="spinner"></span> Analizando fuente de datos... (puede tardar hasta 2 minutos en fuentes grandes)';
    result_div.style.display = 'none';
    btn.disabled = true;

    try {
        var result = await eel.wz_explorar_fuente(params)();
        btn.disabled = false;

        if (result.exito) {
            WZ.explorado = true;
            WZ.contrato  = result.contrato;
            status.innerHTML = '<span style="color:#7ee787">✅ Análisis completado — ' + (result.tablas || 0) + ' tabla(s) encontrada(s)</span>';
            result_div.style.display = 'block';
            result_div.innerHTML = formatExplorerResult(result);
        } else {
            status.innerHTML = '<span style="color:#e3b341">⚠️ No se pudo analizar automáticamente</span>';
            document.getElementById('fuente-manual').style.display = 'block';
            WZ.explorado = true; // Permite continuar con config manual
        }
    } catch(e) {
        btn.disabled = false;
        status.innerHTML = '<span style="color:#ff7b72">❌ Error al analizar: ' + e + '</span>';
        document.getElementById('fuente-manual').style.display = 'block';
        WZ.explorado = true;
    }
}

// ================================================================
// REEMPLAZAR en wizard.js:
// La función formatExplorerResult y la sección de resultado del explorer
// ================================================================

// NUEVA función formatExplorerResult — tabla visual de mapeo
function formatExplorerResult(result) {
    var html = '';
    var confianza = Math.round((result.confianza || 0) * 100);
    var metodo = result.metodo_mapeo === 'ia' ? '🤖 IA' : '🔍 Heurísticas';
    var colorConf = confianza >= 80 ? '#7ee787' : confianza >= 50 ? '#e3b341' : '#ff7b72';

    // Header
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">' +
        '<span style="font-size:0.8rem;color:var(--muted);">' + metodo + '</span>' +
        '<span style="font-size:0.8rem;font-weight:700;color:' + colorConf + ';">Confianza: ' + confianza + '%</span>' +
        '</div>';

    // Tabla de mapeo comprobantes
    var comp = result.mapeo_comprobantes || {};
    var items = result.mapeo_items || {};

    html += '<div style="font-size:0.72rem;font-weight:600;color:var(--muted);text-transform:uppercase;margin-bottom:0.4rem;">Comprobantes — ' + (result.tabla_comp || '') + '</div>';
    html += '<table style="width:100%;border-collapse:collapse;margin-bottom:1rem;font-size:0.8rem;">';
    html += '<thead><tr style="border-bottom:1px solid var(--border);">' +
        '<th style="text-align:left;padding:0.3rem 0.5rem;color:var(--muted);">Campo CPE</th>' +
        '<th style="text-align:left;padding:0.3rem 0.5rem;color:var(--muted);">Campo en sistema</th>' +
        '<th style="text-align:left;padding:0.3rem 0.5rem;color:var(--muted);">Estado</th>' +
        '</tr></thead><tbody>';

    var camposCpe = ['tipo_doc','serie','numero','fecha','total','ruc_cliente','nombre_cliente','estado_pendiente'];
    var etiquetas = {
        'tipo_doc': 'Tipo comprobante',
        'serie': 'Serie',
        'numero': 'Número',
        'fecha': 'Fecha emisión',
        'total': 'Total',
        'ruc_cliente': 'RUC/DNI cliente',
        'nombre_cliente': 'Nombre cliente',
        'estado_pendiente': 'Estado pendiente'
    };
    var requeridos = ['tipo_doc','serie','numero','fecha','total','estado_pendiente'];

    camposCpe.forEach(function(campo) {
        var valorDetectado = comp[campo];
        var esRequerido = requeridos.indexOf(campo) >= 0;
        var estado = valorDetectado
            ? '<span style="color:#7ee787;">✓ Auto</span>'
            : (esRequerido ? '<span style="color:#ff7b72;">⚠ Req.</span>' : '<span style="color:var(--muted);">- Opcional</span>');

        html += '<tr style="border-bottom:1px solid rgba(48,54,61,0.5);">' +
            '<td style="padding:0.35rem 0.5rem;">' + (etiquetas[campo] || campo) + '</td>' +
            '<td style="padding:0.35rem 0.5rem;">' +
            '<input type="text" id="map-comp-' + campo + '" value="' + (valorDetectado || '') + '" ' +
            'placeholder="[campo del sistema]" ' +
            'style="background:var(--input-bg);border:1px solid ' + (valorDetectado ? 'var(--accent)' : 'var(--border)') + ';' +
            'border-radius:4px;color:var(--text);padding:0.2rem 0.4rem;font-size:0.78rem;width:160px;">' +
            '</td>' +
            '<td style="padding:0.35rem 0.5rem;">' + estado + '</td>' +
            '</tr>';
    });
    html += '</tbody></table>';

    // Tabla items si hay
    if (result.tabla_items) {
        html += '<div style="font-size:0.72rem;font-weight:600;color:var(--muted);text-transform:uppercase;margin-bottom:0.4rem;">Items / Detalle — ' + result.tabla_items + '</div>';
        html += '<table style="width:100%;border-collapse:collapse;margin-bottom:0.75rem;font-size:0.8rem;">';
        html += '<thead><tr style="border-bottom:1px solid var(--border);">' +
            '<th style="text-align:left;padding:0.3rem 0.5rem;color:var(--muted);">Campo CPE</th>' +
            '<th style="text-align:left;padding:0.3rem 0.5rem;color:var(--muted);">Campo en sistema</th>' +
            '<th style="text-align:left;padding:0.3rem 0.5rem;color:var(--muted);">Estado</th>' +
            '</tr></thead><tbody>';

        var camposItems = ['descripcion','cantidad','precio','total','codigo','campo_union'];
        var etiqItems = {
            'descripcion': 'Descripción producto',
            'cantidad': 'Cantidad',
            'precio': 'Precio unitario',
            'total': 'Total item',
            'codigo': 'Código producto',
            'campo_union': 'Campo unión (JOIN)'
        };
        var reqItems = ['descripcion','cantidad','precio','total','campo_union'];

        camposItems.forEach(function(campo) {
            var valorDetectado = items[campo];
            var esRequerido = reqItems.indexOf(campo) >= 0;
            var estado = valorDetectado
                ? '<span style="color:#7ee787;">✓ Auto</span>'
                : (esRequerido ? '<span style="color:#ff7b72;">⚠ Req.</span>' : '<span style="color:var(--muted);">- Opcional</span>');

            html += '<tr style="border-bottom:1px solid rgba(48,54,61,0.5);">' +
                '<td style="padding:0.35rem 0.5rem;">' + (etiqItems[campo] || campo) + '</td>' +
                '<td style="padding:0.35rem 0.5rem;">' +
                '<input type="text" id="map-items-' + campo + '" value="' + (valorDetectado || '') + '" ' +
                'placeholder="[campo del sistema]" ' +
                'style="background:var(--input-bg);border:1px solid ' + (valorDetectado ? 'var(--accent)' : 'var(--border)') + ';' +
                'border-radius:4px;color:var(--text);padding:0.2rem 0.4rem;font-size:0.78rem;width:160px;">' +
                '</td>' +
                '<td style="padding:0.35rem 0.5rem;">' + estado + '</td>' +
                '</tr>';
        });
        html += '</tbody></table>';
    }

    // Advertencias
    if (result.advertencias && result.advertencias.length) {
        html += '<div style="margin-top:0.5rem;">';
        result.advertencias.forEach(function(a) {
            html += '<div style="font-size:0.75rem;color:#e3b341;margin-bottom:0.25rem;">⚠ ' + a + '</div>';
        });
        html += '</div>';
    }

    // Guardar mapeo en WZ para usar al continuar
    WZ.mapeo_detectado = result;

    return html;
}

// NUEVA función leerMapeoVisual — lee los inputs de la tabla visual
function leerMapeoVisual() {
    if (!WZ.mapeo_detectado) return null;

    var camposComp  = ['tipo_doc','serie','numero','fecha','total','ruc_cliente','nombre_cliente','estado_pendiente'];
    var camposItems = ['descripcion','cantidad','precio','total','codigo','campo_union'];

    var comp = {};
    camposComp.forEach(function(c) {
        var el = document.getElementById('map-comp-' + c);
        if (el && el.value) comp[c] = el.value;
    });

    var items = {};
    camposItems.forEach(function(c) {
        var el = document.getElementById('map-items-' + c);
        if (el && el.value) items[c] = el.value;
    });

    return {
        comprobantes:   comp,
        items:          items,
        anulaciones:    WZ.mapeo_detectado.mapeo_anulaciones || {},
        transformaciones: WZ.mapeo_detectado.transformaciones || {},
        tabla_comp:     WZ.mapeo_detectado.tabla_comp,
        tabla_items:    WZ.mapeo_detectado.tabla_items,
        tabla_anulaciones: WZ.mapeo_detectado.tabla_anulaciones
    };
}


function validarFuente() {
    var params = getFuenteParams();
    if (!params) return;

    if (!WZ.explorado) {
        showAlert('fuente-alert', 'warn', '⚠️ Se recomienda analizar la fuente antes de continuar. Puedes hacerlo o continuar sin análisis.');
        WZ.explorado = true; // Permite continuar al segundo intento
        return;
    }

    WZ.fuente = params;
    // Incluir mapeo detectado en el contrato
    var mapeoVisual = leerMapeoVisual();
    if (mapeoVisual) {
        WZ.contrato = Object.assign(WZ.contrato || {}, { mapeo: mapeoVisual });
    }
    hideAlert('fuente-alert');
    irPaso(4);
}

// ================================================================
// PASO 4 — SERIES
// ================================================================

function renderSeriesDefault() {
    // Series por defecto sugeridas
    var defaults = {
        boleta:       [{ serie: 'B001', correlativo_inicio: 1, activa: true }],
        factura:      [{ serie: 'F001', correlativo_inicio: 1, activa: true }],
        nota_credito: [],
        nota_debito:  []
    };
    Object.keys(defaults).forEach(function(tipo) {
        WZ.series[tipo] = defaults[tipo];
    });
}

function initSeries() {
    var tipos = ['boleta', 'factura', 'nota_credito', 'nota_debito'];
    tipos.forEach(function(tipo) {
        renderSeriesTipo(tipo);
    });

    // Modo reconfigurar: mostrar aviso y bloquear edición
    if (WZ.modo === 'reconfigurar') {
        document.getElementById('modo-reconf-aviso').style.display = 'block';
        setSeriesReadonly(true);
    }
}

function renderSeriesTipo(tipo) {
    var container = document.getElementById('series-' + tipo);
    if (!container) return;
    container.innerHTML = '';
    (WZ.series[tipo] || []).forEach(function(s, i) {
        container.appendChild(crearSerieRow(tipo, i, s));
    });
}

function crearSerieRow(tipo, idx, s) {
    var div = document.createElement('div');
    div.className = 'serie-row';
    div.id = 'serie-row-' + tipo + '-' + idx;
    div.innerHTML =
        '<span class="serie-badge">' + s.serie + '</span>' +
        '<span class="serie-muted">desde:</span>' +
        '<input type="number" id="serie-' + tipo + '-' + idx + '-corr" value="' + s.correlativo_inicio + '" min="0">' +
        '<input type="hidden" id="serie-' + tipo + '-' + idx + '-cod" value="' + s.serie + '">' +
        '<label style="display:flex;align-items:center;gap:0.3rem;font-size:0.75rem;cursor:pointer;">' +
        '<input type="checkbox" id="serie-' + tipo + '-' + idx + '-activa" ' + (s.activa ? 'checked' : '') + '> Activa</label>' +
        '<button onclick="eliminarSerie(\'' + tipo + '\',' + idx + ')" ' +
        'style="margin-left:auto;background:none;border:none;cursor:pointer;color:var(--error);">✕</button>';
    return div;
}

function addSerie(tipo, prefijo) {
    var codigo = prompt('Código de serie (ej: ' + prefijo + '001):');
    if (!codigo) return;
    codigo = codigo.toUpperCase().trim();
    var corr = parseInt(prompt('Correlativo de inicio:', '1')) || 1;
    WZ.series[tipo].push({ serie: codigo, correlativo_inicio: corr, activa: true });
    renderSeriesTipo(tipo);
}

function eliminarSerie(tipo, idx) {
    WZ.series[tipo].splice(idx, 1);
    renderSeriesTipo(tipo);
}

function leerSeries() {
    var tipos = ['boleta', 'factura', 'nota_credito', 'nota_debito'];
    var resultado = {};
    tipos.forEach(function(tipo) {
        var container = document.getElementById('series-' + tipo);
        if (!container) { resultado[tipo] = []; return; }
        var items = [];
        var inputs = container.querySelectorAll('input[type=number]');
        inputs.forEach(function(inp) {
            var m = inp.id.match(/^serie-[^-]+-(\d+)-corr$/);
            if (!m) return;
            var i = m[1];
            var cod = document.getElementById('serie-' + tipo + '-' + i + '-cod');
            var act = document.getElementById('serie-' + tipo + '-' + i + '-activa');
            if (!cod) return;
            items.push({ serie: cod.value, correlativo_inicio: parseInt(inp.value) || 0, activa: act ? act.checked : true });
        });
        resultado[tipo] = items;
    });
    return resultado;
}

function setSeriesReadonly(readonly) {
    document.querySelectorAll('#series-container input').forEach(function(el) {
        el.disabled = readonly;
    });
    document.querySelectorAll('#series-container button').forEach(function(el) {
        el.disabled = readonly;
        el.style.opacity = readonly ? '0.4' : '1';
    });
}

function toggleEditarSeries(editar) {
    setSeriesReadonly(!editar);
}

// ================================================================
// PASO 5 — ENDPOINT
// ================================================================

var EP_URLS = {
    apifas: 'https://apifas.disateq.com/produccion_text.php',
    ose:    '',
    pse:    '',
    custom: ''
};

function onEpTipoChange(tipo) {
    var url = EP_URLS[tipo] || '';
    document.getElementById('ep-url').value = url;
    document.getElementById('ep-url').readOnly = (tipo === 'apifas');
}

function validarEndpoint() {
    var url = document.getElementById('ep-url').value.trim();
    if (!url || !url.startsWith('http')) {
        showAlert('ep-alert', 'error', '❌ URL del endpoint inválida.'); return;
    }
    WZ.endpoint = {
        nombre:  document.getElementById('ep-tipo').options[document.getElementById('ep-tipo').selectedIndex].text.split('—')[0].trim(),
        url:     url,
        usuario: document.getElementById('ep-usuario').value.trim(),
        token:   document.getElementById('ep-token').value.trim()
    };
    hideAlert('ep-alert');
    irPaso(6);
}

// ================================================================
// PASO 6 — PRUEBA
// ================================================================

async function ejecutarPrueba() {
    var btn = document.getElementById('btn-prueba');
    var estado = document.getElementById('prueba-estado');
    var resultado = document.getElementById('prueba-resultado');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Procesando...';
    estado.style.display = 'block';
    estado.innerHTML = '<span class="spinner"></span> Guardando configuración y ejecutando prueba mock...';
    resultado.style.display = 'none';

    // Guardar config antes de probar
    WZ.series = leerSeries();
    var payload = construirPayload();

    try {
        var saveResult = await eel.wz_guardar_config(payload)();
        if (!saveResult.exito) {
            estado.innerHTML = '<span style="color:var(--error)">❌ Error al guardar config: ' + saveResult.error + '</span>';
            btn.disabled = false; btn.innerHTML = '▶ Ejecutar prueba';
            return;
        }

        var pruebaResult = await eel.wz_ejecutar_prueba(WZ.empresa.alias)();
        btn.disabled = false;
        btn.innerHTML = '▶ Ejecutar prueba';

        if (pruebaResult.exito) {
            var r = pruebaResult.resultados;
            estado.innerHTML = '<span style="color:#7ee787">✅ Prueba completada</span>';
            resultado.style.display = 'block';
            resultado.innerHTML =
                '<div class="prueba-stat"><span>Procesados</span><span class="val">' + r.procesados + '</span></div>' +
                '<div class="prueba-stat"><span>Enviados (mock)</span><span class="val">' + r.enviados + '</span></div>' +
                '<div class="prueba-stat"><span>Errores</span><span class="val ' + (r.errores > 0 ? 'err' : '') + '">' + r.errores + '</span></div>' +
                '<div class="prueba-stat"><span>Ignorados</span><span class="val">' + r.ignorados + '</span></div>';

            WZ.prueba_ok = true;
            document.getElementById('btn-finalizar').disabled = false;
            document.getElementById('btn-envio-real').style.display = 'inline-flex';
        } else {
            estado.innerHTML = '<span style="color:var(--error)">❌ ' + pruebaResult.error + '</span>';
        }
    } catch(e) {
        btn.disabled = false;
        btn.innerHTML = '▶ Ejecutar prueba';
        estado.innerHTML = '<span style="color:var(--error)">❌ Error inesperado: ' + e + '</span>';
    }
}

function mostrarEnvioReal() {
    document.getElementById('prueba-real-section').style.display = 'block';
}

async function confirmarEnvioReal() {
    if (!confirm('¿Confirmas enviar 1 comprobante REAL a SUNAT?\nEsto generará un comprobante electrónico válido.')) return;
    var btn = document.querySelector('#prueba-real-section .btn-warn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Enviando...';
    try {
        var result = await eel.wz_enviar_real(WZ.empresa.alias)();
        btn.disabled = false;
        btn.innerHTML = 'Enviar 1 real de prueba';
        if (result.exito) {
            toast('✅ Envío real exitoso — ' + (result.cdr || 'CDR recibido'));
        } else {
            toast('❌ Error en envío real: ' + result.error);
        }
    } catch(e) {
        btn.disabled = false;
        btn.innerHTML = 'Enviar 1 real de prueba';
        toast('❌ Error: ' + e);
    }
}

// ================================================================
// FINALIZAR
// ================================================================

function construirPayload() {
    return {
        licencia:  WZ.licencia,
        empresa:   WZ.empresa,
        fuente:    WZ.fuente,
        contrato:  WZ.contrato,
        series:    WZ.series,
        endpoint:  WZ.endpoint,
        modo:      WZ.modo
    };
}

async function finalizar() {
    // Guardar config final
    WZ.series = leerSeries();
    var payload = construirPayload();
    try {
        await eel.wz_guardar_config(payload)();
    } catch(e) {}

    // Mostrar pantalla final
    document.getElementById('page-6').classList.remove('active');
    document.getElementById('page-final').classList.add('active');

    // Resumen
    var html =
        '<li><span class="check">✓</span><span>Empresa: <strong>' + WZ.empresa.razon_social + '</strong> (RUC ' + WZ.empresa.ruc + ')</span></li>' +
        '<li><span class="check">✓</span><span>Fuente: <strong>' + WZ.fuente.tipo.toUpperCase() + '</strong> — ' + (WZ.fuente.ruta || WZ.fuente.servidor) + '</span></li>' +
        '<li><span class="check">✓</span><span>Endpoint: <strong>' + WZ.endpoint.nombre + '</strong></span></li>' +
        '<li><span class="check">✓</span><span>Series configuradas: boleta, factura</span></li>' +
        '<li><span class="check">✓</span><span>Licencia: <strong>' + WZ.licencia.tipo + '</strong></span></li>';
    document.getElementById('final-resumen').innerHTML = html;

    // Ocultar stepper
    document.getElementById('stepper').style.display = 'none';
}

async function abrirMotor() {
    try {
        await eel.wz_abrir_motor()();
    } catch(e) {
        toast('Abriendo Motor CPE...');
        setTimeout(function() { window.location.href = 'index.html'; }, 1000);
    }
}

// ================================================================
// MODO RECONFIGURAR — Cargar config existente
// ================================================================

async function cargarConfigExistente() {
    try {
        var result = await eel.get_config_cliente()();
        if (!result.exito) return;

        // Pre-rellenar empresa
        var e = result.empresa;
        document.getElementById('emp-ruc').value    = e.ruc         || '';
        document.getElementById('emp-alias').value  = e.alias       || '';
        document.getElementById('emp-razon').value  = e.razon_social|| '';
        document.getElementById('emp-nombre').value = e.nombre_comercial || '';

        // Pre-rellenar fuente
        if (result.fuente) {
            var tipo = result.fuente.tipo || 'dbf';
            selTipo(tipo);
            if (result.fuente.rutas && result.fuente.rutas[0]) {
                document.getElementById('fuente-ruta-input').value = result.fuente.rutas[0];
            }
        }

        // Pre-rellenar series
        if (result.series) {
            WZ.series = result.series;
        }

        // Pre-rellenar endpoint
        if (result.endpoints && result.endpoints[0]) {
            var ep = result.endpoints[0];
            document.getElementById('ep-url').value     = ep.url || '';
            document.getElementById('ep-usuario').value = (ep.credenciales && ep.credenciales.usuario) || '';
        }

        WZ.empresa = { ruc: e.ruc, alias: e.alias, razon_social: e.razon_social, nombre_comercial: e.nombre_comercial };

    } catch(err) { console.error('Error cargando config:', err); }
}

// ================================================================
// UTILS
// ================================================================

function showAlert(id, tipo, msg) {
    var el = document.getElementById(id);
    if (!el) return;
    el.className = 'wz-alert ' + tipo;
    el.innerHTML = msg;
    el.style.display = 'flex';
}

function hideAlert(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = 'none';
}

function toast(msg) {
    var t = document.getElementById('toast');
    t.textContent = msg;
    t.style.display = 'block';
    setTimeout(function() { t.style.display = 'none'; }, 3000);
}
