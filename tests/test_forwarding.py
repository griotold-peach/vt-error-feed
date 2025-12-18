# tests/test_forwarding.py
from app.domain.events import VTErrorEvent
from app.application.services.forwarding import should_forward


def make_event(
    *,
    failure_reason: str | None = None,
    error_message: str = "",
    error_detail: str = "",
    cause_or_stack_trace: str | None = None,
) -> VTErrorEvent:
    """
    VTErrorEvent 를 직접 만들어주는 헬퍼.
    forwarding 로직에서 쓰는 필드만 채워준다.
    """
    return VTErrorEvent(
        project="test-project",
        error_message=error_message,
        error_detail=error_detail,
        time="2025-01-01T00:00:00.000000000Z[Etc/UTC]",
        failure_reason=failure_reason,
        cause_or_stack_trace=cause_or_stack_trace,
    )


def test_should_forward_by_whitelist_failure_reason():
    """
    failure_reason 이 whitelist에 포함된 경우: 무조건 forward 대상.
    예: AUDIO_PIPELINE_FAILED (개선사항 1에서 사용하는 케이스)
    """
    event = make_event(
        failure_reason="AUDIO_PIPELINE_FAILED",
        error_message="Received Failed Webhook Event by Live API.",
        error_detail="Failure Reason: AUDIO_PIPELINE_FAILED Engine Error Code: NO_VOICE_DETECTED_VAD",
    )

    assert should_forward(event) is True


def test_should_not_forward_engine_error():
    """
    ENGINE_ERROR 는 사용자 입력 오류라서 forward 대상이 아니다.
    (failure_reason whitelist에도 없고, 특수 키워드에도 안 걸리는 케이스)
    """
    event = make_event(
        failure_reason="ENGINE_ERROR",
        error_message="Received Failed Webhook Event by Live API.",
        error_detail="Failure Reason: ENGINE_ERROR Engine Error Code: SOMETHING",
    )

    assert should_forward(event) is False


def test_should_forward_by_special_keyword_video_queue_full():
    """
    Failure Reason 이 없어도, Error Message / Cause 에
    VIDEO_QUEUE_FULL 같은 특수 키워드가 포함되면 forward 대상이 된다.
    (VT5001 / VIDEO_QUEUE_FULL 케이스)
    """
    event = make_event(
        failure_reason=None,
        error_message="Invalid FailureReason value: VIDEO_QUEUE_FULL",
        error_detail="Error Code VT5001 | Error Message Invalid FailureReason value: VIDEO_QUEUE_FULL",
        cause_or_stack_trace="Invalid FailureReason value: VIDEO_QUEUE_FULL",
    )

    assert should_forward(event) is True
