"""Monitoring overview route."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.monitoring import MonitoringOverview
from app.services import metric_service

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("", response_model=MonitoringOverview)
def monitoring_overview(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return MonitoringOverview(items=metric_service.list_monitoring(db))
