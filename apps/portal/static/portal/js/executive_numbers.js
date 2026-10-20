/* Compact USD amounts: K=thousands, M=millions, B=thousand millions. */
function executiveMoney(value){
 if(value==null||value===''||!Number.isFinite(Number(value)))return 'Pendiente';
 const n=Number(value),a=Math.abs(n),unit=a>=1e9?1e9:a>=1e6?1e6:a>=1e3?1e3:1,suffix=unit===1e9?'B':unit===1e6?'M':unit===1e3?'K':'';
 const precision=unit>=1e6?100:1;
 const shown=Math.trunc(n/unit*precision)/precision;
 return shown.toLocaleString('en-US',{maximumFractionDigits:unit>=1e6?2:0})+suffix;
}
if(typeof module!=='undefined')module.exports={executiveMoney};
