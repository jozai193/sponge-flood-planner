"""Export schemas; --check detects changes without rewriting committed artifacts."""
import argparse
import json
from pathlib import Path

from services.api.contracts import CONTRACT_MODELS
from services.api.scenario_contract import ScenarioSpecV2
from services.geodata.enrichment import ApplyEvidenceRequest, EnrichmentRequest
from services.geodata.imports import DrainageSurvey, RainfallSurvey, SurveySource, VectorSurvey

CONTRACT_MODELS=(*CONTRACT_MODELS,SurveySource,DrainageSurvey,RainfallSurvey,VectorSurvey,EnrichmentRequest,ApplyEvidenceRequest,ScenarioSpecV2)

parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / "packages/contracts/schema"
root.mkdir(parents=True, exist_ok=True)
for model in CONTRACT_MODELS:
    output = json.dumps(model.model_json_schema(), indent=2) + "\n"
    path = root / f"{model.__name__}.json"
    if args.check:
        if not path.exists() or path.read_text() != output:
            raise SystemExit(f"Schema out of date: {path.name}")
    else:
        path.write_text(output)
print(f"{len(CONTRACT_MODELS)} contract schemas {'checked' if args.check else 'exported'}")
