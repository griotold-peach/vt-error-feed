from __future__ import annotations

from typing import Any, Dict
import logging

from pydantic import ValidationError

from app.infrastructure.notifier import post_to_forward_channel
from app.adapters.messagecard import VTWebhookMessage
from app.domain.events import VTErrorEvent
from .forwarding import should_forward
from .incident import handle_incident

logger = logging.getLogger(__name__)


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
    await handle_incident(event, payload)

    return forwarded
