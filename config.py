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
