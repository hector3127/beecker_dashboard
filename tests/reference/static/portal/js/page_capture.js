/* Download the current dashboard as a PNG, without reloading its data. */
(()=>{
  const script=document.currentScript;
  const sections=[['executive-page','business-overview'],['operations-page','operativa'],['commercial-page','comercial']];
  const selected=sections.find(([name])=>document.body.classList.contains(name));
  if(!selected)return;
  const main=document.getElementById('main-content');
  const host=document.querySelector('#portal-freshness')||main;
  if(!main||!host)return;
  const button=document.createElement('button');
  button.type='button';button.textContent='↓ Descargar captura';button.setAttribute('data-html2canvas-ignore','true');
  button.style.cssText='border:1px solid #daccff;border-radius:9px;padding:9px 13px;background:#fff;color:#5925d6;font:inherit;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap';
  const status=document.createElement('span');status.setAttribute('role','status');status.setAttribute('data-html2canvas-ignore','true');status.style.cssText='font-size:12px;max-width:260px;white-space:normal';
  host.appendChild(button);host.appendChild(status);
  let library;
  function loadLibrary(){
    if(typeof window.html2canvas==='function')return Promise.resolve(window.html2canvas);
    if(!library)library=new Promise((resolve,reject)=>{
      const tag=document.createElement('script');tag.src=script.dataset.library;
      tag.onload=()=>typeof window.html2canvas==='function'?resolve(window.html2canvas):reject(Error('No se pudo iniciar la captura.'));
      tag.onerror=()=>{library=null;tag.remove();reject(Error('No se pudo cargar la captura. Vuelve a intentarlo.'));};
      document.head.appendChild(tag);
    });
    return library;
  }
  button.addEventListener('click',async()=>{
    button.disabled=true;button.textContent='Generando captura…';status.textContent='';
    try{
      const capture=await loadLibrary();
      if(document.fonts)await document.fonts.ready;
      const width=Math.ceil(main.scrollWidth),height=Math.ceil(main.scrollHeight);
      const scale=Math.min(2,16000/Math.max(width,1),30000/Math.max(height,1),Math.sqrt(45000000/Math.max(width*height,1)));
      const canvas=await capture(main,{
        backgroundColor:'#f3f4fd',scale:scale,useCORS:true,allowTaint:false,logging:false,
        windowWidth:window.innerWidth,scrollX:0,scrollY:0,
        onclone:doc=>{
          const target=doc.getElementById('main-content');
          target.querySelectorAll('textarea').forEach(x=>{x.textContent=x.value;});
          target.querySelectorAll('[hidden],dialog:not([open])').forEach(x=>x.remove());
          const style=doc.createElement('style');
          style.textContent='*{animation:none!important;transition:none!important;caret-color:transparent!important}#main-content [data-html2canvas-ignore]{display:none!important}#main-content .ranking-scroll,#main-content .cost-scroll{max-height:none!important;height:auto!important;overflow:visible!important}';
          doc.head.appendChild(style);
        }
      });
      if(!canvas.width||!canvas.height)throw Error('La captura está vacía. Vuelve a intentarlo.');
      const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
      if(!blob)throw Error('No se pudo generar la imagen.');
      const now=new Date(),stamp=[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-');
      const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=selected[1]+'-'+stamp+'.png';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
      status.textContent='Captura descargada.';
    }catch(error){status.textContent=error.message||'No se pudo generar la captura.';}
    finally{button.disabled=false;button.textContent='↓ Descargar captura';}
  });
})();
