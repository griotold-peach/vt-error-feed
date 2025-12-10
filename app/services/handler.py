# app/services/handler.py
from __future__ import annotations

from typing import Any, Dict
import logging

from pydantic import ValidationError

from .notifier import post_to_teams
from .schemas import VTWebhookMessage, VTErrorEvent

logger = logging.getLogger(__name__)

FORWARD_FAILURE_REASONS = {
    "AUDIO_PIPELINE_FAILED",
    "VIDEO_PIPELINE_FAILED",
    "TIMEOUT",
    "API_ERROR",
}

SPECIAL_FORWARD_KEYWORDS = (
    "VIDEO_QUEUE_FULL",
    "VT5001",
)


def should_forward(event: VTErrorEvent) -> bool:
    if event.failure_reason in FORWARD_FAILURE_REASONS:
        logger.info(
            "Forwarding VT alert (failure_reason=%s, project=%s)",
            event.failure_reason,
            event.project,
        )
        return True

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


async def handle_raw_alert(payload: Dict[str, Any]) -> bool:
    """
    payload 를 받아서 필터링 후, 필요하면 Teams 로 포워딩한다.
    반환값: True 면 포워딩함, False 면 드롭됨.
    """
    try:
        msg = VTWebhookMessage.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Invalid VT webhook payload: %s", exc)
        return False

    event = VTErrorEvent.from_message(msg)

    if not should_forward(event):
        # 포워딩 대상 아님
        return False

    await post_to_teams(payload)
    return True
