import {ArrowRight, CloudRain, Droplets, Leaf, Play, ShieldCheck, Sparkles} from 'lucide-react';
import type {PointerEvent} from 'react';

type Props={
  exiting:boolean;
  location:string;
  onEnter:()=>void;
  onTour:()=>void;
};

const blocks=[
  [760,332,126,62],[914,314,92,48],[1042,350,138,66],[1210,324,78,44],
  [704,438,84,52],[824,422,144,70],[1012,458,96,48],[1146,430,148,72],
  [654,532,132,64],[824,548,86,44],[950,524,152,74],[1144,550,96,48],
  [740,646,146,68],[930,636,104,52],[1084,660,154,72],
] as const;

export default function LaunchExperience({exiting,location,onEnter,onTour}:Props){
  function move(event:PointerEvent<HTMLElement>){
    const box=event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty('--launch-x',`${((event.clientX-box.left)/box.width-.5)*2}`);
    event.currentTarget.style.setProperty('--launch-y',`${((event.clientY-box.top)/box.height-.5)*2}`);
  }

  return <section
    className={`launch-experience ${exiting?'is-exiting':''}`}
    aria-label="SPONGE stormwater model introduction"
    role="dialog"
    aria-modal="true"
    onPointerMove={move}
    onPointerLeave={event=>{event.currentTarget.style.setProperty('--launch-x','0');event.currentTarget.style.setProperty('--launch-y','0');}}
  >
    <div className="launch-noise" aria-hidden="true"/>
    <div className="launch-aurora launch-aurora-one" aria-hidden="true"/>
    <div className="launch-aurora launch-aurora-two" aria-hidden="true"/>
    <div className="launch-rain" aria-hidden="true">{Array.from({length:42},(_,index)=><i key={index} style={{left:`${(index*29)%103}%`,animationDelay:`-${(index%13)*.19}s`,animationDuration:`${.82+(index%6)*.13}s`}}/>)}</div>

    <div className="launch-topbar">
      <div className="launch-brand"><Droplets size={27}/><span>SPONGE</span><small>NEIGHBOURHOOD STORMWATER LAB</small></div>
      <div className="launch-runtime"><i/><span>Browser physics</span><b>No runtime AI</b></div>
    </div>

    <svg className="launch-world" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <linearGradient id="launch-ground" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#163f3d"/><stop offset="1" stopColor="#061c24"/></linearGradient>
        <linearGradient id="launch-water" x1="0" y1="0" x2="1" y2="0"><stop stopColor="#82dded" stopOpacity="0"/><stop offset=".42" stopColor="#82dded"/><stop offset="1" stopColor="#b8f78f" stopOpacity=".35"/></linearGradient>
        <filter id="launch-glow"><feGaussianBlur stdDeviation="5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <path className="launch-ground" d="M486 251 1440 95v805H329Z"/>
      <g className="launch-contours">
        <path d="M410 730c190-91 302-48 449-136 161-96 270-80 524-189"/>
        <path d="M374 778c221-101 340-63 499-151 174-97 301-81 552-199"/>
        <path d="M454 662c166-84 277-42 414-125 150-91 258-76 507-178"/>
        <path d="M533 589c126-68 223-36 345-103 142-77 246-68 471-154"/>
      </g>
      <g className="launch-grid">
        {Array.from({length:10},(_,index)=><path key={`h-${index}`} d={`M${470-index*18} ${282+index*63} 1440 ${126+index*63}`}/>) }
        {Array.from({length:12},(_,index)=><path key={`v-${index}`} d={`M${520+index*88} 246 ${360+index*92} 900`}/>) }
      </g>
      <g className="launch-city">
        {blocks.map(([x,y,w,h],index)=><g className="launch-block" key={`${x}-${y}`} style={{animationDelay:`${1.15+index*.065}s`}}>
          <path className="launch-block-top" d={`M${x} ${y}l${w} -20 ${h} 28 -${w} 20Z`}/>
          <path className="launch-block-side" d={`M${x} ${y}l${h} 28v${Math.round(20+h*.12)}l-${h} -28Z`}/>
          <path className="launch-block-front" d={`M${x+h} ${y+28}l${w} -20v${Math.round(20+h*.12)}l-${w} 20Z`}/>
        </g>)}
      </g>
      <g className="launch-flow" filter="url(#launch-glow)">
        <path d="M1368 298C1190 369 1121 386 1016 463S825 583 596 697"/>
        <path d="M1277 252C1126 341 1055 350 967 416S782 500 542 624"/>
        <path d="M1400 478C1214 489 1136 535 1040 585S830 674 667 760"/>
      </g>
      <g className="launch-resilience">
        <path className="launch-bioswale" d="M1124 396c-94 51-161 89-238 145-72 52-130 82-218 123"/>
        {[0,1,2,3,4].map(index=><circle key={index} cx={1124-index*113} cy={400+index*67} r={8+index%2*3}/>) }
      </g>
      <g className="launch-ripple">
        <circle cx="885" cy="545" r="34"/><circle cx="885" cy="545" r="78"/><circle cx="885" cy="545" r="128"/>
      </g>
      <g className="launch-scanline">
        <path d="M548 762C761 648 884 589 1030 491s261-151 410-193"/>
      </g>
    </svg>

    <div className="launch-copy">
      <div className="launch-location"><span/><b>{location}</b></div>
      <div className="launch-kicker"><Sparkles size={14}/> From rainfall to a defensible plan</div>
      <h1>See the storm.<br/><em>Shape the response.</em></h1>
      <p>Run street-scale flood physics, place green infrastructure, and compare what changes—before concrete is poured. Every result stays tied to its inputs, assumptions, and local planning currency.</p>
      <div className="launch-actions">
        <button className="launch-primary" type="button" autoFocus onClick={onEnter}>Enter the live model <ArrowRight size={18}/></button>
        <button className="launch-secondary" type="button" onClick={onTour}><Play size={16}/> Take the guided tour</button>
      </div>
      <small className="launch-boundary">Atmospheric opening only. Evidence and simulation values begin inside the model.</small>
    </div>

    <aside className="launch-proof" aria-label="SPONGE workflow">
      <div className="launch-proof-heading"><ShieldCheck size={17}/><span>Decision trail</span><b>Reproducible</b></div>
      <article><span>01</span><div><b>Prepare</b><small>Terrain + footprints</small></div></article>
      <article><span>02</span><div><b>Simulate</b><small>Same storm, paired runs</small></div></article>
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
