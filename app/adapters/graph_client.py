"""
Microsoft Graph API 클라이언트
"""
from msal import ConfidentialClientApplication
import aiohttp
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.config import (
    MICROSOFT_APP_ID,
    MICROSOFT_APP_PASSWORD,
    MICROSOFT_TENANT_ID
)

logger = logging.getLogger(__name__)


class GraphClient:
    """Microsoft Graph API 클라이언트"""
    
    def __init__(self):
        self.authority = f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}"
        self.scopes = ["https://graph.microsoft.com/.default"]
        
        self.app = ConfidentialClientApplication(
            client_id=MICROSOFT_APP_ID,
            client_credential=MICROSOFT_APP_PASSWORD,
            authority=self.authority
        )
        
        self._token = None
        self._token_expires_at = None
    
    async def get_access_token(self) -> str:
        """액세스 토큰 획득 (캐싱)"""
        # 토큰이 유효하면 재사용
        if self._token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._token
        
        # 새 토큰 획득
        result = self.app.acquire_token_for_client(scopes=self.scopes)
        
        if "access_token" not in result:
            error = result.get("error_description", "Unknown error")
            logger.error(f"Failed to acquire token: {error}")  # ← 에러는 logger 유지
            raise Exception(f"Token acquisition failed: {error}")
        
        self._token = result["access_token"]
        # 토큰 만료 시간 (55분 후로 설정 - 실제는 60분)
        self._token_expires_at = datetime.now() + timedelta(minutes=55)

        logger.info("🔑 Successfully acquired Graph API token")
        return self._token

    async def get_channel_messages(
        self,
        team_id: str,
        channel_id: str,
        since: Optional[str] = None,
        top: int = 10
    ) -> List[Dict[str, Any]]:
        """채널 메시지 조회"""
        token = await self.get_access_token()
        
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        params = {"$top": top}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.error(f"Graph API error: {resp.status} - {text}")  # ← 에러는 logger 유지
                        return []
                    
                    data = await resp.json()
                    messages = data.get("value", [])
                    
                    # since가 있으면 클라이언트에서 필터링
                    if since:
                        filtered = []
                        for msg in messages:
                            last_modified = msg.get("lastModifiedDateTime")
                            if last_modified and last_modified > since:
                                filtered.append(msg)
                        messages = filtered

                    if messages:
                        logger.info(f"📬 Retrieved {len(messages)} messages")
                    return messages
        
        except Exception as e:
            logger.error(f"Error fetching messages: {e}", exc_info=True)  # ← 에러는 logger 유지
            return []