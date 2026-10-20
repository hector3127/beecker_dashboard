function executiveMoney(value){if(value==null||value===''||!Number.isFinite(Number(value)))return 'Pendiente';const n=Number(value),k=Math.abs(n)>=1000;return Math.trunc(k?n/1000:n).toLocaleString('en-US',{maximumFractionDigits:0})+(k?'K':'');}
if(typeof module!=='undefined')module.exports={executiveMoney};
