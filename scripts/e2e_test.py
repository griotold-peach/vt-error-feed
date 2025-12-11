# scripts/e2e_test.py
"""
E2E 테스트 스크립트

사용법:
    pdm run python scripts/e2e_test.py

주의:
    - 로컬 서버가 실행 중이어야 함 (pdm run dev)
    - 실제 Teams 채널로 메시지가 전송됨
"""
import httpx
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"


def make_live_api_payload(
    project: str,
    failure_reason: str,
    time_str: str,
    error_message: str = "Received Failed Webhook Event by Live API.",
    extra_detail: str = "",
) -> dict:
    """Feed1 (live-api) payload 생성"""
    error_detail = f"Failure Reason: {failure_reason}"
    if extra_detail:
        error_detail += f" {extra_detail}"
    
    return {
        "type": "MessageCard",
        "context": "https://schema.org/extensions",
        "themeColor": "FF0000",
        "title": "🚨 API-Video-Translator Translate Project Exception.",
        "summary": "웹훅 처리중 실패가 발생했습니다.",
        "sections": [{
            "activityTitle": "웹훅 처리중 실패가 발생했습니다.",
            "facts": [
                {"name": "Project", "value": project},
                {"name": "Error Message", "value": error_message},
                {"name": "Error Detail", "value": error_detail},
                {"name": "Time", "value": time_str},
            ]
        }]
    }


def make_monitoring_payload(
    title: str,
    activity_title: str,
    description: str,
    time_str: str,
) -> dict:
    """Feed2 (monitoring) payload 생성"""
    return {
        "type": "MessageCard",
        "context": "https://schema.org/extensions",
        "themeColor": "FFA500",
        "title": title,
        "summary": description,
        "sections": [{
            "activityTitle": activity_title,
            "facts": [
                {"name": "Description", "value": description},
                {"name": "Time", "value": time_str},
            ]
        }]
    }


def make_time(minutes_offset: int = 0, seconds_offset: int = 0) -> str:
    """현재 시각 기준 타임스탬프 생성"""
    now = datetime.utcnow() + timedelta(minutes=minutes_offset, seconds=seconds_offset)
    return now.strftime("%Y-%m-%dT%H:%M:%S.000000000Z[Etc/UTC]")


def post(endpoint: str, payload: dict) -> dict:
    """POST 요청 전송"""
    url = f"{BASE_URL}{endpoint}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, json=payload)
        return {"status_code": resp.status_code, "body": resp.json()}


def print_result(test_name: str, response: dict, expected_status: str):
    """결과 출력"""
    actual_status = response["body"].get("status", "unknown")
    match = "✅" if actual_status == expected_status else "❌"
    print(f"  {match} {test_name}")
    print(f"     예상: {expected_status}, 실제: {actual_status}")


