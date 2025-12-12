# tests/test_anomaly.py
from datetime import datetime, timedelta

from app.domain.anomaly import (
    IncidentType,
    record_event,
    reset_state,
)


# --- 테스트마다 상태 초기화 ------------------------------------------------


def setup_function():
    """각 테스트 함수 실행 전에 anomaly 상태 초기화."""
    reset_state()


def teardown_function():
    """각 테스트 함수 실행 후에도 정리."""
    reset_state()


# --- 헬퍼 함수 ------------------------------------------------------------


def make_time(base: datetime, minutes_offset: int = 0, seconds_offset: int = 0) -> datetime:
    """base 시각에서 분/초 오프셋을 더한 datetime 반환."""
    return base + timedelta(minutes=minutes_offset, seconds=seconds_offset)


# --- TIMEOUT 테스트 (1시간 내 3건, 쿨다운 10분) ----------------------------------------


def test_timeout_no_incident_under_threshold():
    """TIMEOUT: 1시간 내 2건 → incident 아님"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.TIMEOUT, make_time(base, 0)) is False
    assert record_event(IncidentType.TIMEOUT, make_time(base, 30)) is False


def test_timeout_incident_at_threshold():
    """TIMEOUT: 1시간 내 3건 → incident 트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.TIMEOUT, make_time(base, 0)) is False
    assert record_event(IncidentType.TIMEOUT, make_time(base, 20)) is False
    assert record_event(IncidentType.TIMEOUT, make_time(base, 40)) is True


def test_timeout_window_expires():
    """TIMEOUT: 1시간 지난 이벤트는 카운트 안 됨"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 첫 2건
    record_event(IncidentType.TIMEOUT, make_time(base, 0))
    record_event(IncidentType.TIMEOUT, make_time(base, 10))
    
    # 70분 후 (첫 번째 이벤트는 윈도우 밖)
    result = record_event(IncidentType.TIMEOUT, make_time(base, 70))
    assert result is False  # 윈도우 내 2건뿐이므로 트리거 안 됨

def test_timeout_cooldown_suppresses():
    """TIMEOUT: 트리거 후 쿨다운(10분) 내 추가 이벤트 → suppress"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 3건으로 첫 트리거
    record_event(IncidentType.TIMEOUT, make_time(base, 0))
    record_event(IncidentType.TIMEOUT, make_time(base, 10))
    assert record_event(IncidentType.TIMEOUT, make_time(base, 20)) is True  # 트리거!
    
    # 쿨다운(10분) 내 추가 이벤트 → suppress
    assert record_event(IncidentType.TIMEOUT, make_time(base, 22)) is False  # 2분 후
    assert record_event(IncidentType.TIMEOUT, make_time(base, 25)) is False  # 5분 후
    assert record_event(IncidentType.TIMEOUT, make_time(base, 29)) is False  # 9분 후


def test_timeout_cooldown_expires_then_retrigger():
    """TIMEOUT: 쿨다운 지난 후 threshold 충족 → 재트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 첫 트리거 (12:20)
    record_event(IncidentType.TIMEOUT, make_time(base, 0))
    record_event(IncidentType.TIMEOUT, make_time(base, 10))
    assert record_event(IncidentType.TIMEOUT, make_time(base, 20)) is True
    
    # 쿨다운(10분) 지난 후 (12:31) - 이미 윈도우 내 4건
    assert record_event(IncidentType.TIMEOUT, make_time(base, 31)) is True  # 재트리거!


def test_timeout_cooldown_expires_but_under_threshold():
    """TIMEOUT: 쿨다운 지났지만 윈도우 내 건수 부족 → 트리거 안 됨"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 첫 트리거
    record_event(IncidentType.TIMEOUT, make_time(base, 0))
    record_event(IncidentType.TIMEOUT, make_time(base, 10))
    assert record_event(IncidentType.TIMEOUT, make_time(base, 20)) is True
    
    # 2시간 후 - 이전 이벤트 전부 윈도우 밖
    assert record_event(IncidentType.TIMEOUT, make_time(base, 120)) is False  # 1건뿐
    assert record_event(IncidentType.TIMEOUT, make_time(base, 121)) is False  # 2건뿐


