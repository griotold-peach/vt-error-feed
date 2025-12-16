"""
Teams Outgoing Webhook HMAC 검증
"""
import hmac
import hashlib
import base64
from typing import Optional
from fastapi import Header, HTTPException, Request

from app.config import TEAMS_SECURITY_TOKEN, ENV


async def verify_teams_hmac(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> bool:
    """
    Teams Outgoing Webhook의 HMAC-SHA256 서명을 검증합니다.
    
    Teams는 요청 시 Authorization 헤더에 'HMAC <base64_signature>' 형식으로 서명을 보냅니다.
    이 함수는 서버의 Security Token으로 같은 방식으로 서명을 계산하여 비교합니다.
    
    Args:
        request: FastAPI Request 객체 (body를 읽기 위해)
        authorization: Authorization 헤더 값
        
    Returns:
        bool: 검증 성공 시 True
        
    Raises:
        HTTPException: 검증 실패 시 401
    """
    # 개발 환경에서는 HMAC 검증 스킵
    if ENV == "development":
        return True
    
    # Authorization 헤더 확인
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )
    
    if not authorization.startswith("HMAC "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format (expected 'HMAC <signature>')"
        )
    
    # "HMAC " 제거하고 서명 추출
    received_signature = authorization[5:]
    
    # Request body 읽기
    body = await request.body()
    
    # HMAC-SHA256 계산
    expected_signature = base64.b64encode(
        hmac.new(
            TEAMS_SECURITY_TOKEN.encode('utf-8'),  # config에서 가져온 값 사용
            body,
            hashlib.sha256
        ).digest()
    ).decode('utf-8')
    
    # 타이밍 공격 방지를 위한 constant-time 비교
    if not hmac.compare_digest(received_signature, expected_signature):
        raise HTTPException(
            status_code=401,
            detail="Invalid HMAC signature"
        )
    
    return True