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

## [ ] anomaly.py 정리
- [x] public API를 모듈 상단에 문서화
  - [x] 공개 대상: `IncidentType`, `record_event(incident_type: IncidentType, timestamp: datetime) -> bool`
  - [x] 나머지 함수/변수는 내부 구현이라고 명시
- [x] 상태 초기화 헬퍼 추가
  - [x] `_event_windows`, `_minute_counts`, `_last_alert_ts` 를 초기화하는 `reset_state()` 함수 추가
  - [x] `tests/test_handler.py` 에서 anomaly 내부 dict 직접 접근 대신 `reset_state()` 사용하도록 변경
- [ ] 내부 구현 함수 역할 정리
  - [ ] `_record_timeout`, `_record_api_error`, `_record_db_overload`, `_record_yt_download`, `_record_yt_external` 중 공통 패턴이 있으면 유틸 함수로 정리 (behavior 변경 없이)
  - [ ] 로그 메시지 포맷/내용 점검 (필요한 정보만 남기기)
- [ ] 모듈 분리 여부 검토 (후순위)
  - [ ] incident 규칙만 모은 `anomaly_rules.py` / `incident_rules.py` 로 분리할 필요가 있는지 평가
  - [ ] 분리하더라도 `record_event` 시그니처와 동작은 그대로 유지

---

## [ ] notifier.py 정리
- [ ] public API를 명확히 한다
  - [ ] 외부에서 사용하는 함수: `post_to_forward_channel(card: dict)`, `post_to_incident_channel(card: dict)`
  - [ ] `_post_to_teams` 는 내부 구현으로 유지
- [ ] HTTP 클라이언트/에러 처리 정리
  - [ ] `verify=False` 사용 이유를 주석으로 남기고, 나중에 설정화할 TODO 남기기 (ex. 환경에 따라 TLS 검증 on/off)
  - [ ] exception/log 메시지에 포함되는 정보(상태코드, body 길이 등) 최소화/정리
- [ ] 테스트 용이성 고려
  - [ ] notifier 에 대한 최소 단위 테스트 or 통합테스트 아이디어 메모 (현재는 handler 테스트에서 monkeypatch로 대체)
  - [ ] 필요 시 httpx 클라이언트를 주입받는 형태(의존성 주입)로 변경 고려 (후순위)

---

## [ ] schemas.py / 파싱 레이어 정리
- [ ] `VTWebhookMessage` / `VTErrorEvent` 역할을 명확히 문서화
  - [ ] `VTWebhookMessage`: Teams MessageCard JSON (현재 payload.json 기준)
  - [ ] `VTErrorEvent`: 비즈니스 로직에서 사용하는 정제된 도메인 모델
- [ ] `event_datetime()` 개선/정리
  - [ ] docstring 에 실제 예시 포맷 (`2025-12-08T03:40:00.000000000Z[Etc/UTC]`) 명시
  - [ ] timezone-aware datetime(UTC) 반환 보장 확인
  - [ ] 잘못된 포맷일 때 fallback 전략을 주석으로 설명
- [ ] 파싱 어댑터 레이어 준비 (패턴 B 대비)
  - [ ] 나중에 “봇이 텍스트 기반 payload를 보내는 경우”를 대비해서,  
        `adapter` 레이어 설계 아이디어를 주석이나 TODO로 남겨두기
    - [ ] 예: `adapt_raw_payload_to_vt_message(raw: dict | str) -> VTErrorEvent`
  - [ ] 지금은 MessageCard 기준이지만, 실제 봇 payload를 본 뒤 이 레이어에서만 수정하도록 가이드
- [ ] 테스트 아이디어
  - [ ] `event_datetime()` 에 대한 단위 테스트 추가 후보로 메모
  - [ ] `from_message()` 가 facts 누락/이름 변경에 어떻게 대응할지 규칙 정리 (필요 시)

---

## [ ] 테스트 유지 / 강화
- [ ] `tests/test_handler.py` 는 절대 깨지면 안 되는 계약(contract)으로 유지
- [ ] 리팩토링 후 항상 `pdm run test` 또는 `pdm run test -k handler` 로 검증
- [ ] anomaly 리팩토링 시 TIMEOUT/API_ERROR 패턴 검증용 테스트 보강 검토
  - [ ] ex. 쿨다운 동작, 5분/1시간 윈도우 경계 테스트 등
