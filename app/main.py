from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from app.domain.anomaly import reset_state
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
    """헬스체크 엔드포인트"""
    return {
        "status": "ok",
        "poller_running": poller.running if poller else False
    }


@app.post("/debug/reset")
async def reset():
    """장애 상태 리셋 (디버깅용)"""
    reset_state()
    return {"status": "reset"}