def test_timeout_continuous_events_single_alert_per_cooldown():
    """TIMEOUT: 연속 이벤트 시 쿨다운마다 1번만 알림"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    alerts = []
    
    # 10분마다 이벤트 발생 (총 60분간 7개)
    for i in range(7):
        result = record_event(IncidentType.TIMEOUT, make_time(base, i * 10))
        if result:
            alerts.append(i * 10)
    
    # 첫 알림: 20분 (3건째)
    # 두 번째 알림: 30분 (쿨다운 10분 지남 + threshold 충족)
    # 세 번째 알림: 40분
    # ...
    assert 20 in alerts  # 첫 트리거
    assert alerts == [20, 30, 40, 50, 60] # 쿨다운 지나면 재트리거


def test_timeout_window_sliding_correctly():
    """TIMEOUT: 윈도우가 슬라이딩되면서 오래된 이벤트 제외"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 12:00, 12:30에 2건
    record_event(IncidentType.TIMEOUT, make_time(base, 0))
    record_event(IncidentType.TIMEOUT, make_time(base, 30))
    
    # 13:05 (12:00 이벤트는 윈도우 밖, 12:30은 윈도우 내)
    # 윈도우: 12:05 ~ 13:05
    assert record_event(IncidentType.TIMEOUT, make_time(base, 65)) is False  # 2건뿐
    
    # 13:06에 추가
    assert record_event(IncidentType.TIMEOUT, make_time(base, 66)) is True  # 12:30, 13:05, 13:06 = 3건 → 트리거!
    

def test_timeout_exact_window_boundary_excluded():
    """TIMEOUT: 정확히 60분 경계 이벤트는 윈도우에서 제외"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    record_event(IncidentType.TIMEOUT, make_time(base, 0))   # 12:00
    record_event(IncidentType.TIMEOUT, make_time(base, 30))  # 12:30
    
    # 13:00 정각 - 12:00 이벤트는 정확히 60분 → 제외
    # 윈도우 내: 12:30, 13:00 = 2건
    assert record_event(IncidentType.TIMEOUT, make_time(base, 60)) is False
# --- API_ERROR 테스트 (5분 내 5건 OR 동일 분 3건, 쿨다운 5분) --------------------------


def test_api_error_no_incident_under_threshold():
    """API_ERROR: 5분 내 4건, 동일 분 2건 → incident 아님"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.API_ERROR, make_time(base, 0)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 1)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 2)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 3)) is False


def test_api_error_incident_5min_threshold():
    """API_ERROR: 5분 내 5건 → incident 트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    for i in range(4):
        assert record_event(IncidentType.API_ERROR, make_time(base, i)) is False
    
    assert record_event(IncidentType.API_ERROR, make_time(base, 4)) is True


def test_api_error_incident_same_minute_threshold():
    """API_ERROR: 동일 분 3건 → incident 트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, seconds_offset=0)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, seconds_offset=10)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, seconds_offset=20)) is True

def test_api_error_window_expires():
    """API_ERROR: 5분 지난 이벤트는 카운트 안 됨"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 12:00 ~ 12:03에 4건
    record_event(IncidentType.API_ERROR, make_time(base, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 1))
    record_event(IncidentType.API_ERROR, make_time(base, 2))
    record_event(IncidentType.API_ERROR, make_time(base, 3))
    
    # 6분 후 (12:06) - 12:00 이벤트는 윈도우 밖
    # 윈도우: 12:01 ~ 12:06, 윈도우 내 4건 (12:01, 12:02, 12:03, 12:06)
    assert record_event(IncidentType.API_ERROR, make_time(base, 6)) is False


def test_api_error_cooldown_suppresses():
    """API_ERROR: 트리거 후 쿨다운(5분) 내 추가 이벤트 → suppress"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 동일 분 3건으로 첫 트리거 (12:00:20)
    record_event(IncidentType.API_ERROR, make_time(base, 0, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 0, 10))
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, 20)) is True
    
    # 쿨다운(5분) 내 동일 분 3건 다시 발생 (12:01) → suppress
    assert record_event(IncidentType.API_ERROR, make_time(base, 1, 0)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 1, 10)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 1, 20)) is False  # 조건 만족해도 쿨다운 내


