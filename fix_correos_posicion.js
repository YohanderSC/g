#!/usr/bin/env node
/**
 * fix_correos_posicion.js
 * =======================
 * Ejecutar desde la carpeta Ruleta/:
 *   node fix_correos_posicion.js
 *
 * Problema: el bloque de envío masivo y reenvío individual
 * quedó fuera del div#mod-correos y aparece en todos los módulos.
 * Este script lo elimina donde está mal y lo coloca dentro del módulo.
 */

const fs   = require('fs');
const path = require('path');

const ARCHIVO = path.join(__dirname, 'frontend', 'admin.html');
if (!fs.existsSync(ARCHIVO)) {
  console.error('❌ No se encontró frontend/admin.html');
  process.exit(1);
}

let html = fs.readFileSync(ARCHIVO, 'utf8');
let cambios = 0;

// ════════════════════════════════════════════════════
// PASO 1: Eliminar el bloque suelto que aparece fuera
// Buscar y eliminar el div de "Envío masivo" que está
// fuera del módulo correos
// ════════════════════════════════════════════════════

// Patrón del bloque suelto (puede estar en varias formas)
const patronesSueltos = [
  // Bloque completo con los dos paneles lado a lado
  /<div style="display:flex;gap:14px;flex-wrap:wrap">\s*<div class="tabla-wrap"[^>]*>[\s\S]*?Envío masivo[\s\S]*?<\/div>\s*<div class="tabla-wrap"[^>]*>[\s\S]*?Reenvío individual[\s\S]*?<\/div>\s*<\/div>\s*<div id="resultado-correo"[^>]*><\/div>/,
  // Solo el bloque de stats-row con st-inv y st-part fuera del módulo
  /<div class="stats-row">\s*<div class="stat-card"[^>]*>\s*<div class="stat-num" id="st-inv">/,
];

// Estrategia más segura: reconstruir el módulo correos completo
// Primero eliminar TODOS los elementos de correos que están mal ubicados
const ELEMENTOS_A_ELIMINAR = [
  // Stats row con st-inv fuera del módulo
  {
    inicio: '<div class="stats-row">\n          <div class="stat-card" style="--accent:var(--verde)">\n            <div class="stat-num" id="st-inv">',
    fin: '</div>\n        </div>',
  }
];

// ════════════════════════════════════════════════════
// ESTRATEGIA: buscar el div#mod-correos y reconstruirlo
// ════════════════════════════════════════════════════

// Verificar si ya existe el módulo correos con el selector de ruleta (versión nueva)
const tieneNuevoModulo = html.includes('sel-ruleta-correos') || html.includes('correos-acciones');

if (tieneNuevoModulo) {
  console.log('ℹ️  Ya tiene el módulo correos actualizado. Corrigiendo posición...');
} else {
  console.log('ℹ️  Módulo correos con versión anterior. Aplicando corrección...');
}

// ════════════════════════════════════════════════════
// PASO 2: Limpiar cualquier bloque suelto de correos
// fuera del módulo
// ════════════════════════════════════════════════════

// Patrón 1: bloque de stats con st-inv y st-part fuera del módulo
const RE_STATS_SUELTO = /[ \t]*<div class="stats-row">\s*<div class="stat-card" style="--accent:var\(--verde\)">\s*<div class="stat-num" id="st-inv">[\s\S]*?<\/div>\s*<div class="stat-card" style="--accent:var\(--oro\)">\s*<div class="stat-num" id="st-part">[\s\S]*?<\/div>\s*<\/div>/;

if (RE_STATS_SUELTO.test(html)) {
  // Verificar que NO está dentro del módulo correos
  const matchStats = html.match(RE_STATS_SUELTO);
  if (matchStats) {
    const posStats = html.indexOf(matchStats[0]);
    const posMod   = html.indexOf('id="mod-correos"');
    // Si el bloque está ANTES del módulo correos, está suelto → eliminar
    if (posMod === -1 || posStats < posMod) {
      html = html.replace(RE_STATS_SUELTO, '');
      console.log('✅ Bloque stats suelto eliminado');
      cambios++;
    }
  }
}

// Patrón 2: bloque de envío masivo + reenvío individual sueltos
const RE_BLOQUES_SUELTOS = /[ \t]*<div style="display:flex;gap:14px;flex-wrap:wrap">\s*<div class="tabla-wrap" style="flex:1[^>]*>\s*<div style="padding:16px 20px[^"]*">\s*<div style="font-weight:700[^"]*">Env[ií]o masivo[\s\S]*?<\/div>\s*<div id="resultado-correo"[^>]*><\/div>/;

