// Shared persistent logos: account detail and account list. Reads use the
// shared catalogue; uploads send multipart data, which the JSON client cannot.
import { el } from '#app/lib/dom.js';
import { findAccountLogo, loadAccountLogoCatalog, resetAccountLogos } from '#app/lib/account-logos.js';
import { config } from '#app/data/config.js';
const endpoint = '/api/v1/account-logos/';
const root = document.getElementById('account');
const editor = document.getElementById('account-logo-editor');
const initials = name => {
  const words=name.trim().split(/\s+/);
  return words.length===1 ? words[0].slice(0,3).toUpperCase() : words.slice(0,2).map(word=>word[0]).join('').toUpperCase();
};
const fallbacks = new WeakMap();
function restore(host) {
  host.replaceChildren(...fallbacks.get(host).map(node=>node.cloneNode(true)));
  host.classList.remove('has-logo');
}
function image(host, url, name) {
  if(!fallbacks.has(host))fallbacks.set(host,[...host.childNodes].map(node=>node.cloneNode(true)));
  const img=el('img',{src:url,alt:`Logo de ${name}`,loading:root?'eager':'lazy',decoding:'async'});
  img.addEventListener('error',()=>restore(host),{once:true});
  host.replaceChildren(img);host.classList.add('has-logo');
}
if(root){
  const host=root.querySelector('.account-brand');
  host.replaceChildren(el('span',{class:'account-initials','aria-hidden':'true',text:initials(root.dataset.client)}));
  fallbacks.set(host,[...host.childNodes].map(node=>node.cloneNode(true)));
}
async function init(){
  let result;
  try{
    result=await loadAccountLogoCatalog();
  }catch{
    if(editor){editor.hidden=false;document.getElementById('account-logo-status').textContent='No se pudieron consultar los logos. Recarga para reintentar.';}
    return;
  }
  for(const row of document.querySelectorAll('tr[data-name]')){
    const logo=findAccountLogo(result.items,row.dataset.name);
    const host=row.querySelector('.account-avatar');
    if(logo&&host)image(host,logo.url,row.dataset.name);
  }
  if(!root||!editor)return;
  const name=root.dataset.client,host=root.querySelector('.account-brand');
  let current=findAccountLogo(result.items,name);
  if(current)image(host,current.url,name);
  if(!result.can_edit)return;
  editor.hidden=false;
  const id=name=>document.getElementById(name);
  const form=id('account-logo-form'),file=id('account-logo-file'),preview=id('account-logo-preview'),status=id('account-logo-status');
  const remove=id('account-logo-remove'),opener=id('account-logo-open'),saveButton=id('account-logo-save'),filename=id('account-logo-filename');
  const zone=id('logo-dropzone'),empty=id('logo-preview-empty'),badge=id('logo-preview-badge');
  empty.textContent=initials(name);
  opener.hidden=false;
  let previewUrl=null,busy=false;
  function revoke(){if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;}
  function showPreview(url,label){
    preview.hidden=!url;empty.hidden=!!url;badge.hidden=!url;badge.textContent=label;
    if(url)preview.src=url;else preview.removeAttribute('src');
  }
  function clear(){
    revoke();file.value='';showPreview(null,'');form.hidden=true;filename.textContent='Seleccionar imagen';saveButton.disabled=true;
    opener.setAttribute('aria-expanded','false');
    if(!opener.disabled)opener.focus();
  }
  opener.addEventListener('click',()=>{
    if(!form.hidden){clear();return;}
    form.hidden=false;opener.setAttribute('aria-expanded','true');remove.hidden=!current;saveButton.disabled=true;status.textContent='';
    showPreview(current?.url,current?'Logo guardado':'');id('account-logo-select').focus();
  });
  id('account-logo-cancel').addEventListener('click',()=>{clear();status.textContent='';});
  form.addEventListener('keydown',event=>{if(event.key==='Escape'&&!busy){clear();status.textContent='';}});
  id('account-logo-select').addEventListener('click',()=>file.click());
  id('logo-tips-toggle').addEventListener('click',event=>{
    const tips=id('logo-recommendations');tips.hidden=!tips.hidden;event.currentTarget.setAttribute('aria-expanded',String(!tips.hidden));
  });
  function select(){
    revoke();saveButton.disabled=true;filename.textContent='Seleccionar imagen';
    const selected=file.files[0];
    if(!selected){showPreview(current?.url,current?'Logo guardado':'');return;}
    if(selected.size>2*1024*1024||!['image/png','image/jpeg','image/webp'].includes(selected.type)){
      status.textContent='Elige PNG, JPG o WebP de hasta 2 MB.';file.value='';showPreview(current?.url,current?'Logo guardado':'');return;
    }
    previewUrl=URL.createObjectURL(selected);showPreview(previewUrl,'Vista previa');filename.textContent=selected.name;saveButton.disabled=false;status.textContent='';
  }
  file.addEventListener('change',select);
  preview.addEventListener('error',()=>{saveButton.disabled=true;showPreview(null,'');status.textContent='No se pudo abrir la imagen. Elige otra.';});
  zone.addEventListener('dragover',event=>{event.preventDefault();if(!busy)zone.classList.add('is-dragging');});
  zone.addEventListener('dragleave',()=>zone.classList.remove('is-dragging'));
  zone.addEventListener('drop',event=>{
    event.preventDefault();zone.classList.remove('is-dragging');if(busy)return;
    const selected=event.dataTransfer?.files[0];if(!selected)return;
    const transfer=new DataTransfer();transfer.items.add(selected);file.files=transfer.files;select();
  });
  async function save(method){
    if(busy)return;
    busy=true;form.setAttribute('aria-busy','true');
    const buttons=[opener,...editor.querySelectorAll('button')];buttons.forEach(button=>button.disabled=true);file.disabled=true;
    status.textContent=method==='POST'?'Optimizando y guardando logo…':'Quitando logo…';
    try{
      const token=document.cookie.split('; ').find(value=>value.startsWith(config.csrfCookie+'='))?.split('=').slice(1).join('=')||'';
      const body=new FormData();body.append('account',name);if(method==='POST')body.append('image',file.files[0]);
      const response=await fetch(endpoint+(method==='DELETE'?'?account='+encodeURIComponent(name):''),{method,credentials:'same-origin',headers:{'X-CSRFToken':decodeURIComponent(token)},...(method==='POST'?{body}:{})});
      const payload=await response.json();if(!response.ok)throw Error(payload.detail||payload.error?.message||'No se pudo guardar el cambio. Intenta de nuevo.');
      resetAccountLogos();
      current=method==='POST'?payload.data:null;
      if(current)image(host,current.url,name);else restore(host);
      clear();status.textContent=current?'Logo guardado y optimizado. También se mostrará en Todas las cuentas.':'Logo eliminado.';
    }catch(error){status.textContent=error.message;}
    finally{
      busy=false;form.removeAttribute('aria-busy');buttons.forEach(button=>button.disabled=false);file.disabled=false;saveButton.disabled=!file.files.length;
      if(form.hidden)opener.focus();
    }
  }
  form.addEventListener('submit',event=>{event.preventDefault();if(file.files.length)save('POST');});
  remove.addEventListener('click',()=>save('DELETE'));
}
init();
