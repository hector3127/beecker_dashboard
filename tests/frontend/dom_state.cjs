/* Minimal DOM state shared by VM-based frontend tests. */
module.exports=function domState(){
 const classes=new Set(),attributes=new Map();
 return {
  classList:{add(...names){names.forEach(name=>classes.add(name));},remove(...names){names.forEach(name=>classes.delete(name));},contains(name){return classes.has(name);},toggle(name,value){const enabled=value??!classes.has(name);if(enabled)classes.add(name);else classes.delete(name);return enabled;}},
  setAttribute(name,value){attributes.set(name,String(value));},
  removeAttribute(name){attributes.delete(name);},
  getAttribute(name){return attributes.get(name)??null;}
 };
};