def test_api_error_cooldown_expires_then_retrigger():
    """API_ERROR: 쿨다운 지난 후 threshold 충족 → 재트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 첫 트리거 (동일 분 3건)
    record_event(IncidentType.API_ERROR, make_time(base, 0, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 0, 10))
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, 20)) is True
    
    # 쿨다운(5분) 지난 후 (12:05) 동일 분 3건
    record_event(IncidentType.API_ERROR, make_time(base, 5, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 5, 10))
    assert record_event(IncidentType.API_ERROR, make_time(base, 5, 20)) is True  # 재트리거


def test_api_error_cooldown_expires_but_under_threshold():
    """API_ERROR: 쿨다운 지났지만 threshold 미달 → 트리거 안 됨"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 첫 트리거
    record_event(IncidentType.API_ERROR, make_time(base, 0, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 0, 10))
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, 20)) is True
    
    # 10분 후 - 이전 이벤트 전부 윈도우 밖, 동일 분도 아님
    assert record_event(IncidentType.API_ERROR, make_time(base, 10)) is False  # 1건뿐
    assert record_event(IncidentType.API_ERROR, make_time(base, 11)) is False  # 2건뿐


def test_api_error_same_minute_resets_on_new_minute():
    """API_ERROR: 분이 바뀌면 동일 분 카운트 리셋"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 12:00에 2건
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, 0)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, 30)) is False
    
    # 12:01에 2건 (동일 분 카운트 리셋됨)
    assert record_event(IncidentType.API_ERROR, make_time(base, 1, 0)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 1, 30)) is False
    
    # 아직 5분 내 4건이고, 동일 분 2건이므로 트리거 안 됨


def test_api_error_5min_threshold_triggers_before_same_minute():
    """API_ERROR: 5분 내 5건이 동일 분 3건보다 먼저 충족"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 각 분에 1건씩 5건 → 5분 조건으로 트리거
    assert record_event(IncidentType.API_ERROR, make_time(base, 0)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 1)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 2)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 3)) is False
    assert record_event(IncidentType.API_ERROR, make_time(base, 4)) is True  # 5분 내 5건


def test_api_error_exact_window_boundary_excluded():
    """API_ERROR: 정확히 5분 경계 이벤트는 윈도우에서 제외"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 12:00에 4건
    record_event(IncidentType.API_ERROR, make_time(base, 0, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 0, 15))
    record_event(IncidentType.API_ERROR, make_time(base, 0, 30))
    record_event(IncidentType.API_ERROR, make_time(base, 0, 45))
    
    # 12:05 정각 - 12:00:00 이벤트는 정확히 5분 → 제외
    # 윈도우 내: 12:00:15, 12:00:30, 12:00:45, 12:05:00 = 4건
    assert record_event(IncidentType.API_ERROR, make_time(base, 5, 0)) is False


def test_api_error_just_inside_window():
    """API_ERROR: 5분 윈도우 경계 직전에 5건째 → 트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 각 분에 1건씩 (동일 분 트리거 방지)
    record_event(IncidentType.API_ERROR, make_time(base, 0, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 1, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 2, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 3, 0))
    
    # 4분 59초 후 → 5건째 → 트리거
    assert record_event(IncidentType.API_ERROR, make_time(base, 4, 59)) is True


def test_api_error_continuous_events_single_alert_per_cooldown():
    """API_ERROR: 연속 이벤트 시 쿨다운마다 1번만 알림"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    alerts = []
    
    # 1분마다 동일 분 3건씩 발생 (총 15분간)
    for minute in range(0, 15, 1):
        for sec in [0, 10, 20]:
            result = record_event(IncidentType.API_ERROR, make_time(base, minute, sec))
            if result:
                alerts.append(minute)
                break  # 같은 분에 여러 번 트리거 기록 방지
    
    # 첫 알림: 0분 (동일 분 3건)
    # 쿨다운 5분이므로 다음 알림: 5분, 10분
    assert 0 in alerts
    assert 5 in alerts
    assert 10 in alerts
    assert len(alerts) == 3


# --- LIVE_API_DB_OVERLOAD 테스트 (동일 분 3건) ----------------------------

def test_db_overload_no_incident_under_threshold():
    """DB 부하: 동일 분 2건 → incident 아님"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 0)) is False
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 10)) is False


def test_db_overload_incident_at_threshold():
    """DB 부하: 동일 분 3건 → incident 트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 0)) is False
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 10)) is False
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 20)) is True


def test_db_overload_different_minutes_no_incident():
    """DB 부하: 다른 분에 1건씩 → incident 아님"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0)) is False
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 1)) is False
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 2)) is False

