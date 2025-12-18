# app/application/ports/notifier.py
"""
알림 전송 포트 (인터페이스)

Secondary Port: 애플리케이션이 외부 알림 시스템을 사용하기 위한 인터페이스
required Port
"""
from typing import Protocol, Dict, Any


class Notifier(Protocol):
    """
    알림 전송 인터페이스
    
    이 Protocol을 구현하는 어댑터:
    - TeamsNotifier (adapters/teams_notifier.py)
    - SlackNotifier (미래 확장)
    
    Protocol을 사용하는 서비스:
    - handler.py (Feed1 raw alert 처리)
    - monitoring.py (Feed2 monitoring alert 처리)
    - incident.py (장애 알림 전송)
    """
    
    async def send_to_forward_channel(self, card: Dict[str, Any]) -> bool:
        """
        일반 에러/모니터링 채널로 메시지 전송
        
        Args:
            card: MessageCard 형식의 딕셔너리
            
        Returns:
            전송 성공 여부
        """
        ...
    
    async def send_to_incident_channel(self, card: Dict[str, Any]) -> bool:
        """
        장애 알림 채널로 메시지 전송
        
        Args:
            card: MessageCard 형식의 딕셔너리
            
        Returns:
            전송 성공 여부
        """
        ...