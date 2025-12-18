# app/services/message_poller.py
"""
채널 메시지 Polling 서비스
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict
import logging

from app.adapters.graph_client import GraphClient
from app.application.services.message_parser import TeamsMessageParser
from app.application.services.message_processor import MessageProcessor
from app.application.services.duplicate_tracker import DuplicateTracker
from app.config import (
    TEAMS_TEAM_ID,
    TEAMS_FEED1_CHANNEL_ID,
    TEAMS_FEED2_CHANNEL_ID
)

logger = logging.getLogger(__name__)


class MessagePoller:
    """
    채널 메시지 주기적 Polling
    
    책임:
    - 채널에서 새 메시지 조회
    - Feed별로 적절한 processor에게 위임
    - Polling 생명주기 관리
    """
    
    def __init__(
        self,
        graph_client: GraphClient,
        parser: TeamsMessageParser = None,
        processor: MessageProcessor = None,
        duplicate_tracker: DuplicateTracker = None
    ):
        self.graph = graph_client
        self.parser = parser or TeamsMessageParser()
        self.processor = processor or MessageProcessor()
        self.tracker = duplicate_tracker or DuplicateTracker()
        
        self.last_check: Dict[str, str] = {}
        self.running = False
    
    async def poll_channel(self, channel_id: str, feed_type: str):
        """
        단일 채널 polling
        
        Args:
            channel_id: Teams 채널 ID
            feed_type: "feed1" 또는 "feed2"
        """
        since = self.last_check.get(channel_id)
        
        try:
            messages = await self.graph.get_channel_messages(
                team_id=TEAMS_TEAM_ID,
                channel_id=channel_id,
                since=since
            )
            
            for message in messages:
                await self._process_single_message(message, feed_type)
            
            # 마지막 확인 시간 업데이트
            self.last_check[channel_id] = datetime.now(timezone.utc).isoformat()
            
        except Exception as e:
            logger.error(f"Polling error for {feed_type}: {e}", exc_info=True)
    
    async def _process_single_message(self, message: dict, feed_type: str):
        """단일 메시지 처리"""
        msg_id = message.get("id")
        
        # 중복 체크
        if self.tracker.is_processed(msg_id):
            return
        
        # Webhook 메시지만 처리
        if not self.parser.is_webhook_message(message):
            logger.debug(f"⏭️ Skipping user message: {msg_id}")
            return
        
        # Card 메시지 체크
        if not self.parser.is_card_message(message):
            logger.debug(f"⏭️ Skipping webhook message without card: {msg_id}")
            return
        
        logger.info(f"🔍 Found webhook message with Card: {msg_id}")
        
        # Card 파싱
        card = self.parser.parse_card(message)
        if not card:
            logger.warning(f"⚠️ Failed to parse card: {msg_id}")
            return
        
        # Feed별 처리
        if feed_type == "feed1":
            await self.processor.process_feed1(card)
        elif feed_type == "feed2":
            await self.processor.process_feed2(card)
        
        # 처리 완료 기록
        self.tracker.mark_processed(msg_id)
    
    async def start(self, poll_interval: int = 10):
        """
        Polling 시작
        
        Args:
            poll_interval: Polling 주기 (초)
        """
        self.running = True
        
        logger.info("=" * 80)
        logger.info("🚀 Starting message poller...")
        
        # 서버 시작 시각 기록 (첫 polling 스킵)
        now = datetime.now(timezone.utc).isoformat()
        self.last_check[TEAMS_FEED1_CHANNEL_ID] = now
        self.last_check[TEAMS_FEED2_CHANNEL_ID] = now
        
        logger.info(f"📍 Starting from: {now}")
        logger.info(f"📍 Team ID: {TEAMS_TEAM_ID}")
        logger.info(f"📍 Feed1: {TEAMS_FEED1_CHANNEL_ID}")
        logger.info(f"📍 Feed2: {TEAMS_FEED2_CHANNEL_ID}")
        logger.info(f"📍 Poll interval: {poll_interval}s")
        logger.info("=" * 80)
        
        while self.running:
            try:
                logger.debug(f"⏰ Polling at {datetime.now().isoformat()}")
                
                # Feed1 polling
                await self.poll_channel(TEAMS_FEED1_CHANNEL_ID, "feed1")
                
                # Feed2 polling
                await self.poll_channel(TEAMS_FEED2_CHANNEL_ID, "feed2")
                
                # 대기
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Poller loop error: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)
    
    def stop(self):
        """Polling 중지"""
        self.running = False
        logger.info("Message poller stopped")
