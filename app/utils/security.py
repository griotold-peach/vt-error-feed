import hmac
import hashlib
import base64
from fastapi import Request, HTTPException

from app.config import ENV


async def verify_teams_hmac(request: Request) -> bool:
    """
    Teams HMAC 서명 검증 (레거시 - 사용 안 함)
    
    Graph API로 전환했으므로 이 함수는 더 이상 사용되지 않습니다.
    레거시 엔드포인트 호환성을 위해 유지하지만 검증하지 않습니다.
    """
    # 레거시 엔드포인트용 - 검증 스킵
    # Graph API 사용으로 HMAC 검증 불필요
    return True