/* Filter the server-rendered definitions locally, retaining the search in the URL. */
(()=>{
 'use strict';
 const search=document.getElementById('dictionary-search');
 if(!search)return;
 const clear=document.getElementById('dictionary-clear'),count=document.getElementById('dictionary-count'),empty=document.getElementById('dictionary-empty');
 const normalize=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es').trim();
 const rows=Array.from(document.querySelectorAll('[data-dictionary-entry]'),row=>({row,text:normalize(row.textContent)}));
 const apply=(updateUrl=true)=>{
  const query=normalize(search.value);
  let matches=0;
  rows.forEach(({row,text})=>{row.hidden=!!query&&!text.includes(query);if(!row.hidden)matches++;});
  count.textContent=query?matches+' de '+rows.length+' conceptos':rows.length+' conceptos';
  empty.hidden=matches>0;
  clear.hidden=!search.value;
  if(updateUrl){const url=new URL(location.href);if(search.value.trim())url.searchParams.set('q',search.value.trim());else url.searchParams.delete('q');history.replaceState(history.state,'',url);}
 };
 search.value=new URL(location.href).searchParams.get('q')||'';
 search.addEventListener('input',()=>apply());
 clear.addEventListener('click',()=>{search.value='';apply();search.focus();});
 window.addEventListener('popstate',()=>{search.value=new URL(location.href).searchParams.get('q')||'';apply(false);});
 apply(false);
})();
