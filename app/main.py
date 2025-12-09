from fastapi import FastAPI, Request, HTTPException

app = FastAPI(title="VT Error Feed Filter Server")


@app.get("/health")
async def health():
    return {"status": "ok"}