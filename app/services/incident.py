from __future__ import annotations

import logging
from typing import Any, Dict

from app.domain.anomaly import IncidentType, record_event
from app.adapters.teams_notifier import TeamsNotifier
from app.domain.events import VTErrorEvent

logger = logging.getLogger(__name__)

_notifier = TeamsNotifier()

def classify_incident_from_vt(event: VTErrorEvent) -> IncidentType | None:
    """
    VTErrorEvent 의 failure_reason 을 보고 장애 유형으로 매핑한다.
    """
    if event.failure_reason == "TIMEOUT":
        return IncidentType.TIMEOUT
    if event.failure_reason == "API_ERROR":
        return IncidentType.API_ERROR
    return None


async def handle_incident(event: VTErrorEvent, raw_payload: Dict[str, Any]) -> None:
    """
    장애 감지 및 incident 채널 포스팅을 담당한다.
    """
    incident_type = classify_incident_from_vt(event)
    if incident_type is None:
        return

    ts = event.event_datetime()
    is_incident = record_event(incident_type, ts)
    if not is_incident:
        return

    await _notifier.send_to_incident_channel(raw_payload)
    logger.info(
        "Sent incident alert to incident channel. type=%s, project=%s",
        incident_type.name,
        event.project,
    )
