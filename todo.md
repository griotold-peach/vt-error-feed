# Refactor TODO

## [x] handler.py slimming
- [x] `handle_raw_alert(payload: dict) -> bool` 외부 인터페이스는 그대로 유지한다
- [x] forwarding 관련 로직을 별도 모듈로 분리한다
  - [x] `forwarding.py` 모듈 생성
  - [x] `should_forward(event: VTErrorEvent)` 를 forwarding 모듈로 이동
  - [x] forwarding 모듈에서 `rules.py` 의 상수(`FORWARD_FAILURE_REASONS`, `SPECIAL_FORWARD_KEYWORDS`) 를 사용
  - [x] handler.py에서는 `from app.services.forwarding import should_forward` 로 가져다 쓰도록 변경
- [x] incident 관련 로직을 별도 모듈로 분리한다
  - [x] `incident.py` 모듈 생성
  - [x] `classify_incident_from_vt(event)` 를 incident 모듈로 이동
  - [x] anomaly 호출(`record_event`)을 incident 모듈로 캡슐화
    - [x] 예: `handle_incident(event: VTErrorEvent, raw_payload: dict) -> None`
  - [x] handler.py에서는 forwarding/incident 모듈만 호출하도록 단순화
- [x] 최종적으로 handler.py는:
  - [x] payload → `VTWebhookMessage` → `VTErrorEvent` 파싱
  - [x] forwarding 모듈 호출
  - [x] incident 모듈 호출
  - [x] bool 리턴만 담당

---

## [x] anomaly.py 정리
- [x] public API를 모듈 상단에 문서화
  - [x] 공개 대상: `record_event(incident_type: IncidentType, timestamp: datetime) -> bool`
  - [x] `IncidentType`은 `incident_type.py`로 분리
  - [x] 나머지 함수/변수는 내부 구현이라고 명시
- [x] 상태 초기화 헬퍼 추가
  - [x] `_event_windows`, `_minute_counts`, `_last_alert_ts` 를 초기화하는 `reset_state()` 함수 추가
  - [x] `tests/test_handler.py` 에서 anomaly 내부 dict 직접 접근 대신 `reset_state()` 사용하도록 변경
- [x] 내부 구현 함수 역할 정리
  - [x] `_record_*` 함수들을 `incident_config.py` 설정 기반으로 일반화된 `record_event()`로 통합
  - [x] 로그 메시지 포맷/내용 정리 완료
- [x] 모듈 분리
  - [x] `incident_type.py` - IncidentType enum 분리
  - [x] `incident_config.py` - 장애 기준 설정 분리 (threshold, cooldown)

---

## [x] notifier.py 정리
- [x] public API를 명확히 한다
  - [x] 외부에서 사용하는 함수: `post_to_forward_channel(card: dict)`, `post_to_incident_channel(card: dict)`
  - [x] `_post_to_teams` 는 내부 구현으로 유지
- [x] HTTP 클라이언트/에러 처리 정리
  - [x] `verify=False` 사용 이유를 주석으로 남기고, 나중에 설정화할 TODO 남기기 (ex. 환경에 따라 TLS 검증 on/off)
  - [x] exception/log 메시지에 포함되는 정보(상태코드, body 길이 등) 최소화/정리
- [x] 테스트 용이성 고려
  - [x] notifier 에 대한 최소 단위 테스트 or 통합테스트 아이디어 메모 (현재는 handler 테스트에서 monkeypatch로 대체)
  - [x] 필요 시 httpx 클라이언트를 주입받는 형태(의존성 주입)로 변경 고려 (후순위)

---

## [x] monitoring.py 추가 (Feed2 처리)
- [x] Feed2 (VT 실시간 모니터링) 엔드포인트 구현
- [x] `MonitoringEvent` 도메인 모델 추가 (`events.py`)
- [x] handler.py 방식과 통일 (MessageCard → 도메인 모델 → 처리)
- [x] JSON 직접 생성 제거, 원본 payload 전달로 변경
- [x] `test_monitoring.py` 테스트 추가

---

## [x] 테스트 유지 / 강화
- [x] `tests/test_handler.py` 는 절대 깨지면 안 되는 계약(contract)으로 유지
- [x] 리팩토링 후 항상 `pdm run test` 로 검증
- [x] anomaly 리팩토링 시 테스트 보강
  - [x] `test_anomaly.py` 추가
  - [x] 쿨다운 동작 테스트
  - [x] 윈도우 경계값 테스트 (정확히 60분, 30분 등)
  - [x] 모든 IncidentType threshold 테스트
- [x] E2E 테스트 스크립트 추가
  - [x] `scripts/e2e_test.sh` (curl)
  - [x] `scripts/e2e_test.py` (Python)

---

## [x] 문서화
- [x] `ARCHITECTURE.md` 최신화
- [x] `README.md` 작성