if (RE_BLOQUES_SUELTOS.test(html)) {
  const matchB = html.match(RE_BLOQUES_SUELTOS);
  if (matchB) {
    const posB   = html.indexOf(matchB[0]);
    const posMod = html.indexOf('id="mod-correos"');
    if (posMod === -1 || posB < posMod || posB > posMod + 5000) {
      html = html.replace(RE_BLOQUES_SUELTOS, '');
      console.log('✅ Bloque envío masivo/reenvío suelto eliminado');
      cambios++;
    }
  }
}

// ════════════════════════════════════════════════════
// PASO 3: Verificar que el módulo correos existe y
// tiene el contenido correcto DENTRO de él
// ════════════════════════════════════════════════════

const MODULO_CORREOS_OK = `      <!-- ══ CORREOS ══ -->
      <div class="modulo" id="mod-correos">

        <!-- SELECTOR DE RULETA -->
        <div class="tabla-wrap" style="margin-bottom:16px">
          <div style="padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:14px;flex-wrap:wrap">
            <div style="font-size:.72rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--oro)">📧 Enviar invitaciones para:</div>
            <select id="sel-ruleta-correos" onchange="onCambioRuletaCorreos()"
              style="flex:1;min-width:240px;background:var(--card2);border:1px solid var(--border-oro);color:var(--txt);border-radius:9px;padding:9px 14px;font-family:'DM Sans',sans-serif;font-size:.9rem;font-weight:600;outline:none;cursor:pointer">
              <option value="">— Selecciona una ruleta —</option>
            </select>
          </div>
        </div>

        <!-- STATS -->
        <div class="stats-row" id="stats-correos" style="display:none">
          <div class="stat-card" style="--accent:var(--azul)">
            <div class="stat-num" id="st-total-cli">—</div>
            <div class="stat-label">Total clientes</div>
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

        <!-- SIN RULETA SELECCIONADA -->
        <div id="correos-empty" style="text-align:center;padding:48px 24px;color:var(--txt-dd)">
          <div style="font-size:2.5rem;margin-bottom:12px;opacity:.3">📧</div>
          <div>Selecciona una ruleta para gestionar sus correos</div>
        </div>

        <!-- ACCIONES (visible solo si hay ruleta) -->
        <div id="correos-acciones" style="display:none">

          <!-- ENVÍO MASIVO -->
          <div class="tabla-wrap" style="margin-bottom:14px">
            <div style="padding:16px 20px;border-bottom:1px solid var(--border)">
              <div style="font-weight:700;font-size:.95rem;margin-bottom:4px">📤 Envío masivo de invitaciones</div>
              <div style="font-size:.82rem;color:var(--txt-dd)">
                Envía la invitación a todos los clientes con estatus "añadido" en lotes de 500.
              </div>
            </div>
            <div style="padding:16px 20px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
              <div id="preview-ruleta-masivo" style="flex:1;font-size:.82rem;color:var(--oro);font-weight:600;min-width:180px"></div>
              <button class="btn btn-primary" id="btn-masivo" style="white-space:nowrap" onclick="enviarMasivo()">
                📧 Enviar invitaciones masivas
              </button>
            </div>
          </div>

          <!-- ENVÍO INDIVIDUAL -->
          <div class="tabla-wrap" style="margin-bottom:14px">
            <div style="padding:16px 20px;border-bottom:1px solid var(--border)">
              <div style="font-weight:700;font-size:.95rem;margin-bottom:4px">✉️ Envío individual</div>
              <div style="font-size:.82rem;color:var(--txt-dd)">Enviar o reenviar la invitación a un cliente por su correo electrónico</div>
            </div>
            <div style="padding:16px 20px">
              <div style="display:flex;gap:10px;flex-wrap:wrap">
                <input id="inp-reenvio-email" type="email" placeholder="correo@cliente.com"
                  style="flex:1;min-width:220px;background:var(--card2);border:1px solid var(--border);color:var(--txt);border-radius:9px;padding:9px 13px;font-family:'DM Sans',sans-serif;font-size:.88rem;outline:none;transition:border-color .2s"
                  onfocus="this.style.borderColor='var(--oro)'" onblur="this.style.borderColor='var(--border)'"
                  onkeydown="if(event.key==='Enter')reenviarCorreo()">
                <button class="btn btn-primary" onclick="reenviarCorreo()" style="white-space:nowrap">📨 Enviar</button>
              </div>
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

// Buscar el módulo correos existente (cualquier versión)
const RE_MOD_CORREOS = /[ \t]*<!-- ══ CORREOS ══ -->[\s\S]*?<div class="modulo" id="mod-correos">[\s\S]*?<\/div>\s*\n(\s*<!-- ══|$)/;

let reemplazado = false;

// Intento 1: reemplazar el módulo completo
if (html.includes('id="mod-correos"')) {
  // Encontrar el inicio
  const inicio = html.indexOf('<!-- ══ CORREOS ══ -->');
  if (inicio !== -1) {
    // Encontrar el cierre del div del módulo
    let depth    = 0;
    let pos      = html.indexOf('<div class="modulo" id="mod-correos">', inicio);
    if (pos === -1) pos = html.indexOf('<div class="modulo"', inicio);
    let i        = pos;
    let encontrado = false;

    while (i < html.length) {
      if (html.startsWith('<div', i)) depth++;
      if (html.startsWith('</div>', i)) {
        depth--;
        if (depth === 0) {
          // Fin del módulo
          const fin = i + 6;
          const viejo = html.slice(inicio, fin);
          html = html.slice(0, inicio) + MODULO_CORREOS_OK + html.slice(fin);
          console.log('✅ Módulo correos reemplazado completamente');
          reemplazado = true;
          cambios++;
          encontrado = true;
          break;
        }
      }
      i++;
    }
    if (!encontrado) {
      console.warn('⚠️  No se pudo determinar el fin del módulo correos. Reemplazando por id...');
    }
  }
}

// Intento 2: si no existe el módulo, insertarlo antes del cierre del content div
if (!reemplazado && !html.includes('id="mod-correos"')) {
  const MARKER = '    </div><!-- /content -->';
  if (html.includes(MARKER)) {
    html = html.replace(MARKER, MODULO_CORREOS_OK + '\n' + MARKER);
    console.log('✅ Módulo correos insertado antes del cierre del content');
    cambios++;
  } else {
    console.error('❌ No se encontró dónde insertar el módulo correos');
  }
}

// ════════════════════════════════════════════════════
// PASO 4: Asegurar que el JS de correos existe
// ════════════════════════════════════════════════════

if (!html.includes('function onCambioRuletaCorreos')) {
  const JS_CORREOS = `
