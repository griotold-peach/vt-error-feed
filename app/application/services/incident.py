# app/application/services/incident.py
from __future__ import annotations

from typing import Any, Dict

from app.application.ports.notifier import Notifier
from app.domain.events import VTErrorEvent
from app.domain.anomaly import record_event
from app.domain.incident_type import IncidentType


class IncidentService:
    """
    장애 처리 서비스
    
    책임:
    - 장애 발생 여부 판단
    - 장애 알림 전송
    """
    
    def __init__(self, notifier: Notifier):
        """
        Args:
            notifier: 알림 전송 구현체
        """
        self.notifier = notifier
    
    async def handle_incident(self, event: VTErrorEvent, raw_payload: Dict[str, Any]) -> None:
        """
        장애 기준 체크 및 알림 전송
        
        Args:
            event: VT 에러 이벤트
            raw_payload: 원본 payload (Teams 전송용)
        """
        if self._should_trigger_incident(event):
            await self.notifier.send_to_incident_channel(raw_payload)
    
    def _should_trigger_incident(self, event: VTErrorEvent) -> bool:
        """
        장애 발생 여부 판단
        
        Args:
            event: VT 에러 이벤트
            
        Returns:
            장애 발생 여부
        """
        incident_type = event.to_incident_type()

        # event의 incident_type과 timestamp를 사용하여 장애 판단
        if incident_type is None:
            return False
        
        return record_event(incident_type, event.event_datetime())