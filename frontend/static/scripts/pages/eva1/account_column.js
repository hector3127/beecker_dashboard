// Cuenta de origen y logo guardado, sin modificar la identidad del proyecto.
import { el } from '#app/lib/dom.js';
import { findAccountLogo } from '../account/logo-lookup.js';
let logos;
export function mountAccountColumn(table,rows){
  const first=table.tHead.rows[0].cells[0];first.after(el('th',{scope:'col',rowspan:first.rowSpan,text:'Cuenta'}));
  if(!logos)logos=fetch('/api/v1/account-logos/',{credentials:'same-origin'}).then(response=>response.ok?response.json():null).then(body=>body?.data?.items||[]).catch(()=>[]);
  rows.forEach(row=>{const name=row.dataset.client||'',initials=name.trim().split(/\s+/).filter(Boolean).slice(0,2).map(word=>word[0]).join('').toUpperCase()||'—';const host=el('span',{class:'eva1-account-logo','aria-hidden':'true',text:initials});row.cells[0].after(el('td',{},el('span',{class:'eva1-account'},host,el('span',{text:name||'Sin cuenta'}))));logos.then(items=>{const logo=findAccountLogo(items,name);if(!logo)return;const image=el('img',{src:logo.url,alt:'',width:26,height:26,loading:'lazy',decoding:'async'});image.addEventListener('error',()=>host.replaceChildren(initials),{once:true});host.replaceChildren(image);});});
}
