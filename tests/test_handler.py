# tests/test_handler.py
from typing import Dict, Any, List
import pytest
from datetime import datetime, timedelta, timezone

from app.adapters.messagecard import VTWebhookMessage
from app.services.handler import handle_raw_alert


# --- Helper Functions -------------------------------------------------------

def make_base_card(
    error_message: str,
    error_detail: str,
    time_value: str,
) -> VTWebhookMessage:
    """테스트용 기본 카드 생성"""
    return VTWebhookMessage(
        title="🚨 API-Video-Translator Translate Project Exception.",
        summary="웹훅 처리중 실패가 발생했습니다.",
        themeColor="FF0000",
        context="https://schema.org/extensions",
        sections=[{
            "activityTitle": "웹훅 처리중 실패가 발생했습니다.",
            "facts": [
                {"name": "Project", "value": "123456"},
                {"name": "Error Message", "value": error_message},
                {"name": "Error Detail", "value": error_detail},
                {"name": "Time", "value": time_value},
            ],
        }]
    )


def make_time(offset_minutes: int = 0) -> str:
    """현재 시간 + offset_minutes 분"""
    dt = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    return dt.isoformat()


# --- 픽스처 ----------------------------------------------------------------

@pytest.fixture
def fake_notifiers(monkeypatch):
    """
    handler와 incident가 내부에서 사용하는 _notifier를 Mock으로 교체
    """
    from unittest.mock import AsyncMock, MagicMock
    
    forward_calls: List[Dict[str, Any]] = []
    incident_calls: List[Dict[str, Any]] = []

    async def fake_forward(card: Dict[str, Any]) -> bool:
        forward_calls.append(card)
        return True

    async def fake_incident(card: Dict[str, Any]) -> bool:
        incident_calls.append(card)
        return True

    # Mock TeamsNotifier 인스턴스 생성
    mock_notifier = MagicMock()
    mock_notifier.send_to_forward_channel = AsyncMock(side_effect=fake_forward)
    mock_notifier.send_to_incident_channel = AsyncMock(side_effect=fake_incident)
    
    # handler 모듈의 _notifier를 Mock으로 교체
    monkeypatch.setattr(
        "app.services.handler._notifier",
        mock_notifier,
        raising=True,
    )
    
    # ✅ incident 모듈의 _notifier도 Mock으로 교체
    monkeypatch.setattr(
        "app.services.incident._notifier",
        mock_notifier,
        raising=True,
    )
    
    return {
        "forward_calls": forward_calls,
        "incident_calls": incident_calls,
        "mock_notifier": mock_notifier,
    }


# --- 테스트들 ---------------------------------------------------------------

@pytest.mark.anyio
async def test_apf_forwarded_no_incident(fake_notifiers):
    """APF 에러는 포워딩되지만 장애 아님"""
    payload = make_base_card(
        error_message="Received Failed Webhook Event by Live API.",
        error_detail="Failure Reason: AUDIO_PIPELINE_FAILED",
        time_value=make_time(),
    )
    
    result = await handle_raw_alert(payload)
    
    assert result is True
    assert len(fake_notifiers["forward_calls"]) == 1
    assert len(fake_notifiers["incident_calls"]) == 0


@pytest.mark.anyio
async def test_engine_error_dropped(fake_notifiers):
    """ENGINE_ERROR는 드롭됨"""
    payload = make_base_card(
        error_message="Received Failed Webhook Event by Live API.",
        error_detail="Failure Reason: ENGINE_ERROR",
        time_value=make_time(),
    )
    
    result = await handle_raw_alert(payload)
    
    assert result is False
    assert len(fake_notifiers["forward_calls"]) == 0


@pytest.mark.anyio
async def test_video_queue_full_forwarded_no_incident(fake_notifiers):
    """VIDEO_QUEUE_FULL은 포워딩됨"""
    payload = make_base_card(
        error_message="Received Failed Webhook Event by Live API.",
        error_detail="Invalid FailureReason value: VIDEO_QUEUE_FULL",
        time_value=make_time(),
    )
    
    result = await handle_raw_alert(payload)
    
    assert result is True
    assert len(fake_notifiers["forward_calls"]) == 1


@pytest.mark.anyio
async def test_timeout_incident_after_three_events(fake_notifiers):
    """
    TIMEOUT:
    - 개선사항 1: forward 대상
    - 개선사항 2: 1시간 내 3건 이상이면 incident 채널로 1번 알림
    """
    for i in range(3):
        payload = make_base_card(
            error_message="Received Failed Webhook Event by Live API.",
            error_detail="Failure Reason: TIMEOUT HTTP Status: 504 GATEWAY_TIMEOUT",
            time_value=make_time(i * 10),  # 0, 10, 20분
        )
        forwarded = await handle_raw_alert(payload)
        assert forwarded is True
    
    # forward 는 3번 다 호출
    assert len(fake_notifiers["forward_calls"]) == 3
    
    # incident 는 임계치 도달 시 1번만 호출
    assert len(fake_notifiers["incident_calls"]) == 1