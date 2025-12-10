from __future__ import annotations

from typing import Any, Dict
from datetime import datetime, timezone
import logging

from app.domain.anomaly import IncidentType, record_event
from app.infrastructure.notifier import post_to_incident_channel

logger = logging.getLogger(__name__)


def _classify_monitoring_incident(payload: Dict[str, Any]) -> IncidentType | None:
    """
    Feed2 (모니터링 채널) 카드의 title/description 을 기반으로
    IncidentType 으로 매핑한다.

    기대하는 패턴 (대략):
      - "영상 생성 실패 | Description 영상 생성 실패 - 더빙/오디오 생성 실패"
          -> LIVE_API_DB_OVERLOAD
      - "외부 URL 다운로드 실패 | Description 영상 업로드 실패 - YouTube URL 다운로드 실패"
          -> YT_DOWNLOAD_FAIL
      - "Video 파일 업로드 실패 | Description 영상 업로드 실패 - Video 파일 업로드 실패"
          -> YT_EXTERNAL_FAIL
    """
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()

    text = f"{title} | {description}"

    # Live API DB 부하: 더빙/오디오 생성 실패
    if "영상 생성 실패" in text and "더빙/오디오 생성 실패" in text:
        return IncidentType.LIVE_API_DB_OVERLOAD

    # YouTube URL 다운로드 실패
    if "외부 URL 다운로드 실패" in text or "YouTube URL 다운로드 실패" in text:
        return IncidentType.YT_DOWNLOAD_FAIL

    # Video 파일 업로드 실패
    if "Video 파일 업로드 실패" in text:
        return IncidentType.YT_EXTERNAL_FAIL

    return None


def _parse_utc_time(value: str | None) -> datetime:
    """
    Feed2 payload 의 time 문자열을 UTC datetime 으로 파싱한다.

    VT 쪽 포맷과 비슷한 `"2025-12-08T03:40:00.000000000Z[Etc/UTC]"` 형식을 가정하고,
    Z 앞부분만 잘라서 소수점 6자리까지만 남긴 뒤 datetime.fromisoformat 으로 파싱한다.
    파싱이 실패하면 datetime.now(timezone.utc) 로 fallback 한다.
    """
    if not value:
        return datetime.now(timezone.utc)

    raw = value
    try:
        before_z = raw.split("Z", 1)[0]
        if "." in before_z:
            date_part, frac = before_z.split(".", 1)
            frac = (frac + "000000")[:6]
            trimmed = f"{date_part}.{frac}"
        else:
            trimmed = before_z
        return datetime.fromisoformat(trimmed)
    except Exception:
        return datetime.now(timezone.utc)

def _build_incident_card(
    incident_type: IncidentType,
    payload: Dict[str, Any],
    ts: datetime,
) -> Dict[str, Any]:
    """
    Feed2 모니터링 incident 를 Teams Incoming Webhook에서 이해할 수 있는
    MessageCard 형태로 감싸준다.
    """
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()

    return {
        "type": "MessageCard",
        "context": "https://schema.org/extensions",
        "themeColor": "FF0000",
        "title": f"🚨 VT Monitoring Incident: {incident_type.name}",
        "summary": "모니터링 채널에서 장애 패턴이 감지되었습니다.",
        "sections": [
            {
                "activityTitle": title or "VT Monitoring Incident",
                "facts": [
                    {"name": "IncidentType", "value": incident_type.name},
                    {"name": "Description", "value": description},
                    {"name": "Time", "value": ts.isoformat()},
                ],
            }
        ],
    }


async def handle_monitoring_alert(payload: Dict[str, Any]) -> bool:
    """
    Feed2 모니터링 이벤트 하나를 처리한다.

    1) title/description 으로 IncidentType 결정
    2) anomaly.record_event(...) 에 기록
    3) 임계치 도달 시 incident 채널로 Teams MessageCard 전송

    반환값:
      True  -> 이번 호출에서 incident 가 실제로 트리거되어 장애 채널로 전송됨
      False -> 아직 임계치 미달이거나, 매핑되지 않는 이벤트
    """
    incident_type = _classify_monitoring_incident(payload)
    if incident_type is None:
        logger.info("Monitoring payload not mapped to incident type: %s", payload)
        return False

    ts = _parse_utc_time(payload.get("time"))
    is_incident = record_event(incident_type, ts)

    if is_incident:
        card = _build_incident_card(incident_type, payload, ts)
        await post_to_incident_channel(card)
        logger.info(
            "Monitoring incident triggered: type=%s, time=%s",
            incident_type.name,
            ts.isoformat(),
        )
    else:
        logger.info(
            "Monitoring event recorded but no incident yet: type=%s, time=%s",
            incident_type.name,
            ts.isoformat(),
        )

    return is_incident
