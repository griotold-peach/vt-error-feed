# app/services/message_processor.py
"""
Feed별 메시지 처리 로직
"""
import re
from typing import Optional

from app.adapters.messagecard import VTWebhookMessage
from app.container import get_container


class MessageProcessor:
    """Feed별 메시지 처리 및 로깅"""
    
    async def process_feed1(self, card: VTWebhookMessage) -> bool:
        """
        Feed1 메시지 처리
        
        Returns:
            포워딩 여부
        """
        print(f"📨 Processing Feed1: {card.title}")
        
        # 컨테이너에서 AlertHandler 가져오기
        container = get_container()
        handler = container.alert_handler
        
        # 처리
        payload = card.model_dump() if hasattr(card, 'model_dump') else card.dict()
        forwarded = await handler.handle_raw_alert(payload)
        
        if forwarded:
            print(f"✅ Feed1 forwarded to VT Error Feed Prod")
        else:
            print(f"⏭️ Feed1 dropped (not critical)")
        
        return forwarded
    
    async def process_feed2(self, card: VTWebhookMessage) -> bool:
        """
        Feed2 메시지 처리
        
        Returns:
            장애 발생 여부
        """
        print(f"📨 Processing Feed2: {card.title}")
        
        # Description 추출 및 출력
        desc = card.get_fact("Description")
        if desc:
            desc_clean = re.sub(r'<[^>]+>', '', desc)
            print(f"📋 Description: {desc_clean}")
        
        # 컨테이너에서 MonitoringHandler 가져오기
        container = get_container()
        handler = container.monitoring_handler
        
        # 처리
        payload = card.model_dump() if hasattr(card, 'model_dump') else card.dict()
        triggered = await handler.handle_monitoring_alert(payload)
        
        if triggered:
            print(f"🚨 Feed2 incident triggered!")
        else:
            print(f"📊 Feed2 processed")
        
        return triggered