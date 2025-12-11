from fastapi import FastAPI, Request, HTTPException
from app.services.handler import handle_raw_alert
from app.services.monitoring import handle_monitoring_alert
from app.domain.anomaly import reset_state

app = FastAPI(title="VT Error Feed Filter Server")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/vt/webhook/live-api")
async def vt_webhook_live_api(request: Request):
    """
    API-VIdeo-Translator Prod 채널에서 수신
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    forwarded = await handle_raw_alert(payload)

    return {"status": "forwarded" if forwarded else "dropped"}

@app.post("/vt/webhook/monitoring")
async def vt_webhook_monitoring(request: Request):
    """
    Feed2 (VT 실시간 모니터링 채널 [ PM, PO ]) 엔드포인트.
    영상 생성 실패 / 외부 URL 다운로드 실패 / Video 파일 업로드 실패 등을 받아서
    anomaly 규칙에 따라 장애 채널로 incident 를 발생시킨다.
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