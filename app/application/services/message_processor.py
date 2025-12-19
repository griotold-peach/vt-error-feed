# app/services/message_processor.py
"""
Feed별 메시지 처리 로직
"""
import re
from typing import Optional
import logging

from app.adapters.messagecard import VTWebhookMessage
from app.container import get_container

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Feed별 메시지 처리 및 로깅"""
    
    async def process_feed1(self, card: VTWebhookMessage) -> bool:
        """
        Feed1 메시지 처리

        Returns:
            포워딩 여부
        """
        logger.info(f"📨 Processing Feed1: {card.title}")

        # Error Detail 출력 추가
        error_detail = card.get_fact("Error Detail")
        if error_detail:
            error_clean = re.sub(r'<[^>]+>', '', error_detail)
            logger.info(f"📋 Error Detail: {error_clean}")

        # Error Message 출력 (있으면)
        error_message = card.get_fact("Error Message")
        if error_message:
            error_clean = re.sub(r'<[^>]+>', '', error_message)
            logger.info(f"📋 Error Message: {error_clean}")
        
        # 컨테이너에서 AlertHandler 가져오기
        container = get_container()
        handler = container.alert_handler
        
        # 처리
        payload = card.model_dump() if hasattr(card, 'model_dump') else card.model_dump()
        forwarded = await handler.handle_raw_alert(payload)

        if forwarded:
            logger.info(f"✅ Feed1 forwarded to VT Error Feed Prod")
        else:
            logger.info(f"⏭️ Feed1 dropped (not critical)")

        return forwarded
    
    async def process_feed2(self, card: VTWebhookMessage) -> bool:
        """
        Feed2 메시지 처리

        Returns:
            장애 발생 여부
        """
        logger.info(f"📨 Processing Feed2: {card.title}")

        # Description 추출 및 출력
        desc = card.get_fact("Description")
        if desc:
            desc_clean = re.sub(r'<[^>]+>', '', desc)
            logger.info(f"📋 Description: {desc_clean}")
        
        # 컨테이너에서 MonitoringHandler 가져오기
        container = get_container()
        handler = container.monitoring_handler
        
        # 처리
        payload = card.model_dump() if hasattr(card, 'model_dump') else card.model_dump()
        triggered = await handler.handle_monitoring_alert(payload)

        if triggered:
            logger.info(f"🚨 Feed2 incident triggered!")
        else:
            logger.info(f"📊 Feed2 processed")

        return triggered