"""
Teams webhook notifier helpers.

Public API: `post_to_forward_channel(card: Dict[str, Any])` and
`post_to_incident_channel(card: Dict[str, Any])`.
`_post_to_teams` is intentionally kept internal as the shared HTTP implementation detail.
"""
from __future__ import annotations

from typing import Any, Dict
import logging

import httpx

from app.config import TEAMS_FORWARD_WEBHOOK_URL, TEAMS_INCIDENT_WEBHOOK_URL

logger = logging.getLogger(__name__)


async def _post_to_teams(webhook_url: str, card: Dict[str, Any], log_prefix: str) -> None:
    """
    내부 공용 함수: 주어진 webhook_url 로 MessageCard 를 전송한다.
    """
    if not webhook_url:
        logger.error("%s webhook url is not configured. Skip sending.", log_prefix)
        return

    # NOTE: verify=False because Teams webhook endpoints in some internal/staging environments
    # use self-signed certificates.
    # TODO: Allow configuring TLS verification based on environment settings.
    async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
        try:
            resp = await client.post(webhook_url, json=card)
        except httpx.RequestError as exc:
            logger.error("%s request error: %s", log_prefix, exc)
            return

    if resp.is_error:
        logger.error(
            "%s response error. status=%s body=%s",
            log_prefix,
            resp.status_code,
            resp.text[:200],  # keep logs short to avoid dumping entire payload
        )
    else:
        logger.info("%s message successfully posted to Teams.", log_prefix)


async def post_to_forward_channel(card: Dict[str, Any]) -> None:
    """
    일반 에러/모니터링 채널로 보내는 함수.
    (개선사항 1에서 사용)
    """
    await _post_to_teams(
        TEAMS_FORWARD_WEBHOOK_URL,
        card,
        log_prefix="Teams forward",
    )


async def post_to_incident_channel(card: Dict[str, Any]) -> None:
    """
    장애 알림 채널로 보내는 함수.
    (개선사항 2에서 사용)
    """
    await _post_to_teams(
        TEAMS_INCIDENT_WEBHOOK_URL,
        card,
        log_prefix="Teams incident",
    )

# TODO: If we ever need standalone notifier unit tests, consider injecting an httpx.AsyncClient
# (or transport) dependency so fake clients can be passed in without monkeypatching.
