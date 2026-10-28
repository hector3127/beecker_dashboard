/** Native GET navigation feedback; no provider requests or invented loading. */
const form = document.querySelector('.inventory-search');
const button = form?.querySelector('button[type="submit"]');
const progress = document.querySelector('#inventory-cut-progress');
const table = document.querySelector('#summary-projects-table');
const progressChildren = [...(progress?.childNodes ?? [])].map(node => node.cloneNode(true));
const originals = new Map();
let timeout;

function reset() {
  clearTimeout(timeout);
  if (button) button.disabled = false;
  form?.removeAttribute('aria-busy');
  table?.removeAttribute('aria-busy');
  if (progress) {
    progress.hidden = true;
    progress.replaceChildren(...progressChildren.map(node => node.cloneNode(true)));
  }
  for (const [cell, children] of originals) {
    cell.replaceChildren(...children.map(node => node.cloneNode(true)));
  }
  originals.clear();
}

form?.addEventListener('submit', () => {
  if (!button || !progress || !form.checkValidity()) return;
  button.disabled = true;
  form.setAttribute('aria-busy', 'true');
  table?.setAttribute('aria-busy', 'true');
  progress.hidden = false;
  for (const cell of document.querySelectorAll('[data-azure-metric]')) {
    originals.set(cell, [...cell.childNodes].map(node => node.cloneNode(true)));
    const spinner = document.createElement('span');
    spinner.className = 'inventory-spinner';
    spinner.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span');
    label.className = 'inventory-loading-label';
    label.textContent = 'Consultando corte…';
    cell.replaceChildren(spinner, label);
  }
  timeout = setTimeout(() => {
    reset();
    progress.hidden = false;
    progress.textContent = 'La consulta está tardando. Puedes volver a consultar el corte.';
  }, 15000);
});

window.addEventListener('pageshow', reset);
window.addEventListener('pagehide', () => clearTimeout(timeout));