def test_db_overload_cooldown_suppresses():
    """DB 부하: 트리거 후 쿨다운(5분) 내 추가 이벤트 → suppress"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 12:00분에 3건 → 트리거
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 0))
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 10))
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 20)) is True
    
    # 12:01분에 3건 → 쿨다운 내 suppress
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 1, 0))
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 1, 10))
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 1, 20)) is False


def test_db_overload_cooldown_expires_then_retrigger():
    """DB 부하: 쿨다운(5분) 지난 후 → 재트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 12:00분에 3건 → 트리거
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 0))
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 10))
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 20)) is True
    
    # 12:06분에 3건 → 쿨다운 지남 → 재트리거
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 6, 0))
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 6, 10))
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 6, 20)) is True


def test_db_overload_minute_boundary():
    """DB 부하: 분 경계를 넘으면 카운트 리셋"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 12:00:50, 12:00:55 → 2건
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 50))
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 0, 55))
    
    # 12:01:00 → 새로운 분, 카운트 1건으로 리셋
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 1, 0)) is False
    
    # 12:01분에 2건 더 → 총 3건 → 트리거
    record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 1, 10))
    assert record_event(IncidentType.LIVE_API_DB_OVERLOAD, make_time(base, 1, 20)) is True


# --- YT_DOWNLOAD_FAIL 테스트 (30분 내 3건) --------------------------------


def test_yt_download_no_incident_under_threshold():
    """YouTube 다운로드: 30분 내 2건 → incident 아님"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 0)) is False
    assert record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 10)) is False


def test_yt_download_incident_at_threshold():
    """YouTube 다운로드: 30분 내 3건 → incident 트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 0)) is False
    assert record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 10)) is False
    assert record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 20)) is True


def test_yt_download_window_expires():
    """YouTube 다운로드: 30분 지난 이벤트는 카운트 안 됨"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 0))
    record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 10))
    
    # 35분 후 (첫 번째 이벤트는 윈도우 밖)
    result = record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 35))
    assert result is False


# --- 쿨다운 테스트 --------------------------------------------------------


def test_timeout_cooldown_suppresses_second_alert():
    """TIMEOUT: 트리거 후 쿨다운(10분) 내 재발생 → suppress"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 첫 번째 트리거
    record_event(IncidentType.TIMEOUT, make_time(base, 0))
    record_event(IncidentType.TIMEOUT, make_time(base, 10))
    first_trigger = record_event(IncidentType.TIMEOUT, make_time(base, 20))
    assert first_trigger is True
    
    # 쿨다운 내 추가 이벤트 (25분, 30분)
    assert record_event(IncidentType.TIMEOUT, make_time(base, 25)) is False
    assert record_event(IncidentType.TIMEOUT, make_time(base, 28)) is False


def test_timeout_cooldown_expires_allows_new_alert():
    """TIMEOUT: 쿨다운 지나면 다시 트리거 가능"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 첫 번째 트리거
    record_event(IncidentType.TIMEOUT, make_time(base, 0))
    record_event(IncidentType.TIMEOUT, make_time(base, 10))
    assert record_event(IncidentType.TIMEOUT, make_time(base, 20)) is True
    
    # 쿨다운(10분) 지난 후 다시 3건
    record_event(IncidentType.TIMEOUT, make_time(base, 35))
    record_event(IncidentType.TIMEOUT, make_time(base, 45))
    assert record_event(IncidentType.TIMEOUT, make_time(base, 55)) is True


# --- YT_EXTERNAL_FAIL 테스트 (30분 내 3건) --------------------------------


def test_yt_external_no_incident_under_threshold():
    """Video 파일 업로드 실패: 30분 내 2건 → incident 아님"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.YT_EXTERNAL_FAIL, make_time(base, 0)) is False
    assert record_event(IncidentType.YT_EXTERNAL_FAIL, make_time(base, 10)) is False


def test_yt_external_incident_at_threshold():
    """Video 파일 업로드 실패: 30분 내 3건 → incident 트리거"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    assert record_event(IncidentType.YT_EXTERNAL_FAIL, make_time(base, 0)) is False
    assert record_event(IncidentType.YT_EXTERNAL_FAIL, make_time(base, 10)) is False
    assert record_event(IncidentType.YT_EXTERNAL_FAIL, make_time(base, 20)) is True


