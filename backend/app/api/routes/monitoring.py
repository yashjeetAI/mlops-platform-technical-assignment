"""Monitoring overview route."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.monitoring import MonitoringOverview
from app.services import metric_service

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("", response_model=MonitoringOverview)
def monitoring_overview(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, description="Search model name/key"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = metric_service.list_monitoring(db, limit=limit, offset=offset, q=q)
    return MonitoringOverview(items=items, total=total, limit=limit, offset=offset)
