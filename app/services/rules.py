# app/services/rules.py

# 에러 피드 포워딩 대상 Failure Reason
FORWARD_FAILURE_REASONS = {
    "AUDIO_PIPELINE_FAILED",
    "VIDEO_PIPELINE_FAILED",
    "TIMEOUT",
    "API_ERROR",
}

# Failure Reason이 없어도 문자열에 이게 포함되면 포워딩
SPECIAL_FORWARD_KEYWORDS = (
    "VIDEO_QUEUE_FULL",
    "VT5001",
)
