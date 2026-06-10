from typing import Annotated
from fastapi import APIRouter, Depends

from app.api.deps import AgentUser, get_analytics_service
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(_: AgentUser, svc: Annotated[AnalyticsService, Depends(get_analytics_service)]):
    return svc.summary()