// ═══════════════════════════════════════════════════
// MÓDULO CORREOS
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
  const id      = document.getElementById('sel-ruleta-correos').value;
  const stats   = document.getElementById('stats-correos');
  const acciones= document.getElementById('correos-acciones');
  const empty   = document.getElementById('correos-empty');
  const resultado = document.getElementById('resultado-correo');
  if (resultado) resultado.innerHTML = '';

  if (!id) {
    if (stats)    stats.style.display    = 'none';
    if (acciones) acciones.style.display = 'none';
    if (empty)    empty.style.display    = 'block';
    return;
  }

  const ru = ruletasCache.find(r => r.id === parseInt(id));
  if (empty)    empty.style.display    = 'none';
  if (acciones) acciones.style.display = 'block';
  if (stats)    stats.style.display    = 'grid';

  const prev = document.getElementById('preview-ruleta-masivo');
  if (prev && ru) prev.textContent = '📋 Ruleta seleccionada: ' + ru.nombre;

  await cargarEstadoCorreos(id);
  await cargarHistorialCorreos();
}

async function cargarEstadoCorreos(ruletaId) {
  const id = ruletaId || document.getElementById('sel-ruleta-correos')?.value;
  try {
    const pend = await api('/clientes/?pagina=1&estatus=anadido');
    const part = await api('/clientes/?pagina=1&estatus=participo');
    const total = await api('/clientes/?pagina=1');
    const stInv  = document.getElementById('st-inv');
    const stPart = document.getElementById('st-part');
    const stTot  = document.getElementById('st-total-cli');
    if (stInv)  stInv.textContent  = pend.total ?? '—';
    if (stPart) stPart.textContent = part.total ?? '—';
    if (stTot)  stTot.textContent  = total.total ?? '—';
  } catch(e) { console.error('Stats correos:', e); }
}

