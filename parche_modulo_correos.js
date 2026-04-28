#!/usr/bin/env node
/**
 * parche_modulo_correos.js
 * ========================
 * Ejecutar desde la carpeta raíz del proyecto:
 *   node parche_modulo_correos.js
 *
 * Mejoras al módulo de Correos:
 *  1. Selector de ruleta antes de enviar
 *  2. Envío masivo solo a clientes de esa ruleta (estatus anadido)
 *  3. Reenvío individual por email con ruleta seleccionada
 *  4. Stats dinámicas según la ruleta seleccionada
 *  5. Historial de correos enviados por ruleta
 */

const fs   = require('fs');
const path = require('path');

const ARCHIVO = path.join(__dirname, 'frontend', 'admin.html');
if (!fs.existsSync(ARCHIVO)) {
  console.error('❌ No se encontró frontend/admin.html');
  process.exit(1);
}

let html = fs.readFileSync(ARCHIVO, 'utf8');

// ════════════════════════════════════════════════════
// 1. REEMPLAZAR el módulo de correos completo en el HTML
// ════════════════════════════════════════════════════
const OLD_MOD = `      <!-- ══ CORREOS ══ -->
      <div class="modulo" id="mod-correos">
        <div class="stats-row">
          <div class="stat-card" style="--accent:var(--verde)">
            <div class="stat-num" id="st-inv">—</div>
            <div class="stat-label">Pendientes de invitar</div>
          </div>
          <div class="stat-card" style="--accent:var(--oro)">
            <div class="stat-num" id="st-part">—</div>
            <div class="stat-label">Participaron</div>
          </div>
        </div>
        <div style="display:flex;gap:14px;flex-wrap:wrap">
          <div class="tabla-wrap" style="flex:1;min-width:280px">
            <div style="padding:16px 20px;border-bottom:1px solid var(--border)">
              <div style="font-weight:700;margin-bottom:4px">Envío masivo de invitaciones</div>
              <div style="font-size:.82rem;color:var(--txt-dd)">Envía a todos los clientes con estatus "añadido" en lotes de 500</div>
            </div>
            <div style="padding:16px 20px">
              <button class="btn btn-primary" style="width:100%" onclick="enviarMasivo()">📧 Enviar invitaciones masivas</button>
            </div>
          </div>
          <div class="tabla-wrap" style="flex:1;min-width:280px">
            <div style="padding:16px 20px;border-bottom:1px solid var(--border)">
              <div style="font-weight:700;margin-bottom:4px">Reenvío individual</div>
              <div style="font-size:.82rem;color:var(--txt-dd)">Reenviar correo a un cliente específico por ID</div>
            </div>
            <div style="padding:16px 20px;display:flex;gap:10px">
              <input id="inp-reenvio-id" type="number" placeholder="ID del cliente" style="flex:1;background:var(--card2);border:1px solid var(--border);color:var(--txt);border-radius:9px;padding:9px 13px;font-family:'DM Sans',sans-serif;font-size:.88rem;outline:none">
              <button class="btn btn-secondary" onclick="reenviarCorreo()">Reenviar</button>
            </div>
          </div>
        </div>
        <div id="resultado-correo" style="margin-top:14px"></div>
      </div>`;

