import {ArrowRight, CloudRain, Droplets, Leaf, Play, ShieldCheck, Sparkles} from 'lucide-react';
import {useEffect,useRef,useState} from 'react';
import type {CSSProperties,KeyboardEvent,PointerEvent} from 'react';

type Props={
  exiting:boolean;
  onEnter:()=>void;
  onTour:()=>void;
};

const skyline=[
  [640,168,72,194],[721,220,54,142],[784,132,84,230],[878,196,64,166],
  [951,106,96,256],[1057,187,58,175],[1124,144,78,218],[1212,204,55,158],
  [1277,122,94,240],[1380,186,70,176],
] as const;

type RainIntensity='drizzle'|'rain'|'downpour';

const rainDensity:Record<RainIntensity,number>={drizzle:58,rain:118,downpour:190};

function RainCanvas({intensity}:{intensity:RainIntensity}){
  const canvasRef=useRef<HTMLCanvasElement>(null);

  useEffect(()=>{
    const canvas=canvasRef.current;
    if(!canvas)return;
    const context=canvas.getContext('2d');
    if(!context)return;
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    canvas.dataset.motion=reduced?'reduced':'full';
    let width=0,height=0,frame=0,visible=!document.hidden;
    let drops:Array<{x:number;y:number;length:number;speed:number;alpha:number;impact:number;layer:number}>=[];

    const createDrop=(initial=false)=>{
      const layer=Math.random()>.72?1:0;
      return {
        x:Math.random()*(width+180)-90,
        y:initial?Math.random()*height:-80-Math.random()*height*.28,
        length:layer?24+Math.random()*27:8+Math.random()*15,
        speed:layer?14+Math.random()*11:5+Math.random()*8,
        alpha:layer?.28+Math.random()*.22:.08+Math.random()*.16,
        impact:height*(.7+Math.random()*.25),
        layer,
      };
    };
    const resize=()=>{
      width=canvas.clientWidth;
      height=canvas.clientHeight;
      const pixelRatio=Math.min(window.devicePixelRatio||1,1.5);
      canvas.width=Math.max(1,Math.round(width*pixelRatio));
      canvas.height=Math.max(1,Math.round(height*pixelRatio));
      context.setTransform(pixelRatio,0,0,pixelRatio,0,0);
      const scale=Math.min(1,Math.max(.42,(width*height)/1_050_000));
      const count=Math.min(220,Math.round(rainDensity[intensity]*scale));
      drops=Array.from({length:reduced?Math.min(18,count):count},()=>createDrop(true));
    };
    const draw=(animate:boolean)=>{
      context.clearRect(0,0,width,height);
      context.lineCap='round';
      for(const drop of drops){
        context.beginPath();
        context.moveTo(drop.x,drop.y);
        context.lineTo(drop.x-drop.length*.18,drop.y+drop.length);
        context.strokeStyle=`rgba(${drop.layer?'194,238,244':'127,190,202'},${drop.alpha})`;
        context.lineWidth=drop.layer?1.25:.7;
        context.stroke();
        if(drop.y>drop.impact-4&&drop.y<drop.impact+drop.speed){
          context.beginPath();
          context.ellipse(drop.x,drop.impact,drop.layer?13:7,drop.layer?3.5:2,0,0,Math.PI*2);
          context.strokeStyle=`rgba(156,226,235,${drop.alpha*.65})`;
          context.lineWidth=.8;
          context.stroke();
        }
        if(!animate)continue;
        drop.y+=drop.speed;
        drop.x-=drop.speed*.18;
        if(drop.y>height+70||drop.x<-100)Object.assign(drop,createDrop());
      }
    };
    const tick=()=>{
      if(visible){draw(true);frame=window.requestAnimationFrame(tick);}
    };
    const setVisibility=()=>{
      const nextVisible=!document.hidden;
      if(nextVisible&&!visible&&!reduced){visible=true;frame=window.requestAnimationFrame(tick);}
      else if(!nextVisible&&visible){visible=false;window.cancelAnimationFrame(frame);}
    };
    const observer=new IntersectionObserver(([entry])=>{
      const nextVisible=entry.isIntersecting&&!document.hidden;
      if(nextVisible&&!visible&&!reduced){visible=true;frame=window.requestAnimationFrame(tick);}
      else if(!nextVisible&&visible){visible=false;window.cancelAnimationFrame(frame);}
    });
    resize();
    if(reduced)draw(false);else frame=window.requestAnimationFrame(tick);
    observer.observe(canvas);
    window.addEventListener('resize',resize);
    document.addEventListener('visibilitychange',setVisibility);
    return ()=>{
      visible=false;
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('resize',resize);
      document.removeEventListener('visibilitychange',setVisibility);
    };
  },[intensity]);

  return <canvas ref={canvasRef} className="launch-rain-canvas" aria-hidden="true"/>;
}

