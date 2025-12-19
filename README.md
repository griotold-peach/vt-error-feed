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

```bash
# Microsoft Graph API
MICROSOFT_APP_ID=...
MICROSOFT_APP_PASSWORD=...
MICROSOFT_TENANT_ID=...

# Teams 설정
TEAMS_TEAM_ID=...
TEAMS_FEED1_CHANNEL_ID=...
TEAMS_FEED2_CHANNEL_ID=...

TEAMS_FORWARD_WEBHOOK_URL=...

TEAMS_INCIDENT_WEBHOOK_URL=...

# 환경
ENV=production
```

## 장애 기준

| 장애유형 | 기준 | 쿨다운 |
|----------|------|--------|
| TIMEOUT | 1시간 내 3건 이상 | 10분 |
| API_ERROR | 5분 내 5건 이상 OR 동일 분 3건 이상 | 5분 |
| LIVE_API_DB_OVERLOAD | 동일 분 3건 이상 | 5분 |
| YT_DOWNLOAD_FAIL | 30분 내 3건 이상 | 10분 |
| YT_EXTERNAL_FAIL | 30분 내 3건 이상 | 10분 |

장애 기준 변경은 `app/domain/incident_config.py` 수정.

## 프로젝트 구조
```
app/
├── main.py                 # FastAPI 엔트리포인트
├── config.py               # 환경 변수 설정
├── container.py            # 의존성 조립 (DI Container)
│
├── adapters/               # 외부 시스템 연동
│   ├── graph_client.py     # Microsoft Graph API 클라이언트
│   ├── teams_notifier.py   # Teams Webhook 알림 전송
│   └── messagecard.py      # Teams MessageCard 포맷 변환
│
├── application/            # 애플리케이션 계층
│   ├── ports/              # 인터페이스 정의 (Protocol)
│   │   └── notifier.py     # 알림 전송 포트
│   └── services/           # 유스케이스 구현
│       ├── handler.py      # Feed1 처리
│       ├── monitoring.py   # Feed2 처리
│       ├── incident.py     # 장애 감지
│       ├── message_poller.py    # 메시지 폴링
│       ├── message_processor.py # 메시지 처리
│       └── ...
│
└── domain/                 # 도메인 계층
    ├── incident_type.py    # 장애 유형 정의
    ├── incident_config.py  # 장애 임계값 설정
    ├── anomaly.py          # 슬라이딩 윈도우 로직
    ├── events.py           # 도메인 모델
    └── rules.py            # 포워딩 규칙

tests/                      # 테스트 (149개 테스트 통과)
scripts/                    # E2E 테스트 스크립트
```

상세 구조는 [ARCHITECTURE.md](./ARCHITECTURE.md) 참고.

## 슬라이딩 윈도우 동작방식

### 핵심 개념

**1. 슬라이딩 윈도우** - 현재 시점 기준 N분/시간 내 이벤트만 카운트
```
윈도우: 1시간, 현재: 13:30

    윈도우 범위: 12:30 ~ 13:30
    ←―――――――――――――――――――――――→
    
12:00   12:30   13:00   13:30
  ×       ○       ○       ○
 제외    포함    포함    포함
```

**2. Threshold** - 윈도우 내 이벤트 수가 threshold 이상이면 장애 판정

**3. 쿨다운** - 장애 알림 후 일정 시간 동안 추가 알림 방지 (알림 피로 방지)

### 동작 시뮬레이션 (TIMEOUT: 1시간 내 3건, 쿨다운 10분)

| 시간 | 윈도우 상태 | 건수 | 결과 |
|------|-------------|------|------|
| 12:00 | `[12:00]` | 1 | 정상 |
| 12:30 | `[12:00, 12:30]` | 2 | 정상 |
| 12:50 | `[12:00, 12:30, 12:50]` | 3 | 🚨 장애! |
| 12:55 | `[12:00, 12:30, 12:50, 12:55]` | 4 | suppress (쿨다운) |
| 13:05 | `[12:30, 12:50, 12:55, 13:05]` | 4 | 🚨 장애! (쿨다운 끝) |
| 14:10 | `[14:10]` | 1 | 정상 (이전 이벤트 만료) |

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