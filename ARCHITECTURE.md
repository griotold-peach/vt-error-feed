# VT Error Feed Filter Server - Architecture

## Goal

- VT 관련 Teams 에러 피드를 받아서:
  - (1) 특정 에러만 에러 피드 채널로 포워딩
  - (2) 패턴을 감지해서 장애 채널로 알림

## Layers & Modules
```
app/
  __init__.py
  main.py          # FastAPI 엔트리
  config.py        # 환경 변수/설정

  adapters/        # 외부 포맷 ↔ 내부 모델 변환
    __init__.py
    messagecard.py    # Fact, Section, VTWebhookMessage

  domain/          # 비즈니스 도메인 모델 + 규칙
    __init__.py
    events.py         # VTErrorEvent
    anomaly.py        # IncidentType, record_event, reset_state
    rules.py          # FORWARD_FAILURE_REASONS, SPECIAL_FORWARD_KEYWORDS 등

  services/        # use-case / application 서비스
    __init__.py
    handler.py        # /vt/webhook 유즈케이스 (지금 그대로)
    forwarding.py     # should_forward
    incident.py       # classify_incident_from_vt, handle_incident

  infrastructure/  # 외부 시스템 연동 (HTTP, DB, MQ 등)
    __init__.py
    notifier.py       # Teams Webhook 호출

```

- `app/main.py`
  - FastAPI 엔드포인트 정의. `/vt/webhook` 요청에서 JSON payload를 받고 `handle_raw_alert` 유즈케이스에 위임한다.
- `app/config.py`
  - Teams webhook URL 등 환경설정 값을 로드한다.
- `app/adapters/messagecard.py`
  - Teams MessageCard DTO (`Fact`, `Section`, `VTWebhookMessage`). sections[].facts[]에서 name/value를 추출하는 helper를 제공한다.
- `app/domain/events.py`
  - 비즈니스 도메인 모델 `VTErrorEvent` 와 `event_datetime()` 파서.
- `app/domain/anomaly.py`
  - 장애 탐지 모델: `IncidentType`, `record_event(...)`, 테스트용 `reset_state()`. 슬라이딩 윈도우/쿨다운 로직이 여기에 있다.
- `app/domain/rules.py`
  - 비즈니스 상수 (`FORWARD_FAILURE_REASONS`, `SPECIAL_FORWARD_KEYWORDS`).
- `app/services/handler.py`
  - `/vt/webhook` 요청을 처리하는 진입점. payload 파싱 → forwarding 판단 → incident 처리 순으로 orchestrate.
- `app/services/forwarding.py`
  - `should_forward(event)` 로직: failure_reason whitelist와 특수 키워드 매칭.
- `app/services/incident.py`
  - `classify_incident_from_vt` + `handle_incident`: 도메인 anomaly를 호출하고 필요 시 incident 채널에 알림 전송.
- `app/infrastructure/notifier.py`
  - HTTP 연동 계층. Teams webhook 으로 MessageCard를 보내는 `post_to_forward_channel` / `post_to_incident_channel`.

## `/vt/webhook` End-to-End Flow

1. `app/main.py` FastAPI 라우터가 payload JSON을 수신한다.
2. Route handler가 `handle_raw_alert(payload)` (services/handler) 를 호출한다.
3. handler는 `VTWebhookMessage`(adapters) 로 검증하고 `VTErrorEvent`(domain) 로 변환한다.
4. `services/forwarding.should_forward` 가 forwarding 여부를 결정한다. True일 때 infrastructure/notifier 의 forward webhook으로 POST한다.
5. handler는 `services/incident.handle_incident` 를 호출한다. 이 함수는
   - `classify_incident_from_vt` 로 incident type을 결정하고
   - `domain.anomaly.record_event` 로 패턴을 기록/판별하며
   - 임계치를 넘으면 notifier 를 통해 incident webhook으로 POST한다.
6. handler는 forward 여부를 bool 로 반환하고, FastAPI 는 이를 `{"status": "forwarded" | "dropped"}` 응답으로 변환한다.

## Tests

- `tests/test_handler.py`
  - `/vt/webhook` 유즈케이스를 end-to-end 로 검증한다 (forward 여부, incident 알림 호출 횟수 등).
