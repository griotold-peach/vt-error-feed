from dotenv import load_dotenv
import os

# .env 읽어오기
load_dotenv()

TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")

if not TEAMS_WEBHOOK_URL:
    raise RuntimeError("TEAMS_WEBHOOK_URL is not set in .env")
