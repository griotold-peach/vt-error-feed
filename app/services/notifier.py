# app/services/notifier.py
from __future__ import annotations

from typing import Dict, Any
import logging

import httpx

from .config import TEAMS_WEBHOOK_URL

logger = logging.getLogger(__name__)


async def post_to_teams(card: Dict[str, Any]) -> None:
    """
    필터 서버에서 최종으로 Teams 채널로 보내는 함수.
    card: Teams Incoming Webhook용 MessageCard JSON (원본 그대로 or 변형된 것).
    """
    if not TEAMS_WEBHOOK_URL:
        logger.error("TEAMS_WEBHOOK_URL is not configured. Skip sending to Teams.")
        return

    # NOTE: verify=False 는 회사 내부망 / 프록시 환경 때문에 넣어둔 것으로 보임.
    # 가능하면 나중에 인증서 세팅 완료 후 verify=True 로 변경하는 것이 좋다.
    async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
        try:
            resp = await client.post(TEAMS_WEBHOOK_URL, json=card)
        except httpx.RequestError as exc:
            logger.error("Error while sending message to Teams: %s", exc)
            return

    if resp.is_error:
        # 1차 버전은 logger 로만 확인하고, 필요하면 알림/재시도 로직 추가
        logger.error(
            "[Teams notify error] status=%s, body=%s",
            resp.status_code,
            resp.text[:200],
        )
        # 필요하면 여기서 예외를 다시 던질 수도 있음
        # resp.raise_for_status()
    else:
        logger.info("Message successfully posted to Teams.")