const NEW_MOD = `      <!-- ══ CORREOS ══ -->
      <div class="modulo" id="mod-correos">

        <!-- SELECTOR DE RULETA — paso obligatorio -->
        <div class="tabla-wrap" style="margin-bottom:16px">
          <div style="padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:14px;flex-wrap:wrap">
            <div style="font-size:.72rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--oro)">📧 Enviar invitaciones para:</div>
            <select id="sel-ruleta-correos" onchange="onCambioRuletaCorreos()"
              style="flex:1;min-width:240px;background:var(--card2);border:1px solid var(--border-oro);color:var(--txt);border-radius:9px;padding:9px 14px;font-family:'DM Sans',sans-serif;font-size:.9rem;font-weight:600;outline:none;cursor:pointer">
              <option value="">— Selecciona una ruleta —</option>
            </select>
          </div>
        </div>

        <!-- STATS DE LA RULETA SELECCIONADA -->
        <div class="stats-row" id="stats-correos" style="display:none">
          <div class="stat-card" style="--accent:var(--azul)">
            <div class="stat-num" id="st-total-cli">—</div>
            <div class="stat-label">Clientes registrados</div>
          </div>
          <div class="stat-card" style="--accent:var(--naranja)">
            <div class="stat-num" id="st-inv">—</div>
            <div class="stat-label">Pendientes de invitar</div>
          </div>
          <div class="stat-card" style="--accent:var(--verde)">
            <div class="stat-num" id="st-part">—</div>
            <div class="stat-label">Ya participaron</div>
          </div>
          <div class="stat-card" style="--accent:var(--oro)">
            <div class="stat-num" id="st-enviados">—</div>
            <div class="stat-label">Correos enviados</div>
          </div>
        </div>

        <!-- PANEL VACÍO si no hay ruleta seleccionada -->
        <div id="correos-empty" style="text-align:center;padding:48px 24px;color:var(--txt-dd)">
          <div style="font-size:2.5rem;margin-bottom:12px;opacity:.3">📧</div>
          <div>Selecciona una ruleta para gestionar sus correos</div>
        </div>

        <!-- ACCIONES — visible solo si hay ruleta seleccionada -->
        <div id="correos-acciones" style="display:none">

          <!-- ENVÍO MASIVO -->
          <div class="tabla-wrap" style="margin-bottom:14px">
            <div style="padding:16px 20px;border-bottom:1px solid var(--border)">
              <div style="font-weight:700;font-size:.95rem;margin-bottom:4px">📤 Envío masivo de invitaciones</div>
              <div style="font-size:.82rem;color:var(--txt-dd)" id="desc-masivo">
                Envía la invitación a todos los clientes con estatus "añadido" en lotes de 500.
              </div>
            </div>
            <div style="padding:16px 20px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
              <div style="flex:1;min-width:200px">
                <div id="preview-ruleta-masivo" style="font-size:.82rem;color:var(--oro);font-weight:600"></div>
              </div>
              <button class="btn btn-primary" id="btn-masivo" style="white-space:nowrap" onclick="enviarMasivo()">
                📧 Enviar invitaciones masivas
              </button>
            </div>
          </div>

          <!-- ENVÍO INDIVIDUAL -->
          <div class="tabla-wrap" style="margin-bottom:14px">
            <div style="padding:16px 20px;border-bottom:1px solid var(--border)">
              <div style="font-weight:700;font-size:.95rem;margin-bottom:4px">✉️ Envío individual</div>
              <div style="font-size:.82rem;color:var(--txt-dd)">Enviar o reenviar la invitación a un cliente específico por su correo</div>
            </div>
            <div style="padding:16px 20px;display:flex;gap:10px;flex-wrap:wrap">
              <input id="inp-reenvio-email" type="email" placeholder="correo@cliente.com"
                style="flex:1;min-width:220px;background:var(--card2);border:1px solid var(--border);color:var(--txt);border-radius:9px;padding:9px 13px;font-family:'DM Sans',sans-serif;font-size:.88rem;outline:none;transition:border-color .2s"
                onfocus="this.style.borderColor='var(--oro)'" onblur="this.style.borderColor='var(--border)'"
                onkeydown="if(event.key==='Enter')reenviarCorreo()">
              <button class="btn btn-secondary" onclick="reenviarCorreo()" style="white-space:nowrap">
                📨 Enviar
              </button>
            </div>
          </div>

          <!-- HISTORIAL -->
          <div class="tabla-wrap">
            <div style="padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between">
              <div style="font-weight:700;font-size:.95rem">📋 Historial de correos</div>
              <button class="btn btn-secondary btn-sm" onclick="cargarHistorialCorreos()">↻ Actualizar</button>
            </div>
            <table style="width:100%;border-collapse:collapse">
              <thead>
                <tr style="background:var(--card2)">
                  <th style="padding:10px 14px;text-align:left;font-size:.7rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--txt-dd);border-bottom:1px solid var(--border)">Cliente</th>
                  <th style="padding:10px 14px;text-align:left;font-size:.7rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--txt-dd);border-bottom:1px solid var(--border)">Tipo</th>
                  <th style="padding:10px 14px;text-align:left;font-size:.7rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--txt-dd);border-bottom:1px solid var(--border)">Estado</th>
                  <th style="padding:10px 14px;text-align:left;font-size:.7rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--txt-dd);border-bottom:1px solid var(--border)">Fecha</th>
                </tr>
              </thead>
              <tbody id="tabla-historial-correos">
                <tr><td colspan="4" style="text-align:center;padding:24px;color:var(--txt-dd);font-size:.85rem">Selecciona una ruleta para ver el historial</td></tr>
              </tbody>
            </table>
          </div>

        </div><!-- /correos-acciones -->

        <div id="resultado-correo" style="margin-top:14px"></div>
      </div>`;

if (html.includes(OLD_MOD)) {
  html = html.replace(OLD_MOD, NEW_MOD);
  console.log('✅ Módulo correos reemplazado correctamente');
} else {
  // Intentar reemplazo parcial buscando el div del módulo
  console.warn('⚠️  No se encontró el módulo exacto — buscando alternativa...');
  const re = /<!-- ══ CORREOS ══ -->[\s\S]*?<\/div>\s*\n\s*<\/div>\s*\n\s*<\/div>/;
  if (re.test(html)) {
    html = html.replace(re, NEW_MOD);
    console.log('✅ Módulo correos reemplazado (método alternativo)');
  } else {
    console.error('❌ No se pudo encontrar el módulo de correos. Revisa manualmente.');
  }
}

