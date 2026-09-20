import {scenarioInput} from './scenario-input';
import {buildReport,type ReportRequest} from '../../../packages/metrics/report';
import {readSavedComparison,writeSavedComparison,type RecoveryRecord} from './recovery';
import {inputIdentity} from '../../../packages/simulation/src/identity';

export interface CompletedComparison {
 version:1;
 savedAt:string;
 context:RecoveryRecord['context'];
 report:ReportRequest;
}
async function validate(record:CompletedComparison){
 if(record?.version!==1||!record.context?.bundle?.bundle_id||record.context.bundle.bundle_id!==record.report?.provenance?.bundle_id)throw new Error('Unsupported saved comparison');
 await buildReport(record.report);
 const c=record.context,step=record.report.result.evidence.maxStepS??record.report.input.maxStepS??10;
 const input={...scenarioInput(c.input,c.flood,c.city,c.antecedentSaturation??c.importedStorm?.antecedent_saturation??c.input.saturation??0),maxStepS:step};
 if(await inputIdentity(input)!==await inputIdentity({...record.report.input,maxStepS:step}))throw new Error('Saved comparison controls do not match evaluated inputs');
 if(Math.round(c.budget*100)!==record.report.result.evidence.budgetMinor)throw new Error('Saved comparison budget does not match evaluation');
}
// Queue validation and writes together so slower validation cannot overwrite a newer save.
let pending:Promise<unknown>=Promise.resolve();
export function saveCompletedComparison(record:CompletedComparison|null){
 pending=pending.catch(()=>{}).then(async()=>{if(record)await validate(record);await writeSavedComparison(record);});
 return pending;
}
export async function readCompletedComparison():Promise<CompletedComparison|null>{
 await pending.catch(()=>{});
 const record=await readSavedComparison() as CompletedComparison|undefined;
 if(!record)return null;
 await validate(record);return record;
}
