export type MapInspection={kind:'cell'|'building'|'site';id:string;cells:number[];message:string};

/** Convert a picked rendered object back to canonical simulation identities. */
export function inspectPick(object:any,cellCount:number):MapInspection|null{
 if(!object||!Number.isInteger(cellCount)||cellCount<1)return null;
 if(Number.isInteger(object.i)&&object.i>=0&&object.i<cellCount)return {kind:'cell',id:String(object.i),cells:[object.i],message:`Simulation cell ${object.i} · water depth ${Number(object.depth*100).toFixed(1)} cm`};
 if(typeof object.id==='string'&&Array.isArray(object.exterior_cells)){
  const cells=object.exterior_cells.filter((cell:unknown)=>Number.isInteger(cell)&&Number(cell)>=0&&Number(cell)<cellCount);
  return {kind:'building',id:object.id,cells,message:`Building ${object.id} · ${cells.length} exterior sample cells`};
 }
 if(typeof object.id==='string'&&Array.isArray(object.cells)){
  const cells=object.cells.filter((cell:unknown)=>Number.isInteger(cell)&&Number(cell)>=0&&Number(cell)<cellCount);
  if(cells.length!==object.cells.length||!cells.length)return null;
  return {kind:'site',id:object.id,cells,message:`Candidate ${object.id} · ${cells.length} simulation cells`};
 }
 return null;
}
