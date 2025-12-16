"""
Bot Framework Activity 객체를 내부 모델로 변환
"""
from typing import Dict, Any, Optional
import os


def parse_bot_activity(activity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Bot Framework Activity를 파싱하여 우리 형식으로 변환
    
    Activity 구조:
    {
        "type": "message",
        "text": "메시지 내용",
        "channelData": {
            "channel": {"id": "채널ID"},
            "team": {"id": "팀ID"}
        },
        "from": {"id": "발신자ID"},
        ...
    }
    """
    if activity.get("type") != "message":
        return None
    
    text = activity.get("text", "")
    channel_data = activity.get("channelData", {})
    channel_id = channel_data.get("channel", {}).get("id", "")
    
    # Teams 메시지를 우리 형식으로 변환
    return {
        "text": text,
        "channel_id": channel_id,
        "activity": activity  # 원본도 보관 (필요시 사용)
    }


def get_channel_type(channel_id: str) -> Optional[str]:
    """
    채널 ID로 Feed1/Feed2 구분
    
    실제 채널 ID는 Teams에서 봇 설치 후 확인 가능
    지금은 환경변수로 관리
    """
    feed1_channel_id = os.getenv("TEAMS_FEED1_CHANNEL_ID", "")
    feed2_channel_id = os.getenv("TEAMS_FEED2_CHANNEL_ID", "")
    
    if channel_id == feed1_channel_id:
        return "feed1"
    elif channel_id == feed2_channel_id:
        return "feed2"
    
    return None