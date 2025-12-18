# tests/test_monitoring.py
from typing import Any, Dict, List

import pytest

from app.services.monitoring import handle_monitoring_alert
from app.domain import anomaly


# --- 공용 fixture: anomaly 상태 초기화 ------------------------------------


@pytest.fixture(autouse=True)
def reset_anomaly_state():
    """
    anomaly 모듈은 모듈 전역 상태(deque, dict)를 들고 있어서
    테스트마다 깨끗하게 초기화해준다.
    """
    anomaly.reset_state()
    yield
    anomaly.reset_state()


# --- 공용 fixture: notifier monkeypatch ------------------------------------

@pytest.fixture
def fake_notifiers(monkeypatch):
    """
    monitoring이 내부에서 사용하는 _notifier를 Mock으로 교체
    """
    from unittest.mock import AsyncMock, MagicMock
    
    incident_calls: List[Dict[str, Any]] = []

    async def fake_incident(card: Dict[str, Any]) -> bool:
        incident_calls.append(card)
        return True

    # Mock TeamsNotifier 인스턴스 생성
    mock_notifier = MagicMock()
    mock_notifier.send_to_incident_channel = AsyncMock(side_effect=fake_incident)
    
    # monitoring 모듈의 _notifier를 Mock으로 교체
    monkeypatch.setattr(
        "app.services.monitoring._notifier",
        mock_notifier,
        raising=True,
    )
    
    return {
        "incident_calls": incident_calls,
        "mock_notifier": mock_notifier,
    }

# --- 테스트용 payload helpers ---------------------------------------------


def make_monitoring_card(title: str, activity_title: str, description: str, time_value: str) -> Dict[str, Any]:
    """
    Feed2 (모니터링 채널) MessageCard 생성 헬퍼.
    """
    return {
        "type": "MessageCard",
        "context": "https://schema.org/extensions",
        "themeColor": "FFA500",
        "title": title,
        "sections": [
            {
                "activityTitle": activity_title,
                "facts": [
                    {"name": "Description", "value": description},
                    {"name": "Time", "value": time_value},
                ],
            }
        ],
    }


def make_db_overload_card(time_value: str) -> Dict[str, Any]:
    """Live API DB 부하 카드"""
    return make_monitoring_card(
        title="🚨 영상 생성 실패",
        activity_title="더빙/오디오 생성 실패",
        description="영상 생성 실패 - 더빙/오디오 생성 실패",
        time_value=time_value,
    )


def make_yt_download_card(time_value: str) -> Dict[str, Any]:
    """YouTube URL 다운로드 실패 카드"""
    return make_monitoring_card(
        title="🚨 외부 URL 다운로드 실패",
        activity_title="외부 URL 다운로드 실패",
        description="영상 업로드 실패 - YouTube URL 다운로드 실패",
        time_value=time_value,
    )


def make_yt_external_card(time_value: str) -> Dict[str, Any]:
    """Video 파일 업로드 실패 카드"""
    return make_monitoring_card(
        title="🚨 업로드 실패",
        activity_title="Video 파일 업로드 실패",
        description="영상 업로드 실패 - Video 파일 업로드 실패",
        time_value=time_value,
    )


def make_time_same_minute(idx: int) -> str:
    """
    동일 분 내 테스트용 타임스탬프.
    idx=0,1,2 ... 에 따라 초만 바뀜.
    """
    second = idx * 10
    return f"2025-01-01T00:00:{second:02d}.000000000Z[Etc/UTC]"


def make_time_minutes(idx: int) -> str:
    """
    분 단위로 증가하는 타임스탬프.
    idx=0,1,2 ... 에 따라 분만 바뀜.
    """
    minute = idx
    return f"2025-01-01T00:{minute:02d}:00.000000000Z[Etc/UTC]"


# --- LIVE_API_DB_OVERLOAD 테스트 (동일 분 3건) ----------------------------


@pytest.mark.anyio
async def test_db_overload_no_incident_under_threshold(fake_notifiers):
    """
    Live API DB 부하: 동일 분 2건 → incident 아님
    """
    for i in range(2):
        payload = make_db_overload_card(make_time_same_minute(i))
        triggered = await handle_monitoring_alert(payload)
        assert triggered is False

    assert len(fake_notifiers["incident_calls"]) == 0


@pytest.mark.anyio
async def test_db_overload_incident_at_threshold(fake_notifiers):
    """
    Live API DB 부하: 동일 분 3건 → incident 트리거
    """
    for i in range(3):
        payload = make_db_overload_card(make_time_same_minute(i))
        triggered = await handle_monitoring_alert(payload)

    assert triggered is True
    assert len(fake_notifiers["incident_calls"]) == 1


# --- YT_DOWNLOAD_FAIL 테스트 (30분 내 3건) --------------------------------


@pytest.mark.anyio
async def test_yt_download_no_incident_under_threshold(fake_notifiers):
    """
    YouTube 다운로드 실패: 30분 내 2건 → incident 아님
    """
    for i in range(2):
        payload = make_yt_download_card(make_time_minutes(i))
        triggered = await handle_monitoring_alert(payload)
        assert triggered is False

    assert len(fake_notifiers["incident_calls"]) == 0


@pytest.mark.anyio
async def test_yt_download_incident_at_threshold(fake_notifiers):
    """
    YouTube 다운로드 실패: 30분 내 3건 → incident 트리거
    """
    for i in range(3):
        payload = make_yt_download_card(make_time_minutes(i))
        triggered = await handle_monitoring_alert(payload)

    assert triggered is True
    assert len(fake_notifiers["incident_calls"]) == 1


# --- YT_EXTERNAL_FAIL 테스트 (30분 내 3건) --------------------------------


@pytest.mark.anyio
async def test_yt_external_no_incident_under_threshold(fake_notifiers):
    """
    Video 파일 업로드 실패: 30분 내 2건 → incident 아님
    """
    for i in range(2):
        payload = make_yt_external_card(make_time_minutes(i))
        triggered = await handle_monitoring_alert(payload)
        assert triggered is False

    assert len(fake_notifiers["incident_calls"]) == 0


@pytest.mark.anyio
async def test_yt_external_incident_at_threshold(fake_notifiers):
    """
    Video 파일 업로드 실패: 30분 내 3건 → incident 트리거
    """
    for i in range(3):
        payload = make_yt_external_card(make_time_minutes(i))
        triggered = await handle_monitoring_alert(payload)

    assert triggered is True
    assert len(fake_notifiers["incident_calls"]) == 1


# --- 매핑 안 되는 이벤트 테스트 --------------------------------------------


@pytest.mark.anyio
async def test_unknown_event_not_mapped(fake_notifiers):
    """
    알 수 없는 타입의 모니터링 이벤트 → 매핑 안 됨, incident 아님
    """
    payload = make_monitoring_card(
        title="🚨 알 수 없는 에러",
        activity_title="뭔가 실패",
        description="알 수 없는 실패",
        time_value=make_time_minutes(0),
    )

    triggered = await handle_monitoring_alert(payload)

    assert triggered is False
    assert len(fake_notifiers["incident_calls"]) == 0