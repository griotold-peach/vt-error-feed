"""
Bot Framework JWT 토큰 검증
"""
from botframework.connector.auth import (
    JwtTokenValidation,
    SimpleCredentialProvider,
    AuthenticationConfiguration
)
from fastapi import HTTPException, Request
from typing import Dict, Any

from app.config import MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD

async def verify_bot_request(request: Request) -> Dict[str, Any]:
    """
    Bot Framework 요청 검증
    
    1. JWT 토큰 검증
    2. Activity 객체 반환
    """
    # Authorization 헤더 확인
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    # Config에서 가져오기
    if not MICROSOFT_APP_ID or not MICROSOFT_APP_PASSWORD:
        raise HTTPException(
            status_code=500, 
            detail="Bot credentials not configured"
        )
    
    # Activity 파싱
    try:
        activity = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # Credential Provider 생성
    credentials = SimpleCredentialProvider(MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD)
    auth_config = AuthenticationConfiguration()
    
    # JWT 검증
    try:
        await JwtTokenValidation.authenticate_request(
            activity=activity,
            auth_header=auth_header,
            credentials=credentials,
            auth_config=auth_config
        )
    except Exception as e:
        raise HTTPException(
            status_code=401, 
            detail=f"Token validation failed: {str(e)}"
        )
    
    return activity