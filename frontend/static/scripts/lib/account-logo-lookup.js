// Presentation-only account aliases; source names and permissions stay intact.
export function logoName(value){
  return String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim().replace(/\.+$/,'').trim().replace(/\s+/g,' ');
}
function canonical(value){
  const name=logoName(value);
  return {'acs industires':'acs industries','atlas next wave':'atlas nextwave','grupo allen':'grupo alen','cadena comercial oxxo':'oxxo','heineken mexico':'heineken'}[name]||name;
}
export function findAccountLogo(items,name){
  const exact=logoName(name);
  // OXXO and the full legal name already open the same account detail.
  if(canonical(name)==='oxxo'){
    const shared=items.find(item=>logoName(item.key||item.account)==='cadena comercial oxxo');
    if(shared)return shared;
  }
  // Prefer the account's own upload before trying explicitly known aliases.
  const matched=items.find(item=>logoName(item.key||item.account)===exact)||items.find(item=>canonical(item.key||item.account)===canonical(name));
  if(matched)return matched;
  // Monthly sources sometimes provide only the brand. Reuse a saved brand
  // image for explicitly known generic labels; never alias other accounts.
  const brandLogo={'aeromexico':'aeromexico cargo','nestle':'nestle mexico','arca continental':'arca continental mexico'}[exact];
  return brandLogo?items.find(item=>logoName(item.key||item.account)===brandLogo):undefined;
}
