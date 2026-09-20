import {useEffect,useState} from 'react';

/** Yield two paints between shader families; keep the current water visible. */
export function useSceneLoading(identity:unknown){
 const [state,setState]=useState({identity,stage:0});
 const stage=state.identity===identity?state.stage:0;
 useEffect(()=>{
  if(!identity||stage>=4)return;
  let first=0,second=0;
  first=requestAnimationFrame(()=>{second=requestAnimationFrame(()=>setState({identity,stage:stage+1}));});
  return()=>{cancelAnimationFrame(first);cancelAnimationFrame(second);};
 },[identity,stage]);
 return stage;
}

export function sceneLayerStage(id:string){
 if(id.startsWith('water')||id==='terrain-surface')return 0;
 if(['buildings','roofs','mapped-water','green-space'].includes(id))return 1;
 if(['domain-boundary','sidewalks','streets','roof-edges'].includes(id))return 2;
 if(['facade-windows','sites'].includes(id))return 3;
 return 4;
}
