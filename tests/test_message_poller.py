# tests/test_message_poller.py
import asyncio, json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime, timezone

from app.application.services.message_poller import MessagePoller
from app.adapters.graph_client import GraphClient
from app.application.services.message_parser import TeamsMessageParser
from app.application.services.message_processor import MessageProcessor
from app.application.services.duplicate_tracker import DuplicateTracker
from app.adapters.messagecard import VTWebhookMessage
from app.config import (  # ✅ 파일 상단
    TEAMS_TEAM_ID,
    TEAMS_FEED1_CHANNEL_ID,
    TEAMS_FEED2_CHANNEL_ID
)


# --- 픽스처 ----------------------------------------------------------------

@pytest.fixture
def graph_client():
    """Mock GraphClient"""
    return MagicMock(spec=GraphClient)


@pytest.fixture
def parser():
    """Mock TeamsMessageParser"""
    return MagicMock(spec=TeamsMessageParser)


@pytest.fixture
def processor():
    """Mock MessageProcessor"""
    mock = MagicMock(spec=MessageProcessor)
    mock.process_feed1 = AsyncMock(return_value=True)
    mock.process_feed2 = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def tracker():
    """Mock DuplicateTracker"""
    return MagicMock(spec=DuplicateTracker)


@pytest.fixture
def poller(graph_client, parser, processor, tracker):
    """MessagePoller 인스턴스"""
    return MessagePoller(
        graph_client=graph_client,
        parser=parser,
        processor=processor,
        duplicate_tracker=tracker
    )


# --- Helper 데이터 ---------------------------------------------------------

def make_graph_message(msg_id: str = "test123") -> dict:
    """Graph API 메시지 구조"""
    return {
        "id": msg_id,
        "createdDateTime": "2025-12-17T22:30:24.282Z",
        "from": {
            "application": {
                "displayName": "vt prod monitoring"
            }
        },
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.teams.card.o365connector",
                "content": '{"title": "Test"}'
            }
        ],
    }


# --- 초기화 테스트 ---------------------------------------------------------

def test_poller_initialization_with_defaults(graph_client):
    """기본값으로 초기화"""
    poller = MessagePoller(graph_client)
    
    assert poller.graph == graph_client
    assert isinstance(poller.parser, TeamsMessageParser)
    assert isinstance(poller.processor, MessageProcessor)
    assert isinstance(poller.tracker, DuplicateTracker)
    assert poller.last_check == {}
    assert poller.running is False


def test_poller_initialization_with_mocks(graph_client, parser, processor, tracker):
    """Mock 객체로 초기화"""
    poller = MessagePoller(graph_client, parser, processor, tracker)
    
    assert poller.graph == graph_client
    assert poller.parser == parser
    assert poller.processor == processor
    assert poller.tracker == tracker


# --- _process_single_message 테스트 ----------------------------------------

@pytest.mark.anyio
async def test_process_single_message_skips_duplicate(poller, tracker):
    """중복 메시지는 스킵"""
    tracker.is_processed.return_value = True
    
    message = make_graph_message("duplicate_id")
    
    await poller._process_single_message(message, "feed1")
    
    # 중복 체크만 하고 나머지는 호출 안됨
    tracker.is_processed.assert_called_once_with("duplicate_id")
    poller.parser.is_webhook_message.assert_not_called()


@pytest.mark.anyio
async def test_process_single_message_skips_user_message(poller, tracker, parser):
    """사용자 메시지는 스킵"""
    tracker.is_processed.return_value = False
    parser.is_webhook_message.return_value = False
    
    message = make_graph_message()
    
    await poller._process_single_message(message, "feed1")
    
    parser.is_webhook_message.assert_called_once()
    parser.is_card_message.assert_not_called()


@pytest.mark.anyio
async def test_process_single_message_skips_non_card(poller, tracker, parser):
    """Card가 아닌 메시지는 스킵"""
    tracker.is_processed.return_value = False
    parser.is_webhook_message.return_value = True
    parser.is_card_message.return_value = False
    
    message = make_graph_message()
    
    await poller._process_single_message(message, "feed1")
    
    parser.is_card_message.assert_called_once()
    parser.parse_card.assert_not_called()


