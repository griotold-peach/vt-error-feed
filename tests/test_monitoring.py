# tests/test_monitoring.py
import pytest
from typing import Dict, Any, List

from app.application.services.monitoring import MonitoringHandler
from app.adapters.messagecard import VTWebhookMessage


class FakeNotifier:
    """테스트용 Fake Notifier"""
    
    def __init__(self):
        self.incident_calls: List[Dict[str, Any]] = []
    
    async def send_to_incident_channel(self, card: Dict[str, Any]) -> bool:
        self.incident_calls.append(card)
        return True


@pytest.fixture
def fake_notifier():
    """Fake Notifier 픽스처"""
    return FakeNotifier()


@pytest.fixture
def monitoring_handler(fake_notifier):
    """MonitoringHandler 픽스처 (의존성 주입)"""
    return MonitoringHandler(fake_notifier)


# --- 테스트들 ---------------------------------------------------------------

@pytest.mark.anyio
async def test_db_overload_no_incident_under_threshold(monitoring_handler, fake_notifier):
    """DB 과부하 임계값 미만"""
    payload = {
        "title": "VT 실시간 모니터링",
        "sections": [{
            "facts": [
                {"name": "Description", "value": "영상 생성 실패 - 더빙/오디오 생성 실패"}
            ]
        }]
    }
    
    result = await monitoring_handler.handle_monitoring_alert(payload)
    
    # 첫 이벤트는 임계값 미만
    assert result is False
    assert len(fake_notifier.incident_calls) == 0


@pytest.mark.anyio
async def test_db_overload_incident_at_threshold(monitoring_handler, fake_notifier):
    """DB 과부하 임계값 도달 시 장애"""
    from datetime import datetime, timezone
    
    # DB_OVERLOAD 임계값까지 이벤트 발생시키기
    # INCIDENT_THRESHOLDS 설정에 따라 조정 필요
    payload = {
        "title": "VT 실시간 모니터링",
        "sections": [{
            "facts": [
                {"name": "Description", "value": "영상 생성 실패 - 더빙/오디오 생성 실패"},
                {"name": "Time", "value": datetime.now(timezone.utc).isoformat()}
            ]
        }]
    }
    
    # 여러 번 호출하여 임계값 도달 시뮬레이션
    # 실제 임계값에 맞게 조정 필요
    for _ in range(10):
        await monitoring_handler.handle_monitoring_alert(payload)
    
    # 최소 1번은 호출되어야 함
    assert len(fake_notifier.incident_calls) >= 1


@pytest.mark.anyio
async def test_yt_download_no_incident_under_threshold(monitoring_handler, fake_notifier):
    """YouTube 다운로드 실패 임계값 미만"""
    payload = {
        "title": "VT 실시간 모니터링",
        "sections": [{
            "facts": [
                {"name": "Description", "value": "영상 업로드 실패 - YouTube URL 다운로드 실패"}
            ]
        }]
    }
    
    result = await monitoring_handler.handle_monitoring_alert(payload)
    
    assert result is False
    assert len(fake_notifier.incident_calls) == 0


@pytest.mark.anyio
async def test_yt_download_incident_at_threshold(monitoring_handler, fake_notifier):
    """YouTube 다운로드 실패 임계값 도달"""
    from datetime import datetime, timezone
    
    payload = {
        "title": "VT 실시간 모니터링",
        "sections": [{
            "facts": [
                {"name": "Description", "value": "영상 업로드 실패 - YouTube URL 다운로드 실패"},
                {"name": "Time", "value": datetime.now(timezone.utc).isoformat()}
            ]
        }]
    }
    
    # 임계값까지 이벤트 발생
    for _ in range(10):
        await monitoring_handler.handle_monitoring_alert(payload)
    
    assert len(fake_notifier.incident_calls) >= 1


@pytest.mark.anyio
async def test_yt_external_no_incident_under_threshold(monitoring_handler, fake_notifier):
    """외부 URL 다운로드 실패 임계값 미만"""
    payload = {
        "title": "VT 실시간 모니터링",
        "sections": [{
            "facts": [
                {"name": "Description", "value": "영상 업로드 실패 - 외부 URL 다운로드 실패"}
            ]
        }]
    }
    
    result = await monitoring_handler.handle_monitoring_alert(payload)
    
    assert result is False


@pytest.mark.anyio
async def test_yt_external_incident_at_threshold(monitoring_handler, fake_notifier):
    """외부 URL 다운로드 실패 임계값 도달"""
    from datetime import datetime, timezone
    
    payload = {
        "title": "VT 실시간 모니터링",
        "sections": [{
            "facts": [
                {"name": "Description", "value": "영상 업로드 실패 - 외부 URL 다운로드 실패"},
                {"name": "Time", "value": datetime.now(timezone.utc).isoformat()}
            ]
        }]
    }
    
    for _ in range(10):
        await monitoring_handler.handle_monitoring_alert(payload)
    
    assert len(fake_notifier.incident_calls) >= 1


@pytest.mark.anyio
async def test_unknown_event_not_mapped(monitoring_handler, fake_notifier):
    """알 수 없는 이벤트는 매핑되지 않음"""
    payload = {
        "title": "VT 실시간 모니터링",
        "sections": [{
            "facts": [
                {"name": "Description", "value": "알 수 없는 에러"}
            ]
        }]
    }
    
    result = await monitoring_handler.handle_monitoring_alert(payload)
    
    # 알 수 없는 이벤트는 처리되지 않음
    assert result is False
    assert len(fake_notifier.incident_calls) == 0