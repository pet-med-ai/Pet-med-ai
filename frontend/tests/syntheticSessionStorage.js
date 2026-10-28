// Independent browser storage fixture; data survives component remounts only.
export function syntheticSessionStorage(){
  const values=new Map();
  return {getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,String(value)),
    removeItem:key=>values.delete(key),key:index=>[...values.keys()][index]??null,
    get length(){return values.size;}};
}
