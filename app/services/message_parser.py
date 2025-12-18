# app/services/message_parser.py
"""
Teams 메시지 파싱 및 판별 유틸리티
"""
from typing import Optional
import json

from app.adapters.messagecard import VTWebhookMessage


class TeamsMessageParser:
    """Teams 메시지 파싱 및 타입 판별"""
    
    @staticmethod
    def is_webhook_message(message: dict) -> bool:
        """Incoming Webhook 메시지 여부"""
        from_data = message.get("from", {})
        return bool(from_data.get("application"))
    
    @staticmethod
    def is_card_message(message: dict) -> bool:
        """O365 Connector Card 메시지 여부"""
        attachments = message.get("attachments", [])
        
        for attachment in attachments:
            content_type = attachment.get("contentType", "")
            if "o365connector" in content_type.lower():
                return True
        
        return False
    
    @staticmethod
    def parse_card(message: dict) -> Optional[VTWebhookMessage]:
        """
        메시지에서 O365 Card를 파싱하여 VTWebhookMessage 반환
        
        Args:
            message: Graph API 메시지 객체
            
        Returns:
            VTWebhookMessage 또는 None (파싱 실패 시)
        """
        attachments = message.get("attachments", [])
        if not attachments:
            return None
        
        attachment = attachments[0]
        content_type = attachment.get("contentType", "")
        
        if "o365connector" not in content_type.lower():
            return None
        
        content_str = attachment.get("content", "{}")
        try:
            card_dict = json.loads(content_str)
            return VTWebhookMessage.model_validate(card_dict)
        except (json.JSONDecodeError, Exception):
            return None