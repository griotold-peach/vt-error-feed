# tests/test_events.py
from datetime import datetime
from app.domain.events import VTErrorEvent, MonitoringEvent
from app.adapters.messagecard import VTWebhookMessage, Section, Fact


def make_vt_message(time_value: str) -> VTWebhookMessage:
    """
    VTWebhookMessage를 만들어주는 작은 헬퍼.
    필요한 fact만 넣어준다.
    """
    return VTWebhookMessage(
        title="test",
        summary="test",
        sections=[
            Section(
                activityTitle="test-activity",
                facts=[
                    Fact(name="Project", value="test-project"),
                    Fact(name="Error Message", value="something bad happened"),
                    Fact(name="Error Detail", value="Failure Reason: TIMEOUT"),
                    Fact(name="Time", value=time_value),
                    Fact(name="Cause or Stack Trace", value="dummy stack"),
                ],
            )
        ],
    )


def test_event_datetime_parses_valid_timestamp():
    """
    정상 포맷의 Time 문자열이 들어왔을 때,
    event_datetime() 이 기대한 날짜/시간을 파싱하는지 확인한다.
    """
    time_str = "2025-01-01T12:34:56.123456789Z[Etc/UTC]"
    msg = make_vt_message(time_str)
    event = VTErrorEvent.from_message(msg)

    dt = event.event_datetime()

    assert isinstance(dt, datetime)
    assert dt.year == 2025
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 34
    assert dt.second == 56
    # 소수점 6자리까지만 유지되는지 확인 (123456)
    assert dt.microsecond == 123456


def test_event_datetime_handles_missing_time():
    """
    Time 값이 비어 있을 때도 예외 없이 datetime 을 돌려줘야 한다.
    구체적인 값까지는 검증하지 않고, datetime 인스턴스인지 정도만 확인한다.
    """
    msg = make_vt_message(time_value="")
    event = VTErrorEvent.from_message(msg)

    dt = event.event_datetime()

    assert isinstance(dt, datetime)


def test_event_datetime_handles_invalid_format():
    """
    Time 포맷이 이상해도 event_datetime() 이 예외를 던지지 않고
    datetime 을 반환해야 한다 (fallback 동작).
    """
    msg = make_vt_message(time_value="not-a-timestamp")
    event = VTErrorEvent.from_message(msg)

    dt = event.event_datetime()

    assert isinstance(dt, datetime)

def make_monitoring_message(time_value: str) -> VTWebhookMessage:
    """
    MonitoringEvent용 VTWebhookMessage 헬퍼.
    Feed2 구조: Description, Time
    """
    return VTWebhookMessage(
        title="🚨 영상 생성 실패",
        sections=[
            Section(
                activityTitle="더빙/오디오 생성 실패",
                facts=[
                    Fact(name="Description", value="영상 생성 실패 - 더빙/오디오 생성 실패"),
                    Fact(name="Time", value=time_value),
                ],
            )
        ],
    )


def test_monitoring_event_datetime_parses_valid_timestamp():
    """
    MonitoringEvent도 동일한 시간 파싱 로직이 동작하는지 확인.
    """
    time_str = "2025-01-01T12:34:56.123456789Z[Etc/UTC]"
    msg = make_monitoring_message(time_str)
    event = MonitoringEvent.from_message(msg)

    dt = event.event_datetime()

    assert isinstance(dt, datetime)
    assert dt.year == 2025
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 34
    assert dt.second == 56
    assert dt.microsecond == 123456


def test_monitoring_event_from_message():
    """
    MonitoringEvent.from_message()가 필드를 올바르게 추출하는지 확인.
    """
    msg = make_monitoring_message("2025-12-09T15:36:06.804587521Z[Etc/UTC]")
    event = MonitoringEvent.from_message(msg)

    assert event.title == "🚨 영상 생성 실패"
    assert event.description == "영상 생성 실패 - 더빙/오디오 생성 실패"
    assert "2025-12-09" in event.time
