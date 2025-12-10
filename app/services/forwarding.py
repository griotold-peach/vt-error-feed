from __future__ import annotations

import logging

from app.domain.rules import FORWARD_FAILURE_REASONS, SPECIAL_FORWARD_KEYWORDS
from app.domain.events import VTErrorEvent

logger = logging.getLogger(__name__)


def should_forward(event: VTErrorEvent) -> bool:
    """
    VTErrorEvent 가 일반 에러 피드로 포워딩되어야 하는지 여부.
    """
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