@pytest.mark.anyio
async def test_process_single_message_skips_parse_failure(poller, tracker, parser):
    """파싱 실패 시 처리 안함"""
    tracker.is_processed.return_value = False
    parser.is_webhook_message.return_value = True
    parser.is_card_message.return_value = True
    parser.parse_card.return_value = None
    
    message = make_graph_message()
    
    await poller._process_single_message(message, "feed1")
    
    parser.parse_card.assert_called_once()
    poller.processor.process_feed1.assert_not_called()


@pytest.mark.anyio
async def test_process_single_message_feed1_success(poller, tracker, parser, processor):
    """Feed1 메시지 정상 처리"""
    tracker.is_processed.return_value = False
    parser.is_webhook_message.return_value = True
    parser.is_card_message.return_value = True
    
    card = VTWebhookMessage(title="Test Card")
    parser.parse_card.return_value = card
    
    message = make_graph_message("msg123")
    
    await poller._process_single_message(message, "feed1")
    
    # Feed1 processor 호출
    processor.process_feed1.assert_called_once_with(card)
    processor.process_feed2.assert_not_called()
    
    # 처리 완료 기록
    tracker.mark_processed.assert_called_once_with("msg123")


@pytest.mark.anyio
async def test_process_single_message_feed2_success(poller, tracker, parser, processor):
    """Feed2 메시지 정상 처리"""
    tracker.is_processed.return_value = False
    parser.is_webhook_message.return_value = True
    parser.is_card_message.return_value = True
    
    card = VTWebhookMessage(title="Test Card")
    parser.parse_card.return_value = card
    
    message = make_graph_message("msg456")
    
    await poller._process_single_message(message, "feed2")
    
    # Feed2 processor 호출
    processor.process_feed2.assert_called_once_with(card)
    processor.process_feed1.assert_not_called()
    
    # 처리 완료 기록
    tracker.mark_processed.assert_called_once_with("msg456")


# --- poll_channel 테스트 ---------------------------------------------------

@pytest.mark.anyio
async def test_poll_channel_success(poller, graph_client):
    """채널 polling 성공"""
    messages = [
        make_graph_message("msg1"),
        make_graph_message("msg2"),
    ]
    graph_client.get_channel_messages = AsyncMock(return_value=messages)
    
    # _process_single_message를 mock
    poller._process_single_message = AsyncMock()
    
    await poller.poll_channel("test_channel_id", "feed1")
    
    # Graph API 호출 확인
    graph_client.get_channel_messages.assert_called_once()
    
    # 각 메시지 처리 확인
    assert poller._process_single_message.call_count == 2
    
    # last_check 업데이트 확인
    assert "test_channel_id" in poller.last_check


@pytest.mark.anyio
async def test_poll_channel_with_since_parameter(poller, graph_client):
    """since 파라미터와 함께 polling"""
    poller.last_check["channel123"] = "2025-12-17T10:00:00Z"
    
    graph_client.get_channel_messages = AsyncMock(return_value=[])
    poller._process_single_message = AsyncMock()
    
    await poller.poll_channel("channel123", "feed1")
    
    # since 파라미터 전달 확인
    call_kwargs = graph_client.get_channel_messages.call_args.kwargs
    assert call_kwargs["since"] == "2025-12-17T10:00:00Z"


@pytest.mark.anyio
async def test_poll_channel_handles_exception(poller, graph_client, caplog):
    """polling 중 예외 발생 시 로깅"""
    graph_client.get_channel_messages = AsyncMock(
        side_effect=Exception("Network error")
    )
    
    await poller.poll_channel("test_channel", "feed1")
    
    # 로그에 에러 기록 확인
    assert "Polling error for feed1" in caplog.text


@pytest.mark.anyio
async def test_poll_channel_empty_messages(poller, graph_client):
    """메시지가 없을 때"""
    graph_client.get_channel_messages = AsyncMock(return_value=[])
    poller._process_single_message = AsyncMock()
    
    await poller.poll_channel("test_channel", "feed1")
    
    # 처리할 메시지 없음
    poller._process_single_message.assert_not_called()
    
    # last_check는 업데이트됨
    assert "test_channel" in poller.last_check


# --- start/stop 테스트 -----------------------------------------------------

