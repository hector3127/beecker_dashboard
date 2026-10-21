/* Shared loading state: never infer loading from a genuine Pending value. */
(()=>{'use strict';
 const isLoadingMessage=text=>/^(?:cargando|consultando|calculando|preparando|actualizando|guardando)(?:\s|[.…:]|$)/i.test(String(text||'').trim())&&String(text||'').length<220;
 const counters=new WeakMap();
 function begin(target){
  if(!target)return ()=>{};
  counters.set(target,(counters.get(target)||0)+1);
  target.classList.add('portal-loading-region');target.setAttribute('aria-busy','true');
  let finished=false;
  return ()=>{if(finished)return;finished=true;const count=Math.max(0,(counters.get(target)||1)-1);counters.set(target,count);if(!count){target.classList.remove('portal-loading-region');target.setAttribute('aria-busy','false');}};
 }
 if(typeof module!=='undefined')module.exports={isLoadingMessage,begin,inspect};
 if(typeof document==='undefined')return;
 window.PortalLoading={begin};
 function inspect(element){
  if(!element?.matches||element.closest('script,style,svg,button,a,select,textarea,.metric-loading,[contenteditable]'))return;
  if(element.childElementCount!==0){element.classList.remove('portal-loading-message');return;}
  const busy=isLoadingMessage(element.textContent);
  element.classList.toggle('portal-loading-message',busy);
 }
 function scan(root){if(root.nodeType===3){inspect(root.parentElement);return;}inspect(root);root.querySelectorAll?.('*').forEach(inspect);}
 function start(){
  const content=document.getElementById('main-content');if(!content)return;scan(content);
  const observer=new MutationObserver(changes=>{for(const change of changes){if(change.type==='characterData')scan(change.target);else{inspect(change.target);change.addedNodes.forEach(scan);}}});
  observer.observe(content,{subtree:true,childList:true,characterData:true});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
 let endNavigation=null;
 window.addEventListener('beforeunload',()=>{endNavigation=begin(document.getElementById('main-content'));});
 window.addEventListener('pageshow',()=>{endNavigation?.();endNavigation=null;});
})();
