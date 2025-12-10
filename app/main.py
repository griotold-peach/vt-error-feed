from fastapi import FastAPI, Request, HTTPException
from app.services.handler import handle_raw_alert

app = FastAPI(title="VT Error Feed Filter Server")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/vt/webhook/live-api")
async def vt_webhook_live_api(request: Request):
    """
    VT API 서버에서 Teams로 보내던 JSON을 이제 여기로 POST.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    forwarded = await handle_raw_alert(payload)

    return {"status": "forwarded" if forwarded else "dropped"}
