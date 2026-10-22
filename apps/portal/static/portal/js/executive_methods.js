/* Explain the prepared indicators without changing card height or fetching data. */
(()=>{
 'use strict';
 const drawer=document.getElementById('executive-method-dialog');
 if(!drawer)return;
 const buttons=Array.from(document.querySelectorAll('[data-method]'));
 const panels=Array.from(drawer.querySelectorAll('[data-method-panel]'));
 const labels={financial:'Financiera',operations:'Operaciones',commercial:'Comercial'};
 let trigger=null;
 buttons.forEach(button=>button.addEventListener('click',()=>{
  const kind=button.dataset.method;
  if(!labels[kind])return;
  trigger=button;
  panels.forEach(panel=>{panel.hidden=panel.dataset.methodPanel!==kind;});
  document.getElementById('method-context').textContent=labels[kind];
  drawer.querySelector('.method-drawer-body').scrollTop=0;
  document.documentElement.classList.add('portal-modal-open');
  drawer.showModal();
 }));
 drawer.querySelectorAll('[data-method-close]').forEach(button=>button.addEventListener('click',()=>drawer.close()));
 drawer.addEventListener('close',()=>{
  document.documentElement.classList.remove('portal-modal-open');
  if(trigger)trigger.focus({preventScroll:true});
 });
})();
