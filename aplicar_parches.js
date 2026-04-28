#!/usr/bin/env node
/**
 * APLICAR_PARCHES.js
 * ==================
 * Ejecutar desde la carpeta del proyecto:
 *   node aplicar_parches.js
 *
 * Lee tu admin.html, aplica los 4 cambios y lo guarda.
 */

const fs = require('fs');
const path = require('path');

const ARCHIVO = path.join(__dirname, 'frontend', 'admin.html');

if (!fs.existsSync(ARCHIVO)) {
  console.error('❌ No se encontró frontend/admin.html');
  console.error('   Ejecuta este script desde la raíz del proyecto (donde está main.py)');
  process.exit(1);
}

let html = fs.readFileSync(ARCHIVO, 'utf8');
let cambios = 0;

// ════════════════════════════════════════════════════
// MEJORA 1 — Botón "Asignar a Ruleta" en módulo Clientes
// ════════════════════════════════════════════════════
const OLD1 = `<button class="btn btn-secondary" onclick="abrirImport()">📂 Importar XLSX</button>`;
const NEW1 = `<button class="btn btn-secondary" onclick="abrirAsignarRuleta()" title="Asignar cliente existente a una ruleta por email">🎡 Asignar a Ruleta</button>
          <button class="btn btn-secondary" onclick="abrirImport()">📂 Importar XLSX</button>`;

if (html.includes(OLD1)) {
  html = html.replace(OLD1, NEW1);
  console.log('✅ Mejora 1: Botón "Asignar a Ruleta" agregado');
  cambios++;
} else {
  console.warn('⚠️  Mejora 1: No se encontró el punto de inserción (puede ya estar aplicado)');
}

// ════════════════════════════════════════════════════
// MEJORA 2 — Reenvío por EMAIL en módulo Correos
// ════════════════════════════════════════════════════
const OLD2 = `<input id="inp-reenvio-id" type="number" placeholder="ID del cliente"`;
const NEW2 = `<input id="inp-reenvio-email" type="email" placeholder="correo@cliente.com"`;

if (html.includes(OLD2)) {
  html = html.replace(OLD2, NEW2);
  console.log('✅ Mejora 2: Campo de reenvío cambiado a email');
  cambios++;
} else {
  console.warn('⚠️  Mejora 2: No se encontró inp-reenvio-id');
}

// ════════════════════════════════════════════════════
// MEJORA 3 — Ocultar token en la tabla de Clientes
// ════════════════════════════════════════════════════

// Quitar columna Token del encabezado
const OLD3A = `<th>Token</th>`;
if (html.includes(OLD3A)) {
  html = html.replace(OLD3A, '');
  console.log('✅ Mejora 3a: Columna Token eliminada del encabezado');
  cambios++;
}

// Quitar celda de token en las filas (puede tener variantes)
const tokenPatterns = [
  /\s*<td><code[^>]*>\$\{c\.token[^<]+<\/code><\/td>/g,
  /\s*<td style="[^"]*"><code[^>]*>\$\{c\.token[^<]+<\/code><\/td>/g,
];
for (const pat of tokenPatterns) {
  if (pat.test(html)) {
    html = html.replace(pat, '');
    console.log('✅ Mejora 3b: Celda de token eliminada de las filas');
    cambios++;
    break;
  }
}

