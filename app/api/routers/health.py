from fastapi import APIRouter
from app.core.metrics import snapshot
from app.schemas.common import MetricsOut, AckOut


router = APIRouter()


@router.get("/healthz", response_model=AckOut)
async def healthz() -> AckOut:
    return AckOut(ok=True)


@router.get("/metrics", response_model=MetricsOut)
async def metrics() -> MetricsOut:
    data = snapshot()
    return MetricsOut(**data)
