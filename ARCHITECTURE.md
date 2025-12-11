# VT Error Feed Filter Server - Architecture

## Goal

- VT 관련 Teams 에러 피드를 받아서:
  - (1) 특정 에러만 에러 피드 채널로 포워딩 (Feed1)
  - (2) 패턴을 감지해서 장애 채널로 알림 (Feed1 + Feed2)

## Feeds

| Feed | 소스 채널 | 엔드포인트 | 역할 |
|------|-----------|------------|------|
| Feed1 | API-Video-Translator Prod | `/vt/webhook/live-api` | 포워딩 + 장애 탐지 (TIMEOUT, API_ERROR) |
| Feed2 | VT 실시간 모니터링 [PM, PO] | `/vt/webhook/monitoring` | 장애 탐지 (DB부하, 유튜브) |

## 장애 기준

| 장애유형 | 설명 | 장애기준 | 쿨다운 |
|----------|------|----------|--------|
| TIMEOUT | Live API 웹훅 처리 중 타임아웃 | 1시간 내 3건 이상 | 10분 |
| API_ERROR | Live API 웹훅 처리 중 API 에러 | 5분 내 5건 이상 OR 동일 분 3건 이상 | 5분 |
| LIVE_API_DB_OVERLOAD | 영상 생성 실패 (더빙/오디오) | 동일 분 3건 이상 | 5분 |
| YT_DOWNLOAD_FAIL | YouTube URL 다운로드 실패 | 30분 내 3건 이상 | 10분 |
| YT_EXTERNAL_FAIL | Video 파일 업로드 실패 | 30분 내 3건 이상 | 10분 |

## Layers & Modules
```
app/
  __init__.py
  main.py              # FastAPI 엔트리
  config.py            # 환경 변수/설정

  adapters/            # 외부 포맷 ↔ 내부 모델 변환
    __init__.py
    messagecard.py        # Fact, Section, VTWebhookMessage

  domain/              # 비즈니스 도메인 모델 + 규칙
    __init__.py
    incident_type.py      # IncidentType enum
    incident_config.py    # 장애 기준 설정 (threshold, cooldown)
    events.py             # VTErrorEvent, MonitoringEvent
    anomaly.py            # record_event, reset_state (슬라이딩 윈도우)
    rules.py              # FORWARD_FAILURE_REASONS, SPECIAL_FORWARD_KEYWORDS

  services/            # use-case / application 서비스
    __init__.py
    handler.py            # Feed1 처리 (/vt/webhook/live-api)
    monitoring.py         # Feed2 처리 (/vt/webhook/monitoring)
    forwarding.py         # should_forward
    incident.py           # classify_incident_from_vt, handle_incident

  infrastructure/      # 외부 시스템 연동
    __init__.py
    notifier.py           # Teams Webhook 호출

scripts/               # 테스트/유틸리티 스크립트
  e2e_test.sh            # E2E 테스트 (curl)
  e2e_test.py            # E2E 테스트 (Python)
```

## Module 설명

### app/main.py
- FastAPI 엔드포인트 정의
- `/vt/webhook/live-api` → `handler.handle_raw_alert()`
- `/vt/webhook/monitoring` → `monitoring.handle_monitoring_alert()`
- `/debug/reset` → 테스트용 상태 초기화

### app/config.py
- 환경 변수 로드 (`.env`)
- `TEAMS_FORWARD_WEBHOOK_URL`, `TEAMS_INCIDENT_WEBHOOK_URL`

### app/adapters/messagecard.py
- Teams MessageCard DTO (`Fact`, `Section`, `VTWebhookMessage`)
- `get_fact(name)`: sections[].facts[]에서 값 추출

### app/domain/incident_type.py
- `IncidentType` enum: TIMEOUT, API_ERROR, LIVE_API_DB_OVERLOAD, YT_DOWNLOAD_FAIL, YT_EXTERNAL_FAIL

### app/domain/incident_config.py
- `IncidentThreshold` dataclass: window, count, same_minute_count, cooldown
- `INCIDENT_THRESHOLDS`: 장애 유형별 기준 설정

### app/domain/events.py
- `VTErrorEvent`: Feed1 도메인 모델
- `MonitoringEvent`: Feed2 도메인 모델
- `_parse_event_datetime()`: 시간 문자열 파싱 (공통)

### app/domain/anomaly.py
- `record_event(incident_type, timestamp)`: 이벤트 기록 및 장애 판정
- `reset_state()`: 테스트용 상태 초기화
- 슬라이딩 윈도우 + 쿨다운 로직

### app/domain/rules.py
- `FORWARD_FAILURE_REASONS`: 포워딩 대상 Failure Reason
- `SPECIAL_FORWARD_KEYWORDS`: 특수 키워드 (VIDEO_QUEUE_FULL 등)

### app/services/handler.py
- Feed1 처리 진입점
- payload 파싱 → 포워딩 판단 → 장애 처리

### app/services/monitoring.py
- Feed2 처리 진입점
- payload 파싱 → 장애 유형 분류 → 장애 처리

### app/services/forwarding.py
- `should_forward(event)`: 포워딩 여부 판단

### app/services/incident.py
- `classify_incident_from_vt(event)`: Feed1 이벤트 → IncidentType 매핑
- `handle_incident(event, payload)`: 장애 탐지 및 알림

### app/infrastructure/notifier.py
- `post_to_forward_channel(card)`: 포워딩 채널로 전송
- `post_to_incident_channel(card)`: 장애 알림 채널로 전송

## End-to-End Flow

### Feed1 (`/vt/webhook/live-api`)

1. `main.py`가 payload 수신
2. `handler.handle_raw_alert(payload)` 호출
3. `VTWebhookMessage` → `VTErrorEvent` 변환
4. `forwarding.should_forward(event)` → True면 포워딩 채널로 전송
5. `incident.handle_incident(event, payload)` → 장애 기준 체크 → 트리거 시 장애 채널로 전송
6. 응답: `{"status": "forwarded" | "dropped"}`

### Feed2 (`/vt/webhook/monitoring`)

1. `main.py`가 payload 수신
2. `monitoring.handle_monitoring_alert(payload)` 호출
3. `VTWebhookMessage` → `MonitoringEvent` 변환
4. `_classify_incident_type(event)` → IncidentType 매핑
5. `anomaly.record_event(incident_type, ts)` → 장애 기준 체크 → 트리거 시 장애 채널로 전송
6. 응답: `{"status": "incident_triggered" | "recorded"}`

## Tests
```
tests/
  conftest.py           # 공통 fixture
  test_events.py        # VTErrorEvent, MonitoringEvent 테스트
  test_forwarding.py    # should_forward 단위 테스트
  test_handler.py       # Feed1 통합 테스트
  test_monitoring.py    # Feed2 통합 테스트
  test_anomaly.py       # 슬라이딩 윈도우 단위 테스트
```

### 테스트 실행
```bash
# 전체 테스트
pdm run test

# 특정 파일
pdm run pytest tests/test_anomaly.py -v

# E2E 테스트 (서버 실행 필요)
pdm run dev  # 터미널 1
pdm run python scripts/e2e_test.py  # 터미널 2
```