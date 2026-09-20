import {coastalLevel,validateCoastal,type CoastalBoundary} from './coastal';
import {validateFacilityLinks,type FacilityLink} from './facilities';
import {inputIdentity} from './identity';
export interface GPUCheckpoint {version:1;inputHash:string;state:Float32Array;history:Float32Array;time:number;steps:number;retries:number;initialVolume:number;rainVolume:number;inflowVolume:number;coastalOutflowVolume?:number}
/** WebGL2 finite-volume HLL engine. Physical time never depends on rendering. */
export interface Inflow {cell:number;flowM3S:number;startS:number;endS:number;source:string}
export interface Outlet {tailwaterElevationM?:number;cell:number;crestDepthM:number;ratePerS:number;maxFlowM3S:number;source:string}
export interface GPUInput {coastal?:CoastalBoundary;planningWaterMask?:Uint8Array;spatialOrder?:1|2;facilityLinks?:FacilityLink[];maxStepS?:number;inflows?:Inflow[];outlets?:Outlet[];nx:number;ny:number;dx:number;dy:number;z:Float32Array;solid:Uint8Array;rainWeights:Float32Array;roughness:Float32Array;infiltration:Float32Array;capacity:Float32Array;percolation?:Float32Array;depth?:Float32Array;saturation?:number;boundary?:'closed'|'open'}
export function validateGPUInput(input:GPUInput){
  if(![1,2].includes(input.spatialOrder??1))throw new Error('Invalid spatial order');
  validateFacilityLinks(input);validateCoastal(input);
  if(!Number.isFinite(input.maxStepS??1)||(input.maxStepS??1)<=0||(input.maxStepS??1)>30)throw new Error("Invalid maximum timestep");
  if(!Number.isInteger(input.nx)||!Number.isInteger(input.ny)||input.nx<4||input.ny<4||input.nx>2048||input.ny>2048)throw new Error('Invalid grid dimensions');
  if(!Number.isFinite(input.dx)||!Number.isFinite(input.dy)||input.dx<=0||input.dy<=0)throw new Error('Invalid grid spacing');
  if(!Number.isFinite(input.saturation??0)||(input.saturation??0)<0||(input.saturation??0)>1)throw new Error('Invalid initial saturation');
  for(const key of ['z','solid','rainWeights','roughness','infiltration','capacity','percolation','depth','planningWaterMask'] as const){const values=input[key];if(!values&&['percolation','depth','planningWaterMask'].includes(key))continue;
    if(!values||values.length!==input.nx*input.ny)throw new Error('Array/grid mismatch: '+key);
    for(let i=0;i<values.length;i++){if(!Number.isFinite(values[i])||(key!=='z'&&values[i]<0))throw new Error('Invalid '+key);if((key==='solid'||key==='planningWaterMask')&&values[i]!==0&&values[i]!==1)throw new Error('Invalid solid mask');}
  }
  const inflowCells=new Set<number>();for(const f of input.inflows??[]){if(!Number.isInteger(f.cell)||f.cell<0||f.cell>=input.z.length||input.solid[f.cell]||inflowCells.has(f.cell)||!f.source?.trim()||![f.flowM3S,f.startS,f.endS].every(v=>Number.isFinite(v)&&v>=0)||f.endS<=f.startS)throw new Error('Invalid or duplicate inflow');inflowCells.add(f.cell);}
  const outletCells=new Set<number>();for(const o of input.outlets??[]){if(!Number.isInteger(o.cell)||o.cell<0||o.cell>=input.z.length||input.solid[o.cell]||outletCells.has(o.cell)||!o.source?.trim()||(o.tailwaterElevationM!==undefined&&!Number.isFinite(o.tailwaterElevationM))||![o.crestDepthM,o.ratePerS,o.maxFlowM3S].every(v=>Number.isFinite(v)&&v>=0))throw new Error('Invalid or duplicate outlet');outletCells.add(o.cell);}
  for(let i=0;i<input.solid.length;i++)if(input.solid[i]&&input.rainWeights[i]!==0)throw new Error('Roof rainfall must route to surface cells');
}
const vertex=`#version 300 es
void main(){vec2 p=vec2(float((gl_VertexID<<1)&2),float(gl_VertexID&2));gl_Position=vec4(p*2.-1.,0.,1.);}`;
const common=`#version 300 es
precision highp float;
precision highp int;
uniform sampler2D coastalTex;uniform float seaLevel;uniform sampler2D inflowTex;uniform float forcingTime;uniform sampler2D outletTex;uniform sampler2D stateTex;uniform sampler2D bedTex;uniform sampler2D hydroTex;uniform sampler2D historyTex;
uniform int spatialOrder;uniform ivec2 size;uniform vec2 spacing;uniform float dt;uniform float rain;uniform int openBoundary;
const float g=9.80665;const float dry=0.00001;
vec4 cell(ivec2 p){ivec2 q=clamp(p,ivec2(0),size-1);vec4 s=texelFetch(stateTex,q,0);
if(p.x<0)s.y=openBoundary==1?min(s.y,0.):-s.y;if(p.x>=size.x)s.y=openBoundary==1?max(s.y,0.):-s.y;
if(p.y<0)s.z=openBoundary==1?min(s.z,0.):-s.z;if(p.y>=size.y)s.z=openBoundary==1?max(s.z,0.):-s.z;return s;}
vec4 bed(ivec2 p){return texelFetch(bedTex,clamp(p,ivec2(0),size-1),0);}
bool inside(ivec2 p){return all(greaterThanEqual(p,ivec2(0)))&&all(lessThan(p,size));}
vec4 primitive(ivec2 p){vec4 s=cell(p);return vec4(bed(p).x+s.x,bed(p).x,s.x>dry?s.yz/s.x:vec2(0.));}
vec4 limitedSlope(ivec2 p,ivec2 d){
 if(spatialOrder==1||!inside(p)||bed(p).z>.5||bed(p-d).z>.5||bed(p+d).z>.5)return vec4(0.);
 vec4 a=primitive(p)-primitive(p-d),b=primitive(p+d)-primitive(p),m=vec4(0.);
 for(int k=0;k<4;k++)if(a[k]*b[k]>0.)m[k]=sign(a[k])*min(abs(a[k]),abs(b[k]));
 float h=cell(p).x;m.x=m.y+clamp(m.x-m.y,-2.*h,2.*h);return m;
}
void reconstruct(ivec2 p,ivec2 d,float side,inout vec4 s,inout vec4 b){
 vec4 v=primitive(p),slope=limitedSlope(p,d);b.x=v.y+side*.5*slope.y;
 float h=max(0.,v.x+side*.5*slope.x-b.x);s.xyz=vec3(h,h*(v.zw+side*.5*slope.zw));
}

`;
const fluxShader=common+`
uniform int axis;layout(location=0)out vec4 fluxOut;layout(location=1)out vec4 correctionOut;
void main(){ivec2 f=ivec2(gl_FragCoord.xy);ivec2 direction=axis==0?ivec2(1,0):ivec2(0,1);
ivec2 lp=f-direction,rp=f;vec4 l=cell(lp),r=cell(rp),bl=bed(lp),br=bed(rp);
int normal=axis==0?1:2;
vec4 coastal=texelFetch(coastalTex,clamp(inside(lp)?lp:rp,ivec2(0),size-1),0);
if(spatialOrder==2){reconstruct(lp,direction,1.,l,bl);reconstruct(rp,direction,-1.,r,br);}
// Mirror the reconstructed face, not the cell centre. Otherwise a limited
// velocity slope can leave a nonzero mass flux through a closed domain edge.
if(!inside(lp)){l=r;bl=br;l[normal]=openBoundary==1?min(r[normal],0.):-r[normal];}
if(!inside(rp)){r=l;br=bl;r[normal]=openBoundary==1?max(l[normal],0.):-l[normal];}
if(!inside(lp)&&coastal[axis==0?0:2]>.5){float h=max(0.,seaLevel-br.x);l=r;l.xyz=vec3(h,r.x>dry?r.yz*h/r.x:vec2(0.));}
if(!inside(rp)&&coastal[axis==0?1:3]>.5){float h=max(0.,seaLevel-bl.x);r=l;r.xyz=vec3(h,l.x>dry?l.yz*h/l.x:vec2(0.));}
if(bl.z>.5){l=r;l[normal]=-l[normal];bl.x=br.x;}
if(br.z>.5){r=l;r[normal]=-r[normal];br.x=bl.x;}
float h0l=l.x,h0r=r.x,zs=max(bl.x,br.x);float hl=max(0.,h0l+bl.x-zs),hr=max(0.,h0r+br.x-zs);
vec2 vl=h0l>dry?l.yz/h0l:vec2(0.),vr=h0r>dry?r.yz/h0r:vec2(0.);
vec3 ul=vec3(hl,vl*hl),ur=vec3(hr,vr*hr);float nl=axis==0?vl.x:vl.y,nr=axis==0?vr.x:vr.y;
vec3 fl=ul*nl,fr=ur*nr;fl.x=ul[normal];fr.x=ur[normal];fl[normal]+=.5*g*hl*hl;fr[normal]+=.5*g*hr*hr;
float sl=min(0.,min(nl-sqrt(g*hl),nr-sqrt(g*hr))),sr=max(0.,max(nl+sqrt(g*hl),nr+sqrt(g*hr)));
vec3 flux=sr-sl>1e-15?(sr*fl-sl*fr+sl*sr*(ur-ul))/(sr-sl):vec3(0.);
fluxOut=vec4(flux,0.);correctionOut=vec4(.5*g*(h0l*h0l-hl*hl),.5*g*(h0r*h0r-hr*hr),0.,0.);
}`;
const updateShader=common+`
uniform sampler2D fluxX;uniform sampler2D fluxY;uniform sampler2D corrX;uniform sampler2D corrY;uniform sampler2D startTex;
uniform int averageStage;layout(location=0)out vec4 result;
void main(){ivec2 p=ivec2(gl_FragCoord.xy);vec4 s=cell(p);vec4 b=bed(p);
vec3 rhs=-(texelFetch(fluxX,p+ivec2(1,0),0).xyz-texelFetch(fluxX,p,0).xyz)/spacing.x
 -(texelFetch(fluxY,p+ivec2(0,1),0).xyz-texelFetch(fluxY,p,0).xyz)/spacing.y;
rhs.y+=(texelFetch(corrX,p,0).y-texelFetch(corrX,p+ivec2(1,0),0).x)/spacing.x;
rhs.z+=(texelFetch(corrY,p,0).y-texelFetch(corrY,p+ivec2(0,1),0).x)/spacing.y;
if(spatialOrder==2){rhs.y-=g*s.x*limitedSlope(p,ivec2(1,0)).y/spacing.x;rhs.z-=g*s.x*limitedSlope(p,ivec2(0,1)).y/spacing.y;}
vec3 next=s.xyz+dt*rhs;if(averageStage==1)next=.5*(texelFetch(startTex,p,0).xyz+next);
result=b.z>.5?vec4(0.):vec4(next,s.w);}`;
const sourceShader=common+`
layout(location=0)out vec4 result;layout(location=1)out vec4 historyOut;
void main(){ivec2 p=ivec2(gl_FragCoord.xy);vec4 s=cell(p),b=bed(p),hyd=texelFetch(hydroTex,p,0),hist=texelFetch(historyTex,p,0);
vec4 incoming=texelFetch(inflowTex,p,0);float incomingDepth=(forcingTime>=incoming.y&&forcingTime<incoming.z)?incoming.x*dt:0.;float added=rain*dt*b.w+incomingDepth;s.x+=added;bool wet=s.x>dry;
float capacity=hyd.y+(hyd.x-hyd.y)*exp(-hist.y/3600.);
float transfer=min(min(max(s.x,0.),capacity*dt),max(0.,hyd.z-s.w));
s.yz*=s.x>0.?(s.x-transfer)/s.x:0.;s.x-=transfer;s.w+=transfer;
float deep=min(s.w,hyd.w*dt);s.w-=deep;
vec4 outlet=texelFetch(outletTex,p,0);float drained=min(max(0.,s.x-max(outlet.x,outlet.w-b.x))*(1.-exp(-outlet.y*dt)),outlet.z*dt);s.yz*=s.x>0.?(s.x-drained)/s.x:0.;s.x-=drained;
s.yz/=1.+dt*g*b.y*b.y*length(s.yz)/pow(max(s.x,dry),7./3.);
result=b.z>.5?vec4(0.):s;
historyOut=vec4(max(hist.x,s.x),wet?hist.y+dt:hist.y*exp(-dt/86400.),hist.z+deep,hist.w+drained);
}`;
// Gather transfers from an immutable snapshot, so shared receivers and cycles
// do not depend on link order. Sparse receiver lists avoid scanning every link.
const facilityShader=common+`
uniform sampler2D linksTex;uniform sampler2D linkIndexTex;
layout(location=0)out vec4 result;layout(location=1)out vec4 historyOut;
ivec2 coords(int id){return ivec2(id%size.x,id/size.x);}
float release(int id){
 if(id<0)return 0.;vec4 a=texelFetch(linksTex,ivec2(id,0),0),b=texelFetch(linksTex,ivec2(id,1),0);
 ivec2 donor=coords(int(a.x));vec4 s=cell(donor);
 float available=max(0.,(b.y>.5?s.w:s.x)-a.z);
 if(b.y<.5&&a.y>=0.){ivec2 receiver=coords(int(a.y));available=min(available,max(0.,(bed(donor).x+s.x-bed(receiver).x-cell(receiver).x)*.5));}
 vec4 rating=texelFetch(linksTex,ivec2(id,2),0);
 if(rating.x>.5){float head=max(0.,s.x-a.z),tail=0.;
  if(a.y>=0.){ivec2 receiver=coords(int(a.y));tail=max(0.,bed(receiver).x+cell(receiver).x-bed(donor).x-a.z);}
  float q=0.;if(head>tail&&head>0.)q=rating.x<1.5?rating.y*rating.z*sqrt(2.*g*(head-tail)):rating.y*rating.z*pow(head,1.5)*pow(max(0.,1.-pow(tail/head,1.5)),.385);
  return min(available,min(q*dt/(spacing.x*spacing.y),b.x*dt));
 }
 return min(available*(1.-exp(-a.w*dt)),b.x*dt);
}
void main(){ivec2 p=ivec2(gl_FragCoord.xy);vec4 s=cell(p),hist=texelFetch(historyTex,p,0),index=texelFetch(linkIndexTex,p,0);
 float surface=release(int(index.x)),soil=release(int(index.y)),incoming=0.,exported=0.;
 for(int k=0;k<2;k++){int id=int(index[k]);if(id>=0&&texelFetch(linksTex,ivec2(id,0),0).y<0.)exported+=release(id);}
 int id=int(index.z);for(int k=0;k<4096;k++){if(id<0)break;incoming+=release(id);id=int(texelFetch(linksTex,ivec2(id,1),0).z);}
 s.yz*=s.x>0.?max(0.,s.x-surface)/s.x:0.;s.x=s.x-surface+incoming;s.w-=soil;
 result=s;historyOut=vec4(max(hist.x,s.x),hist.yz,hist.w+exported);
}`;
const speedShader=common+`
out vec4 result;void main(){ivec2 p=ivec2(gl_FragCoord.xy);vec4 s=cell(p);vec2 v=s.x>dry?abs(s.yz/s.x):vec2(0.);float c=sqrt(max(0.,g*s.x));
float speed=(v.x+c)/spacing.x+(v.y+c)/spacing.y;
float bad=(any(isnan(s))||any(isinf(s))||s.x<-.000001)?1.:0.;result=vec4(speed,bad,0.,0.);}`;
const reduceShader=`#version 300 es
precision highp float;precision highp int;uniform sampler2D inputTex;uniform ivec2 inputSize;out vec4 result;
void main(){ivec2 p=ivec2(gl_FragCoord.xy)*2;vec4 m=vec4(0.);for(int y=0;y<2;y++)for(int x=0;x<2;x++){ivec2 q=p+ivec2(x,y);if(all(lessThan(q,inputSize)))m=max(m,texelFetch(inputTex,q,0));}result=m;}`;
const copyShader=`#version 300 es
precision highp float;uniform sampler2D inputTex;out vec4 result;void main(){result=texelFetch(inputTex,ivec2(gl_FragCoord.xy),0);}`;

