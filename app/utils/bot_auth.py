"""
Bot Framework JWT 토큰 검증
"""
from botframework.connector.auth import (
    JwtTokenValidation,
    SimpleCredentialProvider,
)
from fastapi import HTTPException, Request
from typing import Dict, Any
import logging
import base64
import json

from app.config import MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD

logger = logging.getLogger(__name__)

async def verify_bot_request(request: Request) -> Dict[str, Any]:
    """
    Bot Framework 요청 검증
    
    1. JWT 토큰 검증
    2. Activity 객체 반환
    """
    # Authorization 헤더 확인
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header:
        logger.error("❌ No Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    logger.info(f"🔍 Authorization header present: {auth_header[:50]}...")
    
    # Config에서 가져오기
    if not MICROSOFT_APP_ID or not MICROSOFT_APP_PASSWORD:
        logger.error("❌ Bot credentials not configured")
        logger.error(f"  - MICROSOFT_APP_ID: {MICROSOFT_APP_ID}")
        logger.error(f"  - MICROSOFT_APP_PASSWORD: {'SET' if MICROSOFT_APP_PASSWORD else 'NOT SET'}")
        raise HTTPException(
            status_code=500, 
            detail="Bot credentials not configured"
        )
    
    logger.info(f"🔍 Bot credentials configured:")
    logger.info(f"  - App ID: {MICROSOFT_APP_ID}")
    logger.info(f"  - Password: {'*' * 10}...{MICROSOFT_APP_PASSWORD[-5:] if MICROSOFT_APP_PASSWORD else 'NOT SET'}")
    
    # JWT 디코딩 (검증 전 디버깅)
    try:
        token = auth_header.replace("Bearer ", "")
        
        # Payload 디코딩
        payload_part = token.split('.')[1]
        payload_part += '=' * (4 - len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_part))
        
        logger.info(f"🔍 JWT Payload (before validation):")
        logger.info(f"  - aud (audience): {payload.get('aud')}")
        logger.info(f"  - iss (issuer): {payload.get('iss')}")
        logger.info(f"  - exp (expires): {payload.get('exp')}")
        logger.info(f"  - serviceUrl: {payload.get('serviceUrl')}")
        
        # 환경변수와 비교
        if payload.get('aud') != MICROSOFT_APP_ID:
            logger.error(f"❌ AUDIENCE MISMATCH DETECTED!")
            logger.error(f"  - JWT aud:     '{payload.get('aud')}'")
            logger.error(f"  - Expected:    '{MICROSOFT_APP_ID}'")
            logger.error(f"  - Match: {payload.get('aud') == MICROSOFT_APP_ID}")
        else:
            logger.info(f"✅ Audience matches expected App ID")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to decode JWT for debugging: {e}")
    
    # Activity 파싱
    try:
        activity = await request.json()
        logger.info(f"🔍 Activity parsed:")
        logger.info(f"  - type: {activity.get('type')}")
        logger.info(f"  - channelId: {activity.get('channelId')}")
        logger.info(f"  - from: {activity.get('from', {}).get('name')}")
    except Exception as e:
        logger.error(f"❌ Invalid JSON body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # Credential Provider 생성
    credentials = SimpleCredentialProvider(MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD)
    
    logger.info(f"🔍 Starting JWT validation...")
    
    # JWT 검증 (auth_config 제거!)
    try:
        await JwtTokenValidation.authenticate_request(
            activity=activity,
            auth_header=auth_header,
            credentials=credentials
        )
        logger.info(f"✅ JWT validation successful!")
        
    except Exception as e:
        logger.error(f"❌ Token validation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=401, 
            detail=f"Token validation failed: {str(e)}"
        )
    
    return activity