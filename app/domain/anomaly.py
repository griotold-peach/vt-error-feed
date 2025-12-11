"""
Incident anomaly tracking helpers.

Public API: `IncidentType` and `record_event(incident_type: IncidentType, timestamp: datetime) -> bool`.
All module-level state containers and helpers (e.g. `_event_windows`, `_minute_counts`,
`_last_alert_ts`, `_record_*`, `_cleanup_*`) are internal implementation details.
Use `reset_state()` only in tests to clear those structures between runs.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Deque, DefaultDict, Dict

import logging

logger = logging.getLogger(__name__)


class IncidentType(Enum):
    """
    장애 유형 정의.

    - TIMEOUT: Live API 웹훅 처리 중 타임아웃
    - API_ERROR: Live API 웹훅 처리 중 API 에러
    - LIVE_API_DB_OVERLOAD: 영상 생성 실패 (더빙/오디오), Live API DB 부하
    - YT_DOWNLOAD_FAIL: YouTube URL 다운로드 실패
    - YT_EXTERNAL_FAIL: 외부 요인으로 인한 영상 업로드 실패 (Video 파일 업로드 실패)
    """

    TIMEOUT = auto()
    API_ERROR = auto()
    LIVE_API_DB_OVERLOAD = auto()
    YT_DOWNLOAD_FAIL = auto()
    YT_EXTERNAL_FAIL = auto()


# 각 장애 유형별로 최근 이벤트의 타임스탬프를 저장하는 슬라이딩 윈도우
_event_windows: DefaultDict[IncidentType, Deque[datetime]] = defaultdict(deque)

# "동일 분 N건 이상" 조건을 위해 minute bucket 을 저장
# key: "YYYY-MM-DD HH:MM" 문자열
_minute_counts: DefaultDict[IncidentType, Dict[str, int]] = defaultdict(dict)

# 마지막으로 장애 알림을 발생시킨 시각 (쿨다운용)
_last_alert_ts: Dict[IncidentType, datetime] = {}


def reset_state() -> None:
    """
    테스트에서 anomaly 상태를 초기화할 때 사용한다.
    """
    _event_windows.clear()
    _minute_counts.clear()
    _last_alert_ts.clear()


def _minute_key(ts: datetime) -> str:
    """분 단위 버킷 키."""
    return ts.strftime("%Y-%m-%d %H:%M")


def _cleanup_window(
    incident_type: IncidentType,
    now: datetime,
    window: timedelta,
) -> Deque[datetime]:
    """
    슬라이딩 윈도우에서 window 범위 밖의 타임스탬프를 제거한다.
    """
    q = _event_windows[incident_type]
    cutoff = now - window
    while q and q[0] <= cutoff:
        q.popleft()
    return q


def _cleanup_minute_counts(
    incident_type: IncidentType,
    now: datetime,
    keep_for: timedelta = timedelta(hours=2),
) -> Dict[str, int]:
    """
    너무 오래된 minute bucket 은 정리한다.
    (메모리 무한 증가 방지용, 장애 기준에는 영향 없음)
    """
    counts = _minute_counts[incident_type]
    cutoff = now - keep_for

    # minute key 를 다시 datetime 으로 파싱해서 비교
    for key in list(counts.keys()):
        try:
            bucket_dt = datetime.strptime(key, "%Y-%m-%d %H:%M")
        except ValueError:
            # 혹시라도 포맷 깨지면 그냥 삭제
            del counts[key]
            continue

        if bucket_dt < cutoff:
            del counts[key]

    return counts


def _check_cooldown(
    incident_type: IncidentType,
    now: datetime,
    cooldown: timedelta,
) -> bool:
    """
    동일 장애 유형에 대해 쿨다운 시간 내에 또 발생했다면
    알림을 suppress 하고 False 를 리턴한다.
    """
    last = _last_alert_ts.get(incident_type)
    if last is not None and now - last < cooldown:
        logger.info(
            "Incident %s triggered but in cooldown window (last=%s, now=%s)",
            incident_type.name,
            last.isoformat(),
            now.isoformat(),
        )
        return False

    _last_alert_ts[incident_type] = now
    return True


def _record_timeout(now: datetime) -> bool:
    """
    TIMEOUT 장애 기준:
    - 1시간 내 3건 이상
    """
    window = timedelta(hours=1)
    threshold = 3

    q = _cleanup_window(IncidentType.TIMEOUT, now, window)
    q.append(now)

    if len(q) >= threshold:
        # 너무 자주 알리지 않기 위해 쿨다운 적용 (예: 10분)
        if _check_cooldown(IncidentType.TIMEOUT, now, cooldown=timedelta(minutes=10)):
            logger.info(
                "TIMEOUT incident triggered: %d events within last %s",
                len(q),
                window,
            )
            return True

    return False


def _record_api_error(now: datetime) -> bool:
    """
    API_ERROR 장애 기준:
    - 5분 내 5건 이상
      OR
    - 동일 분 3건 이상
    """
    # 규칙 1: 5분 내 5건 이상
    window_5m = timedelta(minutes=5)
    threshold_5m = 5

    q = _cleanup_window(IncidentType.API_ERROR, now, window_5m)
    q.append(now)
    cond1 = len(q) >= threshold_5m

    # 규칙 2: 동일 분 3건 이상
    counts = _cleanup_minute_counts(IncidentType.API_ERROR, now)
    mkey = _minute_key(now)
    counts[mkey] = counts.get(mkey, 0) + 1
    cond2 = counts[mkey] >= 3

    if cond1 or cond2:
        if _check_cooldown(
            IncidentType.API_ERROR,
            now,
            cooldown=timedelta(minutes=5),
        ):
            logger.info(
                "API_ERROR incident triggered: 5m_count=%d, minute_count=%d, minute=%s",
                len(q),
                counts[mkey],
                mkey,
            )
            return True

    return False


def _record_db_overload(now: datetime) -> bool:
    """
    Live API DB 부하 장애 기준:
    - 동일 분 3건 이상
    """
    counts = _cleanup_minute_counts(IncidentType.LIVE_API_DB_OVERLOAD, now)
    mkey = _minute_key(now)
    counts[mkey] = counts.get(mkey, 0) + 1

    if counts[mkey] >= 3:
        if _check_cooldown(
            IncidentType.LIVE_API_DB_OVERLOAD,
            now,
            cooldown=timedelta(minutes=5),
        ):
            logger.info(
                "LIVE_API_DB_OVERLOAD incident triggered: minute_count=%d, minute=%s",
                counts[mkey],
                mkey,
            )
            return True

    return False


def _record_yt_download(now: datetime) -> bool:
    """
    유튜브 다운로드 장애 기준:
    - 30분 내 3건 이상
    """
    window = timedelta(minutes=30)
    threshold = 3

    q = _cleanup_window(IncidentType.YT_DOWNLOAD_FAIL, now, window)
    q.append(now)

    if len(q) >= threshold:
        if _check_cooldown(
            IncidentType.YT_DOWNLOAD_FAIL,
            now,
            cooldown=timedelta(minutes=10),
        ):
            logger.info(
                "YT_DOWNLOAD_FAIL incident triggered: %d events within last %s",
                len(q),
                window,
            )
            return True

    return False


def _record_yt_external(now: datetime) -> bool:
    """
    유튜브 외부 장애 기준:
    - 30분 내 3건 이상
    """
    window = timedelta(minutes=30)
    threshold = 3

    q = _cleanup_window(IncidentType.YT_EXTERNAL_FAIL, now, window)
    q.append(now)

    if len(q) >= threshold:
        if _check_cooldown(
            IncidentType.YT_EXTERNAL_FAIL,
            now,
            cooldown=timedelta(minutes=10),
        ):
            logger.info(
                "YT_EXTERNAL_FAIL incident triggered: %d events within last %s",
                len(q),
                window,
            )
            return True

    return False


def record_event(incident_type: IncidentType, timestamp: datetime) -> bool:
    """
    장애 이벤트 하나를 기록하고, 이번 이벤트가 장애 기준을 만족하는지 판별한다.

    :param incident_type: 장애 유형
    :param timestamp: 이벤트 발생 시각 (UTC 기준 datetime 권장)
    :return: True 이면 이번 이벤트에서 "장애 알림"을 발생시켜야 함, False 이면 단순히 기록만.
    """
    if not isinstance(timestamp, datetime):
        raise TypeError("timestamp must be a datetime instance")

    if incident_type == IncidentType.TIMEOUT:
        return _record_timeout(timestamp)

    if incident_type == IncidentType.API_ERROR:
        return _record_api_error(timestamp)

    if incident_type == IncidentType.LIVE_API_DB_OVERLOAD:
        return _record_db_overload(timestamp)

    if incident_type == IncidentType.YT_DOWNLOAD_FAIL:
        return _record_yt_download(timestamp)

    if incident_type == IncidentType.YT_EXTERNAL_FAIL:
        return _record_yt_external(timestamp)

    logger.warning("Unknown incident type: %r", incident_type)
    return False
