# app/domain/incident_config.py
from datetime import timedelta
from dataclasses import dataclass
from app.domain.incident_type import IncidentType


@dataclass(frozen=True)
class IncidentThreshold:
    window: timedelta | None      # 슬라이딩 윈도우 (None이면 동일 분 기준만)
    count: int                    # threshold 건수
    same_minute_count: int | None # 동일 분 기준 (None이면 사용 안 함)
    cooldown: timedelta           # 쿨다운


INCIDENT_THRESHOLDS: dict[IncidentType, IncidentThreshold] = {
    IncidentType.TIMEOUT: IncidentThreshold(
        window=timedelta(hours=1),
        count=3,
        same_minute_count=None,
        cooldown=timedelta(minutes=10),
    ),
    IncidentType.API_ERROR: IncidentThreshold(
        window=timedelta(minutes=5),
        count=5,
        same_minute_count=3,
        cooldown=timedelta(minutes=5),
    ),
    IncidentType.LIVE_API_DB_OVERLOAD: IncidentThreshold(
        window=None,
        count=0,
        same_minute_count=3,
        cooldown=timedelta(minutes=5),
    ),
    IncidentType.YT_DOWNLOAD_FAIL: IncidentThreshold(
        window=timedelta(minutes=30),
        count=3,
        same_minute_count=None,
        cooldown=timedelta(minutes=10),
    ),
    IncidentType.YT_EXTERNAL_FAIL: IncidentThreshold(
        window=timedelta(minutes=30),
        count=3,
        same_minute_count=None,
        cooldown=timedelta(minutes=10),
    ),
}