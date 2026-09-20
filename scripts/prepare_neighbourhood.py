import argparse
import json

from services.geodata.prepare import prepare

parser=argparse.ArgumentParser()
parser.add_argument("--lon",type=float,default=-75.164)
parser.add_argument("--lat",type=float,default=39.965)
parser.add_argument("--extent",type=int,default=600)
parser.add_argument("--cells",type=int,default=128)
parser.add_argument("--source",choices=["terrarium","usgs_1m"],default="terrarium")
parser.add_argument("--label",default="Spring Garden, Philadelphia")
parser.add_argument("--public-sample",action="store_true")
args=parser.parse_args()
manifest=prepare({"longitude":args.lon,"latitude":args.lat,"extent_m":args.extent,"grid_cells":args.cells,
                  "source":args.source,"label":args.label},lambda stage:print(stage,flush=True))
print(json.dumps({"bundle_id":manifest["bundle_id"],"buildings":len(manifest["buildings"]),
                  "candidates":len(manifest["candidates"]),"quality":manifest["quality"]},indent=2))
if args.public_sample:
    from services.api.database import Resource, Session
    with Session.begin() as db:
        db.merge(Resource(id=manifest["bundle_id"],session_id=None,kind="sample",status="completed",
                          payload={"bundle_id":manifest["bundle_id"],"label":manifest["label"]}))