def run_tests():
    print("=" * 60)
    print("E2E 테스트 시작")
    print("=" * 60)
    
    # 서버 헬스 체크
    print("\n[0] 서버 헬스 체크")
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{BASE_URL}/health")
            if resp.status_code == 200:
                print("  ✅ 서버 정상")
            else:
                print("  ❌ 서버 응답 오류")
                return
    except Exception as e:
        print(f"  ❌ 서버 연결 실패: {e}")
        print("     pdm run dev 로 서버를 먼저 실행하세요.")
        return

    # anomaly 상태 초기화
    print("\n[0.5] anomaly 상태 초기화")
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(f"{BASE_URL}/debug/reset")
            if resp.status_code == 200:
                print("  ✅ 상태 초기화 완료")
            else:
                print("  ⚠️ 초기화 실패, 테스트 계속 진행")
    except Exception as e:
        print(f"  ⚠️ 초기화 실패: {e}")
    # =========================================================
    print("\n" + "=" * 60)
    print("Feed1 (live-api) 테스트")
    print("=" * 60)
    
    # 테스트 1: ENGINE_ERROR
    print("\n[1] ENGINE_ERROR - 포워딩 X, 장애 알림 X")
    payload = make_live_api_payload(
        project="e2e-test-001",
        failure_reason="ENGINE_ERROR",
        time_str=make_time(),
        extra_detail="Engine Error Code: NO_VOICE_DETECTED_VAD",
    )
    result = post("/vt/webhook/live-api", payload)
    print_result("ENGINE_ERROR", result, "dropped")
    
    time.sleep(0.5)
    
    # 테스트 2: AUDIO_PIPELINE_FAILED
    print("\n[2] AUDIO_PIPELINE_FAILED - 포워딩 O, 장애 알림 X")
    payload = make_live_api_payload(
        project="e2e-test-002",
        failure_reason="AUDIO_PIPELINE_FAILED",
        time_str=make_time(),
    )
    result = post("/vt/webhook/live-api", payload)
    print_result("AUDIO_PIPELINE_FAILED", result, "forwarded")
    
    time.sleep(0.5)
    
    # 테스트 3: VIDEO_QUEUE_FULL (특수 키워드)
    print("\n[3] VIDEO_QUEUE_FULL - 포워딩 O, 장애 알림 X")
    payload = {
        "type": "MessageCard",
        "context": "https://schema.org/extensions",
        "themeColor": "FF0000",
        "title": "🚨 API-Video-Translator Exception",
        "summary": "An exception occurred",
        "sections": [{
            "activityTitle": "An exception occurred",
            "facts": [
                {"name": "Error Code", "value": "VT5001"},
                {"name": "Error Message", "value": "Invalid FailureReason value: VIDEO_QUEUE_FULL"},
                {"name": "Cause or Stack Trace", "value": "Invalid FailureReason value: VIDEO_QUEUE_FULL"},
                {"name": "Time", "value": make_time()},
            ]
        }]
    }
    result = post("/vt/webhook/live-api", payload)
    print_result("VIDEO_QUEUE_FULL", result, "forwarded")
    
    time.sleep(0.5)
    
    # 테스트 4: TIMEOUT 3건 (장애 트리거)
    print("\n[4] TIMEOUT 3건 - 포워딩 O x3, 장애 알림 O (3번째에서)")
    for i in range(3):
        payload = make_live_api_payload(
            project=f"e2e-test-timeout-{i+1}",
            failure_reason="TIMEOUT",
            time_str=make_time(minutes_offset=i),
        )
        result = post("/vt/webhook/live-api", payload)
        print(f"     TIMEOUT #{i+1}: {result['body'].get('status')}")
        time.sleep(0.3)
    
    time.sleep(0.5)
    
    # 테스트 5: API_ERROR 동일 분 3건
    print("\n[5] API_ERROR 동일 분 3건 - 포워딩 O x3, 장애 알림 O")
    base_time = make_time(minutes_offset=10)  # 이전 테스트와 시간 분리
    for i in range(3):
        payload = make_live_api_payload(
            project=f"e2e-test-api-error-{i+1}",
            failure_reason="API_ERROR",
            time_str=base_time,  # 동일 분
        )
        result = post("/vt/webhook/live-api", payload)
        print(f"     API_ERROR #{i+1}: {result['body'].get('status')}")
        time.sleep(0.3)

    # =========================================================
    print("\n" + "=" * 60)
    print("Feed2 (monitoring) 테스트")
    print("=" * 60)
    
    # 테스트 6: DB 부하 1건 (트리거 안 됨)
    print("\n[6] 영상 생성 실패 (DB 부하) 1건 - 장애 알림 X")
    payload = make_monitoring_payload(
        title="🚨 영상 생성 실패",
        activity_title="더빙/오디오 생성 실패",
        description="영상 생성 실패 - 더빙/오디오 생성 실패",
        time_str=make_time(minutes_offset=20),
    )
    result = post("/vt/webhook/monitoring", payload)
    print_result("DB 부하 1건", result, "recorded")
    
    time.sleep(0.5)
    
    # 테스트 7: DB 부하 동일 분 3건 (트리거)
    print("\n[7] 영상 생성 실패 (DB 부하) 동일 분 3건 - 장애 알림 O")
    base_time = make_time(minutes_offset=30)
    for i in range(3):
        payload = make_monitoring_payload(
            title="🚨 영상 생성 실패",
            activity_title="더빙/오디오 생성 실패",
            description="영상 생성 실패 - 더빙/오디오 생성 실패",
            time_str=base_time,  # 동일 분
        )
        result = post("/vt/webhook/monitoring", payload)
        status = result['body'].get('status')
        print(f"     DB 부하 #{i+1}: {status}")
        time.sleep(0.3)
    
    time.sleep(0.5)
    
    # 테스트 8: YouTube 다운로드 실패 3건
    print("\n[8] YouTube 다운로드 실패 3건 - 장애 알림 O (3번째에서)")
    for i in range(3):
        payload = make_monitoring_payload(
            title="🚨 외부 URL 다운로드 실패",
            activity_title="외부 URL 다운로드 실패",
            description="영상 업로드 실패 - YouTube URL 다운로드 실패",
            time_str=make_time(minutes_offset=40 + i),
        )
        result = post("/vt/webhook/monitoring", payload)
        status = result['body'].get('status')
        print(f"     YT 다운로드 #{i+1}: {status}")
        time.sleep(0.3)
    
    time.sleep(0.5)
    
    # 테스트 9: Video 파일 업로드 실패 3건
    print("\n[9] Video 파일 업로드 실패 3건 - 장애 알림 O (3번째에서)")
    for i in range(3):
        payload = make_monitoring_payload(
            title="🚨 업로드 실패",
            activity_title="Video 파일 업로드 실패",
            description="영상 업로드 실패 - Video 파일 업로드 실패",
            time_str=make_time(minutes_offset=50 + i),
        )
        result = post("/vt/webhook/monitoring", payload)
        status = result['body'].get('status')
        print(f"     Video 업로드 #{i+1}: {status}")
        time.sleep(0.3)
    
    time.sleep(0.5)
    
    # 테스트 10: 알 수 없는 에러 타입
    print("\n[10] 알 수 없는 에러 타입 - 장애 알림 X")
    payload = make_monitoring_payload(
        title="🚨 알 수 없는 에러",
        activity_title="뭔가 실패",
        description="알 수 없는 실패",
        time_str=make_time(minutes_offset=60),
    )
    result = post("/vt/webhook/monitoring", payload)
    print_result("알 수 없는 에러", result, "recorded")

    # =========================================================
    print("\n" + "=" * 60)
    print("E2E 테스트 완료")
    print("=" * 60)
    print("\nTeams 채널에서 확인할 메시지:")
    print("  [포워딩 채널]")
    print("    - AUDIO_PIPELINE_FAILED 1건")
    print("    - VIDEO_QUEUE_FULL 1건")
    print("    - TIMEOUT 3건")
    print("    - API_ERROR 3건")
    print("  [장애 알림 채널]")
    print("    - TIMEOUT 장애 1건")
    print("    - API_ERROR 장애 1건")
    print("    - DB 부하 장애 1건")
    print("    - YouTube 다운로드 장애 1건")
    print("    - Video 업로드 장애 1건")


if __name__ == "__main__":
    run_tests()