// ════════════════════════════════════════════════════
// 2. AGREGAR JS DEL MÓDULO CORREOS
// ════════════════════════════════════════════════════
const JS = `
// ═══════════════════════════════════════════════════
// MÓDULO CORREOS — con selector de ruleta
// ═══════════════════════════════════════════════════

function llenarSelectorCorreos() {
  const sel = document.getElementById('sel-ruleta-correos');
  if (!sel) return;
  const valAct = sel.value;
  sel.innerHTML = '<option value="">— Selecciona una ruleta —</option>';
  ruletasCache.forEach(r => {
    const o = document.createElement('option');
    o.value = r.id;
    o.textContent = (r.activa ? '🟢' : '🔴') + ' ' + r.nombre;
    if (String(r.id) === valAct) o.selected = true;
    sel.appendChild(o);
  });
}

async function onCambioRuletaCorreos() {
  const id = document.getElementById('sel-ruleta-correos').value;
  const stats   = document.getElementById('stats-correos');
  const acciones= document.getElementById('correos-acciones');
  const empty   = document.getElementById('correos-empty');

  if (!id) {
    stats.style.display    = 'none';
    acciones.style.display = 'none';
    empty.style.display    = 'block';
    return;
  }

  const ru = ruletasCache.find(r => r.id === parseInt(id));
  empty.style.display    = 'none';
  acciones.style.display = 'block';
  stats.style.display    = 'grid';

  // Mostrar nombre de la ruleta seleccionada
  const prev = document.getElementById('preview-ruleta-masivo');
  if (prev && ru) prev.textContent = '📋 Ruleta: ' + ru.nombre;

  await cargarEstadoCorreos(id);
  await cargarHistorialCorreos();
}

async function cargarEstadoCorreos(ruletaId) {
  const id = ruletaId || document.getElementById('sel-ruleta-correos')?.value;
  if (!id) return;
  try {
    // Total de clientes
    const total = await api(\`/clientes/?pagina=1\`);
    document.getElementById('st-total-cli').textContent = total.total ?? '—';

    // Pendientes (estatus anadido)
    const pend  = await api(\`/clientes/?pagina=1&estatus=anadido\`);
    document.getElementById('st-inv').textContent = pend.total ?? '—';

    // Participaron
    const part  = await api(\`/clientes/?pagina=1&estatus=participo\`);
    document.getElementById('st-part').textContent = part.total ?? '—';

    // Correos enviados — historial de la ruleta
    try {
      const hist = await api(\`/correos/historial/ruleta/\${id}\`);
      document.getElementById('st-enviados').textContent = hist.total ?? '—';
    } catch { document.getElementById('st-enviados').textContent = '—'; }

  } catch(e) { console.error('Error stats correos:', e); }
}

async function cargarHistorialCorreos() {
  const id  = document.getElementById('sel-ruleta-correos')?.value;
  const tbl = document.getElementById('tabla-historial-correos');
  if (!id || !tbl) return;

  tbl.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--txt-dd)">Cargando...</td></tr>';

  try {
    const d = await api(\`/correos/historial/ruleta/\${id}\`);
    const rows = d.datos || d.correos || [];

    const tipoIco = { invitacion:'📩', felicitacion:'🏆', referido:'🤝', reenvio:'🔄' };
    const estCol  = { enviado:'badge-verde', fallido:'badge-rojo', pendiente:'badge-naranja' };

    tbl.innerHTML = rows.length
      ? rows.map((c, i) => \`
          <tr style="border-top:1px solid var(--border);background:\${i%2===0?'var(--card2)':'transparent'}">
            <td style="padding:10px 14px;font-size:.83rem">\${c.cliente_email || c.email || '—'}</td>
            <td style="padding:10px 14px;font-size:.8rem">\${tipoIco[c.tipo]||'📧'} \${c.tipo||'—'}</td>
            <td style="padding:10px 14px"><span class="badge \${estCol[c.estado]||'badge-azul'}">\${c.estado||'—'}</span></td>
            <td style="padding:10px 14px;font-size:.78rem;color:var(--txt-dd)">\${c.fecha_envio?.slice(0,16)||'—'}</td>
          </tr>\`).join('')
      : '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--txt-dd);font-size:.85rem">Sin correos enviados para esta ruleta</td></tr>';
  } catch {
    tbl.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--txt-dd)">Sin historial disponible</td></tr>';
  }
}

async function enviarMasivo() {
  const ruletaId  = document.getElementById('sel-ruleta-correos')?.value;
  const btn       = document.getElementById('btn-masivo');
  const resultado = document.getElementById('resultado-correo');
  const ru        = ruletasCache.find(r => r.id === parseInt(ruletaId));

  if (!ruletaId) { toast('Selecciona una ruleta primero', 'err'); return; }

  if (!confirm(\`¿Enviar invitaciones masivas para la ruleta "\${ru?.nombre || ruletaId}"?\`)) return;

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="border-top-color:#000"></div> Enviando...';

  try {
    const d = await api(\`/correos/masivo/?ruleta_id=\${ruletaId}\`, { method:'POST' });
    resultado.innerHTML = \`
      <div class="tabla-wrap" style="padding:16px 20px">
        <div style="font-weight:700;margin-bottom:8px;color:var(--verde)">✅ Envío completado — \${ru?.nombre||''}</div>
        <div style="font-size:.85rem;color:var(--txt-d);display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-top:10px">
          <div>Total<br><strong style="font-size:1.1rem">\${d.total}</strong></div>
          <div>Enviados<br><strong style="font-size:1.1rem;color:var(--verde)">\${d.enviados}</strong></div>
          <div>Fallidos<br><strong style="font-size:1.1rem;color:var(--rojo)">\${d.fallidos}</strong></div>
          <div>Lotes<br><strong style="font-size:1.1rem">\${d.lotes_procesados}</strong></div>
        </div>
      </div>\`;
    toast(\`✅ Enviados: \${d.enviados}  |  Fallidos: \${d.fallidos}\`, 'ok');
    await onCambioRuletaCorreos();
  } catch(e) {
    resultado.innerHTML = \`<div style="color:var(--rojo);font-size:.85rem;padding:12px">❌ \${e.message}</div>\`;
    toast(e.message, 'err');
  } finally {
    btn.disabled  = false;
    btn.innerHTML = '📧 Enviar invitaciones masivas';
  }
}

async function reenviarCorreo() {
  const ruletaId = document.getElementById('sel-ruleta-correos')?.value;
  const emailEl  = document.getElementById('inp-reenvio-email');
  const idEl     = document.getElementById('inp-reenvio-id');
  const valor    = (emailEl || idEl)?.value?.trim();

  if (!ruletaId) { toast('Selecciona una ruleta primero', 'err'); return; }
  if (!valor)    { toast('Ingresa el correo del cliente', 'err'); return; }

  try {
    let url;
    if (valor.includes('@')) {
      url = \`/correos/reenviar/email/?email=\${encodeURIComponent(valor)}&ruleta_id=\${ruletaId}\`;
    } else {
      url = \`/correos/reenviar/\${valor}?ruleta_id=\${ruletaId}\`;
    }
    const d = await api(url, { method:'POST' });
    toast(\`📨 Correo enviado a \${d.email || valor}\`, 'ok');
    if (emailEl) emailEl.value = '';
    if (idEl)    idEl.value    = '';
    await cargarHistorialCorreos();
  } catch(e) { toast(e.message, 'err'); }
}
`;

