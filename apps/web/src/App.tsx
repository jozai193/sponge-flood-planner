import {
  composeForcing,
  validateScenarioExecution,
} from "../../../packages/domain/scenario";
import { assessScenarioData } from "../../../packages/domain/data-admission";
import ScenarioDataStatus from "./ScenarioDataStatus";
import { scenarioSpec } from "../../../packages/domain/scenario-wire";
import { validationStatus } from "../../../packages/metrics/validation-status";
import { loadBundleResources } from "./bundle-loader";
import { useSceneLoading, sceneLayerStage } from "./scene-loading";
import { terrainSurface } from "./terrain-surface";
import { scenarioInput as buildScenarioInput } from "./scenario-input";
import { rainfallSensitivityEnsemble } from "../../../packages/simulation/src/rainfall";

import { waterPlanningMask, dryCandidates } from "./water-planning";

import {
  readRecovery,
  saveRecovery,
  type RecoveryRecord,
  type PausedStorm,
} from "./recovery";

import {
  readCompletedComparison,
  saveCompletedComparison,
  type CompletedComparison,
} from "./completed-comparison";

import { useEffect, useRef, useState, useMemo } from "react";

import DeckGL from "@deck.gl/react";

import { OrbitView, COORDINATE_SYSTEM } from "@deck.gl/core";

import { PolygonLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";

import {
  Droplets,
  Search,
  Play,
  Square,
  Layers,
  ShieldCheck,
  Route,
  CloudRain,
  Sparkles,
} from "lucide-react";

import type { GPUInput } from "../../../packages/simulation/src/gpu";

import {
  compileDesign,
  type PhysicalDesign,
} from "../../../packages/domain/interventions";
import { normaliseCurrency } from "../../../packages/domain/currency";

import Replay from "./Replay";

import DataAudit from "./DataAudit";

import DataEnrichment from "./DataEnrichment";

import FloodInputs, { type FloodConfiguration } from "./FloodInputs";

import DesignEditor from "./DesignEditor";
import {INTERVENTION_COLOURS,INTERVENTION_NAMES} from "./intervention-style";
import LaunchExperience from "./LaunchExperience";
import {
  api,
  authenticatedFetch,
  getSessionToken,
  readSessionValue,
  setSessionToken,
  uploadTerrain,
  writeSessionValue,
} from "./api-client";
import { useLaunchExperience } from "./use-launch-experience";

import {
  cityGeometry,
  cityLayers,
  cityLighting,
  type CityContext,
} from "./city-scene";

import {
  loadImagery,
  imageryMesh,
  imageryLayer,
  roofImageryMesh,
  roofImageryLayer,
  type ImageryDescriptor,
} from "./imagery";

import "./style.css";
import "./judge-tour.css";

type Building = {
  height_source?: string;
  id: string;
  geometry: { type: string; coordinates: any };
  height_m: number;
  base_elevation_m: number;
  exterior_cells: number[];
};

type Bundle = {
  bundle_id: string;
  label: string;
  country_code?: string | null;
  currency?: string;
  currency_source?: string;
  extent_m: number;
  grid: {
    elevation_origin_m?: number;
    vertical_datum?: string;
    nx: number;
    ny: number;
    dx_m: number;
    dy_m: number;
    crs: string;
    origin_x_m: number;
    origin_y_m: number;
  };
  buildings: Building[];
  candidates: any[];
  sources?: { provider?: string; attribution?: string }[];
  assumptions: string[];
  quality: Record<string, unknown>;
};

type Frame = {
  time_s: number;
  depth: Float32Array;
  maxDepth: Float32Array;
  ledger: { relative_residual: number; rain_m3: number; stored_m3: number };
};

export default function App() {
  const [startupReady, setStartupReady] = useState(false);

  const [preparing, setPreparing] = useState(false),
    [preparationStatus, setPreparationStatus] = useState("");

  const preparationActive = useRef(false);

  const [bundle, setBundle] = useState<Bundle | null>(null),
    [input, setInput] = useState<GPUInput | null>(null),
    [frame, setFrame] = useState<Frame | null>(null);
  const currency = normaliseCurrency(bundle?.currency);

  const [importedStorm, setImportedStorm] = useState<any>(null);
  const [antecedentSaturation, setAntecedentSaturation] = useState(0.25);
  const [noaaReturnPeriod, setNoaaReturnPeriod] = useState(100),
    [noaaDistribution, setNoaaDistribution] = useState("centered"),
    [loadingStorm, setLoadingStorm] = useState(false);

  const [query, setQuery] = useState(""),
    [status, setStatus] = useState("Connecting to local services…"),
    [error, setError] = useState(""),
    [running, setRunning] = useState(false);
  const [region, setRegion] = useState(""),
    [searching, setSearching] = useState(false),
    [searchNote, setSearchNote] = useState("");
  const searchRequest = useRef<AbortController | null>(null);

  const [rain, setRain] = useState(100),
    [minutes, setMinutes] = useState(60),
    [showSources, setShowSources] = useState(false),
    [showJudgeTour, setShowJudgeTour] = useState(
      () => new URLSearchParams(window.location.search).get("tour") === "1",
    ),
    [device, setDevice] = useState(""),
    [locations, setLocations] = useState<any[]>([]);

  const [satellite, setSatellite] = useState(true),
    [satelliteImage, setSatelliteImage] = useState<HTMLCanvasElement | null>(
      null,
    ),
    [imageryStatus, setImageryStatus] = useState("");

  const [imageryDescriptor, setImageryDescriptor] =
    useState<ImageryDescriptor | null>(null);
  const {launch,closeLaunch,playLaunch}=useLaunchExperience();

  useEffect(() => {
    setSatelliteImage(null);
    setImageryDescriptor(null);
    if (!bundle) return;
    let alive = true;
    setImageryStatus("Loading satellite imagery…");
    (async () => {
      try {
        const descriptor = await api(
          "/bundles/" + bundle.bundle_id + "/imagery",
        );
        const texture = await loadImagery(descriptor);
        if (alive) {
          setImageryDescriptor(descriptor);
          setSatelliteImage(texture);
          setImageryStatus("Satellite imagery · capture date varies");
        }
      } catch {
        if (alive)
          setImageryStatus("Satellite imagery unavailable · model view shown");
      }
    })();
    return () => {
      alive = false;
    };
  }, [bundle]);

  const [areaSize, setAreaSize] = useState(600),
    [gridSize, setGridSize] = useState(128),
    [renderQuality, setRenderQuality] = useState("balanced"),
    [waterHeightScale, setWaterHeightScale] = useState(1),
    [sideView, setSideView] = useState(false),
    [planView, setPlanView] = useState(false);
  const sceneStage = useSceneLoading(bundle?.bundle_id);
  useEffect(() => {
    if (sceneStage < 4)
      delete document.documentElement.dataset.sceneDetailReadyMs;
  }, [sceneStage]);

  const [context, setContext] = useState<CityContext | null>(null),
    [contextStatus, setContextStatus] = useState("Loading street detail"),
    [detail, setDetail] = useState(true);

  const lighting = useMemo(
    () => [cityLighting(renderQuality !== "eco" && !satellite)],
    [renderQuality, satellite],
  );

  const [flood, setFlood] = useState<FloodConfiguration>({
    mode: "rain",
    inflows: [],
    outlets: [],
    source: "",
  });
  const [budget, setBudget] = useState(2000000);
  const [drawMode, setDrawMode] = useState(false);
  const [drawnSites, setDrawnSites] = useState<any[]>([]);

  const planningWaterMask = useMemo(
    () => (input ? waterPlanningMask(input, context) : new Uint8Array()),
    [input, context],
  );

  const planningInput = useMemo(
    () => (input ? { ...input, planningWaterMask } : null),
    [input, planningWaterMask],
  );

  const planningSites = useMemo(
    () =>
      dryCandidates([...(bundle?.candidates ?? []), ...drawnSites], planningWaterMask).map(
        (site) => ({ ...site, budgetMinor: Math.round(budget * 100) }),
      ),
    [bundle, drawnSites, planningWaterMask, budget],
  );

  function drawCandidate(x:number,y:number){
    if(!input)return;
    const west=-input.nx*input.dx/2,south=-input.ny*input.dy/2,cx=Math.floor((x-west)/input.dx),cy=Math.floor((y-south)/input.dy);
    if(cx<0||cx>=input.nx||cy<0||cy>=input.ny){setError('Draw inside the simulation grid.');return;}
    const cells:number[]=[];for(let yy=Math.max(0,cy-1);yy<=Math.min(input.ny-1,cy+1);yy++)for(let xx=Math.max(0,cx-1);xx<=Math.min(input.nx-1,cx+1);xx++){const cell=yy*input.nx+xx;if(!input.solid[cell]&&!planningWaterMask[cell])cells.push(cell);}
    if(cells.length<4){setError('Drawn site overlaps buildings or mapped permanent water; choose a clearer area.');return;}
    const elevations=cells.map(cell=>input.z[cell]),slope=(Math.max(...elevations)-Math.min(...elevations))/(3*Math.min(input.dx,input.dy)),id=`drawn-${cx}-${cy}`;
    setDrawnSites(previous=>[...previous.filter(s=>s.id!==id),{id,x_m:x,y_m:y,elevation_m:input.z[cy*input.nx+cx],cells,area_m2:cells.length*input.dx*input.dy,slope,eligibility:'unverified',parcel_ids:[],source_note:'User-drawn grid footprint; parcel, utility, protected-area and construction eligibility unverified'}]);
    setError('');setStatus(`Placed ${id} with ${cells.length} simulation cells; confirm eligibility before use.`);
  }
  function placeCandidateWithKeyboard(){if(!input)return;const cells=[...Array(input.z.length).keys()].sort((a,b)=>{const ax=a%input.nx-input.nx/2,ay=Math.floor(a/input.nx)-input.ny/2,bx=b%input.nx-input.nx/2,by=Math.floor(b/input.nx)-input.ny/2;return ax*ax+ay*ay-bx*bx-by*by;});for(const cell of cells){const cx=cell%input.nx,cy=Math.floor(cell/input.nx),footprint=[] as number[];for(let yy=cy-1;yy<=cy+1;yy++)for(let xx=cx-1;xx<=cx+1;xx++){const i=yy*input.nx+xx;if(xx>=0&&xx<input.nx&&yy>=0&&yy<input.ny&&!input.solid[i]&&!planningWaterMask[i])footprint.push(i);}if(footprint.length===9){const west=-input.nx*input.dx/2,south=-input.ny*input.dy/2;drawCandidate(west+(cx+.5)*input.dx,south+(cy+.5)*input.dy);return;}}setError('No clear 3 × 3 grid footprint is available for keyboard placement.');}

  const scenarioInput = useMemo(
    () =>
      input
        ? buildScenarioInput(input, flood, context, antecedentSaturation)
        : null,
    [input, flood, context, antecedentSaturation],
  );

  const forcing = useMemo(
    () =>
      composeForcing(flood, {
        depthMm: rain,
        durationS: minutes * 60,
        recessionS: importedStorm?.recession_s ?? 3600,
        intervals: importedStorm?.intervals,
        name: importedStorm?.name,
        returnPeriodYears: importedStorm?.return_period_years,
        sourceIds: importedStorm?.source_ids,
        distribution: importedStorm?.distribution,
        antecedentSaturation,
        evidence: importedStorm?.evidence,
      }),
    [flood, rain, minutes, importedStorm, antecedentSaturation],
  );
  const activeForcing = forcing.components;
  const runDuration = forcing.storm.duration;
  const simulationEnd = runDuration + forcing.storm.recession;
  const dataScreen = useMemo(() => {
    if (!scenarioInput || !bundle) return {};
    try {
      return {
        assessment: assessScenarioData(
          scenarioSpec(scenarioInput, forcing, {
            bundleId: bundle.bundle_id,
            horizontalCrs: bundle.grid.crs,
            verticalDatum: bundle.grid.vertical_datum,
            elevationOriginM: bundle.grid.elevation_origin_m,
          }),
          bundle,
        ),
      };
    } catch (error) {
      return { error: String(error) };
    }
  }, [scenarioInput, forcing, bundle]);
  function validateDataForRun() {
    if (dataScreen.error) throw new Error(dataScreen.error);
    if (!dataScreen.assessment?.exploratory_allowed)
      throw new Error(
        "Scenario and terrain metadata do not match. Reload the intended terrain bundle.",
      );
  }

  function changeFlood(next: FloodConfiguration) {
    setPausedRun(null);
    setFlood(next);
    clearComparison();
    setFrame(null);
    setRenderInput(null);
  }

  const loadStarted = useRef(0),
    sceneMeasured = useRef(false);

  const worker = useRef<Worker | null>(null),
    active = useRef(""),
    loadRevision = useRef(0);
  const contextRequest = useRef<AbortController | null>(null);
  const bundleRequest = useRef<AbortController | null>(null);

  const [designs, setDesigns] = useState<PhysicalDesign[]>([]),
    [renderInput, setRenderInput] = useState<GPUInput | null>(null);
  const [designPulse,setDesignPulse]=useState<{id:string;kind:PhysicalDesign['kind'];progress:number;run:number}|null>(null);
  const [designNotice,setDesignNotice]=useState<{id:string;kind:PhysicalDesign['kind'];run:number}|null>(null);
  const designPulseFrame=useRef<number|null>(null),designNoticeTimer=useRef<number|null>(null),designPulseRun=useRef(0);
  useEffect(()=>()=>{
    if(designPulseFrame.current!==null)cancelAnimationFrame(designPulseFrame.current);
    if(designNoticeTimer.current!==null)window.clearTimeout(designNoticeTimer.current);
  },[]);

  const [replay, setReplay] = useState<{ baseline: Frame[]; planned: Frame[] }>(
      { baseline: [], planned: [] },
    ),
    [comparison, setComparison] = useState<any>(null),
    [planning, setPlanning] = useState(false);

  const [savedComparison, setSavedComparison] =
      useState<CompletedComparison | null>(null),
    [comparisonSaveStatus, setComparisonSaveStatus] = useState("");

  const restoredComparison = useRef<any>(null);

  useEffect(() => {
    readCompletedComparison()
      .then(setSavedComparison)
      .catch((e) =>
        setComparisonSaveStatus("Saved comparison unavailable: " + String(e)),
      );
  }, []);

  useEffect(() => {
    if (
      !comparison ||
      comparison === restoredComparison.current ||
      !bundle ||
      !input ||
      !scenarioInput ||
      !renderInput
    )
      return;

    const record: CompletedComparison = {
      version: 1,
      savedAt: new Date().toISOString(),
      context: {
        bundle,
        input,
        designs,
        flood,
        rain,
        minutes,
        importedStorm,
        antecedentSaturation,
        budget,
        city: context,
        contextStatus,
      },
      report: {
        input: scenarioInput,
        plannedInput: renderInput,
        baseline: replay.baseline,
        planned: replay.planned,
        result: comparison,
        provenance: bundle,
      },
    };

    setComparisonSaveStatus("Saving completed comparison…");

    saveCompletedComparison(record)
      .then(() => {
        setSavedComparison(record);
        setComparisonSaveStatus("Completed comparison saved in this browser.");
      })
      .catch((e) =>
        setComparisonSaveStatus(
          "Comparison remains available in this tab, but saving failed: " +
            String(e),
        ),
      );
  }, [comparison]);

  function restoreComparison() {
    if (!savedComparison) return;

    const c = savedComparison.context,
      r = savedComparison.report;

    worker.current?.terminate();
    active.current = crypto.randomUUID();
    loadRevision.current++;
    contextRequest.current?.abort();
    bundleRequest.current?.abort();

    setPausedRun(null);
    setRunning(false);
    setPlanning(false);
    setFrame(null);
    setError("");

    setBundle(c.bundle);
    setInput(c.input);
    setDesigns(c.designs);
    setFlood(c.flood);
    setRain(c.rain);
    setMinutes(c.minutes);
    setImportedStorm(c.importedStorm);
    setAntecedentSaturation(
      c.antecedentSaturation ??
        c.importedStorm?.antecedent_saturation ??
        c.input.saturation ??
        0,
    );
    setBudget(c.budget);
    setContext(c.city);
    setContextStatus(c.contextStatus);

    restoredComparison.current = r.result;
    setRenderInput(r.plannedInput);
    setReplay({
      baseline: r.baseline as Frame[],
      planned: r.planned as Frame[],
    });
    setComparison(r.result);
    setStatus("Saved comparison restored · original evaluated results");
  }

  function discardComparison() {
    saveCompletedComparison(null)
      .then(() => {
        setSavedComparison(null);
        setComparisonSaveStatus("Saved comparison removed.");
      })
      .catch((e) =>
        setComparisonSaveStatus(
          "Could not remove saved comparison: " + String(e),
        ),
      );
  }

  function clearComparison() {
    setPausedRun(null);
    setReplay({ baseline: [], planned: [] });
    setComparison(null);
  }

  function useStorm(storm: any, statusPrefix = "Loaded rainfall") {
    worker.current?.terminate();
    active.current = crypto.randomUUID();
    setRunning(false);
    setPlanning(false);
    setRenderInput(null);
    setImportedStorm(storm);
    setRain(storm.depth_m * 1000);
    setMinutes(storm.duration_s / 60);
    setAntecedentSaturation(storm.antecedent_saturation ?? 0.25);
    clearComparison();
    setFrame(null);
    setStatus(statusPrefix + ": " + storm.name);
    setError("");
  }

  function changeAntecedent(value: number) {
    setAntecedentSaturation(value);
    if (importedStorm)
      setImportedStorm({ ...importedStorm, antecedent_saturation: value });
    clearComparison();
    setFrame(null);
    setRenderInput(null);
  }

  async function loadNoaaStorm() {
    if (!bundle || loadingStorm) return;
    setLoadingStorm(true);
    setError("");
    try {
      const query = new URLSearchParams({
        duration_minutes: String(minutes),
        return_period_years: String(noaaReturnPeriod),
        distribution: noaaDistribution,
        antecedent_saturation: String(antecedentSaturation),
      });
      useStorm(
        await api(
          "/bundles/" + bundle.bundle_id + "/design-storms/noaa?" + query,
        ),
        "Loaded NOAA Atlas 14 design storm",
      );
    } catch (error) {
      setError(
        "Could not load NOAA Atlas 14 point precipitation. " + String(error),
      );
    } finally {
      setLoadingStorm(false);
    }
  }

  const contextLoading = contextStatus === "Loading street detail";

  function changeDesign(next: PhysicalDesign[]) {
    if (contextLoading) return;
    setPausedRun(null);
    try {
      if (input)
        for (const candidate of next)
          compileDesign(
            planningInput ?? input,
            [candidate],
            Number.MAX_SAFE_INTEGER,
          );
      const changed=next.find(candidate=>{const previous=designs.find(item=>item.id===candidate.id);return !previous||JSON.stringify(previous)!==JSON.stringify(candidate);});
      setDesigns(next);
      if(changed){
        if(designPulseFrame.current!==null)cancelAnimationFrame(designPulseFrame.current);
        if(designNoticeTimer.current!==null)window.clearTimeout(designNoticeTimer.current);
        const run=++designPulseRun.current,started=performance.now(),tick=(now:number)=>{
          const progress=Math.min(1,(now-started)/1500);
          setDesignPulse({id:changed.id,kind:changed.kind,progress,run});
          if(progress<1)designPulseFrame.current=requestAnimationFrame(tick);
          else setDesignPulse(current=>current?.run===run?null:current);
        };
        setDesignNotice({id:changed.id,kind:changed.kind,run});
        designNoticeTimer.current=window.setTimeout(()=>setDesignNotice(current=>current?.run===run?null:current),5200);
        designPulseFrame.current=requestAnimationFrame(tick);
      }
      clearComparison();
      setFrame(null);
      setRenderInput(null);
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }

  async function loadContext(id: string, revision: number) {
    contextRequest.current?.abort();
    const controller = new AbortController();
    contextRequest.current = controller;
    try {
      const c = await api(
        "/bundles/" + id + "/context",
        undefined,
        AbortSignal.any([controller.signal, AbortSignal.timeout(45_000)]),
      );
      if (revision === loadRevision.current) {
        setContext(c);
        setContextStatus(
          c.attribution ?? "Global landscape context; street data unavailable",
        );
      }
    } catch {
      if (revision === loadRevision.current && !controller.signal.aborted)
        setContextStatus("Street detail unavailable");
    } finally {
      if (contextRequest.current === controller) contextRequest.current = null;
    }
  }
  function retryContext() {
    if (
      !bundle ||
      running ||
      contextLoading ||
      preparing ||
      bundleRequest.current
    )
      return;
    clearComparison();
    setFrame(null);
    setRenderInput(null);
    setContextStatus("Loading street detail");
    void loadContext(bundle.bundle_id, ++loadRevision.current);
  }

  async function load(id: string) {
    setPausedRun(null);
    loadStarted.current = performance.now();
    // The old map can still render while downloading; only measure the new bundle.
    sceneMeasured.current = true;
    document.documentElement.removeAttribute("data-scene-load-ms");
    document.documentElement.removeAttribute("data-bundle-fetch-ms");
    worker.current?.terminate();
    active.current = crypto.randomUUID();
    setRunning(false);
    setPlanning(false);
    clearComparison();
    setStatus("Loading terrain and footprints…");
    setError("");
    setFrame(null);
    setDesigns([]);setDrawnSites([]);setDrawMode(false);
    setRenderInput(null);
    setFlood({ mode: "rain", inflows: [], outlets: [], source: "" });
    setImportedStorm(null);
    setAntecedentSaturation(0.25);
    setContext(null);
    setContextStatus("Loading street detail");
    const revision = ++loadRevision.current;
    contextRequest.current?.abort();
    bundleRequest.current?.abort();
    const controller = new AbortController();
    bundleRequest.current = controller;
    try {
      const result = await loadBundleResources(
        id,
        getSessionToken(),
        (signal) =>
          api("/bundles/" + id, undefined, signal, true) as Promise<Bundle>,
        controller.signal,
        authenticatedFetch,
      );
      if (revision !== loadRevision.current) return;
      void loadContext(id, revision);
      document.documentElement.dataset.bundleFetchMs =
        result.fetchMs.toFixed(1);
      sceneMeasured.current = false;
      setBundle(result.bundle);
      setInput(result.input);
      writeSessionValue("sponge-location", id);
      const locationUrl = new URL(window.location.href);
      locationUrl.searchParams.set("bundle", id);
      window.history.replaceState(null, "", locationUrl);
      setStatus("Ready to explore");
    } catch (error) {
      if (controller.signal.aborted || revision !== loadRevision.current)
        return;
      setContextStatus("Street detail unavailable");
      throw error;
    } finally {
      if (bundleRequest.current === controller) bundleRequest.current = null;
    }
  }

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        if (!getSessionToken()) {
          // Session creation is safe to repeat: an interrupted response can only
          // leave an unused, expiring session behind.
          const s = await api("/sessions", {}, undefined, true);
          setSessionToken(s.token);
        }
        const saved =
          new URLSearchParams(window.location.search).get("bundle") ??
          readSessionValue("sponge-location");
        if (saved) {
          if (alive) await load(saved);
        } else {
          const examples = await api("/examples", undefined, undefined, true);
          if (alive && examples.length) await load(examples[0].bundle_id);
        }
      } catch (e) {
        if (alive) setError(String(e));
      } finally {
        if (alive) setStartupReady(true);
      }
    })();
    return () => {
      alive = false;
      loadRevision.current++;
      contextRequest.current?.abort();
      bundleRequest.current?.abort();
      worker.current?.terminate();
    };
  }, []);

  function clearSearch() {
    searchRequest.current?.abort();
    searchRequest.current = null;
    setSearching(false);
    setLocations([]);
    setSearchNote("");
  }

  async function search() {
    if (preparationActive.current || searchRequest.current || !startupReady)
      return;
    if (!query.trim()) {
      setSearchNote("Enter a place name or latitude, longitude.");
      return;
    }
    const controller = new AbortController();
    searchRequest.current = controller;
    setSearching(true);
    setLocations([]);
    setSearchNote("");
    setError("");
    try {
      const r = await api("/geocode", { query, region }, controller.signal);
      if (searchRequest.current !== controller) return;
      setLocations(r.locations);
      setSearchNote(
        [
          ...(r.warnings ?? []),
          r.locations.length
            ? "Confirm the city and coordinates before selecting a result."
            : "No matching place found. Add a city or region, try a nearby landmark, or paste coordinates.",
        ].join(" "),
      );
    } catch (e) {
      if (searchRequest.current === controller)
        setSearchNote(
          "Search could not finish. " +
            String(e) +
            " You can also paste latitude, longitude.",
        );
    } finally {
      if (searchRequest.current === controller) {
        searchRequest.current = null;
        setSearching(false);
      }
    }
  }

  useEffect(() => () => searchRequest.current?.abort(), []);

  async function prepare(location: any) {
    if (preparationActive.current || location.terrain_supported === false)
      return;

    preparationActive.current = true;
    setPreparing(true);
    setError("");
    clearSearch();

    setPreparationStatus(
      "Preparing " +
        location.label +
        "… The current map remains visible until it is ready.",
    );

    try {
      const job = await api("/neighbourhoods", {
        longitude: location.longitude,
        latitude: location.latitude,
        label: location.label.slice(0, 160),
        extent_m: areaSize,
        grid_cells: gridSize,
        source: "auto",
        country_code: location.country_code ?? undefined,
        currency: normaliseCurrency(location.currency),
      });

      let result;

      do {
        await new Promise((r) => setTimeout(r, 1000));
        result = await api("/neighbourhoods/" + job.id);

        setPreparationStatus(
          result.status === "queued"
            ? result.worker_available === false
              ? "Terrain worker is offline. Your location is queued; start SPONGE with Start-SPONGE.ps1 to continue."
              : "Your location is queued for terrain preparation…"
            : "Preparing " +
                location.label +
                ": " +
                (result.stage ?? result.status),
        );
      } while (["queued", "running"].includes(result.status));

      if (result.status !== "completed")
        throw new Error(result.error ?? "Terrain preparation failed");

      await load(result.bundle_id);
      setPreparationStatus("");
    } catch (e) {
      setPreparationStatus(
        "Location could not be loaded. The previous map is still shown.",
      );
      setError(String(e));
    } finally {
      preparationActive.current = false;
      setPreparing(false);
    }
  }

  const [pausedRun, setPausedRun] = useState<PausedStorm | null>(null);

  const [recoverable, setRecoverable] = useState<RecoveryRecord | null>(null),
    [recoveryStatus, setRecoveryStatus] = useState("");

  useEffect(() => {
    readRecovery()
      .then(setRecoverable)
      .catch((e) => setRecoveryStatus("Saved run unavailable: " + String(e)));
  }, []);

  function discardRecovery() {
    setRecoverable(null);
    setPausedRun(null);
    saveRecovery(null).catch((e) =>
      setRecoveryStatus("Could not remove saved run: " + String(e)),
    );
  }

  function recoverSaved() {
    if (!recoverable) return;
    const c = recoverable.context;
    worker.current?.terminate();
    active.current = crypto.randomUUID();
    loadRevision.current++;
    contextRequest.current?.abort();
    bundleRequest.current?.abort();
    clearComparison();
    setBundle(c.bundle);
    setInput(c.input);
    setDesigns(c.designs);
    setFlood(c.flood);
    setRain(c.rain);
    setMinutes(c.minutes);
    setImportedStorm(c.importedStorm);
    setAntecedentSaturation(
      c.antecedentSaturation ??
        c.importedStorm?.antecedent_saturation ??
        c.input.saturation ??
        0,
    );
    setBudget(c.budget);
    setContext(c.city);
    setContextStatus(c.contextStatus);
    setRenderInput(recoverable.run.input);
    setPausedRun(recoverable.run);
    setRunning(false);
    setPlanning(false);
    setFrame(null);
    setStatus(
      "Saved storm restored. Resume to continue from " +
        Math.round(recoverable.run.checkpoint.solver.time) +
        " seconds.",
    );
    setRecoverable(null);
  }

  function run(resume = false) {
    if (!scenarioInput || contextLoading) return;
    try {
      validateScenarioExecution(scenarioInput, forcing);
      validateDataForRun();
    } catch (e) {
      setError(String(e));
      return;
    }
    let compiled: GPUInput;
    try {
      compiled = compileDesign(
        scenarioInput!,
        designs,
        Math.round(budget * 100),
      );
    } catch (e) {
      setError(String(e));
      return;
    }
    const saved = resume ? pausedRun : null;
    if (!resume) discardRecovery();
    if (saved) compiled = saved.input;
    else setPausedRun(null);
    clearComparison();
    setRenderInput(compiled);
    worker.current?.terminate();
    const w = new Worker(
      new URL("../../../packages/simulation/src/worker.ts", import.meta.url),
      { type: "module" },
    );
    worker.current = w;
    active.current = crypto.randomUUID();
    setFrame(null);
    setRunning(true);
    setError("");
    setStatus(
      flood.mode === "rain"
        ? "Simulating rainfall"
        : "Simulating flood sources",
    );
    w.onmessage = (e) => {
      if (e.data.runId !== active.current) return;
      if (e.data.type === "CHECKPOINT") {
        const paused: PausedStorm = {
          checkpoint: e.data.checkpoint,
          input: compiled,
          duration: saved?.duration ?? runDuration,
          recession: saved?.recession ?? simulationEnd - runDuration,
          depth: saved?.depth ?? forcing.storm.depth,
          intervals: saved?.intervals ?? forcing.storm.intervals,
        };
        setPausedRun(paused);
        const record: RecoveryRecord = {
          version: 1,
          savedAt: new Date().toISOString(),
          run: paused,
          context: {
            bundle,
            input: input!,
            designs,
            flood,
            rain,
            minutes,
            importedStorm,
            antecedentSaturation,
            budget,
            city: context,
            contextStatus,
          },
        };
        saveRecovery(record)
          .then(() => {
            if (e.data.runId === active.current)
              setRecoveryStatus(
                e.data.reason === "automatic"
                  ? "Automatic recovery saved at " +
                      Math.round(paused.checkpoint.solver.time) +
                      " simulated seconds."
                  : "Stopped storm saved on this browser.",
              );
          })
          .catch((err) => {
            if (e.data.runId === active.current)
              setRecoveryStatus(
                "Resume is available in this tab, but saving failed: " +
                  String(err),
              );
          });
      }
      if (e.data.type === "FRAME") setFrame(e.data.frame);
      if (e.data.type === "INFO") setDevice(e.data.info.renderer);
      if (e.data.type === "DONE") discardRecovery();
      if (["DONE", "ERROR", "CANCELLED"].includes(e.data.type)) {
        setRunning(false);
        setStatus(
          e.data.type === "DONE"
            ? "Storm and recession completed"
            : "Simulation stopped",
        );
        if (e.data.error) setError(e.data.error);
      }
    };
    const runId = active.current;
    w.onerror = (e) => {
      if (active.current !== runId) return;
      setRunning(false);
      setStatus(
        "Simulation interrupted. Resume the last available checkpoint.",
      );
      setError(e.message || "Simulation worker failed");
    };
    w.onmessageerror = () => {
      if (active.current !== runId) return;
      w.terminate();
      setRunning(false);
      setStatus(
        "Simulation interrupted. Resume the last available checkpoint.",
      );
      setError("Could not read a simulation worker message");
    };
    w.postMessage({
      type: "RUN",
      input: compiled,
      duration: saved?.duration ?? runDuration,
      recession: saved?.recession ?? simulationEnd - runDuration,
      depth: saved?.depth ?? forcing.storm.depth,
      intervals: saved?.intervals ?? forcing.storm.intervals,
      checkpoint: saved?.checkpoint,
      runId: active.current,
    });
  }

  async function runCpuFallback() {
    if (!bundle || !scenarioInput) return;
    if (
      designs.length ||
      forcing.components.external ||
      forcing.components.coastal
    ) {
      setError(
        "CPU reference fallback accepts rainfall-only baseline runs. Remove designs and disable external/coastal sources; no source is silently dropped.",
      );
      return;
    }
    setRunning(true);
    setFrame(null);
    setError("");
    setStatus("Running bounded server CPU reference…");
    try {
      const intervals = forcing.storm.intervals ?? [
          {
            start_s: 0,
            end_s: forcing.storm.duration,
            rate_m_s: forcing.storm.depth / forcing.storm.duration,
          },
        ],
        result = await api(`/bundles/${bundle.bundle_id}/cpu-reference`, {
          storm: {
            schema_version: "sponge.v1",
            name: forcing.storm.name ?? "CPU reference rainfall",
            duration_s: forcing.storm.duration,
            recession_s: forcing.storm.recession,
            depth_m: forcing.storm.depth,
            intervals,
            return_period_years: forcing.storm.returnPeriodYears ?? null,
            source_ids: forcing.storm.sourceIds ?? [],
            distribution: forcing.storm.distribution ?? "uniform",
            antecedent_saturation: antecedentSaturation,
          },
          antecedent_saturation: antecedentSaturation,
        });
      const f = result.frame;
      setFrame({
        time_s: f.time_s,
        depth: new Float32Array(f.depth),
        maxDepth: new Float32Array(f.maxDepth),
        ledger: f.ledger,
      });
      setRenderInput(scenarioInput);
      setDevice("Server CPU float64 HLL reference");
      setStatus(
        "CPU reference completed · rainfall-only baseline; no GPU or design result claimed",
      );
    } catch (e) {
      setError(String(e));
      setStatus("CPU reference unavailable");
    } finally {
      setRunning(false);
    }
  }

  function experiment(mode: "PLAN" | "COMPARE") {
    if (!scenarioInput || contextLoading) return;
    try {
      validateScenarioExecution(scenarioInput, forcing);
      validateDataForRun();
    } catch (e) {
      setError(String(e));
      return;
    }
    clearComparison();
    setFrame(null);
    setError("");
    setRunning(true);
    setPlanning(true);

    worker.current?.terminate();
    const w = new Worker(
      new URL(
        "../../../packages/simulation/src/planner-worker.ts",
        import.meta.url,
      ),
      { type: "module" },
    );
    worker.current = w;
    const id = crypto.randomUUID();
    active.current = id;

    setStatus(
      mode === "PLAN" ? "Searching feasible plans…" : "Preparing comparison…",
    );

    w.onerror = (e) => {
      if (active.current !== id) return;
      setError(e.message);
      setRunning(false);
      setPlanning(false);
    };

    w.onmessage = (e) => {
      const d = e.data;
      if (d.runId !== active.current) return;

      if (d.type === "PROGRESS") setStatus(d.message);

      if (d.type === "REPLAY")
        setReplay((previous) => ({
          ...previous,
          [d.side]: [...previous[d.side as "baseline" | "planned"], d.frame],
        }));

      if (d.type === "COMPLETE") {
        try {
          const scenario = scenarioSpec(scenarioInput, forcing, {
            bundleId: bundle?.bundle_id,
            horizontalCrs: bundle?.grid.crs,
            verticalDatum: bundle?.grid.vertical_datum,
            elevationOriginM: bundle?.grid.elevation_origin_m,
            inputHash: d.evidence.baselineInputHash,
          });
          const planned = compileDesign(
            scenarioInput,
            d.designs,
            Math.round(budget * 100),
          );
          setComparison({ ...d, evidence: { ...d.evidence, scenario } });
          setRenderInput(planned);
          setStatus(
            d.evidence.robustPlanning
              ? "Comparison complete · identical 80/100/120% rainfall sensitivity ensemble; point-storm replay shown"
              : "Comparison complete · identical storm and initial surface conditions",
          );
        } catch (error) {
          clearComparison();
          setStatus("Comparison evidence could not be verified");
          setError(String(error));
        }
      }

      if (["COMPLETE", "ERROR", "CANCELLED"].includes(d.type)) {
        setRunning(false);
        setPlanning(false);
        if (d.type !== "COMPLETE") {
          clearComparison();
          setStatus("Comparison stopped");
        }
        if (d.error) setError(d.error);
      }
    };

    w.postMessage({
      mode,
      input: scenarioInput,
      designs,
      budgetMinor: Math.round(budget * 100),
      currency,
      storm: forcing.storm,
      stormEnsemble:
        mode === "PLAN" && forcing.components.rainfall
          ? rainfallSensitivityEnsemble(forcing.storm)
          : [forcing.storm],
      runId: id,
    });
  }

  const satelliteMesh = useMemo(
    () =>
      input && imageryDescriptor
        ? imageryMesh(renderInput ?? input, imageryDescriptor.cornersUV)
        : null,
    [input, renderInput, imageryDescriptor],
  );

  const terrainMesh = useMemo(
    () => (input ? terrainSurface(renderInput ?? input) : null),
    [input, renderInput],
  );
  const geometry = useMemo(
    () =>
      input && bundle
        ? cityGeometry(
            renderInput ?? input,
            bundle.extent_m,
            bundle.buildings,
            context,
            terrainMesh!,
          )
        : null,
    [input, renderInput, bundle, context, terrainMesh],
  );

  const roofMesh = useMemo(
    () =>
      input && geometry && imageryDescriptor
        ? roofImageryMesh(input, geometry.blocks, imageryDescriptor.cornersUV)
        : null,
    [input, geometry, imageryDescriptor],
  );

  const cameraPreset = useMemo(
    () => ({
      target: [0, 0, 15] as [number, number, number],
      rotationX: planView ? 89 : sideView ? 15 : 42,
      rotationOrbit: planView ? 0 : -18,
      zoom: 0.15 + Math.log2(600 / (bundle?.extent_m ?? 600)),
    }),
    [sideView, planView, bundle?.extent_m],
  );

  const designSceneLayers=useMemo(()=>{
    if(!input||!designs.length)return [];
    const displayInput=renderInput??input,west=-displayInput.nx*displayInput.dx/2,south=-displayInput.ny*displayInput.dy/2;
    const cells=designs.flatMap(design=>design.cells.map(cell=>{const x=cell%displayInput.nx,y=Math.floor(cell/displayInput.nx),top=displayInput.z[cell]+(frame?.depth[cell]??0)+.12;return {design,polygon:[[west+x*displayInput.dx,south+y*displayInput.dy,top],[west+(x+1)*displayInput.dx,south+y*displayInput.dy,top],[west+(x+1)*displayInput.dx,south+(y+1)*displayInput.dy,top],[west+x*displayInput.dx,south+(y+1)*displayInput.dy,top]]};}));
    const labels=designs.map(design=>{const positions=design.cells.map(cell=>{const x=cell%displayInput.nx,y=Math.floor(cell/displayInput.nx);return [west+(x+.5)*displayInput.dx,south+(y+.5)*displayInput.dy,displayInput.z[cell]+(frame?.depth[cell]??0)+1.4];});return {design,position:positions.reduce((sum,point)=>sum.map((value,index)=>value+point[index]),[0,0,0]).map(value=>value/positions.length)};});
    const pulse=designPulse?labels.filter(item=>item.design.id===designPulse.id).map(item=>({...item,progress:designPulse.progress})):[];
    return [
      new PolygonLayer({coordinateSystem:COORDINATE_SYSTEM.CARTESIAN,id:'selected-design-footprints',data:cells,getPolygon:d=>d.polygon,getFillColor:d=>INTERVENTION_COLOURS[(d as {design:PhysicalDesign}).design.kind],getLineColor:[229,255,188,245],stroked:true,lineWidthMinPixels:2,pickable:true}),
      new TextLayer({coordinateSystem:COORDINATE_SYSTEM.CARTESIAN,id:'selected-design-labels',data:labels,getPosition:d=>d.position,getText:d=>INTERVENTION_NAMES[(d as {design:PhysicalDesign}).design.kind],getSize:12,getColor:[238,255,218,255],background:true,getBackgroundColor:[14,55,51,220],getTextAnchor:'middle',getAlignmentBaseline:'bottom',billboard:true}),
      new ScatterplotLayer({coordinateSystem:COORDINATE_SYSTEM.CARTESIAN,id:'selected-design-placement-pulse',data:pulse,getPosition:d=>d.position,getRadius:d=>6+(bundle?.extent_m??600)*.065*d.progress,getFillColor:[0,0,0,0],getLineColor:d=>{const colour=INTERVENTION_COLOURS[(d as {design:PhysicalDesign}).design.kind];return [colour[0],colour[1],colour[2],Math.round(245*(1-d.progress))];},stroked:true,lineWidthMinPixels:3,radiusUnits:'meters'}),
    ];
  },[input,renderInput,frame,designs,designPulse,bundle?.extent_m]);

  const layers = useMemo(() => {
    if (!geometry || !input) return [];
    const base = cityLayers(
      geometry,
      renderInput ?? input,
      frame,
      planningSites,
      detail && renderQuality !== "eco",
      waterHeightScale,
    ).filter(
      (layer) =>
        sceneLayerStage(layer.id) <= sceneStage &&
        layer.props.visible !== false,
    );
    if (!satellite || !satelliteImage || !satelliteMesh || !roofMesh)
      return [...base,...designSceneLayers];
    return [
      imageryLayer(satelliteMesh, satelliteImage),
      ...base.filter(
        (l) =>
          ![
            "terrain-surface",
            "green-space",
            "sidewalks",
            "streets",
            "roofs",
            "roof-edges",
          ].includes(l.id),
      ),
      roofImageryLayer(roofMesh, satelliteImage),
      ...designSceneLayers,
    ];
  }, [
    geometry,
    input,
    renderInput,
    frame,
    bundle,
    planningSites,
    detail,
    renderQuality,
    waterHeightScale,
    satellite,
    satelliteImage,
    satelliteMesh,
    roofMesh,
    sceneStage,
    designSceneLayers,
  ]);

  return (
    <>
    {launch.visible&&<LaunchExperience key={launch.run} exiting={launch.exiting} onEnter={closeLaunch} onTour={()=>{closeLaunch();window.setTimeout(()=>setShowJudgeTour(true),780);}}/>}
    <div className={`app ${launch.visible?'is-launching':''}`} aria-hidden={launch.visible||undefined} inert={launch.visible||undefined}>
      <header>
        <div className="brand">
          <Droplets size={27} />
          SPONGE
        </div>
        <span className="subtitle">Neighbourhood stormwater lab</span>
        <button className="quiet tour-button" onClick={() => setShowJudgeTour(true)}>
          <Route size={17} /> Judge tour
        </button>
        <button className="quiet" onClick={() => setShowSources(!showSources)}>
          <ShieldCheck size={17} /> Data & assumptions
        </button>
      </header>

      <aside>
        <div className="eyebrow">01 / LOCATION</div>
        <h1>{bundle?.label ?? "Explore a neighbourhood"}</h1>
        <div className="search">
          <input
            aria-label="Address"
            disabled={preparing}
            value={query}
            onChange={(e) => {
              clearSearch();
              setQuery(e.target.value);
            }}
            placeholder="Place, address or coordinates"
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <button
            aria-label="Search"
            disabled={preparing || searching || !startupReady}
            onClick={search}
          >
            <Search size={18} />
          </button>
        </div>
        <input
          className="search-region"
          aria-label="City or region"
          disabled={preparing}
          value={region}
          onChange={(e) => {
            clearSearch();
            setRegion(e.target.value);
          }}
          placeholder="City or region (optional)"
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <details className="search-help note">
          <summary>Can’t find a place?</summary>
          <p>
            Add its city or country, or copy coordinates from a map and paste
            them above as latitude, longitude. Coordinates work even when the
            place name is missing.
          </p>
          <p>
            Search is worldwide, but map names and buildings are incomplete.
            Terrain currently supports 80°S–80°N; availability and resolution
            vary. Finding a place does not validate its flood accuracy.
          </p>
        </details>
        {(searching || searchNote) && (
          <p role="status" className="note">
            {searching ? "Searching places…" : searchNote}
          </p>
        )}
        {locations.map((l, i) => (
          <div className="location-result" key={i}>
            <button
              className="location"
              aria-label={l.label}
              disabled={preparing || l.terrain_supported === false}
              onClick={() => prepare(l)}
            >
              {l.label}
              <small>
                {l.latitude.toFixed(5)}, {l.longitude.toFixed(5)}
                {l.provider ? " · " + l.provider : ""}
                {l.currency ? " · costs in " + l.currency + (l.currency_source === "fallback" ? " (fallback)" : "") : ""}
              </small>
            </button>
            {l.terrain_supported === false && (
              <p className="note">{l.coverage_note}</p>
            )}
          </div>
        ))}
        {locations.some((l) => l.provider && l.provider !== "Coordinates") && (
          <p className="note">
            Search data:{" "}
            <a
              href="https://www.openstreetmap.org/copyright"
              target="_blank"
              rel="noreferrer"
            >
              © OpenStreetMap contributors
            </a>{" "}
            ·{" "}
            <a
              href="https://github.com/komoot/photon"
              target="_blank"
              rel="noreferrer"
            >
              Photon
            </a>{" "}
            / Nominatim
          </p>
        )}

        {preparationStatus && (
          <p role="status" className="note">
            {preparationStatus}
          </p>
        )}

        {savedComparison && !running && (
          <div className="recovery">
            <p>Saved comparison: {savedComparison.context.bundle.label}</p>
            <button
              disabled={!startupReady || preparing}
              onClick={restoreComparison}
            >
              Restore saved comparison
            </button>
            <button onClick={discardComparison}>
              Discard saved comparison
            </button>
          </div>
        )}
        {comparisonSaveStatus && <p className="note">{comparisonSaveStatus}</p>}

        <label>
          Area width
          <select
            value={areaSize}
            disabled={running || preparing}
            onChange={(e) => setAreaSize(+e.target.value)}
          >
            <option value="600">600 m neighbourhood</option>
            <option value="1200">1.2 km district</option>
            <option value="2000">2 km district</option>
          </select>
        </label>
        <label>
          Simulation grid
          <select
            value={gridSize}
            disabled={running || preparing}
            onChange={(e) => setGridSize(+e.target.value)}
          >
            <option value="128">128 × 128 · lower compute</option>
            <option value="256">256 × 256 · finer detail</option>
            <option value="512">512 × 512 · heavy compute</option>
          </select>
        </label>
        <p className="note">
          Next location: {(areaSize / gridSize).toFixed(2)} m cells. Finer
          sampling does not improve source elevation accuracy. Changes apply
          when you select a search result.
        </p>
        <div className="facts">
          <span>{bundle?.buildings.length ?? "—"} buildings</span>
          <span>{input ? input.dx.toFixed(2) + " m grid" : "—"}</span>
        </div>
        <hr />
        <div className="eyebrow">02 / STORM</div>
        <label>
          Rainfall depth{" "}
          <strong>
            {rain.toLocaleString(undefined, { maximumFractionDigits: 1 })} mm
          </strong>
          <input
            type="range"
            min="0"
            max={Math.max(250, Math.ceil(rain / 50) * 50)}
            step="1"
            value={rain}
            onChange={(e) => {
              setImportedStorm(null);
              setRain(+e.target.value);
              clearComparison();
              setFrame(null);
            }}
            disabled={running || !activeForcing.rainfall}
          />
        </label>
        <label>
          Duration
          <select
            aria-label="Duration"
            value={minutes}
            onChange={(e) => {
              setImportedStorm(null);
              setMinutes(+e.target.value);
              clearComparison();
              setFrame(null);
            }}
            disabled={running}
          >
            {importedStorm && ![10, 60, 360].includes(minutes) && (
              <option value={minutes}>{minutes} minutes · imported</option>
            )}
            <option value="10">10 minutes</option>
            <option value="60">1 hour</option>
            <option value="360">6 hours</option>
          </select>
        </label>
        <label>
          Antecedent soil condition
          <select
            aria-label="Antecedent soil condition"
            value={antecedentSaturation}
            onChange={(e) => changeAntecedent(+e.target.value)}
            disabled={running}
          >
            <option value="0.1">Dry · 10% saturation</option>
            <option value="0.25">Typical assumption · 25%</option>
            <option value="0.75">Wet · 75%</option>
            <option value="1">Saturated · 100%</option>
          </select>
        </label>
        <details className="note storm-builder">
          <summary>Load NOAA Atlas 14 design storm</summary>
          <label>
            Annual recurrence interval
            <select
              aria-label="NOAA return period"
              value={noaaReturnPeriod}
              onChange={(e) => setNoaaReturnPeriod(+e.target.value)}
              disabled={running || loadingStorm}
            >
              <option value="2">2-year</option>
              <option value="5">5-year</option>
              <option value="10">10-year</option>
              <option value="25">25-year</option>
              <option value="50">50-year</option>
              <option value="100">100-year</option>
              <option value="200">200-year</option>
              <option value="500">500-year</option>
            </select>
          </label>
          <label>
            Temporal pattern
            <select
              aria-label="Temporal rainfall pattern"
              value={noaaDistribution}
              onChange={(e) => setNoaaDistribution(e.target.value)}
              disabled={running || loadingStorm}
            >
              <option value="uniform">Uniform</option>
              <option value="centered">Centered peak</option>
              <option value="front_loaded">Front-loaded</option>
              <option value="rear_loaded">Rear-loaded</option>
            </select>
          </label>
          <button
            disabled={
              !bundle ||
              running ||
              loadingStorm ||
              ![10, 60, 360].includes(minutes)
            }
            onClick={loadNoaaStorm}
          >
            {loadingStorm ? "Loading NOAA data…" : "Load NOAA point estimate"}
          </button>
          <p>
            NOAA supplies a point precipitation total and 90% confidence
            interval. SPONGE applies the selected synthetic time pattern; it is
            not a NOAA hyetograph or an areal storm.
          </p>
        </details>
        <p className="note">
          {!activeForcing.rainfall
            ? "Rainfall disabled for this scenario."
            : importedStorm
              ? "Sourced rainfall intervals: " + importedStorm.name
              : "Custom uniform rainfall; no assigned return period."}{" "}
          Simulation window: {Math.round(simulationEnd / 60)} minutes.
        </p>
        {importedStorm?.evidence && (
          <div className="note storm-evidence">
            <strong>
              {importedStorm.evidence.estimate_mm} mm point estimate
            </strong>{" "}
            · 90% interval {importedStorm.evidence.confidence_interval.lower_mm}
            –{importedStorm.evidence.confidence_interval.upper_mm} mm · annual
            exceedance probability{" "}
            {(
              importedStorm.evidence.annual_exceedance_probability * 100
            ).toFixed(2)}
            %<br />
            {importedStorm.evidence.region} · Atlas 14 volume{" "}
            {importedStorm.evidence.volume}, version{" "}
            {importedStorm.evidence.version}
            <br />
            <a
              href={importedStorm.evidence.product_page}
              target="_blank"
              rel="noreferrer"
            >
              Official NOAA PFDS
            </a>{" "}
            · point estimate, not areal rainfall
          </div>
        )}

        <button
          className="primary"
          disabled={!input || (!running && contextLoading)}
          onClick={() =>
            running ? worker.current?.postMessage({ type: "CANCEL" }) : run()
          }
        >
          {running ? <Square size={17} /> : <Play size={17} />}{" "}
          {running ? "Stop simulation" : "Run storm"}
        </button>
        {!running && (
          <button
            disabled={!bundle || contextLoading || bundle.grid.nx * bundle.grid.ny > 128 * 128}
            onClick={runCpuFallback}
          >
            Run CPU reference fallback
          </button>
        )}
        {pausedRun && !running && (
          <button className="primary" onClick={() => run(true)}>
            Resume stopped storm
          </button>
        )}
        {recoverable && !running && (
          <div className="recovery">
            <p>
              Saved storm: {recoverable.context.bundle.label} ·{" "}
              {Math.round(recoverable.run.checkpoint.solver.time)} seconds
            </p>
            <button disabled={!startupReady} onClick={recoverSaved}>
              Restore saved storm
            </button>
            <button onClick={discardRecovery}>Discard saved storm</button>
          </div>
        )}
        {recoveryStatus && <p className="note">{recoveryStatus}</p>}
        {!contextLoading &&
          bundle &&
          (context === null || context.water === undefined) && (
            <div className="note">
              <p>
                Vegetation or water coverage is unavailable. Retrying clears the
                current result so it can be recalculated with updated coverage.
              </p>
              <button disabled={running || preparing} onClick={retryContext}>
                Retry landscape coverage
              </button>
            </div>
          )}
        <div className="status">
          {contextLoading
            ? "Loading vegetation and water coverage before simulation…"
            : status}
        </div>
        {error && (
          <div role="alert" className="error">
            {error}
          </div>
        )}
        <hr />
        <ScenarioDataStatus {...dataScreen} />
        <FloodInputs
          elevationOriginM={bundle?.grid.elevation_origin_m}
          verticalDatum={bundle?.grid.vertical_datum}
          input={planningInput}
          value={flood}
          onChange={changeFlood}
          disabled={running || contextLoading}
        />
        <hr />
        <div className="eyebrow">MODEL CONDITIONS</div>
        <details className="note" aria-label="Model validation limits">
          <summary>{validationStatus.summary}</summary>
          <p>{validationStatus.numericalEvidence}</p>
          <p>{validationStatus.terrain}</p>
          <p>{validationStatus.planning}</p>
          <p>{validationStatus.damage}</p>
        </details>
        <p className="note">
          Order {input?.spatialOrder ?? 1} surface solver ·{" "}
          {activeForcing.coastal && flood.coastal
            ? "Prescribed coastal level on " +
              flood.coastal.edge +
              "; other edges closed"
            : "Closed surface edges"}{" "}
          · {flood.outlets.length} parameterised outlets · assumed soil
          materials. Green markers are candidate areas with unverified
          eligibility. {Math.max(0,(bundle?.candidates.length ?? 0) - planningSites.filter(site=>!String(site.id).startsWith('drawn-')).length)}{" "}
          sites excluded by mapped water coverage.{" "}
          {context?.water === undefined
            ? "Water screening unavailable or loading; eligibility remains unverified."
            : "Water screening uses satellite classification, not a site survey."}
        </p>
        <label>
          Budget ({currency})
          <input
            type="number"
            value={budget}
            min="0"
            disabled={running}
            onChange={(e) => {
              setBudget(+e.target.value);
              clearComparison();
              setFrame(null);
            }}
          />
        </label>
        <p className="note">{bundle?.currency_source === "fallback"
          ? `A country currency could not be inferred, so ${currency} is the editable fallback.`
          : `Costs use the selected location’s ${currency} currency.`} Values are
          local planning assumptions; no exchange-rate conversion is applied.</p>
        <hr />
        <p className="note">
          Planner: physics search · no runtime AI service. Add eligible
          candidate designs below, then search their subsets within your budget.
        </p>
        <button
          className="primary"
          disabled={running || contextLoading || !designs.length}
          onClick={() => experiment("PLAN")}
        >
          Plan with physics
        </button>
        <button
          className="primary compare-button"
          disabled={running || contextLoading || !designs.length}
          onClick={() => experiment("COMPARE")}
        >
          Compare selected design
        </button>
        <DesignEditor
          key={`${bundle?.bundle_id}-${currency}`}
          sites={planningSites}
          designs={designs}
          onChange={changeDesign}
          disabled={running || contextLoading}
          budgetMinor={Math.round(budget * 100)}
          currency={currency}
        />
      </aside>

      <main>
        {input && (
          <DeckGL
            key={
              (bundle?.bundle_id ?? "empty") +
              (planView ? "-plan" : sideView ? "-side" : "-overview")
            }
            views={new OrbitView({ id: "orbit", orbitAxis: "Z" })}
            initialViewState={cameraPreset}
            onAfterRender={() => {
              if (
                sceneStage === 4 &&
                !document.documentElement.dataset.sceneDetailReadyMs
              )
                document.documentElement.dataset.sceneDetailReadyMs =
                  performance.now().toFixed(1);
              if (input && !sceneMeasured.current) {
                sceneMeasured.current = true;
                document.documentElement.dataset.sceneLoadMs = (
                  performance.now() - loadStarted.current
                ).toFixed(1);
              }
            }}
            useDevicePixels={
              renderQuality === "high"
                ? true
                : renderQuality === "eco"
                  ? 0.75
                  : 1
            }
            controller={true}
            onClick={(info: any) => {
              if(drawMode){const coordinate=info.coordinate??info.viewport?.unproject?.([info.x,info.y],{targetZ:0});if(coordinate)drawCandidate(coordinate[0],coordinate[1]);}
            }}
            layers={layers}
            effects={lighting}
            getTooltip={({ object }: any) =>
              object
                ? {
                    text:
                      typeof object.depth === "number"
                        ? "Water depth: " +
                          (object.depth * 100).toFixed(1) +
                          " cm"
                        : object.name ||
                          "Building " +
                            object.id +
                            " · " +
                            object.height_m +
                            " m · " +
                            (object.height_source ??
                              "height source unavailable"),
                    style: { background: "#183f3c", color: "#eef4df" },
                  }
                : null
            }
          />
        )}
        <div className={`storm-atmosphere ${running?'is-running':''}`} aria-hidden="true">
          <div className="storm-cloud storm-cloud-one"/><div className="storm-cloud storm-cloud-two"/>
          <div className="rain-field">{Array.from({length:28},(_,index)=><i key={index} style={{left:`${(index*37)%101}%`,animationDelay:`-${(index%9)*.17}s`,animationDuration:`${.72+(index%5)*.09}s`}}/>)}</div>
          <div className="storm-lightning"/><div className="storm-vignette"/>
        </div>
        {designNotice&&<div key={designNotice.run} className={`design-stage-toast ${designNotice.kind}`} aria-live="polite">
          <Sparkles size={17}/><div><strong>{INTERVENTION_NAMES[designNotice.kind]} placed</strong><span>{designNotice.id} · ready for paired simulation</span></div>
        </div>}
        <div className="maplabel">
          {planView
            ? "TOP-DOWN 2D PLAN"
            : bundle
              ? "FOOTPRINT-BASED 3D MODEL"
              : "PREPARING TERRAIN"}
          <small>
            {planView
              ? "Drag to pan · scroll to zoom"
              : "Drag to orbit · scroll to zoom"}
          </small>
          <small>{contextStatus}</small>
          <small>
            {bundle?.buildings.length ?? 0} mapped 3D buildings · coverage may
            be incomplete
          </small>
          <small>
            {bundle?.buildings.filter((b) =>
              b.height_source?.startsWith("provider"),
            ).length ?? 0}{" "}
            source-reported heights · roofs and facades illustrative
          </small>
          <small>
            {context?.trees.filter((t) => t.basis !== "classified-cover")
              .length ?? 0}{" "}
            mapped trees ·{" "}
            {context?.trees.filter((t) => t.basis === "classified-cover")
              .length ?? 0}{" "}
            illustrative trees from classified cover
          </small>
          {context?.landscape_status && (
            <small>{context.landscape_status}</small>
          )}
          {!!context?.water?.length && (
            <small>
              Mapped permanent water ·{" "}
              {activeForcing.coastal && flood.coastal
                ? "exploratory coastal forcing"
                : "coastal waves not simulated"}
            </small>
          )}
          {satellite && <small>{imageryStatus}</small>}
          {waterHeightScale > 1 && (
            <small>
              Water height exaggerated {waterHeightScale}× · depth readings
              unchanged
            </small>
          )}
        </div>
        <div className="scene-controls">
          <button
            aria-pressed={sideView}
            onClick={() => {
              setSideView(!sideView);
              setPlanView(false);
            }}
          >
            {sideView ? "Overview" : "Side view"}
          </button>
          <button
            aria-pressed={planView}
            onClick={() => {
              setPlanView(!planView);
              setSideView(false);
            }}
          >
            {planView ? "3D overview" : "2D plan view"}
          </button>
          <button
            aria-pressed={drawMode}
            onClick={() => {
              setDrawMode(!drawMode);
              setPlanView(true);
              setSideView(false);
            }}
          >
            {drawMode ? "Stop drawing" : "Draw candidate"}
          </button>
          <button onClick={playLaunch}><CloudRain size={15}/> Opening sequence</button>
          {drawMode && <button onClick={placeCandidateWithKeyboard}>Place candidate near map centre</button>}
          <button onClick={() => setSatellite(!satellite)}>
            {satellite ? "Model view" : "Satellite view"}
          </button>
          <button onClick={() => setDetail(!detail)}>
            {detail ? "Hide details" : "Show details"}
          </button>
          <select
            aria-label="Render quality"
            value={renderQuality}
            onChange={(e) => setRenderQuality(e.target.value)}
          >
            <option value="eco">Eco</option>
            <option value="balanced">Balanced</option>
            <option value="high">High detail</option>
          </select>
          <select
            aria-label="Water height display"
            value={waterHeightScale}
            onChange={(e) => setWaterHeightScale(+e.target.value)}
          >
            <option value="1">Water height: actual</option>
            <option value="5">Water height: 5× display</option>
            <option value="10">Water height: 10× display</option>
          </select>
          <span>
            {bundle?.extent_m} m × {bundle?.extent_m} m
          </span>
        </div>
        <div className="map-credit">
          {satellite && satelliteImage && (
            <span>
              Imagery: Esri, Vantor, Earthstar Geographics, GIS User Community
              ·{" "}
            </span>
          )}
          Building footprints ·{" "}
          {bundle?.sources
            ?.filter((s) =>
              /building|Overture|Overpass/i.test(s.provider ?? ""),
            )
            .map((s) => s.attribution ?? s.provider)
            .filter((v, i, a) => a.indexOf(v) === i)
            .join(" / ") || "See data & assumptions"}{" "}
          | ESA WorldCover 2021 / CC BY 4.0 |{" "}
          <a
            href="https://www.openstreetmap.org/copyright"
            target="_blank"
            rel="noreferrer"
          >
            © OpenStreetMap
          </a>
        </div>
        <div className="metrics">
          <div>
            <span>Simulated time</span>
            <strong>
              {Math.floor((frame?.time_s ?? 0) / 60)}
              <small> min</small>
            </strong>
          </div>
          <div>
            <span>Area above 10 cm</span>
            <strong>
              {input && frame
                ? (
                    frame.maxDepth.reduce(
                      (sum, h, i) =>
                        sum + (h > 0.1 && !planningWaterMask[i] ? 1 : 0),
                      0,
                    ) *
                    input.dx *
                    input.dy
                  ).toLocaleString(undefined, { maximumFractionDigits: 0 })
                : "—"}
              <small> m²</small>
            </strong>
          </div>
          <div>
            <span>Water balance residual</span>
            <strong>
              {frame ? (frame.ledger.relative_residual * 100).toFixed(3) : "—"}
              <small> %</small>
            </strong>
          </div>
          <div>
            <span>Damage estimate</span>
            <strong className="unavailable">Not available</strong>
            <small>Building valuations needed</small>
          </div>
        </div>
        <div className="legend">
          <span className="water" /> Water: pale = shallow, dark = deep · arrows
          = flow <span className="amber" /> Above 10 cm <span className="red" />{" "}
          Above 30 cm
        </div>
      </main>

      {comparison && input && renderInput && bundle && (
        <Replay
          renderQuality={renderQuality}
          waterHeightScale={waterHeightScale}
          baseline={replay.baseline}
          planned={replay.planned}
          input={scenarioInput!}
          plannedInput={renderInput}
          extent={bundle.extent_m}
          provenance={bundle}
          context={context}
          satelliteImage={satellite ? satelliteImage : null}
          imageryDescriptor={imageryDescriptor}
          result={comparison}
          onClose={clearComparison}
        />
      )}

      {showJudgeTour && (
        <section className="judge-tour" role="dialog" aria-modal="true" aria-labelledby="judge-tour-title">
          <button className="tour-close" aria-label="Close judge tour" onClick={() => setShowJudgeTour(false)}>Close</button>
          <div className="eyebrow">EARTH FORWARD · 90-SECOND TOUR</div>
          <h2 id="judge-tour-title">Turn a flood map into a testable neighbourhood decision.</h2>
          <p className="tour-lead">SPONGE helps communities screen where green infrastructure may reduce stormwater flooding before committing to surveys and engineered design.</p>
          <div className="tour-steps">
            <article><span>1</span><div><strong>Stress the neighbourhood</strong><p>Run a disclosed storm over sourced terrain and buildings. The water-balance residual stays visible.</p></div></article>
            <article><span>2</span><div><strong>Design within a budget</strong><p>Place and edit rain gardens, bioswales, permeable pavement or detention. Storage, overflow, eligibility and cost assumptions stay explicit.</p></div></article>
            <article><span>3</span><div><strong>Compare—not just animate</strong><p>Replay baseline and planned runs under identical forcing, expose local worsening, then export the exact inputs, outputs and hashes.</p></div></article>
          </div>
          <div className="tour-proof">
            <h3>What is different?</h3>
            <p>Many tools stop at a risk score, a static map or a polished digital twin. SPONGE links live browser physics, finite-capacity interventions, robust budget search and tamper-checked evidence—while refusing to invent missing accuracy, valuations or parcel eligibility.</p>
            <p><strong>Built and learned across:</strong> hydrodynamics, WebGL2 shaders, geospatial provenance, accessible interaction, recovery and production deployment. The verified release has more than 480 automated checks plus a live container smoke test.</p>
          </div>
          <div className="tour-actions">
            <button className="primary" onClick={() => setShowJudgeTour(false)}>Explore the prepared neighbourhood</button>
            <button onClick={() => { setShowJudgeTour(false); setShowSources(true); }}>Inspect sources and limits</button>
          </div>
          <small>Exploratory screening only—not a calibrated forecast or engineering design.</small>
        </section>
      )}

      {showSources && (
        <section className="sources">
          <button onClick={() => setShowSources(false)}>Close</button>
          <h2>Data & model assumptions</h2>
          {bundle && (
            <DataEnrichment
              key={"enrichment-" + bundle.bundle_id}
              bundleId={bundle.bundle_id}
              api={api}
              uploadTerrain={uploadTerrain}
              onLoad={load}
              onRainfall={(storm) => useStorm(storm, "Imported rainfall")}
            />
          )}
          {bundle && (
            <DataAudit
              key={"audit-" + bundle.bundle_id}
              bundleId={bundle.bundle_id}
              load={api}
            />
          )}
          {bundle?.assumptions.map((a) => (
            <p key={a}>{a}</p>
          ))}
          <pre>{JSON.stringify(bundle?.quality, null, 2)}</pre>
          <p>
            Facade windows, road widths and tree canopy sizes are illustrative
            display details. Satellite mode projects overhead imagery onto
            simplified flat roofs; image alignment, capture date and actual roof
            shape may differ. Continuous terrain is interpolated for display;
            simulation elevations are unchanged. Buildings use source-reported
            heights where available, mapped floors with assumed 3 m per floor,
            or an assumed 9 m height. This is not an exact replica of the
            buildings.
          </p>
          {context?.assumptions.map((a) => (
            <p key={a}>{a}</p>
          ))}
          <p>{device || "GPU identified when simulation starts"}</p>
          <p>
            Development model. Numerical tests do not establish site-specific
            flood accuracy.
          </p>
        </section>
      )}
    </div>
    </>
  );
}
