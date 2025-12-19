# app/application/services/monitoring.py
from __future__ import annotations

from typing import Any, Dict
import logging

from pydantic import ValidationError

from app.application.ports.notifier import Notifier
from app.adapters.messagecard import VTWebhookMessage
from app.domain.events import VTErrorEvent
from app.domain.anomaly import record_event

logger = logging.getLogger(__name__)


class MonitoringHandler:
    """
    Feed2 Monitoring Alert 처리 서비스
    
    책임:
    - VT monitoring payload 검증 및 파싱
    - 장애 여부 판단
    - 장애 알림 전송
    """
    
    def __init__(self, notifier: Notifier):
        """
        Args:
            notifier: 알림 전송 구현체
        """
        self.notifier = notifier
    
    async def handle_monitoring_alert(self, payload: Dict[str, Any]) -> bool:
        try:
            msg = VTWebhookMessage.model_validate(payload)
        except ValidationError as exc:
            logger.warning(f"⚠️ Invalid VT monitoring payload: {exc}")
            return False
        
        # ✅ MonitoringEvent로 변환
        from app.domain.events import MonitoringEvent
        from app.domain.anomaly import record_event
        
        event = MonitoringEvent.from_message(msg)
        
        # ✅ 이벤트 자체가 변환 담당
        incident_type = event.to_incident_type()
        
        if incident_type is not None:
            if record_event(incident_type, event.event_datetime()):
                await self.notifier.send_to_incident_channel(payload)
                return True
        
        return False

