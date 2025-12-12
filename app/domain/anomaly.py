# app/domain/anomaly.py
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Deque, DefaultDict, Dict

import logging

from app.domain.incident_type import IncidentType
from app.domain.incident_config import INCIDENT_THRESHOLDS

logger = logging.getLogger(__name__)


# 각 장애 유형별로 최근 이벤트의 타임스탬프를 저장하는 슬라이딩 윈도우
_event_windows: DefaultDict[IncidentType, Deque[datetime]] = defaultdict(deque)

# "동일 분 N건 이상" 조건을 위해 minute bucket 을 저장
_minute_counts: DefaultDict[IncidentType, Dict[str, int]] = defaultdict(dict)

# 마지막으로 장애 알림을 발생시킨 시각 (쿨다운용)
_last_alert_ts: Dict[IncidentType, datetime] = {}


def reset_state() -> None:
    """테스트에서 anomaly 상태를 초기화할 때 사용한다."""
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
    """슬라이딩 윈도우에서 window 범위 밖의 타임스탬프를 제거한다."""
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
    """너무 오래된 minute bucket 은 정리한다."""
    counts = _minute_counts[incident_type]
    cutoff = now - keep_for

    for key in list(counts.keys()):
        try:
            bucket_dt = datetime.strptime(key, "%Y-%m-%d %H:%M")
            # naive datetime으로 비교하기 위해 cutoff에서 tzinfo 제거
            cutoff_naive = cutoff.replace(tzinfo=None) if cutoff.tzinfo else cutoff
            if bucket_dt < cutoff_naive:
                del counts[key]
        except ValueError:
            del counts[key]

    return counts


def _check_cooldown(
    incident_type: IncidentType,
    now: datetime,
    cooldown: timedelta,
) -> bool:
    """쿨다운 시간 내에 또 발생했다면 False 를 리턴한다."""
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


def record_event(incident_type: IncidentType, timestamp: datetime) -> bool:
    """
    장애 이벤트 하나를 기록하고, 장애 기준을 만족하는지 판별한다.

    :param incident_type: 장애 유형
    :param timestamp: 이벤트 발생 시각 (UTC 기준 datetime 권장)
    :return: True 이면 장애 알림 발생, False 이면 단순 기록
    """
    if not isinstance(timestamp, datetime):
        raise TypeError("timestamp must be a datetime instance")

    config = INCIDENT_THRESHOLDS.get(incident_type)
    if config is None:
        logger.warning("Unknown incident type: %r", incident_type)
        return False

    triggered = False

    # 조건 1: 슬라이딩 윈도우 기준 (window + count)
    if config.window is not None and config.count > 0:
        q = _cleanup_window(incident_type, timestamp, config.window)
        q.append(timestamp)
        if len(q) >= config.count:
            triggered = True

    # 조건 2: 동일 분 기준 (same_minute_count)
    if config.same_minute_count is not None:
        counts = _cleanup_minute_counts(incident_type, timestamp)
        mkey = _minute_key(timestamp)
        counts[mkey] = counts.get(mkey, 0) + 1
        if counts[mkey] >= config.same_minute_count:
            triggered = True

    if triggered:
        if _check_cooldown(incident_type, timestamp, config.cooldown):
            logger.info(
                "Incident %s triggered: type=%s, time=%s",
                incident_type.name,
                incident_type.name,
                timestamp.isoformat(),
            )
            return True

    return False