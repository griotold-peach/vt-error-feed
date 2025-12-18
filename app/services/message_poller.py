"""
채널 메시지 Polling 서비스
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Set
import logging

from app.adapters.graph_client import GraphClient
from app.services.handler import handle_raw_alert
from app.services.monitoring import handle_monitoring_alert
from app.config import (
    TEAMS_TEAM_ID,
    TEAMS_FEED1_CHANNEL_ID,
    TEAMS_FEED2_CHANNEL_ID
)

logger = logging.getLogger(__name__)


class MessagePoller:
    """채널 메시지 주기적 Polling"""
    
    def __init__(self, graph_client: GraphClient):
        self.graph = graph_client
        self.last_check: Dict[str, str] = {}  # {channel_id: last_datetime}
        self.processed_ids: Set[str] = set()  # 중복 방지
        self.running = False
    
    def is_card_message(self, message: dict) -> bool:
        """Card 메시지 여부 확인 (Adaptive Card 또는 O365 Connector Card)"""
        attachments = message.get("attachments", [])
        
        for attachment in attachments:
            content_type = attachment.get("contentType", "")
            # Adaptive Card 또는 O365 Connector Card
            if "adaptive" in content_type.lower() or "o365connector" in content_type.lower():
                return True
        
        return False
    
    def is_webhook_message(self, message: dict) -> bool:
        """Incoming Webhook 메시지 여부"""
        from_data = message.get("from", {})
        
        # Webhook은 application으로 옴
        if from_data.get("application"):
            return True
        
        return False
    
    async def process_feed1_message(self, message: dict):
        """Feed1 메시지 처리"""
        print(f"📨 Processing Feed1 message: {message.get('id')}")
        
        attachments = message.get("attachments", [])
        if not attachments:
            print("⚠️ No attachments")
            return
        
        attachment = attachments[0]
        content_type = attachment.get("contentType", "")
        
        if "o365connector" in content_type.lower():
            import json
            
            # O365 Card 파싱
            content_str = attachment.get("content", "{}")
            try:
                card = json.loads(content_str)  # ← 이미 VTWebhookMessage 포맷!
            except:
                print("⚠️ Failed to parse card content")
                return
            
            # 디버깅 출력 (선택)
            print(f"📌 Title: {card.get('title')}")
            
            forwarded = await handle_raw_alert(card)
            
            if forwarded:
                print(f"✅ Feed1 forwarded to VT Error Feed Prod")
            else:
                print(f"⏭️ Feed1 dropped (not critical)")
        
        else:
            print(f"⚠️ Unknown content type: {content_type}")
    
    async def process_feed2_message(self, message: dict):
        """Feed2 메시지 처리"""
        print(f"📨 Processing Feed2 message: {message.get('id')}")
        
        attachments = message.get("attachments", [])
        if not attachments:
            print("⚠️ No attachments")
            return
        
        attachment = attachments[0]
        content_type = attachment.get("contentType", "")
        
        if "o365connector" in content_type.lower():
            import json
            
            content_str = attachment.get("content", "{}")
            try:
                card = json.loads(content_str)
            except:
                print("⚠️ Failed to parse card content")
                return
            
            print(f"📌 Title: {card.get('title')}")
            
            # ✅ 디버깅: Description 출력
            sections = card.get("sections", [])
            if sections:
                facts = sections[0].get("facts", [])
                for fact in facts:
                    if fact.get("name") == "Description":
                        import re
                        desc = re.sub(r'<[^>]+>', '', fact.get("value", ""))
                        print(f"📋 Description: {desc}")
            
            triggered = await handle_monitoring_alert(card)
            
            if triggered:
                print(f"🚨 Feed2 incident triggered!")
            else:
                print(f"📊 Feed2 recorded only")
        
        else:
            print(f"⚠️ Unknown content type: {content_type}")
    
    async def poll_channel(self, channel_id: str, channel_type: str):
        """단일 채널 polling"""
        since = self.last_check.get(channel_id)
        
        try:
            messages = await self.graph.get_channel_messages(
                team_id=TEAMS_TEAM_ID,
                channel_id=channel_id,
                since=since
            )
            
            for message in messages:
                msg_id = message.get("id")
                
                # 중복 체크
                if msg_id in self.processed_ids:
                    continue
                
                # Webhook 메시지만 처리
                if not self.is_webhook_message(message):
                    print(f"⏭️ Skipping user message: {msg_id}")
                    continue
                
                # Card 메시지 체크 (Adaptive 또는 O365 Connector)
                if not self.is_card_message(message):  # ← 함수명 변경
                    print(f"⏭️ Skipping webhook message without card: {msg_id}")
                    continue
                
                print(f"🔍 Found webhook message with Card: {msg_id}")
                
                # 채널별 처리
                if channel_type == "feed1":
                    await self.process_feed1_message(message)
                elif channel_type == "feed2":
                    await self.process_feed2_message(message)
                
                # 처리 완료 기록
                self.processed_ids.add(msg_id)
            
            # 마지막 확인 시간 업데이트
            self.last_check[channel_id] = datetime.now(timezone.utc).isoformat()
            
        except Exception as e:
            logger.error(f"Polling error for {channel_type}: {e}", exc_info=True)
    
    async def cleanup_processed_ids(self):
        """processed_ids 정리 (메모리 관리)"""
        while self.running:
            await asyncio.sleep(3600)  # 1시간
            
            # 최근 1000개만 유지
            if len(self.processed_ids) > 1000:
                # 절반 삭제
                to_remove = len(self.processed_ids) - 500
                for _ in range(to_remove):
                    self.processed_ids.pop()
                
                logger.info(f"Cleaned up processed_ids: {len(self.processed_ids)} remaining")
    
    async def start(self):
        """Polling 시작"""
        self.running = True
        print("=" * 80)
        print("🚀 Starting message poller...")
        print(f"📍 Team ID: {TEAMS_TEAM_ID}")
        print(f"📍 Feed1: {TEAMS_FEED1_CHANNEL_ID}")
        print(f"📍 Feed2: {TEAMS_FEED2_CHANNEL_ID}")
        print("=" * 80)
        
        # Cleanup task 시작
        asyncio.create_task(self.cleanup_processed_ids())
        
        while self.running:
            try:
                print(f"\n⏰ Polling at {datetime.now().isoformat()}")
                
                # Feed1 polling
                await self.poll_channel(TEAMS_FEED1_CHANNEL_ID, "feed1")
                
                # Feed2 polling
                await self.poll_channel(TEAMS_FEED2_CHANNEL_ID, "feed2")
                
                # 10초 대기
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Poller loop error: {e}", exc_info=True)
                await asyncio.sleep(10)
    
    def stop(self):
        """Polling 중지"""
        self.running = False
        logger.info("Message poller stopped")