// Insertar antes del cierre del último </script>
const lastScript = html.lastIndexOf('</script>');
if (lastScript !== -1) {
  html = html.slice(0, lastScript) + JS + '\n</script>' + html.slice(lastScript + 9);
  console.log('✅ JS del módulo correos agregado');
} else {
  console.error('❌ No se encontró </script> en el archivo');
}

// ════════════════════════════════════════════════════
// 3. Conectar llenarSelectorCorreos() al init y al
//    cambio de ruletas en el sidebar
// ════════════════════════════════════════════════════
// Cuando el módulo correos se activa, llenar el selector
const OLD_CORREOS_IR = `if (mod === 'correos') cargarEstadoCorreos();`;
const NEW_CORREOS_IR = `if (mod === 'correos') { llenarSelectorCorreos(); cargarEstadoCorreos(); }`;
if (html.includes(OLD_CORREOS_IR)) {
  html = html.replace(OLD_CORREOS_IR, NEW_CORREOS_IR);
  console.log('✅ Selector correos conectado al cambio de módulo');
}

// También llenar cuando se recarga ruletas
const OLD_LLENAR = `function llenarSelectores() {`;
const NEW_LLENAR = `function llenarSelectores() {\n  // Selector de ruleta en correos\n  llenarSelectorCorreos();`;
if (html.includes(OLD_LLENAR) && !html.includes('llenarSelectorCorreos()')) {
  html = html.replace(OLD_LLENAR, NEW_LLENAR);
  console.log('✅ Selector correos conectado a llenarSelectores()');
}

// ════════════════════════════════════════════════════
// GUARDAR
// ════════════════════════════════════════════════════
fs.writeFileSync(ARCHIVO, html, 'utf8');
console.log('\n✅ admin.html actualizado con el módulo de correos mejorado');
console.log('   Reinicia el servidor y recarga el navegador.\n');
