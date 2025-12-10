# VT Error Feed Filter Server - Architecture

## Goal

- VT 관련 Teams 에러 피드를 받아서:
  - (1) 특정 에러만 에러 피드 채널로 포워딩
  - (2) 패턴을 감지해서 장애 채널로 알림

## Main Flow

- `app/main.py`
  - `/vt/webhook`:
    - JSON payload 수신 (VT 서버 또는 봇이 POST)
    - `handle_raw_alert(payload)` 호출
    - 반환값에 따라 `{"status": "forwarded" | "dropped"}` 응답

- `app/services/handler.py`
  - `handle_raw_alert(payload: dict) -> bool`:
    - `VTWebhookMessage` → `VTErrorEvent` 로 파싱
    - `should_forward(event)`:
      - 개선사항 1 (어떤 에러만 forward 채널로 보낼지)
    - `classify_incident_from_vt(event)` + `record_event(...)`:
      - 개선사항 2 (TIMEOUT/API_ERROR 패턴 감지 → incident 채널로 알림)
    - 내부에서 `post_to_forward_channel`, `post_to_incident_channel` 호출

- `app/adapters/messagecard.py`
  - Teams MessageCard → `VTWebhookMessage`
  - sections[].facts[] 기반 DTO (`Fact`, `Section`)

- `app/domain/events.py`
  - `VTErrorEvent` (도메인 모델)
  - `event_datetime()` 으로 Time 문자열을 datetime(UTC)로 변환

- `app/domain/anomaly.py`
  - `IncidentType`, `record_event(incident_type, timestamp) -> bool`
  - 슬라이딩 윈도우 / minute bucket 기반 장애 탐지 로직

- `app/services/notifier.py`
  - `post_to_forward_channel(card: dict)`
  - `post_to_incident_channel(card: dict)`

- `app/domain/rules.py`
  - 비즈니스 규칙 상수:
    - forward 대상 Failure Reason
    - 특수 키워드 (VT5001, VIDEO_QUEUE_FULL 등)

## Tests

- `tests/test_handler.py`
  - `handle_raw_alert` 기준 end-to-end-ish 테스트
  - forward/dropped 판단 + incident 채널 호출 여부 검증
