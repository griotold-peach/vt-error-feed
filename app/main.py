from fastapi import FastAPI, Request, HTTPException, Depends
from contextlib import asynccontextmanager
import asyncio

from app.services.handler import handle_raw_alert
from app.services.monitoring import handle_monitoring_alert
from app.domain.anomaly import reset_state
from app.utils.security import verify_teams_hmac
from app.adapters.graph_client import GraphClient
from app.services.message_poller import MessagePoller

import logging

logger = logging.getLogger(__name__)

# Global poller instance
poller: MessagePoller = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    # Startup
    global poller
    
    print("=" * 80)
    print("🚀 Starting VT Error Feed Filter Server")
    print("=" * 80)
    
    # Graph API 클라이언트 생성
    graph_client = GraphClient()
    
    # Message Poller 생성 및 시작
    poller = MessagePoller(graph_client)
    asyncio.create_task(poller.start())
    
    yield
    
    # Shutdown
    if poller:
        poller.stop()
    
    print("=" * 80)
    print("👋 Shutting down VT Error Feed Filter Server")
    print("=" * 80)


app = FastAPI(
    title="VT Error Feed Filter Server",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    return {"status": "ok", "poller_running": poller.running if poller else False}


# 기존 레거시 엔드포인트 유지
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