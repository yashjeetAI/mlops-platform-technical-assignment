"""Monitoring response schemas (camelCase JSON via CamelModel)."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import Environment, MonitoringStatus
from app.schemas.base import CamelModel


class MetricPoint(CamelModel):
    timestamp: datetime
    version: str
    environment: Environment
    latency_ms: float
    throughput_rpm: float
    error_rate: float
    quality_score: float
    drift_score: float
    availability: float


class MonitoringSummary(CamelModel):
    model_id: UUID
    model_key: str
    name: str
    monitoring_status: MonitoringStatus
    last_inference_at: datetime | None
    latest: MetricPoint | None
    series: list[MetricPoint] = Field(default_factory=list)


class MonitoringOverviewItem(CamelModel):
    model_id: UUID
    model_key: str
    name: str
    monitoring_status: MonitoringStatus
    last_inference_at: datetime | None
    latest: MetricPoint | None


class MonitoringOverview(CamelModel):
    items: list[MonitoringOverviewItem] = Field(default_factory=list)
