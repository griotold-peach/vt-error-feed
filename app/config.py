from dotenv import load_dotenv
import os

# .env 읽어오기
load_dotenv()

TEAMS_FORWARD_WEBHOOK_URL = os.getenv("TEAMS_FORWARD_WEBHOOK_URL")
TEAMS_INCIDENT_WEBHOOK_URL = os.getenv("TEAMS_INCIDENT_WEBHOOK_URL")
TEAMS_SECURITY_TOKEN = os.getenv("TEAMS_SECURITY_TOKEN", "")  # 빈 문자열 기본값

ENV = os.getenv("ENV", "development")

if ENV == "production":
    if not TEAMS_FORWARD_WEBHOOK_URL:
        raise RuntimeError("TEAMS_FORWARD_WEBHOOK_URL is not set")
    if not TEAMS_INCIDENT_WEBHOOK_URL:
        raise RuntimeError("TEAMS_INCIDENT_WEBHOOK_URL is not set")
    if not TEAMS_SECURITY_TOKEN:
        raise RuntimeError("TEAMS_SECURITY_TOKEN is not set")