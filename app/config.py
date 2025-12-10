from dotenv import load_dotenv
import os

# .env 읽어오기
load_dotenv()

TEAMS_FORWARD_WEBHOOK_URL = os.getenv("TEAMS_FORWARD_WEBHOOK_URL")
TEAMS_INCIDENT_WEBHOOK_URL = os.getenv("TEAMS_INCIDENT_WEBHOOK_URL")


if not TEAMS_FORWARD_WEBHOOK_URL:
    raise RuntimeError("TEAMS_FORWARD_WEBHOOK_URL is not set in .env")

if not TEAMS_INCIDENT_WEBHOOK_URL:
    raise RuntimeError("TEAMS_INCIDENT_WEBHOOK_URL is not set in .env")