// ════════════════════════════════════════════════════
// JS — Funciones nuevas para las mejoras 1 y 2
// ════════════════════════════════════════════════════
const JS_NUEVO = `
// ═══════════════════════════════════════════════════
// MEJORA 1 — Asignar cliente a ruleta por email
// ═══════════════════════════════════════════════════
function abrirAsignarRuleta() {
  document.getElementById('modal-titulo').textContent = 'Asignar cliente a ruleta';
  document.getElementById('modal-body').innerHTML = \`
    <div style="margin-bottom:14px;font-size:.85rem;color:var(--txt-d);line-height:1.6">
      Ingresa el email del cliente y selecciona la ruleta. Si el cliente no existe, se crea automaticamente.
    </div>
    <div class="form-row">
      <label>Email del cliente</label>
      <input type="email" id="f-asignar-email" placeholder="correo@cliente.com">
    </div>
    <div class="form-row">
      <label>Ruleta</label>
      <select id="f-asignar-ruleta">
        <option value="">Selecciona una ruleta...</option>
        \${ruletasCache.map(r => \`<option value="\${r.id}">\${r.nombre}</option>\`).join('')}
      </select>
    </div>
    <div id="resultado-asignacion" style="margin-top:10px"></div>
  \`;
  document.getElementById('modal-footer').innerHTML = \`
    <button class="btn btn-secondary" onclick="cerrarModal()">Cancelar</button>
    <button class="btn btn-primary" id="btn-asignar" onclick="confirmarAsignacion()">Asignar</button>
  \`;
  abrirModal();
}

async function confirmarAsignacion() {
  const email    = document.getElementById('f-asignar-email').value.trim();
  const ruletaId = document.getElementById('f-asignar-ruleta').value;
  const res      = document.getElementById('resultado-asignacion');
  const btn      = document.getElementById('btn-asignar');

  if (!email)    { toast('Ingresa el email del cliente', 'err'); return; }
  if (!ruletaId) { toast('Selecciona una ruleta', 'err'); return; }

  btn.disabled = true; btn.textContent = 'Asignando...';
  try {
    const d = await api(\`/clientes/asignar-ruleta/?email=\${encodeURIComponent(email)}&ruleta_id=\${ruletaId}\`, { method: 'POST' });
    res.innerHTML = \`
      <div style="background:var(--verde-p);border:1px solid rgba(39,174,96,.3);border-radius:10px;padding:12px 14px;font-size:.84rem;color:var(--verde)">
        \${d.creado ? '✅ Cliente creado y asignado' : '✅ Cliente asignado correctamente'}<br>
        <span style="color:var(--txt-dd);font-size:.78rem">\${d.email} → \${d.ruleta}</span>
      </div>\`;
    toast(d.mensaje, 'ok');
    cargarClientes(1);
    cargarDashboard();
  } catch(e) {
    res.innerHTML = \`<div style="background:var(--rojo-p);border:1px solid rgba(231,76,60,.3);border-radius:10px;padding:12px 14px;font-size:.84rem;color:var(--rojo)">❌ \${e.message}</div>\`;
  } finally {
    btn.disabled = false; btn.textContent = 'Asignar';
  }
}

// ═══════════════════════════════════════════════════
// MEJORA 2 — Reenviar correo por email (no por ID)
// ═══════════════════════════════════════════════════
async function reenviarCorreo() {
  const emailInput = document.getElementById('inp-reenvio-email');
  const idInput    = document.getElementById('inp-reenvio-id');
  const valor      = (emailInput || idInput)?.value?.trim();
  if (!valor) { toast('Ingresa el email del cliente', 'err'); return; }

  try {
    let d;
    // Si tiene @ es email, si no es ID (compatibilidad)
    if (valor.includes('@')) {
      d = await api(\`/correos/reenviar/email/?email=\${encodeURIComponent(valor)}\`, { method: 'POST' });
    } else {
      d = await api(\`/correos/reenviar/\${valor}\`, { method: 'POST' });
    }
    toast(\`Correo reenviado a \${d.email || valor}\`, 'ok');
    if (emailInput) emailInput.value = '';
    if (idInput)    idInput.value = '';
  } catch(e) { toast(e.message, 'err'); }
}
`;

// Insertar el JS antes del cierre de </script>
if (html.includes('</script>')) {
  html = html.replace(/(<\/script>\s*<\/body>)/i, JS_NUEVO + '\n$1');
  console.log('✅ JS de mejoras 1 y 2 agregado');
  cambios++;
} else {
  html = html.replace('</script>', JS_NUEVO + '\n</script>');
  console.log('✅ JS de mejoras 1 y 2 agregado (fallback)');
  cambios++;
}

// ════════════════════════════════════════════════════
// GUARDAR
// ════════════════════════════════════════════════════
fs.writeFileSync(ARCHIVO, html, 'utf8');
console.log(`\n✅ admin.html actualizado — ${cambios} cambios aplicados`);
console.log('   Recarga el navegador para ver los cambios.');
