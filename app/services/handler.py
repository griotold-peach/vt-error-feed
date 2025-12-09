from .notifier import post_to_teams


async def handle_raw_alert(payload: dict) -> None:
    """
    dubbing API 서버가 기존에 Teams로 보내던 JSON payload를
    그대로 받아서 VT Error Feed Dev 채널로 보내는 1차 버전.
    """
    # 나중에 여기서 filters.py 로 분기 태워서
    #   - 그냥 피드 채널로만 가는 알림
    #   - 장애 채널까지 가는 알림
    # 이런 식으로 나눌 예정.
    await post_to_teams(payload)
