import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RESUME_PATH = Path(os.environ.get("RESUME_PATH", ""))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
JOBS_FILE = Path(os.environ.get("JOBS_FILE", "jobs.json"))

# Notifications
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# WhatsApp via Evolution API
EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "")
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "")
EVOLUTION_PHONE = os.environ.get("EVOLUTION_PHONE", "")  # e.g. 919876543210@s.whatsapp.net
