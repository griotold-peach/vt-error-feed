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


# --- TIMEOUT 테스트 (1시간 내 3건) ----------------------------------------


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


# --- API_ERROR 테스트 (5분 내 5건 OR 동일 분 3건) --------------------------


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