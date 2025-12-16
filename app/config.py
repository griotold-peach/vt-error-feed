from dotenv import load_dotenv
import os

# .env 읽어오기
load_dotenv()

TEAMS_FORWARD_WEBHOOK_URL = os.getenv("TEAMS_FORWARD_WEBHOOK_URL")
TEAMS_INCIDENT_WEBHOOK_URL = os.getenv("TEAMS_INCIDENT_WEBHOOK_URL")
TEAMS_SECURITY_TOKEN = os.getenv("TEAMS_SECURITY_TOKEN", "")

ENV = os.getenv("ENV", "development")

# Bot Framework 설정 추가
MICROSOFT_APP_ID = os.getenv("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD", "")

# Teams 채널 ID 설정
TEAMS_FEED1_CHANNEL_ID = os.getenv("TEAMS_FEED1_CHANNEL_ID", "")
TEAMS_FEED2_CHANNEL_ID = os.getenv("TEAMS_FEED2_CHANNEL_ID", "")

if ENV == "production":
    if not TEAMS_FORWARD_WEBHOOK_URL:
        raise RuntimeError("TEAMS_FORWARD_WEBHOOK_URL is not set")
    if not TEAMS_INCIDENT_WEBHOOK_URL:
        raise RuntimeError("TEAMS_INCIDENT_WEBHOOK_URL is not set")
    if not MICROSOFT_APP_ID:
        raise RuntimeError("MICROSOFT_APP_ID is not set")
    if not MICROSOFT_APP_PASSWORD:
        raise RuntimeError("MICROSOFT_APP_PASSWORD is not set")