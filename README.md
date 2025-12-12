# VT Error Feed Filter Server

VT 관련 Teams 에러 피드를 필터링하고, 장애 패턴을 감지하여 알림을 보내는 서버.

## 주요 기능

1. **에러 피드 필터링** - 중요한 에러만 포워딩 채널로 전달
2. **장애 패턴 감지** - 슬라이딩 윈도우 기반으로 장애 기준 충족 시 장애 채널로 알림

## 빠른 시작
```bash
# 의존성 설치
pdm install

# 서버 실행
pdm run dev

# 테스트 실행
pdm run test
```

## 환경 변수

`.env` 파일에 다음 변수 설정 필요:

| 변수명 | 설명 |
|--------|------|
| `TEAMS_FORWARD_WEBHOOK_URL` | 포워딩 채널 Webhook URL |
| `TEAMS_INCIDENT_WEBHOOK_URL` | 장애 알림 채널 Webhook URL |

## API 엔드포인트

| 엔드포인트 | 설명 |
|------------|------|
| `GET /health` | 헬스 체크 |
| `POST /vt/webhook/live-api` | Feed1 (API-Video-Translator) 처리 |
| `POST /vt/webhook/monitoring` | Feed2 (VT 실시간 모니터링) 처리 |

## 장애 기준

| 장애유형 | 기준 |
|----------|------|
| TIMEOUT | 1시간 내 3건 이상 |
| API_ERROR | 5분 내 5건 이상 OR 동일 분 3건 이상 |
| LIVE_API_DB_OVERLOAD | 동일 분 3건 이상 |
| YT_DOWNLOAD_FAIL | 30분 내 3건 이상 |
| YT_EXTERNAL_FAIL | 30분 내 3건 이상 |

장애 기준 변경은 `app/domain/incident_config.py` 수정.

## 프로젝트 구조
```
app/
├── main.py                 # FastAPI 엔트리
├── config.py               # 환경 변수
├── adapters/               # 외부 포맷 변환
├── domain/                 # 비즈니스 로직
│   ├── incident_type.py    # 장애 유형 enum
│   ├── incident_config.py  # 장애 기준 설정
│   ├── anomaly.py          # 슬라이딩 윈도우
│   └── events.py           # 도메인 모델
├── services/               # 유즈케이스
└── infrastructure/         # 외부 시스템 연동

tests/                      # 테스트
scripts/                    # E2E 테스트 스크립트
```

상세 구조는 [ARCHITECTURE.md](./ARCHITECTURE.md) 참고.

## 설계 결정

### 슬라이딩 윈도우 저장소: 메모리 vs 데이터베이스

**결정: 인메모리 방식 채택**

| 항목 | 메모리 | 데이터베이스 (Redis 등) |
|------|--------|------------------------|
| 구현 복잡도 | 낮음 | 높음 |
| 응답 속도 | 빠름 | 네트워크 지연 |
| 서버 재시작 시 | 초기화 | 유지 |
| 다중 인스턴스 | 공유 안 됨 | 공유 가능 |

**근거:**
- 최악의 경우에도 메모리 사용량 ~26KB 수준
- 장애 감지용 데이터라 재시작 후 초기화되어도 무방
- 현재 단일 인스턴스 운영으로 충분

**향후 검토 시점:**
- 다중 인스턴스(로드밸런싱) 필요 시
- 장애 이력 분석/리포팅 기능 추가 시