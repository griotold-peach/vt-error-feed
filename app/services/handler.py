from __future__ import annotations

from typing import Any, Dict
import logging

from pydantic import ValidationError

from .notifier import post_to_forward_channel, post_to_incident_channel
from .schemas import VTWebhookMessage, VTErrorEvent
from .anomaly import IncidentType, record_event

logger = logging.getLogger(__name__)

# 일반 에러 피드 필터링 (개선사항 1) 용 상수들
FORWARD_FAILURE_REASONS = {
    "AUDIO_PIPELINE_FAILED",
    "VIDEO_PIPELINE_FAILED",
    "TIMEOUT",
    "API_ERROR",
}

# Failure Reason 이 없어도, 메시지 내용에 이 키워드가 들어가면 포워딩
# (VT5001 / VIDEO_QUEUE_FULL 케이스)
SPECIAL_FORWARD_KEYWORDS = (
    "VIDEO_QUEUE_FULL",
    "VT5001",
)


def should_forward(event: VTErrorEvent) -> bool:
    """
    VTErrorEvent 가 일반 에러 피드로 포워딩되어야 하는지 여부.
    (개선사항 1)
    """
    # 1) Failure Reason whitelist
    if event.failure_reason in FORWARD_FAILURE_REASONS:
        logger.info(
            "Forwarding VT alert (failure_reason=%s, project=%s)",
            event.failure_reason,
            event.project,
        )
        return True

    # 2) VT5001 / VIDEO_QUEUE_FULL 등 특수 케이스
    blob = " ".join(
        [
            event.error_message or "",
            event.error_detail or "",
            event.cause_or_stack_trace or "",
        ]
    )
    if any(keyword in blob for keyword in SPECIAL_FORWARD_KEYWORDS):
        logger.info(
            "Forwarding VT alert (special keyword matched, project=%s)",
            event.project,
        )
        return True

    logger.info(
        "Dropping VT alert (failure_reason=%s, project=%s)",
        event.failure_reason,
        event.project,
    )
    return False


def classify_incident_from_vt(event: VTErrorEvent) -> IncidentType | None:
    """
    VTErrorEvent 의 failure_reason 을 보고 장애 유형으로 매핑.
    (개선사항 2 – Feed1 기준 TIMEOUT / API_ERROR)
    """
    if event.failure_reason == "TIMEOUT":
        return IncidentType.TIMEOUT
    if event.failure_reason == "API_ERROR":
        return IncidentType.API_ERROR
    return None


async def handle_raw_alert(payload: Dict[str, Any]) -> bool:
    """
    dubbing API 서버가 기존에 Teams로 보내던 JSON payload를 받아서

      1) 일반 에러 피드 채널로 보낼지 여부 판단 (개선사항 1)
      2) 장애 기준 충족 시 장애 채널로도 알림 보내기 (개선사항 2)

    까지 수행한다.

    반환값:
      True  -> forward 채널로 포워딩함
      False -> forward 채널로는 포워딩하지 않음
    """
    try:
        msg = VTWebhookMessage.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Invalid VT webhook payload: %s", exc)
        return False

    event = VTErrorEvent.from_message(msg)

    # ------ (1) 일반 에러 피드 포워딩 (개선사항 1) ------
    forwarded = False
    if should_forward(event):
        await post_to_forward_channel(payload)
        forwarded = True

    # ------ (2) 장애 기준 체크 (개선사항 2) ------
    incident_type = classify_incident_from_vt(event)
    if incident_type is not None:
        ts = event.event_datetime()
        is_incident = record_event(incident_type, ts)
        if is_incident:
            # TODO: 필요하면 여기서 멘션(@고은님 등) 추가해서 카드 변형 후 전송
            await post_to_incident_channel(payload)
            logger.info(
                "Sent incident alert to incident channel. type=%s, project=%s",
                incident_type.name,
                event.project,
            )

    return forwarded
