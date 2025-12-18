# app/domain/events.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import re

from pydantic import BaseModel

from app.adapters.messagecard import VTWebhookMessage
from app.domain.incident_type import IncidentType


def _parse_event_datetime(raw: str | None) -> datetime:
    """
    이벤트 시각 문자열을 UTC datetime으로 파싱한다.
    
    예상 포맷: "2025-12-09T20:10:51.796441041Z[Etc/UTC]"
    파싱 실패 시 현재 시각(UTC)으로 fallback.
    """
    if not raw:
        return datetime.now(timezone.utc)
    
    try:
        before_z = raw.split("Z", 1)[0]
        if "." in before_z:
            date_part, frac = before_z.split(".", 1)
            frac = (frac + "000000")[:6]
            trimmed = f"{date_part}.{frac}"
        else:
            trimmed = before_z
        
        # ✅ timezone 추가!
        dt = datetime.fromisoformat(trimmed)
        
        # ✅ naive datetime이면 UTC로 변환
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt
    except Exception:
        return datetime.now(timezone.utc)


class VTErrorEvent(BaseModel):
    """
    Feed1 (live-api) 도메인 모델.
    """

    project: str
    error_message: str
    error_detail: str
    time: str

    failure_reason: Optional[str] = None
    cause_or_stack_trace: Optional[str] = None

    @classmethod
    def from_message(cls, msg: VTWebhookMessage) -> "VTErrorEvent":
        project = msg.get_fact("Project") or ""
        error_message = msg.get_fact("Error Message") or ""
        error_detail = msg.get_fact("Error Detail") or ""
        time = msg.get_fact("Time") or ""
        cause = msg.get_fact("Cause or Stack Trace") or ""

        failure_reason = None
        if error_detail:
            m = re.search(r"Failure Reason:\s*([A-Z0-9_]+)", error_detail)
            if m:
                failure_reason = m.group(1)

        return cls(
            project=project,
            error_message=error_message,
            error_detail=error_detail,
            time=time,
            failure_reason=failure_reason,
            cause_or_stack_trace=cause,
        )

    def event_datetime(self) -> datetime:
        return _parse_event_datetime(self.time)
    
    # ✅ 이렇게 추가!
    def to_incident_type(self) -> Optional[IncidentType]:
        """이 이벤트에 해당하는 IncidentType 반환"""
        from app.domain.incident_type import IncidentType
        
        if self.failure_reason == "TIMEOUT":
            return IncidentType.TIMEOUT
        elif self.failure_reason == "API_ERROR":
            return IncidentType.API_ERROR
        
        return None


class MonitoringEvent(BaseModel):
    """
    Feed2 (VT 실시간 모니터링) 도메인 모델.
    """
    
    title: str
    description: str
    time: str
    
    @classmethod
    def from_message(cls, msg: VTWebhookMessage) -> "MonitoringEvent":
        title = msg.title or ""
        description = msg.get_fact("Description") or ""
        time = msg.get_fact("Time") or ""
        
        return cls(
            title=title,
            description=description,
            time=time,
        )
    
    def event_datetime(self) -> datetime:
        return _parse_event_datetime(self.time)
    
    # ✅ 이것도 추가!
    def to_incident_type(self) -> Optional[IncidentType]:
        """이 이벤트에 해당하는 IncidentType 반환"""
        from app.domain.incident_type import IncidentType
        
        description = self.description.lower()
        
        if "더빙/오디오 생성 실패" in description:
            return IncidentType.LIVE_API_DB_OVERLOAD
        elif "youtube url 다운로드 실패" in description:
            return IncidentType.YT_DOWNLOAD_FAIL
        elif "외부 url 다운로드 실패" in description or "video 파일 업로드 실패" in description:
            return IncidentType.YT_EXTERNAL_FAIL
        
        return None