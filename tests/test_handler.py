# tests/test_handler.py
import pytest
from typing import Dict, Any, List

from app.application.services.handler import AlertHandler
from app.application.services.incident import IncidentService
from app.adapters.messagecard import VTWebhookMessage
from app.domain.events import VTErrorEvent


class FakeNotifier:
    """테스트용 Fake Notifier"""
    
    def __init__(self):
        self.forward_calls: List[Dict[str, Any]] = []
        self.incident_calls: List[Dict[str, Any]] = []
    
    async def send_to_forward_channel(self, card: Dict[str, Any]) -> bool:
        self.forward_calls.append(card)
        return True
    
    async def send_to_incident_channel(self, card: Dict[str, Any]) -> bool:
        self.incident_calls.append(card)
        return True


@pytest.fixture
def fake_notifier():
    """Fake Notifier 픽스처"""
    return FakeNotifier()


@pytest.fixture
def incident_service(fake_notifier):
    """IncidentService 픽스처"""
    return IncidentService(fake_notifier)


@pytest.fixture
def alert_handler(fake_notifier, incident_service):
    """AlertHandler 픽스처 (의존성 주입)"""
    return AlertHandler(fake_notifier, incident_service)


# --- 테스트들 ---------------------------------------------------------------

@pytest.mark.anyio
async def test_apf_forwarded_no_incident(alert_handler, fake_notifier):
    """APF 에러는 포워딩되지만 장애 아님"""
    payload = {
        "title": "🚨 Error",
        "sections": [{
            "facts": [
                {"name": "Error Detail", "value": "Failure Reason: AUDIO_PIPELINE_FAILED"}
            ]
        }]
    }
    
    result = await alert_handler.handle_raw_alert(payload)
    
    assert result is True
    assert len(fake_notifier.forward_calls) == 1


@pytest.mark.anyio
async def test_engine_error_dropped(alert_handler, fake_notifier):
    """ENGINE_ERROR는 드롭됨"""
    payload = {
        "title": "🚨 Error",
        "sections": [{
            "facts": [
                {"name": "Error Detail", "value": "Failure Reason: ENGINE_ERROR"}
            ]
        }]
    }
    
    result = await alert_handler.handle_raw_alert(payload)
    
    assert result is False
    assert len(fake_notifier.forward_calls) == 0


@pytest.mark.anyio
async def test_video_queue_full_forwarded_no_incident(alert_handler, fake_notifier):
    """VIDEO_QUEUE_FULL은 포워딩됨"""
    payload = {
        "title": "🚨 Error",
        "sections": [{
            "facts": [
                {"name": "Error Detail", "value": "Invalid FailureReason value: VIDEO_QUEUE_FULL"}
            ]
        }]
    }
    
    result = await alert_handler.handle_raw_alert(payload)
    
    assert result is True
    assert len(fake_notifier.forward_calls) == 1


@pytest.mark.anyio
async def test_timeout_incident_after_three_events(alert_handler, fake_notifier):
    """TIMEOUT 3번 발생 시 장애"""
    from datetime import datetime, timedelta, timezone
    
    for i in range(3):
        time_value = (datetime.now(timezone.utc) + timedelta(minutes=i*10)).isoformat()
        
        payload = {
            "title": "🚨 Error",
            "sections": [{
                "facts": [
                    {"name": "Error Detail", "value": "Failure Reason: TIMEOUT"},
                    {"name": "Time", "value": time_value}
                ]
            }]
        }
        
        result = await alert_handler.handle_raw_alert(payload)
        assert result is True
    
    # forward는 3번 호출
    assert len(fake_notifier.forward_calls) == 3
    
    # incident는 임계치 도달 시 1번 호출
    assert len(fake_notifier.incident_calls) == 1