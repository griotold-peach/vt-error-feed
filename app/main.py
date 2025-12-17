from fastapi import FastAPI, Request, HTTPException, Depends
from app.services.handler import handle_raw_alert
from app.services.monitoring import handle_monitoring_alert
from app.domain.anomaly import reset_state
from app.utils.security import verify_teams_hmac
from app.utils.bot_auth import verify_bot_request
from app.adapters.bot_activity import parse_bot_activity, get_channel_type

import logging
import json

logger = logging.getLogger(__name__)

app = FastAPI(title="VT Error Feed Filter Server")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/messages")
async def bot_messages(
    request: Request,
    activity: dict = Depends(verify_bot_request)
):
    """
    Bot Framework 메시지 수신 엔드포인트
    RSC 권한으로 채널의 모든 메시지를 받음
    """
    # ✅ Activity 전체 로그 출력
    logger.info("=" * 80)
    logger.info("📨 Received Bot Activity:")
    logger.info(json.dumps(activity, indent=2, ensure_ascii=False))
    logger.info("=" * 80)
    
    # Activity 파싱
    parsed = parse_bot_activity(activity)
    
    if not parsed:
        # message 타입이 아니면 무시
        logger.info("⚠️ Not a message type, ignoring")
        return {"status": "ignored", "reason": "not_a_message"}
    
    logger.info(f"✅ Parsed activity:")
    logger.info(f"  - channel_id: {parsed.get('channel_id')}")
    logger.info(f"  - text: {parsed.get('text')}")
    
    # 채널 구분
    channel_type = get_channel_type(parsed["channel_id"])
    
    if not channel_type:
        # 등록된 채널이 아니면 무시
        logger.info(f"⚠️ Unknown channel: {parsed['channel_id']}")
        return {
            "status": "ignored", 
            "reason": "unknown_channel",
            "channel_id": parsed["channel_id"]
        }
    
    logger.info(f"✅ Channel identified: {channel_type}")
    
    # Feed1/Feed2 구분해서 기존 로직 호출
    if channel_type == "feed1":
        # Teams 메시지를 기존 포맷으로 변환
        logger.info("🔄 Converting to Feed1 format...")
        payload = convert_to_feed1_format(parsed)
        forwarded = await handle_raw_alert(payload)
        logger.info(f"✅ Feed1 result: {'forwarded' if forwarded else 'dropped'}")
        return {"status": "forwarded" if forwarded else "dropped", "channel": "feed1"}
    
    elif channel_type == "feed2":
        logger.info("🔄 Converting to Feed2 format...")
        payload = convert_to_feed2_format(parsed)
        triggered = await handle_monitoring_alert(payload)
        logger.info(f"✅ Feed2 result: {'incident_triggered' if triggered else 'recorded'}")
        return {
            "status": "incident_triggered" if triggered else "recorded", 
            "channel": "feed2"
        }


def convert_to_feed1_format(parsed: dict) -> dict:
    """
    Bot Activity를 Feed1 형식으로 변환
    
    TODO: 실제 Feed1 메시지 형식을 확인해서 구현 필요
    현재는 임시로 Activity를 그대로 반환
    실제 메시지를 로그로 확인한 후 수정
    """
    activity = parsed["activity"]
    
    # 임시 구현 - 실제 형식에 맞게 수정 필요
    # Feed1의 실제 메시지 포맷을 보고 매핑
    return {
        "text": parsed["text"],
        "from": activity.get("from", {}),
        "channelData": activity.get("channelData", {}),
        # TODO: 실제 필요한 필드 추가
    }


def convert_to_feed2_format(parsed: dict) -> dict:
    """
    Bot Activity를 Feed2 형식으로 변환
    
    TODO: 실제 Feed2 메시지 형식을 확인해서 구현 필요
    """
    activity = parsed["activity"]
    
    # 임시 구현 - 실제 형식에 맞게 수정 필요
    return {
        "text": parsed["text"],
        "from": activity.get("from", {}),
        "channelData": activity.get("channelData", {}),
        # TODO: 실제 필요한 필드 추가
    }


# 기존 엔드포인트들 (HMAC 검증용 - 레거시, 나중에 제거 가능)
@app.post("/vt/webhook/live-api")
async def vt_webhook_live_api(
    request: Request,
    _: bool = Depends(verify_teams_hmac)
):
    """
    API-Video-Translator Prod 채널에서 수신 (레거시)
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    forwarded = await handle_raw_alert(payload)
    return {"status": "forwarded" if forwarded else "dropped"}


@app.post("/vt/webhook/monitoring")
async def vt_webhook_monitoring(
    request: Request,
    _: bool = Depends(verify_teams_hmac)
):
    """
    Feed2 (VT 실시간 모니터링 채널 [ PM, PO ]) 엔드포인트 (레거시)
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    triggered = await handle_monitoring_alert(payload)
    return {"status": "incident_triggered" if triggered else "recorded"}


@app.post("/debug/reset")
async def reset():
    reset_state()
    return {"status": "reset"}