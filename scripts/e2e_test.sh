#!/bin/bash
# scripts/e2e_test.sh

BASE_URL="http://localhost:8000"

echo "=== anomaly 상태 초기화 ==="
curl -s -X POST "$BASE_URL/debug/reset"
echo ""

echo "=== Feed1 (live-api) 테스트 ==="

echo ""
echo "1. ENGINE_ERROR (포워딩 X, 장애 알림 X)"
curl -s -X POST "$BASE_URL/vt/webhook/live-api" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "MessageCard",
    "context": "https://schema.org/extensions",
    "themeColor": "FF0000",
    "title": "🚨 API-Video-Translator Translate Project Exception.",
    "summary": "웹훅 처리중 실패가 발생했습니다.",
    "sections": [{
      "activityTitle": "웹훅 처리중 실패가 발생했습니다.",
      "facts": [
        {"name": "Project", "value": "test-001"},
        {"name": "Error Message", "value": "Received Failed Webhook Event by Live API."},
        {"name": "Error Detail", "value": "Failure Reason: ENGINE_ERROR Engine Error Code: NO_VOICE_DETECTED_VAD"},
        {"name": "Time", "value": "2025-01-01T12:00:00.000000000Z[Etc/UTC]"}
      ]
    }]
  }'
echo ""

echo ""
echo "2. AUDIO_PIPELINE_FAILED (포워딩 O, 장애 알림 X)"
curl -s -X POST "$BASE_URL/vt/webhook/live-api" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "MessageCard",
    "context": "https://schema.org/extensions",
    "themeColor": "FF0000",
    "title": "🚨 API-Video-Translator Translate Project Exception.",
    "summary": "웹훅 처리중 실패가 발생했습니다.",
    "sections": [{
      "activityTitle": "웹훅 처리중 실패가 발생했습니다.",
      "facts": [
        {"name": "Project", "value": "test-002"},
        {"name": "Error Message", "value": "Received Failed Webhook Event by Live API."},
        {"name": "Error Detail", "value": "Failure Reason: AUDIO_PIPELINE_FAILED Engine Error Code: SOMETHING"},
        {"name": "Time", "value": "2025-01-01T12:01:00.000000000Z[Etc/UTC]"}
      ]
    }]
  }'
echo ""

echo ""
echo "3. TIMEOUT 3건 (포워딩 O x3, 장애 알림 O x1)"
for i in 1 2 3; do
  echo "  TIMEOUT #$i"
  curl -s -X POST "$BASE_URL/vt/webhook/live-api" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"MessageCard\",
      \"context\": \"https://schema.org/extensions\",
      \"themeColor\": \"FF0000\",
      \"title\": \"🚨 API-Video-Translator Translate Project Exception.\",
      \"summary\": \"웹훅 처리중 실패가 발생했습니다.\",
      \"sections\": [{
        \"activityTitle\": \"웹훅 처리중 실패가 발생했습니다.\",
        \"facts\": [
          {\"name\": \"Project\", \"value\": \"test-timeout-$i\"},
          {\"name\": \"Error Message\", \"value\": \"Received Failed Webhook Event by Live API.\"},
          {\"name\": \"Error Detail\", \"value\": \"Failure Reason: TIMEOUT\"},
          {\"name\": \"Time\", \"value\": \"2025-01-01T12:0$i:00.000000000Z[Etc/UTC]\"}
        ]
      }]
    }"
  echo ""
done

echo ""
echo "=== Feed2 (monitoring) 테스트 ==="

echo ""
echo "4. 영상 생성 실패 (DB 부하) 동일 분 3건 (장애 알림 O)"
for i in 1 2 3; do
  echo "  DB 부하 #$i"
  curl -s -X POST "$BASE_URL/vt/webhook/monitoring" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"MessageCard\",
      \"context\": \"https://schema.org/extensions\",
      \"themeColor\": \"FFA500\",
      \"title\": \"🚨 영상 생성 실패\",
      \"summary\": \"영상 생성 실패 - 더빙/오디오 생성 실패\",
      \"sections\": [{
        \"activityTitle\": \"더빙/오디오 생성 실패\",
        \"facts\": [
          {\"name\": \"Description\", \"value\": \"영상 생성 실패 - 더빙/오디오 생성 실패\"},
          {\"name\": \"Time\", \"value\": \"2025-01-01T13:00:0${i}0.000000000Z[Etc/UTC]\"}
        ]
      }]
    }"
  echo ""
done

echo ""
echo "5. YouTube 다운로드 실패 3건 (장애 알림 O)"
for i in 1 2 3; do
  echo "  YT 다운로드 #$i"
  curl -s -X POST "$BASE_URL/vt/webhook/monitoring" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"MessageCard\",
      \"context\": \"https://schema.org/extensions\",
      \"themeColor\": \"FFA500\",
      \"title\": \"🚨 외부 URL 다운로드 실패\",
      \"summary\": \"영상 생성 실패 - 더빙/오디오 생성 실패\",
      \"sections\": [{
        \"activityTitle\": \"외부 URL 다운로드 실패\",
        \"facts\": [
          {\"name\": \"Description\", \"value\": \"영상 업로드 실패 - YouTube URL 다운로드 실패\"},
          {\"name\": \"Time\", \"value\": \"2025-01-01T14:0$i:00.000000000Z[Etc/UTC]\"}
        ]
      }]
    }"
  echo ""
done

echo ""
echo "=== E2E 테스트 완료 ==="
echo "Teams 채널에서 결과 확인하세요:"
echo "- 포워딩 채널: AUDIO_PIPELINE_FAILED 1건, TIMEOUT 3건"
echo "- 장애 알림 채널: TIMEOUT 1건, DB부하 1건, YT다운로드 1건"