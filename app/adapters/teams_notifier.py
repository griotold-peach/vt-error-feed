# app/adapters/teams_notifier.py
"""
Teams Webhook 알림 전송 어댑터
"""
from typing import Dict, Any
import httpx

from app.config import TEAMS_FORWARD_WEBHOOK_URL, TEAMS_INCIDENT_WEBHOOK_URL


class TeamsNotifier:
    """Teams Webhook으로 MessageCard 전송"""
    
    def __init__(self, timeout: float = 5.0, verify_ssl: bool = False):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
    
    async def send_to_forward_channel(self, card: Dict[str, Any]) -> bool:
        """
        일반 에러/모니터링 채널로 전송
        
        Args:
            card: MessageCard 딕셔너리
            
        Returns:
            전송 성공 여부
        """
        return await self._post_to_teams(
            TEAMS_FORWARD_WEBHOOK_URL,
            card,
            "Teams forward"
        )
    
    async def send_to_incident_channel(self, card: Dict[str, Any]) -> bool:
        """
        장애 알림 채널로 전송
        
        Args:
            card: MessageCard 딕셔너리
            
        Returns:
            전송 성공 여부
        """
        return await self._post_to_teams(
            TEAMS_INCIDENT_WEBHOOK_URL,
            card,
            "Teams incident"
        )
    
    async def _post_to_teams(
        self,
        webhook_url: str,
        card: Dict[str, Any],
        log_prefix: str
    ) -> bool:
        """
        Teams Webhook으로 MessageCard 전송
        
        Args:
            webhook_url: Teams Incoming Webhook URL
            card: MessageCard 딕셔너리
            log_prefix: 로그 접두사
            
        Returns:
            전송 성공 여부
        """
        if not webhook_url:
            print(f"❌ {log_prefix} webhook url is not configured. Skip sending.")
            return False
        
        async with httpx.AsyncClient(
            timeout=self.timeout,
            verify=self.verify_ssl
        ) as client:
            try:
                resp = await client.post(webhook_url, json=card)
                
                if resp.is_error:
                    print(
                        f"❌ {log_prefix} response error. "
                        f"status={resp.status_code} body={resp.text[:200]}"
                    )
                    return False
                
                print(f"✅ {log_prefix} message successfully posted to Teams.")
                return True
                
            except httpx.RequestError as exc:
                print(f"❌ {log_prefix} request error: {exc}")
                return False


# 하위 호환성을 위한 모듈 레벨 인스턴스 (임시)
_default_notifier = TeamsNotifier()


async def post_to_forward_channel(card: Dict[str, Any]) -> None:
    """
    [DEPRECATED] 하위 호환성을 위한 함수
    새 코드에서는 TeamsNotifier 클래스를 직접 사용하세요.
    """
    await _default_notifier.send_to_forward_channel(card)


async def post_to_incident_channel(card: Dict[str, Any]) -> None:
    """
    [DEPRECATED] 하위 호환성을 위한 함수
    새 코드에서는 TeamsNotifier 클래스를 직접 사용하세요.
    """
    await _default_notifier.send_to_incident_channel(card)