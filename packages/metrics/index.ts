export interface DamageCurve {id:string;source:string;points:[number,number][]}
export interface Asset {id:string;exteriorCells:number[];firstFloorElevationM:number|null;structureValueMinor:number|null;curve:DamageCurve|null}
export function fraction(depth:number,curve:DamageCurve):number{
  if(!Number.isFinite(depth)||!curve.points.length)throw new Error('Invalid damage input');
  for(let i=0;i<curve.points.length;i++){const [x,y]=curve.points[i];if(!Number.isFinite(x)||!Number.isFinite(y)||y<0||y>1||(i>0&&(x<=curve.points[i-1][0]||y<curve.points[i-1][1])))throw new Error('Invalid depth-damage curve');}
  if(depth<=0)return 0;const p=curve.points;if(depth<=p[0][0])return p[0][1];
  for(let i=1;i<p.length;i++)if(depth<=p[i][0])return p[i-1][1]+(p[i][1]-p[i-1][1])*(depth-p[i-1][0])/(p[i][0]-p[i-1][0]);return p.at(-1)![1];
}
export function eventLoss(assets:Asset[],maximumExteriorEta:Float32Array){
  let totalMinor=0,valued=0;const buildings=assets.map(asset=>{
    if(asset.firstFloorElevationM===null||asset.structureValueMinor===null||asset.curve===null||asset.exteriorCells.length===0)return {id:asset.id,lossMinor:null,depthM:null};
    if(!Number.isSafeInteger(asset.structureValueMinor)||asset.structureValueMinor<0)throw new Error('Invalid asset value');
    let eta=-Infinity;for(const cell of asset.exteriorCells){if(cell<0||cell>=maximumExteriorEta.length||!Number.isFinite(maximumExteriorEta[cell]))throw new Error('Invalid exterior sample');eta=Math.max(eta,maximumExteriorEta[cell]);}
    const depthM=Math.max(0,eta-asset.firstFloorElevationM),lossMinor=Math.round(asset.structureValueMinor*fraction(depthM,asset.curve));totalMinor+=lossMinor;valued++;return {id:asset.id,lossMinor,depthM};
  });return {totalMinor:valued?totalMinor:null,valuationCoverage:assets.length?valued/assets.length:0,unvaluedBuildings:assets.length-valued,buildings};
}
