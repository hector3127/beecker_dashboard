import test from 'node:test';
import assert from 'node:assert/strict';
import { findAccountLogo } from '../../frontend/static/scripts/pages/account/logo-lookup.js';
const items=[{key:'cadena comercial oxxo',url:'oxxo.png'},{key:'grupo alen',url:'alen.png'},{key:'nestle mexico',url:'mexico.png'}];
test('trailing punctuation and spaces reuse the saved logo',()=>assert.equal(findAccountLogo(items,'  Cadena   Comercial Oxxo.  ').url,'oxxo.png'));
test('known Grupo Allen alias matches Grupo AlEn',()=>assert.equal(findAccountLogo(items,'Grupo Allen').url,'alen.png'));
test('known short OXXO name reuses the full account logo',()=>assert.equal(findAccountLogo(items,'OXXO').url,'oxxo.png'));
test('accents and case match',()=>assert.equal(findAccountLogo(items,'NESTLÉ MÉXICO').url,'mexico.png'));
test('a distinct country is never assigned a similar logo',()=>assert.equal(findAccountLogo(items,'Nestle Chile'),undefined));
test('OXXO and the legal name share the canonical logo even with two uploads',()=>{
  const duplicate=[...items,{key:'oxxo',url:'short-name.png'}];
  for(const name of ['OXXO','Cadena Comercial Oxxo','Cadena Comercial Oxxo.'])assert.equal(findAccountLogo(duplicate,name).url,'oxxo.png');
});
test('exact uploads still take priority for other known aliases',()=>assert.equal(findAccountLogo([{key:'heineken',url:'short.png'},{key:'heineken mexico',url:'own.png'}],'Heineken Mexico').url,'own.png'));

test('generic monthly brand labels reuse saved images',()=>{
  const saved=[...items,{key:'arca continental mexico',url:'arca.png'}];
  assert.equal(findAccountLogo(saved,'Nestlé').url,'mexico.png');
  assert.equal(findAccountLogo(saved,'ARCA CONTINENTAL').url,'arca.png');
});
test('specific country logos retain priority and never fall back to Mexico',()=>{
  const saved=[...items,{key:'nestle chile',url:'chile.png'},{key:'arca continental mexico',url:'arca.png'}];
  assert.equal(findAccountLogo(saved,'Nestlé Chile').url,'chile.png');
  assert.equal(findAccountLogo(saved,'Arca Continental Peru'),undefined);
});
test('a generic brand own upload takes priority',()=>{
  assert.equal(findAccountLogo([...items,{key:'nestle',url:'brand.png'}],'Nestlé').url,'brand.png');
});

test('Atlas Next Wave reuses the saved Atlas NextWave logo',()=>{
  const saved=[{key:'atlas nextwave',url:'atlas.png'}];
  assert.equal(findAccountLogo(saved,'Atlas Next Wave').url,'atlas.png');
  assert.equal(findAccountLogo(saved,'ATLAS NEXTWAVE').url,'atlas.png');
  assert.equal(findAccountLogo(saved,'Atlas'),undefined);
});
test('an exact Atlas variant upload still takes priority',()=>{
  const saved=[{key:'atlas nextwave',url:'atlas.png'},{key:'atlas next wave',url:'own.png'}];
  assert.equal(findAccountLogo(saved,'Atlas Next Wave').url,'own.png');
});

test('Aeroméxico in EVA 4 reuses the saved brand logo',()=>{
  const saved=[{key:'aeromexico cargo',url:'aero.png'}];
  assert.equal(findAccountLogo(saved,'Aeroméxico').url,'aero.png');
  assert.equal(findAccountLogo(saved,'Aeromexico Cargo').url,'aero.png');
  assert.equal(findAccountLogo(saved,'Aeromexico Connect'),undefined);
});
test('Aeroméxico own upload has priority over the brand fallback',()=>{
  const saved=[{key:'aeromexico cargo',url:'cargo.png'},{key:'aeromexico',url:'own.png'}];
  assert.equal(findAccountLogo(saved,'Aeroméxico').url,'own.png');
});

test('the historical ACS Industires typo reuses ACS Industries',()=>{
  const saved=[{key:'acs industries',url:'acs.png'}];
  for(const name of ['ACS Industries','ACS Industries ','ACS Industires'])assert.equal(findAccountLogo(saved,name).url,'acs.png');
  assert.equal(findAccountLogo(saved,'ACS'),undefined);
});
