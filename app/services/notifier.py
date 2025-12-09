import httpx

from .config import TEAMS_WEBHOOK_URL


async def post_to_teams(card: dict) -> None:
    """
    필터 서버에서 최종으로 Teams 채널로 보내는 함수.
    card: Teams Incoming Webhook용 MessageCard JSON.
    """
    async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
        resp = await client.post(TEAMS_WEBHOOK_URL, json=card)

    if resp.is_error:
        # 1차 버전은 그냥 print 로만 보고, 나중에 logger 붙이면 됨
        print(
            f"[Teams notify error] status={resp.status_code}, body={resp.text[:200]}"
        )
        resp.raise_for_status()