def test_yt_external_window_expires():
    """Video 파일 업로드 실패: 30분 지난 이벤트는 카운트 안 됨"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    record_event(IncidentType.YT_EXTERNAL_FAIL, make_time(base, 0))
    record_event(IncidentType.YT_EXTERNAL_FAIL, make_time(base, 10))
    
    # 35분 후 (첫 번째 이벤트는 윈도우 밖)
    result = record_event(IncidentType.YT_EXTERNAL_FAIL, make_time(base, 35))
    assert result is False


# --- API_ERROR 윈도우 만료 테스트 -----------------------------------------


def test_api_error_window_expires():
    """API_ERROR: 5분 지난 이벤트는 카운트 안 됨"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    record_event(IncidentType.API_ERROR, make_time(base, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 1))
    record_event(IncidentType.API_ERROR, make_time(base, 2))
    record_event(IncidentType.API_ERROR, make_time(base, 3))
    
    # 6분 후 (첫 번째 이벤트는 윈도우 밖)
    result = record_event(IncidentType.API_ERROR, make_time(base, 6))
    assert result is False


# --- 경계값 테스트 --------------------------------------------------------


def test_timeout_exact_window_boundary():
    """TIMEOUT: 정확히 60분 경계 - 60분 된 이벤트는 제외"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    record_event(IncidentType.TIMEOUT, make_time(base, 0))
    record_event(IncidentType.TIMEOUT, make_time(base, 30))
    
    # 정확히 60분 후 → 첫 번째 이벤트(0분)는 윈도우 밖
    result = record_event(IncidentType.TIMEOUT, make_time(base, 60))
    assert result is False


def test_timeout_just_inside_window():
    """TIMEOUT: 59분 후 → 아직 윈도우 내"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    record_event(IncidentType.TIMEOUT, make_time(base, 0))
    record_event(IncidentType.TIMEOUT, make_time(base, 30))
    
    # 59분 후 → 첫 번째 이벤트 아직 윈도우 내
    result = record_event(IncidentType.TIMEOUT, make_time(base, 59))
    assert result is True


def test_yt_download_exact_window_boundary():
    """YT_DOWNLOAD: 정확히 30분 경계 - 30분 된 이벤트는 제외"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 0))
    record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 15))
    
    # 정확히 30분 후 → 첫 번째 이벤트(0분)는 윈도우 밖
    result = record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 30))
    assert result is False


def test_yt_download_just_inside_window():
    """YT_DOWNLOAD: 29분 후 → 아직 윈도우 내"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 0))
    record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 15))
    
    # 29분 후 → 첫 번째 이벤트 아직 윈도우 내
    result = record_event(IncidentType.YT_DOWNLOAD_FAIL, make_time(base, 29))
    assert result is True


# --- 쿨다운 경계값 테스트 --------------------------------------------------


def test_api_error_cooldown_exact_boundary():
    """API_ERROR: 정확히 쿨다운(5분) 경계"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 첫 트리거 (동일 분 3건)
    record_event(IncidentType.API_ERROR, make_time(base, 0, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 0, 10))
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, 20)) is True
    
    # 정확히 5분 후 다시 3건 → 쿨다운 끝났으므로 트리거
    record_event(IncidentType.API_ERROR, make_time(base, 5, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 5, 10))
    assert record_event(IncidentType.API_ERROR, make_time(base, 5, 20)) is True


def test_api_error_cooldown_just_before_boundary():
    """API_ERROR: 쿨다운 끝나기 직전(4분 59초) → 아직 suppress"""
    base = datetime(2025, 1, 1, 12, 0, 0)
    
    # 첫 트리거
    record_event(IncidentType.API_ERROR, make_time(base, 0, 0))
    record_event(IncidentType.API_ERROR, make_time(base, 0, 10))
    assert record_event(IncidentType.API_ERROR, make_time(base, 0, 20)) is True
    
    # 4분 59초 후 다시 3건 → 아직 쿨다운 내
    record_event(IncidentType.API_ERROR, make_time(base, 4, 59))
    record_event(IncidentType.API_ERROR, make_time(base, 4, 59))
    assert record_event(IncidentType.API_ERROR, make_time(base, 4, 59)) is False