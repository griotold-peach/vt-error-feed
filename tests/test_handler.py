# tests/test_handler.py
import asyncio
from typing import Any, Dict, List

import pytest

from app.services.handler import handle_raw_alert
from app.services import anomaly


# --- 공용 fixture: anomaly 상태 초기화 ------------------------------------


@pytest.fixture(autouse=True)
def reset_anomaly_state():
    """
    anomaly 모듈은 모듈 전역 상태(deque, dict)를 들고 있어서
    테스트마다 깨끗하게 초기화해준다.
    """
    anomaly.reset_state()
    yield
    # 끝나고 한 번 더 정리 (겹쳐도 문제 없음)
    anomaly.reset_state()


# --- 공용 fixture: notifier monkeypatch ------------------------------------


@pytest.fixture
def fake_notifiers(monkeypatch):
    """
    handler 가 내부에서 호출하는 post_to_forward_channel / post_to_incident_channel
    을 가짜 함수로 바꿔서 실제 Teams 호출을 막고, 몇 번 불렸는지만 기록한다.
    """
    forward_calls: List[Dict[str, Any]] = []
    incident_calls: List[Dict[str, Any]] = []

    async def fake_forward(card: Dict[str, Any]) -> None:
        forward_calls.append(card)

    async def fake_incident(card: Dict[str, Any]) -> None:
        incident_calls.append(card)

    # handler/incident 모듈 안의 심볼을 패치해야 한다
    monkeypatch.setattr(
        "app.services.handler.post_to_forward_channel",
        fake_forward,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.incident.post_to_incident_channel",
        fake_incident,
        raising=True,
    )

    return {
        "forward_calls": forward_calls,
        "incident_calls": incident_calls,
    }


# --- 테스트용 payload helpers ---------------------------------------------


def make_base_card(error_message: str, error_detail: str, time_value: str) -> Dict[str, Any]:
    return {
        "type": "MessageCard",
        "context": "https://schema.org/extensions",
        "themeColor": "FF0000",
        "title": "🚨 API-Video-Translator Translate Project Exception.",
        "summary": "웹훅 처리중 실패가 발생했습니다.",
        "sections": [
            {
                "activityTitle": "웹훅 처리중 실패가 발생했습니다.",
                "facts": [
                    {"name": "Project", "value": "test-project"},
                    {"name": "Error Message", "value": error_message},
                    {"name": "Error Detail", "value": error_detail},
                    {"name": "Time", "value": time_value},
                ],
            }
        ],
    }


def make_time(idx: int) -> str:
    """
    테스트용 타임스탬프 생성 helper.
    idx=0,1,2 ... 에 따라 분만 바뀌게.
    """
    # 2025-01-01T00:00, 00:10, 00:20 ... 이런 식
    minute = idx * 10
    return f"2025-01-01T00:{minute:02d}:00.000000000Z[Etc/UTC]"


# --- 테스트들 -------------------------------------------------------------


@pytest.mark.anyio
async def test_apf_forwarded_no_incident(fake_notifiers):
    """
    AUDIO_PIPELINE_FAILED:
    - 개선사항 1: forward 대상 (status=True)
    - 개선사항 2: 장애 기준(type: TIMEOUT/API_ERROR)이 아니므로 incident 아님
    """
    payload = make_base_card(
        error_message="Received Failed Webhook Event by Live API.",
        error_detail="Failure Reason: AUDIO_PIPELINE_FAILED Engine Error Code: NO_VOICE_DETECTED_VAD",
        time_value=make_time(0),
    )

    forwarded = await handle_raw_alert(payload)

    assert forwarded is True
    assert len(fake_notifiers["forward_calls"]) == 1
    assert len(fake_notifiers["incident_calls"]) == 0


@pytest.mark.anyio
async def test_engine_error_dropped(fake_notifiers):
    """
    ENGINE_ERROR:
    - 개선사항 1: forward 대상 아님 (status=False)
    - 개선사항 2: 장애 기준에도 안 걸림
    """
    payload = make_base_card(
        error_message="Received Failed Webhook Event by Live API.",
        error_detail="Failure Reason: ENGINE_ERROR Engine Error Code: NO_VOICE_DETECTED_VAD",
        time_value=make_time(0),
    )

    forwarded = await handle_raw_alert(payload)

    assert forwarded is False
    assert len(fake_notifiers["forward_calls"]) == 0
    assert len(fake_notifiers["incident_calls"]) == 0


@pytest.mark.anyio
async def test_video_queue_full_forwarded_no_incident(fake_notifiers):
    """
    VT5001 / VIDEO_QUEUE_FULL:
    - Failure Reason 은 없지만 키워드 매칭으로 forward 대상
    - 장애 기준(type: TIMEOUT/API_ERROR)이 아니므로 incident 아님
    """
    payload = {
        "type": "MessageCard",
        "context": "https://schema.org/extensions",
        "themeColor": "FF0000",
        "title": "🚨 API-Video-Translator Exception",
        "summary": "An exception occurred in the application",
        "sections": [
            {
                "activityTitle": "An exception occurred in the application",
                "facts": [
                    {"name": "Error Code", "value": "VT5001"},
                    {
                        "name": "Error Message",
                        "value": "Invalid FailureReason value: VIDEO_QUEUE_FULL",
                    },
                    {
                        "name": "Cause or Stack Trace",
                        "value": "Invalid FailureReason value: VIDEO_QUEUE_FULL",
                    },
                    {"name": "Time", "value": make_time(0)},
                ],
            }
        ],
    }

    forwarded = await handle_raw_alert(payload)

    assert forwarded is True
    assert len(fake_notifiers["forward_calls"]) == 1
    assert len(fake_notifiers["incident_calls"]) == 0


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
            time_value=make_time(i),  # 0, 10, 20분
        )
        forwarded = await handle_raw_alert(payload)
        assert forwarded is True

    # forward 는 3번 다 호출
    assert len(fake_notifiers["forward_calls"]) == 3
    # incident 는 임계치 도달 시 1번만 호출
    assert len(fake_notifiers["incident_calls"]) == 1
