from dotenv import load_dotenv
import os

# .env 읽어오기
load_dotenv()

# Graph API 인증
MICROSOFT_APP_ID = os.getenv("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD", "")
MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "")

# Teams 정보
TEAMS_TEAM_ID = os.getenv("TEAMS_TEAM_ID", "")
TEAMS_FEED1_CHANNEL_ID = os.getenv("TEAMS_FEED1_CHANNEL_ID", "")
TEAMS_FEED2_CHANNEL_ID = os.getenv("TEAMS_FEED2_CHANNEL_ID", "")

# Forward Webhooks
TEAMS_FORWARD_WEBHOOK_URL = os.getenv("TEAMS_FORWARD_WEBHOOK_URL", "")
TEAMS_INCIDENT_WEBHOOK_URL = os.getenv("TEAMS_INCIDENT_WEBHOOK_URL", "")

# Environment
ENV = os.getenv("ENV", "development")

# Production 환경 검증
if ENV == "production":
    # Graph API 필수 변수
    if not MICROSOFT_APP_ID:
        raise RuntimeError("MICROSOFT_APP_ID is not set")
    if not MICROSOFT_APP_PASSWORD:
        raise RuntimeError("MICROSOFT_APP_PASSWORD is not set")
    if not MICROSOFT_TENANT_ID:
        raise RuntimeError("MICROSOFT_TENANT_ID is not set")
    
    # Teams 정보 필수 변수
    if not TEAMS_TEAM_ID:
        raise RuntimeError("TEAMS_TEAM_ID is not set")
    if not TEAMS_FEED1_CHANNEL_ID:
        raise RuntimeError("TEAMS_FEED1_CHANNEL_ID is not set")
    if not TEAMS_FEED2_CHANNEL_ID:
        raise RuntimeError("TEAMS_FEED2_CHANNEL_ID is not set")
    
    # Forward Webhooks 필수 변수
    if not TEAMS_FORWARD_WEBHOOK_URL:
        raise RuntimeError("TEAMS_FORWARD_WEBHOOK_URL is not set")
    if not TEAMS_INCIDENT_WEBHOOK_URL:
        raise RuntimeError("TEAMS_INCIDENT_WEBHOOK_URL is not set")