async function cargarHistorialCorreos() {
  const id  = document.getElementById('sel-ruleta-correos')?.value;
  const tbl = document.getElementById('tabla-historial-correos');
  if (!tbl) return;
  if (!id) {
    tbl.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--txt-dd)">Selecciona una ruleta para ver el historial</td></tr>';
    return;
  }
  tbl.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--txt-dd)">Cargando...</td></tr>';
  try {
    const d = await api('/correos/historial/ruleta/' + id);
    const rows = d.datos || d.correos || [];
    const tipoIco = { invitacion:'📩', felicitacion:'🏆', referido:'🤝', reenvio:'🔄' };
    const estCol  = { enviado:'badge-verde', fallido:'badge-rojo', pendiente:'badge-naranja' };
    tbl.innerHTML = rows.length
      ? rows.map((c,i) => \`<tr style="border-top:1px solid var(--border);background:\${i%2===0?'var(--card2)':'transparent'}">
          <td style="padding:10px 14px;font-size:.83rem">\${c.cliente_email||c.email||'—'}</td>
          <td style="padding:10px 14px;font-size:.8rem">\${tipoIco[c.tipo]||'📧'} \${c.tipo||'—'}</td>
          <td style="padding:10px 14px"><span class="badge \${estCol[c.estado]||'badge-azul'}">\${c.estado||'—'}</span></td>
          <td style="padding:10px 14px;font-size:.78rem;color:var(--txt-dd)">\${c.fecha_envio?.slice(0,16)||'—'}</td>
        </tr>\`).join('')
      : '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--txt-dd)">Sin correos enviados aún</td></tr>';
  } catch {
    tbl.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--txt-dd)">Sin historial disponible</td></tr>';
  }
}

async function enviarMasivo() {
  const ruletaId = document.getElementById('sel-ruleta-correos')?.value;
  const btn      = document.getElementById('btn-masivo');
  const resultado= document.getElementById('resultado-correo');
  const ru       = ruletasCache.find(r => r.id === parseInt(ruletaId));
  if (!ruletaId) { toast('Selecciona una ruleta primero', 'err'); return; }
  if (!confirm('¿Enviar invitaciones para la ruleta "' + (ru?.nombre||ruletaId) + '"?')) return;
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="border-top-color:#000"></div> Enviando...';
  try {
    const d = await api('/correos/masivo/?ruleta_id=' + ruletaId, { method:'POST' });
    if (resultado) resultado.innerHTML = \`
      <div class="tabla-wrap" style="padding:16px 20px">
        <div style="font-weight:700;margin-bottom:10px;color:var(--verde)">✅ Envío completado — \${ru?.nombre||''}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;font-size:.85rem;color:var(--txt-d)">
          <div>Total<br><strong style="font-size:1.1rem;color:var(--txt)">\${d.total}</strong></div>
          <div>Enviados<br><strong style="font-size:1.1rem;color:var(--verde)">\${d.enviados}</strong></div>
          <div>Fallidos<br><strong style="font-size:1.1rem;color:var(--rojo)">\${d.fallidos}</strong></div>
          <div>Lotes<br><strong style="font-size:1.1rem;color:var(--txt)">\${d.lotes_procesados}</strong></div>
        </div>
      </div>\`;
    toast('Enviados: ' + d.enviados + '  |  Fallidos: ' + d.fallidos, 'ok');
    await onCambioRuletaCorreos();
  } catch(e) {
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
    const url = valor.includes('@')
      ? '/correos/reenviar/email/?email=' + encodeURIComponent(valor) + '&ruleta_id=' + ruletaId
      : '/correos/reenviar/' + valor + '?ruleta_id=' + ruletaId;
    const d = await api(url, { method:'POST' });
    toast('📨 Correo enviado a ' + (d.email || valor), 'ok');
    if (emailEl) emailEl.value = '';
    if (idEl)    idEl.value    = '';
    await cargarHistorialCorreos();
  } catch(e) { toast(e.message, 'err'); }
}
`;

  const lastScript = html.lastIndexOf('</script>');
  if (lastScript !== -1) {
    html = html.slice(0, lastScript) + JS_CORREOS + '\n</script>' + html.slice(lastScript + 9);
    console.log('✅ JS del módulo correos agregado');
    cambios++;
  }
}

// ════════════════════════════════════════════════════
// Conectar al switch de navegación
// ════════════════════════════════════════════════════
const OLD_NAV = `if (mod === 'correos') cargarEstadoCorreos();`;
const NEW_NAV = `if (mod === 'correos') { llenarSelectorCorreos(); }`;
if (html.includes(OLD_NAV)) {
  html = html.replace(OLD_NAV, NEW_NAV);
  console.log('✅ Navegación a correos corregida');
  cambios++;
}

// Si no estaba la conexión, agregar
const OLD_NAV2 = `if (mod === 'correos') { llenarSelectorCorreos(); cargarEstadoCorreos(); }`;
if (html.includes(OLD_NAV2)) {
  html = html.replace(OLD_NAV2, `if (mod === 'correos') { llenarSelectorCorreos(); }`);
  cambios++;
}

// ════════════════════════════════════════════════════
// Conectar llenarSelectorCorreos a llenarSelectores()
// ════════════════════════════════════════════════════
if (html.includes('function llenarSelectores()') && !html.includes('llenarSelectorCorreos()')) {
  html = html.replace(
    'function llenarSelectores() {',
    'function llenarSelectores() {\n  llenarSelectorCorreos();'
  );
  console.log('✅ Selector correos conectado a llenarSelectores()');
  cambios++;
}

// ════════════════════════════════════════════════════
// GUARDAR
// ════════════════════════════════════════════════════
fs.writeFileSync(ARCHIVO, html, 'utf8');
console.log(`\n✅ Listo — ${cambios} correcciones aplicadas`);
console.log('   Reinicia el servidor: uvicorn main:app --reload');
console.log('   Recarga el navegador (Ctrl+Shift+R)');
