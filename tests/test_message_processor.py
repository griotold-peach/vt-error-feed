# tests/test_message_processor.py
from unittest.mock import AsyncMock, patch
import pytest

from app.services.message_processor import MessageProcessor
from app.adapters.messagecard import VTWebhookMessage


# --- 픽스처 ----------------------------------------------------------------

@pytest.fixture
def processor():
    """MessageProcessor 인스턴스"""
    return MessageProcessor()


@pytest.fixture
def feed1_card():
    """Feed1 카드"""
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
    """Feed2 카드"""
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
    """Feed1 처리 시 handle_raw_alert 호출"""
    with patch('app.services.message_processor.handle_raw_alert',
               new_callable=AsyncMock, return_value=True) as mock_handler:
        
        result = await processor.process_feed1(feed1_card)
        
        # Handler 호출 확인
        mock_handler.assert_called_once_with(feed1_card)
        assert result is True


@pytest.mark.anyio
async def test_process_feed1_returns_true_when_forwarded(processor, feed1_card):
    """포워딩된 경우 True 반환"""
    with patch('app.services.message_processor.handle_raw_alert',
               new_callable=AsyncMock, return_value=True):
        
        result = await processor.process_feed1(feed1_card)
        assert result is True


@pytest.mark.anyio
async def test_process_feed1_returns_false_when_dropped(processor, feed1_card):
    """드롭된 경우 False 반환"""
    with patch('app.services.message_processor.handle_raw_alert',
               new_callable=AsyncMock, return_value=False):
        
        result = await processor.process_feed1(feed1_card)
        assert result is False


@pytest.mark.anyio
async def test_process_feed1_handler_exception(processor, feed1_card):
    """Handler에서 예외 발생 시 전파"""
    with patch('app.services.message_processor.handle_raw_alert',
               new_callable=AsyncMock, side_effect=Exception("Handler error")):
        
        with pytest.raises(Exception, match="Handler error"):
            await processor.process_feed1(feed1_card)


# --- process_feed2 테스트 --------------------------------------------------

@pytest.mark.anyio
async def test_process_feed2_calls_handler(processor, feed2_card):
    """Feed2 처리 시 handle_monitoring_alert 호출"""
    with patch('app.services.message_processor.handle_monitoring_alert',
               new_callable=AsyncMock, return_value=False) as mock_handler:
        
        result = await processor.process_feed2(feed2_card)
        
        # Handler 호출 확인
        mock_handler.assert_called_once_with(feed2_card)
        assert result is False


@pytest.mark.anyio
async def test_process_feed2_returns_true_when_incident(processor, feed2_card):
    """장애 발생 시 True 반환"""
    with patch('app.services.message_processor.handle_monitoring_alert',
               new_callable=AsyncMock, return_value=True):
        
        result = await processor.process_feed2(feed2_card)
        assert result is True


@pytest.mark.anyio
async def test_process_feed2_returns_false_when_no_incident(processor, feed2_card):
    """장애가 아닌 경우 False 반환"""
    with patch('app.services.message_processor.handle_monitoring_alert',
               new_callable=AsyncMock, return_value=False):
        
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
    
    with patch('app.services.message_processor.handle_monitoring_alert',
               new_callable=AsyncMock, return_value=False):
        
        # Description이 없어도 에러 없이 처리
        result = await processor.process_feed2(card)
        assert result is False


# --- 엣지 케이스 -----------------------------------------------------------

@pytest.mark.anyio
async def test_process_feed1_with_none_title(processor):
    """타이틀이 None인 카드"""
    card = VTWebhookMessage(summary="Test")
    
    with patch('app.services.message_processor.handle_raw_alert',
               new_callable=AsyncMock, return_value=True):
        
        # 예외 없이 처리됨
        result = await processor.process_feed1(card)
        assert result is True


@pytest.mark.anyio
async def test_process_feed2_with_empty_sections(processor):
    """sections가 비어있는 카드"""
    card = VTWebhookMessage(title="Test", sections=[])
    
    with patch('app.services.message_processor.handle_monitoring_alert',
               new_callable=AsyncMock, return_value=False):
        
        # 에러 없이 처리됨
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
    
    with patch('app.services.message_processor.handle_raw_alert',
               new_callable=AsyncMock, return_value=True):
        
        for card in cards:
            result = await processor.process_feed1(card)
            assert result is True


# --- 통합 시나리오 ---------------------------------------------------------

@pytest.mark.anyio
async def test_sequential_processing(processor, feed1_card, feed2_card):
    """순차적으로 여러 카드 처리"""
    with patch('app.services.message_processor.handle_raw_alert',
               new_callable=AsyncMock, return_value=True) as mock_feed1, \
         patch('app.services.message_processor.handle_monitoring_alert',
               new_callable=AsyncMock, return_value=False) as mock_feed2:
        
        # Feed1 처리
        result1 = await processor.process_feed1(feed1_card)
        assert result1 is True
        
        # Feed2 처리
        result2 = await processor.process_feed2(feed2_card)
        assert result2 is False
        
        # 각각 한 번씩 호출됨
        mock_feed1.assert_called_once()
        mock_feed2.assert_called_once()