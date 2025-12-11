# app/services/monitoring.py
from __future__ import annotations

from typing import Any, Dict
import logging

from pydantic import ValidationError

from app.adapters.messagecard import VTWebhookMessage
from app.domain.events import MonitoringEvent
from app.domain.anomaly import IncidentType, record_event
from app.infrastructure.notifier import post_to_incident_channel

logger = logging.getLogger(__name__)


def _classify_incident_type(event: MonitoringEvent) -> IncidentType | None:
    """
    MonitoringEvent의 title/description을 기반으로 IncidentType 매핑.
    """
    text = f"{event.title} | {event.description}"
    
    # Live API DB 부하: 더빙/오디오 생성 실패
    if "영상 생성 실패" in text and "더빙/오디오 생성 실패" in text:
        return IncidentType.LIVE_API_DB_OVERLOAD
    
    # YouTube URL 다운로드 실패
    if "외부 URL 다운로드 실패" in text or "YouTube URL 다운로드 실패" in text:
        return IncidentType.YT_DOWNLOAD_FAIL
    
    # Video 파일 업로드 실패
    if "Video 파일 업로드 실패" in text:
        return IncidentType.YT_EXTERNAL_FAIL
    
    return None


async def handle_monitoring_alert(payload: Dict[str, Any]) -> bool:
    """
    Feed2 모니터링 이벤트 처리.
    
    1) VTWebhookMessage로 파싱
    2) MonitoringEvent로 변환
    3) IncidentType 분류
    4) anomaly.record_event()로 장애 기준 체크
    5) 기준 충족 시 원본 payload를 incident 채널로 전송
    
    Returns:
        True: incident 트리거되어 장애 채널로 전송됨
        False: 기준 미달 또는 매핑 안 됨
    """
    # 1) MessageCard 파싱
    try:
        msg = VTWebhookMessage.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Invalid monitoring payload: %s", exc)
        return False
    
    # 2) 도메인 모델로 변환
    event = MonitoringEvent.from_message(msg)
    
    # 3) IncidentType 분류
    incident_type = _classify_incident_type(event)
    if incident_type is None:
        logger.info(
            "Monitoring event not mapped to incident type: title=%s",
            event.title,
        )
        return False
    
    # 4) 장애 기준 체크
    ts = event.event_datetime()
    is_incident = record_event(incident_type, ts)
    
    if not is_incident:
        logger.info(
            "Monitoring event recorded but no incident yet: type=%s, time=%s",
            incident_type.name,
            ts.isoformat(),
        )
        return False
    
    # 5) 장애 채널로 원본 payload 전송
    await post_to_incident_channel(payload)
    logger.info(
        "Monitoring incident triggered: type=%s, time=%s",
        incident_type.name,
        ts.isoformat(),
    )
    
    return True