type Texture={handle:WebGLTexture;w:number;h:number};
export class GPUSolver {
  readonly gl:WebGL2RenderingContext; private fb:WebGLFramebuffer;private vao:WebGLVertexArrayObject;
  private textures:Texture[]=[];private programs:WebGLProgram[]=[];
  private coastalWaveRate=0;private coastalT:Texture;private coastalOutflowVolume=0;private linksT:Texture;private linkIndexT:Texture;private facilityP:WebGLProgram;private inflowT:Texture;private inflowVolume=0;private outletT:Texture;private bedT:Texture;private hydroT:Texture;private states:Texture[];private histories:Texture[];
  private fluxX:Texture;private fluxY:Texture;private corrX:Texture;private corrY:Texture;private speedT:Texture;private reductions:Texture[]=[];
  private fluxP:WebGLProgram;private updateP:WebGLProgram;private sourceP:WebGLProgram;private speedP:WebGLProgram;private reduceP:WebGLProgram;
  private current=0;private historyCurrent=0;time=0;steps=0;private rainArea=0;private initialVolume=0;private rainVolume=0;private outflowVolume=0;
  private backupState:Texture;private backupHistory:Texture;private copyP:WebGLProgram;retries=0;
  constructor(readonly input:GPUInput, canvas:OffscreenCanvas|HTMLCanvasElement=new OffscreenCanvas(1,1)){
    validateGPUInput(input);if(input.coastal){const peak=input.coastal.levels.reduce((m,k)=>Math.max(m,k.elevationM),-Infinity),lowest=input.coastal.cells.reduce((m,i)=>Math.min(m,input.z[i]),Infinity);this.coastalWaveRate=Math.sqrt(9.80665*Math.max(0,peak-lowest))*(1/input.dx+1/input.dy);}
    this.rainArea=input.rainWeights.reduce((a,b)=>a+b,0)*input.dx*input.dy;
    if(input.boundary==='open')throw new Error('Open GPU boundaries require a verified boundary-flux ledger; use CPU execution');
    const gl=canvas.getContext('webgl2',{antialias:false,depth:false,stencil:false,preserveDrawingBuffer:false,powerPreference:'high-performance'}) as WebGL2RenderingContext|null;
    if(!gl||!gl.getExtension('EXT_color_buffer_float'))throw new Error('GPU_UNSUPPORTED: WebGL2 floating-point targets unavailable');
    this.gl=gl;this.fb=gl.createFramebuffer()!;this.vao=gl.createVertexArray()!;gl.bindVertexArray(this.vao);
    this.fluxP=this.program(fluxShader);this.updateP=this.program(updateShader);this.sourceP=this.program(sourceShader);this.speedP=this.program(speedShader);this.reduceP=this.program(reduceShader);
    this.copyP=this.program(copyShader);this.facilityP=this.program(facilityShader);
    const {nx,ny}=input;const coast=new Float32Array(nx*ny*4);if(input.coastal)for(const cell of input.coastal.cells)coast[cell*4+['west','east','south','north'].indexOf(input.coastal.edge)]=1;this.coastalT=this.texture(nx,ny,coast);const bed=new Float32Array(nx*ny*4),hydro=bed.slice(),state=bed.slice(),history=bed.slice();
    for(let i=0;i<nx*ny;i++){bed.set([input.z[i],input.roughness[i],input.solid[i],input.rainWeights[i]],i*4);
      hydro.set([input.infiltration[i],input.infiltration[i],input.capacity[i],input.percolation?.[i]??0],i*4);
      state[i*4]=input.solid[i]?0:input.depth?.[i]??0;state[i*4+3]=input.solid[i]?0:input.capacity[i]*(input.saturation??0);history[i*4]=state[i*4];
      this.initialVolume+=(state[i*4]+state[i*4+3])*input.dx*input.dy;}
    const outlets=new Float32Array(nx*ny*4);for(const o of input.outlets??[])outlets.set([o.crestDepthM,o.ratePerS,o.maxFlowM3S/(input.dx*input.dy),o.tailwaterElevationM??-1e20],o.cell*4);this.outletT=this.texture(nx,ny,outlets);
    const inflows=new Float32Array(nx*ny*4);for(const f of input.inflows??[])inflows.set([f.flowM3S/(input.dx*input.dy),f.startS,f.endS,0],f.cell*4);this.inflowT=this.texture(nx,ny,inflows);
    const links=input.facilityLinks??[],width=Math.max(1,links.length),linkData=new Float32Array(width*12),indices=new Float32Array(nx*ny*4).fill(-1);
    links.forEach((link,i)=>{linkData.set([link.cell,link.targetCell??-1,link.crestDepthM,link.ratePerS],i*4);
      linkData.set([link.maxFlowM3S/(input.dx*input.dy),link.reservoir==='subsurface'?1:0,link.targetCell===null?-1:indices[link.targetCell*4+2],0],width*4+i*4);
      const r=link.rating;if(r)linkData.set([r.kind==='orifice'?1:2,r.coefficient,r.kind==='orifice'?r.areaM2:r.widthM,0],width*8+i*4);
      indices[link.cell*4+(link.reservoir==='subsurface'?1:0)]=i;if(link.targetCell!==null)indices[link.targetCell*4+2]=i;
    });this.linksT=this.texture(width,3,linkData);this.linkIndexT=this.texture(nx,ny,indices);
    this.bedT=this.texture(nx,ny,bed);this.hydroT=this.texture(nx,ny,hydro);
    this.states=[this.texture(nx,ny,state),this.texture(nx,ny),this.texture(nx,ny),this.texture(nx,ny)];
    this.histories=[this.texture(nx,ny,history),this.texture(nx,ny)];
    this.backupState=this.texture(nx,ny);this.backupHistory=this.texture(nx,ny);
    this.fluxX=this.texture(nx+1,ny);this.corrX=this.texture(nx+1,ny);this.fluxY=this.texture(nx,ny+1);this.corrY=this.texture(nx,ny+1);
    this.speedT=this.texture(nx,ny);let w=nx,h=ny;while(w>1||h>1){w=Math.ceil(w/2);h=Math.ceil(h/2);this.reductions.push(this.texture(w,h));}
  }
  private program(fragment:string){const gl=this.gl;const build=(type:number,text:string)=>{const s=gl.createShader(type)!;gl.shaderSource(s,text);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s)??'Shader compile failed');return s;};
    const vs=build(gl.VERTEX_SHADER,vertex),fs=build(gl.FRAGMENT_SHADER,fragment),p=gl.createProgram()!;gl.attachShader(p,vs);gl.attachShader(p,fs);gl.linkProgram(p);gl.deleteShader(vs);gl.deleteShader(fs);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p)??'Shader link failed');this.programs.push(p);return p;}
  private texture(w:number,h:number,data?:Float32Array):Texture{const gl=this.gl,handle=gl.createTexture()!;gl.bindTexture(gl.TEXTURE_2D,handle);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,w,h,0,gl.RGBA,gl.FLOAT,data??null);const t={handle,w,h};this.textures.push(t);return t;}
  private draw(p:WebGLProgram,targets:Texture[],samplers:Record<string,Texture>,numbers:Record<string,number>={},inputSize?:[number,number]){
    const gl=this.gl;gl.bindFramebuffer(gl.FRAMEBUFFER,this.fb);for(let i=0;i<2;i++)gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0+i,gl.TEXTURE_2D,targets[i]?.handle??null,0);
    gl.drawBuffers(targets.map((_,i)=>gl.COLOR_ATTACHMENT0+i));if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw new Error('Incomplete float framebuffer');
    gl.viewport(0,0,targets[0].w,targets[0].h);gl.useProgram(p);gl.bindVertexArray(this.vao);let unit=0;
    for(const [name,t] of Object.entries(samplers)){if(targets.some(out=>out.handle===t.handle))throw new Error('Texture feedback prevented');gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,t.handle);gl.uniform1i(gl.getUniformLocation(p,name),unit++);}
    gl.uniform2i(gl.getUniformLocation(p,'size'),this.input.nx,this.input.ny);gl.uniform2f(gl.getUniformLocation(p,'spacing'),this.input.dx,this.input.dy);
    gl.uniform1f(gl.getUniformLocation(p,'seaLevel'),this.input.coastal?coastalLevel(this.input.coastal,this.time):0);
    gl.uniform1i(gl.getUniformLocation(p,'spatialOrder'),this.input.spatialOrder??1);
    gl.uniform1i(gl.getUniformLocation(p,'openBoundary'),this.input.boundary==='open'?1:0);
    if(inputSize)gl.uniform2i(gl.getUniformLocation(p,'inputSize'),...inputSize);
    for(const [name,n] of Object.entries(numbers)){const loc=gl.getUniformLocation(p,name);if(name==='axis'||name==='averageStage')gl.uniform1i(loc,n);else gl.uniform1f(loc,n);}
    gl.drawArrays(gl.TRIANGLES,0,3);
  }
  private base(state=this.states[this.current]){return {coastalTex:this.coastalT,inflowTex:this.inflowT,outletTex:this.outletT,stateTex:state,bedTex:this.bedT,hydroTex:this.hydroT,historyTex:this.histories[this.historyCurrent]};}
  private read(t:Texture){const gl=this.gl;gl.bindFramebuffer(gl.FRAMEBUFFER,this.fb);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,t.handle,0);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT1,gl.TEXTURE_2D,null,0);gl.readBuffer(gl.COLOR_ATTACHMENT0);const out=new Float32Array(t.w*t.h*4);gl.readPixels(0,0,t.w,t.h,gl.RGBA,gl.FLOAT,out);return out;}
  stableDt(){this.draw(this.speedP,[this.speedT],this.base());let previous=this.speedT;
    for(const target of this.reductions){this.draw(this.reduceP,[target],{inputTex:previous},{},[previous.w,previous.h]);previous=target;}
    const v=this.read(previous);if(v[1]>.5)throw new Error('NUMERICAL_INVALID: non-finite or negative GPU state');return Math.min(this.input.maxStepS??1,.4/Math.max(v[0]+this.coastalWaveRate,1e-12));}
  private sources(dt:number,rain:number){const next=(this.current+1)%4,hn=1-this.historyCurrent;this.draw(this.sourceP,[this.states[next],this.histories[hn]],this.base(),{dt,rain,forcingTime:this.time});this.current=next;this.historyCurrent=hn;
    if(this.input.facilityLinks?.length){const target=(this.current+1)%4,history=1-this.historyCurrent;
      this.draw(this.facilityP,[this.states[target],this.histories[history]],{...this.base(),linksTex:this.linksT,linkIndexTex:this.linkIndexT},{dt});this.current=target;this.historyCurrent=history;
    }
  }
  private boundaryExchange(){
    const b=this.input.coastal;if(!b)return [0,0];
    const gl=this.gl,xAxis=b.edge==='west'||b.edge==='east',texture=xAxis?this.fluxX:this.fluxY;
    const width=xAxis?1:this.input.nx,height=xAxis?this.input.ny:1;
    const x=b.edge==='east'?this.input.nx:0,y=b.edge==='north'?this.input.ny:0;
    gl.bindFramebuffer(gl.FRAMEBUFFER,this.fb);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,texture.handle,0);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT1,gl.TEXTURE_2D,null,0);gl.readBuffer(gl.COLOR_ATTACHMENT0);
    const data=new Float32Array(width*height*4);gl.readPixels(x,y,width,height,gl.RGBA,gl.FLOAT,data);
    let incoming=0,outgoing=0;const sign=b.edge==='west'||b.edge==='south'?1:-1,length=xAxis?this.input.dy:this.input.dx;
    for(let i=0;i<data.length;i+=4){const rate=data[i]*sign*length;incoming+=Math.max(0,rate);outgoing+=Math.max(0,-rate);}
    return [incoming,outgoing];
  }
  private stage(from:Texture,to:Texture,start:Texture,dt:number,averageStage:number){const b=this.base(from);this.draw(this.fluxP,[this.fluxX,this.corrX],b,{axis:0,seaLevel:this.input.coastal?coastalLevel(this.input.coastal,this.time+dt/2):0});this.draw(this.fluxP,[this.fluxY,this.corrY],b,{axis:1,seaLevel:this.input.coastal?coastalLevel(this.input.coastal,this.time+dt/2):0});
    const exchange=this.boundaryExchange();
    this.draw(this.updateP,[to],{...b,fluxX:this.fluxX,fluxY:this.fluxY,corrX:this.corrX,corrY:this.corrY,startTex:start},{dt,averageStage});return exchange;}
  step(requestedDt:number,rain:number){
    if(!Number.isFinite(requestedDt)||requestedDt<=0||!Number.isFinite(rain)||rain<0)throw new Error('Invalid timestep/forcing');
    if(this.gl.isContextLost())throw new Error('GPU context lost');
    const saved=this.current,savedHistory=this.historyCurrent;
    this.draw(this.copyP,[this.backupState],{inputTex:this.states[saved]});this.draw(this.copyP,[this.backupHistory],{inputTex:this.histories[savedHistory]});
    let dt=Math.min(requestedDt,this.stableDt());for(const f of this.input.inflows??[])for(const knot of [f.startS,f.endS])if(knot>this.time+1e-7)dt=Math.min(dt,knot-this.time);
    for(const knot of this.input.coastal?.levels??[])if(knot.timeS>this.time+1e-7)dt=Math.min(dt,knot.timeS-this.time);
    for(let attempt=0;attempt<12;attempt++){
      try{
        this.sources(dt/2,rain);if(dt>this.stableDt()*1.01)throw new Error('NUMERICAL_INVALID: post-rain CFL');
        const start=this.current,stage=(start+1)%4,end=(start+2)%4;
        const firstExchange=this.stage(this.states[start],this.states[stage],this.states[start],dt,0);this.current=stage;this.stableDt();
        const secondExchange=this.stage(this.states[stage],this.states[end],this.states[start],dt,1);this.current=end;this.stableDt();this.sources(dt/2,rain);this.stableDt();
        for(const f of this.input.inflows??[])if(this.time>=f.startS&&this.time<f.endS)this.inflowVolume+=f.flowM3S*dt;
        this.inflowVolume+=dt*.5*(firstExchange[0]+secondExchange[0]);this.coastalOutflowVolume+=dt*.5*(firstExchange[1]+secondExchange[1]);
        this.time+=dt;this.steps++;this.rainVolume+=rain*dt*this.rainArea;return dt;
      }catch(error){
        this.current=saved;this.historyCurrent=savedHistory;this.draw(this.copyP,[this.states[saved]],{inputTex:this.backupState});this.draw(this.copyP,[this.histories[savedHistory]],{inputTex:this.backupHistory});
        if(!String(error).includes('NUMERICAL_INVALID'))throw error;dt/=2;this.retries++;
      }
    }throw new Error('NUMERICAL_INVALID: twelve timestep retries exhausted');
  }
  async checkpoint():Promise<GPUCheckpoint>{
    if(this.gl.isContextLost())throw new Error('Cannot checkpoint a lost GPU context');
    const snapshot={version:1 as const,state:this.read(this.states[this.current]),history:this.read(this.histories[this.historyCurrent]),time:this.time,steps:this.steps,retries:this.retries,initialVolume:this.initialVolume,rainVolume:this.rainVolume,inflowVolume:this.inflowVolume,coastalOutflowVolume:this.coastalOutflowVolume};
    return {...snapshot,inputHash:await inputIdentity(this.input)};
  }
  async restore(checkpoint:GPUCheckpoint){
    // Validate completely before overwriting any current state.
    if(checkpoint.version!==1||checkpoint.inputHash!==await inputIdentity(this.input))throw new Error('Checkpoint input or version mismatch');
    for(const key of ['time','steps','retries','initialVolume','rainVolume','inflowVolume'] as const)if(!Number.isFinite(checkpoint[key])||checkpoint[key]<0)throw new Error('Invalid checkpoint counters');
    if(!Number.isInteger(checkpoint.steps)||!Number.isInteger(checkpoint.retries))throw new Error('Invalid checkpoint step counters');
    for(const data of [checkpoint.state,checkpoint.history])if(!(data instanceof Float32Array)||data.length!==this.input.nx*this.input.ny*4||data.some(v=>!Number.isFinite(v)))throw new Error('Invalid checkpoint arrays');
    for(let i=0;i<this.input.z.length;i++){
      const j=i*4,s=checkpoint.state,h=checkpoint.history;
      if(s[j]<-1e-6||s[j+3]<-1e-6||s[j+3]>this.input.capacity[i]+1e-6||h[j]<s[j]-1e-6||h.subarray(j,j+4).some(v=>v<0))throw new Error('Invalid checkpoint physical state');
      if(this.input.solid[i]&&s.subarray(j,j+4).some(v=>v!==0))throw new Error('Checkpoint water inside building');
    }
    let accounted=0;for(let i=0;i<checkpoint.state.length;i+=4)accounted+=checkpoint.state[i]+checkpoint.state[i+3]+checkpoint.history[i+2]+checkpoint.history[i+3];
    if(!Number.isFinite(checkpoint.coastalOutflowVolume??0)||(checkpoint.coastalOutflowVolume??0)<0)throw new Error('Invalid coastal ledger');
    const supplied=checkpoint.initialVolume+checkpoint.rainVolume+checkpoint.inflowVolume;
    if(Math.abs(supplied-accounted*this.input.dx*this.input.dy-(checkpoint.coastalOutflowVolume??0))>Math.max(supplied,1)*.001)throw new Error('Checkpoint water balance failed');
    if(this.gl.isContextLost())throw new Error('Cannot restore a lost GPU context; create a new solver');
    const gl=this.gl;for(const [texture,data] of [[this.states[this.current],checkpoint.state],[this.histories[this.historyCurrent],checkpoint.history]] as const){gl.bindTexture(gl.TEXTURE_2D,texture.handle);gl.texSubImage2D(gl.TEXTURE_2D,0,0,0,texture.w,texture.h,gl.RGBA,gl.FLOAT,data);}
    this.time=checkpoint.time;this.steps=checkpoint.steps;this.retries=checkpoint.retries;this.initialVolume=checkpoint.initialVolume;this.rainVolume=checkpoint.rainVolume;this.inflowVolume=checkpoint.inflowVolume;this.coastalOutflowVolume=checkpoint.coastalOutflowVolume??0;
  }
  frame(){const state=this.read(this.states[this.current]),history=this.read(this.histories[this.historyCurrent]);const depth=new Float32Array(this.input.nx*this.input.ny),maxDepth=depth.slice(),subsurfaceDepth=depth.slice(),velocityX=depth.slice(),velocityY=depth.slice();let stored=0,subsurface=0,deep=0,outflow=0;
    for(let i=0;i<depth.length;i++){depth[i]=state[i*4];subsurfaceDepth[i]=state[i*4+3];if(depth[i]>1e-5){velocityX[i]=state[i*4+1]/depth[i];velocityY[i]=state[i*4+2]/depth[i];}maxDepth[i]=history[i*4];if(!Number.isFinite(depth[i])||depth[i]<-1e-6)throw new Error('NUMERICAL_INVALID: GPU depth');stored+=state[i*4]+state[i*4+3];subsurface+=state[i*4+3];deep+=history[i*4+2];outflow+=history[i*4+3];}
    this.outflowVolume=outflow*this.input.dx*this.input.dy+this.coastalOutflowVolume;stored*=this.input.dx*this.input.dy;deep*=this.input.dx*this.input.dy;
    const residual=this.initialVolume+this.rainVolume+this.inflowVolume-stored-deep-this.outflowVolume;
    return {time_s:this.time,depth,maxDepth,subsurfaceDepth,velocityX,velocityY,steps:this.steps,ledger:{initial_m3:this.initialVolume,rain_m3:this.rainVolume,inflow_m3:this.inflowVolume,stored_m3:stored,surface_m3:stored-subsurface*this.input.dx*this.input.dy,subsurface_m3:subsurface*this.input.dx*this.input.dy,deep_percolation_m3:deep,outflow_m3:this.outflowVolume,residual_m3:residual,relative_residual:Math.abs(residual)/Math.max(this.initialVolume+this.rainVolume+this.inflowVolume,1)}};
  }
  info(){const ext=this.gl.getExtension('WEBGL_debug_renderer_info');return {renderer:ext?this.gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):this.gl.getParameter(this.gl.RENDERER),engine:'webgl2-hll',spatialOrder:this.input.spatialOrder??1,allocatedBytes:this.textures.reduce((a,t)=>a+t.w*t.h*16,0),readback:'synchronous bounded snapshots'};}
  dispose(){for(const t of this.textures)this.gl.deleteTexture(t.handle);for(const p of this.programs)this.gl.deleteProgram(p);this.gl.deleteFramebuffer(this.fb);this.gl.deleteVertexArray(this.vao);}
}