export default function LaunchExperience({exiting,onEnter,onTour}:Props){
  const sectionRef=useRef<HTMLElement>(null);
  const [divider,setDivider]=useState(52);
  const [intensity,setIntensity]=useState<RainIntensity>('rain');
  const sceneDivider=divider*14.4;
  const floodTop={drizzle:425,rain:390,downpour:354}[intensity];

  function move(event:PointerEvent<HTMLElement>){
    const box=event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty('--launch-x',`${((event.clientX-box.left)/box.width-.5)*2}`);
    event.currentTarget.style.setProperty('--launch-y',`${((event.clientY-box.top)/box.height-.5)*2}`);
  }

  function moveDivider(clientX:number){
    const box=sectionRef.current?.getBoundingClientRect();
    if(!box)return;
    setDivider(Math.min(82,Math.max(30,((clientX-box.left)/box.width)*100)));
  }

  function dividerKey(event:KeyboardEvent<HTMLButtonElement>){
    if(event.key!=='ArrowLeft'&&event.key!=='ArrowRight'&&event.key!=='Home'&&event.key!=='End')return;
    event.preventDefault();
    if(event.key==='Home')setDivider(30);
    else if(event.key==='End')setDivider(82);
    else setDivider(value=>Math.min(82,Math.max(30,value+(event.key==='ArrowRight'?2:-2))));
  }

  return <section
    ref={sectionRef}
    className={`launch-experience ${exiting?'is-exiting':''}`}
    data-rain={intensity}
    style={{'--launch-divider':`${divider}%`} as CSSProperties}
    aria-label="SPONGE stormwater model introduction"
    role="dialog"
    aria-modal="true"
    onPointerMove={move}
    onPointerLeave={event=>{event.currentTarget.style.setProperty('--launch-x','0');event.currentTarget.style.setProperty('--launch-y','0');}}
  >
    <div className="launch-noise" aria-hidden="true"/>
    <div className="launch-aurora launch-aurora-one" aria-hidden="true"/>
    <div className="launch-aurora launch-aurora-two" aria-hidden="true"/>
    <div className="launch-lightning" aria-hidden="true"/>
    <RainCanvas intensity={intensity}/>

    <div className="launch-photo-world" role="group" aria-label="Two-image rainy street comparison">
      <figure className="launch-photo-panel launch-photo-conventional">
        <img src="/media/launch-city-conventional.webp" alt="Conventional city street with shallow floodwater pooling over asphalt and concrete"/>
        <figcaption><b>Conventional surface</b><span>Water runs off and pools</span></figcaption>
      </figure>
      <figure className="launch-photo-panel launch-photo-permeable">
        <img src="/media/launch-city-permeable.webp" alt="The matching city street with semi-permeable pavers, planted drainage, and reduced pooling"/>
        <figcaption><b>Semi-permeable surface</b><span>Water filters through the edge</span></figcaption>
      </figure>
    </div>
    <div className="launch-surface-animation" aria-hidden="true">
      <div className="launch-runoff-motion"><i/><i/><i/></div>
      <div className="launch-absorption-motion"><i/><i/><i/><i/></div>
    </div>

    <div className="launch-topbar">
      <div className="launch-brand"><Droplets size={27}/><span>SPONGE</span><small>NEIGHBOURHOOD STORMWATER LAB</small></div>
      <div className="launch-runtime"><i/><span>Browser physics</span><b>No runtime AI</b></div>
    </div>

    <div className="launch-weather-controls" role="group" aria-label="Rain intensity">
      <span>Rain intensity</span>
      {(['drizzle','rain','downpour'] as const).map(value=><button
        key={value}
        type="button"
        aria-pressed={intensity===value}
        onClick={()=>setIntensity(value)}
      >{value}</button>)}
    </div>

    <svg className="launch-world" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <linearGradient id="launch-sky" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#071923"/><stop offset=".64" stopColor="#0c3440"/><stop offset="1" stopColor="#09292e"/></linearGradient>
        <linearGradient id="launch-road" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#172e35"/><stop offset="1" stopColor="#07151c"/></linearGradient>
        <linearGradient id="launch-flood" x1="0" y1="0" x2=".84" y2="1"><stop stopColor="#99e8f4" stopOpacity=".18"/><stop offset=".48" stopColor="#5bc4da" stopOpacity=".72"/><stop offset="1" stopColor="#167491" stopOpacity=".92"/></linearGradient>
        <linearGradient id="launch-divider" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#e8fff3" stopOpacity="0"/><stop offset=".35" stopColor="#e8fff3"/><stop offset="1" stopColor="#c9f17a" stopOpacity=".18"/></linearGradient>
        <pattern id="launch-pavers" width="34" height="24" patternUnits="userSpaceOnUse" patternTransform="skewX(-18)"><rect width="34" height="24" fill="#153e3c"/><path d="M0 0h34v24H0zM17 0v24M0 12h34" fill="none" stroke="#79a792" strokeOpacity=".34" strokeWidth="1.2"/></pattern>
        <filter id="launch-glow"><feGaussianBlur stdDeviation="5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <filter id="launch-soft"><feGaussianBlur stdDeviation="13"/></filter>
        <clipPath id="launch-conventional-clip"><rect x="0" y="0" width={sceneDivider} height="900"/></clipPath>
        <clipPath id="launch-permeable-clip"><rect x={sceneDivider} y="0" width={1440-sceneDivider} height="900"/></clipPath>
      </defs>

      <rect width="1440" height="900" fill="url(#launch-sky)"/>
      <circle className="launch-moon" cx="1185" cy="154" r="54"/>
      <circle className="launch-moon-haze" cx="1185" cy="154" r="104"/>
      <g className="launch-stars">{Array.from({length:24},(_,index)=><circle key={index} cx={610+(index*97)%820} cy={44+(index*53)%215} r={index%5===0?1.6:.8}/>)}</g>
      <path className="launch-horizon" d="M560 359Q1010 302 1440 352V466H560Z"/>

      <g className="launch-skyline">
        {skyline.map(([x,y,w,h],index)=><g key={`${x}-${y}`} className="launch-building" style={{animationDelay:`${.42+index*.055}s`}}>
          <rect x={x} y={y} width={w} height={h} rx="2"/>
          {Array.from({length:Math.max(2,Math.floor(w/25))},(_,column)=>Array.from({length:Math.max(3,Math.floor(h/34))},(_,row)=><rect className="launch-window" key={`${column}-${row}`} x={x+11+column*21} y={y+16+row*29} width="5" height="9" style={{animationDelay:`${(index+column+row)%7*.37}s`}}/>))}
        </g>)}
      </g>

      <g className="launch-street">
        <path className="launch-road" d="M750 345H1205L1440 900H472Z"/>
        <path className="launch-left-walk" d="M674 347h88L494 900H176Z"/>
        <path className="launch-right-walk" d="M1193 347h74l173 349v204h-15Z"/>
        <path className="launch-curb launch-curb-left" d="M762 347 494 900"/>
        <path className="launch-curb launch-curb-right" d="M1139 347 1133 900"/>
        <path className="launch-lane launch-lane-left" d="M939 384 818 900"/>
        <path className="launch-lane launch-lane-right" d="M1040 384 1052 900"/>
      </g>

      <g className="launch-flood-zone" clipPath="url(#launch-conventional-clip)">
        <path className="launch-flood" d={`M472 900 750 ${floodTop}c142-37 304-30 455 5l235 505Z`}/>
        <path className="launch-flood-edge" d="M541 822c105-31 205 27 307-7 58-19 111-8 171 12"/>
        <path className="launch-flood-edge" d="M604 702c91-26 158 18 249-7 55-15 105-7 149 8"/>
        <path className="launch-flood-edge" d="M885 602c93-22 174 16 264-5 67-16 126-5 186 15"/>
        <path className="launch-reflection" d="M720 418 604 805M824 399 755 862M918 404 900 824"/>
        <g className="launch-car">
          <path d="M674 581h155l46 91-14 62H639l-14-62Z"/>
          <rect x="669" y="610" width="161" height="70" rx="9"/>
          <path className="launch-windscreen" d="m694 602 18-48h80l27 48Z"/>
          <circle cx="668" cy="718" r="20"/><circle cx="836" cy="718" r="20"/>
          <circle className="launch-headlight" cx="663" cy="657" r="8"/><circle className="launch-headlight" cx="832" cy="657" r="8"/>
        </g>
        <g className="launch-splash"><path d="M617 725q-56 13-91 65M866 725q62 14 92 70"/><circle cx="574" cy="759" r="18"/><circle cx="921" cy="766" r="21"/></g>
        <g className="launch-drain" transform="translate(1086 690)"><rect width="96" height="31" rx="4"/><path d="M12 8v15M28 8v15M44 8v15M60 8v15M76 8v15"/><path className="launch-drain-surge" d="M-16-3q64-28 128 0M-8-18q56-24 111 0"/></g>
      </g>

      <g className="launch-resilient-zone" clipPath="url(#launch-permeable-clip)">
        <path className="launch-safe-road" d="M750 345H1205L1440 900H472Z"/>
        <path className="launch-permeable" d="M1139 347h74l218 553h-298Z"/>
        <path className="launch-safe-sheen" d="M770 401c138-29 283-23 416 8l183 445H575Z"/>
        <path className="launch-curb launch-curb-left" d="M762 347 494 900"/>
        <path className="launch-curb launch-curb-right" d="M1139 347 1133 900"/>
        <path className="launch-lane launch-lane-left" d="M939 384 818 900"/>
        <path className="launch-lane launch-lane-right" d="M1040 384 1052 900"/>
        <path className="launch-bioswale" d="M1184 389c42 71 77 149 102 234 24 79 42 156 54 232"/>
        {[0,1,2,3,4,5].map(index=><g className="launch-plant" key={index} transform={`translate(${1194+index*25} ${430+index*73}) scale(${.64+index*.1})`}>
          <path d="M0 24V0M0 13c-14-1-18-12-18-20 12 0 21 6 18 20ZM1 7c12-2 18-11 18-19C7-12-1-5 1 7Z"/>
        </g>)}
        <g className="launch-infiltration" filter="url(#launch-glow)">
          <path d="M1165 550v86M1214 596v104M1264 650v112M1310 714v105"/>
          <path d="m1156 626 9 12 9-12m31 64 9 12 9-12m32 62 9 12 9-12m28 55 9 12 9-12"/>
        </g>
        <g className="launch-dry-car" transform="translate(1010 516) scale(.56)">
          <path d="M0 89h180l35 76-12 48H-23l-12-48Z"/>
          <path d="m33 87 22-57h78l29 57Z"/>
          <circle cx="3" cy="200" r="18"/><circle cx="179" cy="200" r="18"/>
        </g>
        <g className="launch-streetlights">
          {[0,1,2].map(index=><g key={index} transform={`translate(${1104+index*55} ${415+index*116}) scale(${.55+index*.2})`}>
            <path d="M0 150V0h38v18"/><circle cx="42" cy="23" r="8"/><path className="launch-light-cone" d="m42 29-42 112h84Z"/>
          </g>)}
        </g>
        <g className="launch-calm-drain" transform="translate(1086 690)"><rect width="96" height="31" rx="4"/><path d="M12 8v15M28 8v15M44 8v15M60 8v15M76 8v15"/></g>
      </g>
    </svg>

    <button
      className="launch-divider"
      type="button"
      role="separator"
      aria-label="Before and after comparison divider"
      aria-orientation="vertical"
      aria-valuemin={30}
      aria-valuemax={82}
      aria-valuenow={Math.round(divider)}
      aria-valuetext={`${Math.round(divider)} percent conventional street`}
      onKeyDown={dividerKey}
      onPointerDown={event=>{event.currentTarget.setPointerCapture(event.pointerId);moveDivider(event.clientX);}}
      onPointerMove={event=>{if(event.currentTarget.hasPointerCapture(event.pointerId))moveDivider(event.clientX);}}
    ><span><i/><b>Drag to compare</b></span></button>

    <div className="launch-copy">
      <div className="launch-location"><span/><b>Built for any neighbourhood</b></div>
      <div className="launch-kicker"><Sparkles size={14}/> Any neighbourhood · same rainfall · two futures</div>
      <h1>One storm.<br/><em>Two futures.</em></h1>
      <p>Watch water overwhelm a conventional street, then test how permeable walkways and planted drainage change the outcome. Use local terrain, local assumptions, and local planning currency—wherever the project is.</p>
      <div className="launch-actions">
        <button className="launch-primary" type="button" autoFocus onClick={onEnter}>Enter the live model <ArrowRight size={18}/></button>
        <button className="launch-secondary" type="button" onClick={onTour}><Play size={16}/> Take the guided tour</button>
      </div>
      <small className="launch-boundary">Cinematic comparison only. Evidence and simulation values begin inside the model.</small>
    </div>

    <div className="launch-comparison" aria-hidden="true">
      <div className="launch-comparison-flood"><span>Existing surface</span><b>Runoff accumulates</b></div>
      <div className="launch-comparison-safe"><span>Designed surface</span><b>Permeable + planted</b></div>
    </div>

    <aside className="launch-proof" aria-label="SPONGE workflow">
      <div className="launch-proof-heading"><ShieldCheck size={17}/><span>Controlled comparison</span><b>Reproducible</b></div>
      <article><span>01</span><div><b>Prepare</b><small>Local terrain + footprints</small></div></article>
      <article><span>02</span><div><b>Compare</b><small>One storm, paired streets</small></div></article>
      <article><span>03</span><div><b>Explain</b><small>Evidence-ready exports</small></div></article>
    </aside>

    <div className="launch-stages" aria-hidden="true">
      <div className="launch-stage"><CloudRain size={16}/><span>01</span><b>Rainfall</b></div>
      <i/>
      <div className="launch-stage"><Droplets size={16}/><span>02</span><b>Surface flow</b></div>
      <i/>
      <div className="launch-stage"><Leaf size={16}/><span>03</span><b>Design response</b></div>
    </div>
    <div className="launch-progress" aria-hidden="true"><i/></div>
  </section>;
}