@pytest.mark.anyio
async def test_start_initializes_last_check(poller):
    """start 시 last_check 초기화"""
    poller.poll_channel = AsyncMock()
    
    # start 실행 후 즉시 중지
    async def stop_after_first_iteration():
        await asyncio.sleep(0.01)
        poller.stop()

    await asyncio.gather(
        poller.start(poll_interval=0.01),
        stop_after_first_iteration()
    )
    
    # last_check가 초기화되었는지 확인
    assert TEAMS_FEED1_CHANNEL_ID in poller.last_check
    assert TEAMS_FEED2_CHANNEL_ID in poller.last_check


@pytest.mark.anyio
async def test_start_polls_both_channels(poller):
    """start 시 두 채널 모두 polling"""
    poller.poll_channel = AsyncMock()
    
    async def stop_after_first_iteration():
        await asyncio.sleep(0.01)
        poller.stop()

    await asyncio.gather(
        poller.start(poll_interval=0.01),
        stop_after_first_iteration()
    )
    
    # 두 채널 모두 polling 확인
    calls = poller.poll_channel.call_args_list
    feed_types = [call.args[1] for call in calls]
    assert "feed1" in feed_types
    assert "feed2" in feed_types


def test_stop_sets_running_false(poller):
    """stop 호출 시 running이 False로 변경"""
    poller.running = True
    
    poller.stop()
    
    assert poller.running is False


@pytest.mark.anyio
async def test_start_continues_on_error(poller, caplog):
    """에러 발생 시에도 polling 계속"""
    call_count = 0
    
    async def mock_poll_channel(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("First error")
        # 두 번째 호출 후 중지
        if call_count >= 2:
            poller.stop()
    
    poller.poll_channel = mock_poll_channel
    
    await poller.start(poll_interval=0.01)
    
    # 에러 발생 후에도 계속 실행되었는지 확인
    assert call_count >= 2
    assert "Poller loop error" in caplog.text


# --- 통합 테스트 -----------------------------------------------------------

@pytest.mark.anyio
async def test_end_to_end_feed1_processing(graph_client):
    """Feed1 전체 플로우 통합 테스트"""
    poller = MessagePoller(graph_client)
    
    card_dict = {
        "title": "🚨 Error",
        "summary": "웹훅 처리중 실패",
        "sections": [{
            "facts": [
                {"name": "Error Detail", "value": "Failure Reason: TIMEOUT"}
            ]
        }]
    }
    
    message = {
        "id": "integration_test_123",
        "createdDateTime": "2025-12-17T22:30:24.282Z",
        "from": {"application": {"displayName": "webhook"}},
        "attachments": [{
            "contentType": "application/vnd.microsoft.teams.card.o365connector",
            "content": json.dumps(card_dict)
        }]
    }
    
    graph_client.get_channel_messages = AsyncMock(return_value=[message])
    
    # ✅ get_container를 Mock!
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_raw_alert = AsyncMock(return_value=True)
        mock_container.alert_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        await poller.poll_channel("test_channel", "feed1")
    
    # 메시지가 처리되었는지 확인
    assert poller.tracker.is_processed("integration_test_123")


@pytest.mark.anyio
async def test_end_to_end_duplicate_prevention(graph_client):
    """중복 방지 통합 테스트"""
    poller = MessagePoller(graph_client)
    
    message = {
        "id": "duplicate_test",
        "createdDateTime": "2025-12-17T22:30:24.282Z",
        "from": {"application": {"displayName": "webhook"}},
        "attachments": [{
            "contentType": "application/vnd.microsoft.teams.card.o365connector",
            "content": json.dumps({"title": "Test"})
        }]
    }
    
    graph_client.get_channel_messages = AsyncMock(return_value=[message])
    
    # ✅ get_container를 Mock!
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_raw_alert = AsyncMock()
        mock_container.alert_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        # 첫 번째 polling
        await poller.poll_channel("test_channel", "feed1")
        assert mock_handler.handle_raw_alert.call_count == 1
        
        # 두 번째 polling (같은 메시지)
        await poller.poll_channel("test_channel", "feed1")
        
        # 중복이므로 handler가 다시 호출되지 않음
        assert mock_handler.handle_raw_alert.call_count == 1