from services.api.database import update_resource
from services.geodata.prepare import prepare


def prepare_job(resource_id, request):
    try:
        manifest=prepare(request,lambda stage:update_resource(resource_id,"running",stage=stage))
        update_resource(resource_id,"completed",bundle_id=manifest["bundle_id"],stage="ready")
    except Exception as exc:
        # A provider failure cannot publish a ready bundle. Keep compact evidence.
        update_resource(resource_id,"failed",error=str(exc)[:600],error_type=type(exc).__name__)
        raise
