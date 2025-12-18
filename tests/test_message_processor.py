# tests/test_message_processor.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.adapters.messagecard import VTWebhookMessage
from app.application.services.message_processor import MessageProcessor


# --- 픽스처 ----------------------------------------------------------------

@pytest.fixture
def processor():
    """MessageProcessor 인스턴스"""
    return MessageProcessor()


@pytest.fixture
def feed1_card():
    """Feed1 테스트 카드"""
    return VTWebhookMessage(
        title="🚨 API-Video-Translator Exception",
        summary="웹훅 처리중 실패가 발생했습니다.",
        sections=[{
            "facts": [
                {"name": "Project", "value": "276459"},
                {"name": "Error Detail", "value": "Failure Reason: TIMEOUT"}
            ]
        }]
    )


@pytest.fixture
def feed2_card():
    """Feed2 테스트 카드"""
    return VTWebhookMessage(
        title="🚨 업로드 실패",
        summary="An exception occurred",
        sections=[{
            "facts": [
                {"name": "Description", "value": "<p>영상 생성 실패 - 더빙/오디오 생성 실패</p>"},
                {"name": "Time", "value": "2025-12-17T23:44:04.151606+0000[UTC]"}
            ]
        }]
    )


# --- process_feed1 테스트 --------------------------------------------------

@pytest.mark.anyio
async def test_process_feed1_calls_handler(processor, feed1_card):
    """Feed1 처리 시 AlertHandler 호출"""
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_raw_alert = AsyncMock(return_value=True)
        mock_container.alert_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        result = await processor.process_feed1(feed1_card)
        
        assert result is True
        mock_handler.handle_raw_alert.assert_called_once()


@pytest.mark.anyio
async def test_process_feed1_returns_true_when_forwarded(processor, feed1_card):
    """포워딩 시 True 반환"""
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_raw_alert = AsyncMock(return_value=True)
        mock_container.alert_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        result = await processor.process_feed1(feed1_card)
        
        assert result is True


@pytest.mark.anyio
async def test_process_feed1_returns_false_when_dropped(processor):
    """드롭 시 False 반환"""
    card = VTWebhookMessage(
        title="Test",
        sections=[{
            "facts": [
                {"name": "Error Detail", "value": "Failure Reason: ENGINE_ERROR"}
            ]
        }]
    )
    
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_raw_alert = AsyncMock(return_value=False)
        mock_container.alert_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        result = await processor.process_feed1(card)
        
        assert result is False


@pytest.mark.anyio
async def test_process_feed1_handler_exception(processor, feed1_card):
    """Handler에서 예외 발생 시 처리"""
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_raw_alert = AsyncMock(side_effect=Exception("Handler error"))
        mock_container.alert_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        # 예외 발생 확인
        with pytest.raises(Exception, match="Handler error"):
            await processor.process_feed1(feed1_card)


# --- process_feed2 테스트 --------------------------------------------------

@pytest.mark.anyio
async def test_process_feed2_calls_handler(processor, feed2_card):
    """Feed2 처리 시 MonitoringHandler 호출"""
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_monitoring_alert = AsyncMock(return_value=False)
        mock_container.monitoring_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        result = await processor.process_feed2(feed2_card)
        
        mock_handler.handle_monitoring_alert.assert_called_once()


@pytest.mark.anyio
async def test_process_feed2_returns_true_when_incident(processor):
    """장애 발생 시 True 반환"""
    card = VTWebhookMessage(
        title="Test",
        sections=[{
            "facts": [
                {"name": "Description", "value": "영상 생성 실패 - 더빙/오디오 생성 실패"}
            ]
        }]
    )
    
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_monitoring_alert = AsyncMock(return_value=True)
        mock_container.monitoring_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        result = await processor.process_feed2(card)
        
        assert result is True


@pytest.mark.anyio
async def test_process_feed2_returns_false_when_no_incident(processor, feed2_card):
    """장애 미발생 시 False 반환"""
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_monitoring_alert = AsyncMock(return_value=False)
        mock_container.monitoring_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        result = await processor.process_feed2(feed2_card)
        
        assert result is False


@pytest.mark.anyio
async def test_process_feed2_handles_missing_description(processor):
    """Description이 없는 경우 정상 처리"""
    card = VTWebhookMessage(
        title="🚨 업로드 실패",
        sections=[{
            "facts": [
                {"name": "Time", "value": "2025-12-17"}
            ]
        }]
    )
    
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_monitoring_alert = AsyncMock(return_value=False)
        mock_container.monitoring_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        result = await processor.process_feed2(card)
        
        assert result is False


# --- 엣지 케이스 테스트 ----------------------------------------------------

@pytest.mark.anyio
async def test_process_feed1_with_none_title(processor):
    """타이틀이 None인 카드"""
    card = VTWebhookMessage(summary="Test")
    
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_raw_alert = AsyncMock(return_value=True)
        mock_container.alert_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        result = await processor.process_feed1(card)
        
        assert result is True


@pytest.mark.anyio
async def test_process_feed2_with_empty_sections(processor):
    """sections가 비어있는 카드"""
    card = VTWebhookMessage(title="Test", sections=[])
    
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_monitoring_alert = AsyncMock(return_value=False)
        mock_container.monitoring_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        result = await processor.process_feed2(card)
        
        assert result is False


@pytest.mark.anyio
async def test_process_feed1_various_cards(processor):
    """다양한 카드 구조 테스트"""
    cards = [
        VTWebhookMessage(title="Test1"),
        VTWebhookMessage(title="Test2", summary="Summary"),
        VTWebhookMessage(title="Test3", sections=[{"facts": []}]),
    ]
    
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_handler = MagicMock()
        mock_handler.handle_raw_alert = AsyncMock(return_value=True)
        mock_container.alert_handler = mock_handler
        mock_get_container.return_value = mock_container
        
        for card in cards:
            result = await processor.process_feed1(card)
            assert result is True


@pytest.mark.anyio
async def test_sequential_processing(processor, feed1_card, feed2_card):
    """순차적으로 여러 카드 처리"""
    with patch('app.application.services.message_processor.get_container') as mock_get_container:
        mock_container = MagicMock()
        
        mock_alert_handler = MagicMock()
        mock_alert_handler.handle_raw_alert = AsyncMock(return_value=True)
        
        mock_monitoring_handler = MagicMock()
        mock_monitoring_handler.handle_monitoring_alert = AsyncMock(return_value=False)
        
        mock_container.alert_handler = mock_alert_handler
        mock_container.monitoring_handler = mock_monitoring_handler
        
        mock_get_container.return_value = mock_container
        
        result1 = await processor.process_feed1(feed1_card)
        result2 = await processor.process_feed2(feed2_card)
        
        assert result1 is True
        assert result2 is False