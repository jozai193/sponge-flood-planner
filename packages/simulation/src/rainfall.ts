export interface RainInterval {start_s:number;end_s:number;rate_m_s:number}
export interface StormEvidence {
  provider:string;product:string;source_url:string;product_page?:string;retrieved_at:string;source_sha256:string;
  location:{label:string;latitude:number;longitude:number};region?:string;volume?:string;version?:string;authors?:string;
  series?:string;annual_exceedance_probability?:number;estimate_mm:number;
  confidence_interval?:{level:number;lower_mm:number;upper_mm:number};spatial_support:string;
  temporal_distribution_source:string;stationarity_note?:string;
}
export interface StormRun {duration:number;recession:number;depth:number;intervals?:RainInterval[];
  name?:string;returnPeriodYears?:number|null;sourceIds?:string[];distribution?:string;
  antecedentSaturation?:number;evidence?:StormEvidence}
export function validateRainfall(storm:StormRun){
  if(!Number.isFinite(storm.duration)||storm.duration<=0||!Number.isFinite(storm.recession)||storm.recession<0||!Number.isFinite(storm.depth)||storm.depth<0)throw new Error('Invalid storm');
  if(storm.returnPeriodYears!=null&&(!Number.isFinite(storm.returnPeriodYears)||storm.returnPeriodYears<=0))throw new Error('Invalid storm return period');
  if(storm.antecedentSaturation!=null&&(!Number.isFinite(storm.antecedentSaturation)||storm.antecedentSaturation<0||storm.antecedentSaturation>1))throw new Error('Invalid antecedent saturation');
  if(storm.intervals){
    if(!storm.intervals.length||storm.intervals.length>10000)throw new Error('Invalid rainfall interval count');
    let end=0,depth=0;
    for(const i of storm.intervals){
      if(![i.start_s,i.end_s,i.rate_m_s].every(Number.isFinite)||i.start_s<end||i.end_s<=i.start_s||i.end_s>storm.duration||i.rate_m_s<0||i.rate_m_s>.001)throw new Error('Invalid rainfall interval');
      end=i.end_s;depth+=(i.end_s-i.start_s)*i.rate_m_s;
    }
    if(Math.abs(depth-storm.depth)>Math.max(1e-9,storm.depth*1e-4))throw new Error('Rainfall integral does not match event depth');
  }
}
/** Explicit non-probabilistic depth sensitivity set. Every alternative receives identical members. */
export function rainfallSensitivityEnsemble(storm:StormRun,factors=[.8,1,1.2]){
 validateRainfall(storm);
 if(!factors.length||factors.some(f=>!Number.isFinite(f)||f<=0||f>10))throw new Error('Invalid rainfall sensitivity factors');
 return factors.map(f=>{const member={...storm,depth:storm.depth*f,intervals:storm.intervals?.map(i=>({...i,rate_m_s:i.rate_m_s*f})),sensitivity_factor:f};validateRainfall(member);return member;});
}
export function rainfallAt(storm:StormRun,time:number){
  const end=storm.duration+storm.recession;
  if(!storm.intervals)return {rate:time<storm.duration-1e-7?storm.depth/storm.duration:0,knot:time<storm.duration-1e-7?storm.duration:end};
  for(const i of storm.intervals){
    if(time<i.start_s-1e-7)return {rate:0,knot:i.start_s};
    if(time<i.end_s-1e-7)return {rate:i.rate_m_s,knot:i.end_s};
  }
  return {rate:0,knot:end};
}
