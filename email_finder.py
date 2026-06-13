import re
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_%]+")
_SKIP_DOMAINS = {"example.com", "domain.com", "email.com", "test.com", "sentry.io"}

HEADERS = {"User-Agent": "job-finder/1.0 (personal job search)"}
TIMEOUT = 15


def find_email(job: dict) -> tuple:
    """Return (email_or_None, linkedin_hints_list)."""
    description = job.get("description", "") or ""
    apply_link = job.get("apply_link") or job.get("url", "")
    company = job.get("company", "")
    title = job.get("title", "")

    email = _extract_email(description)
    if email:
        return email, []

    email, hints = _scan_page(apply_link)
    if email:
        return email, hints

    email, search_hints = _ddg_search(company, title)
    return email, list(set(hints + search_hints))


def _extract_email(text: str):
    for match in EMAIL_RE.findall(text):
        domain = match.split("@")[1].lower()
        if domain not in _SKIP_DOMAINS:
            return match
    return None


def _scan_page(url: str) -> tuple:
    if not url:
        return None, []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("mailto:"):
                candidate = a["href"][7:].split("?")[0].strip()
                if candidate and EMAIL_RE.match(candidate):
                    return candidate, []
        email = _extract_email(soup.get_text(" "))
        hints = list(set(LINKEDIN_RE.findall(r.text)))
        return email, hints
    except Exception:
        return None, []


def _ddg_search(company: str, title: str) -> tuple:
    if not company:
        return None, []
    query = f'"{company}" "{title}" hiring contact email'
    hints: list = []
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=5):
                snippet = (result.get("body") or "") + " " + (result.get("href") or "")
                hints += LINKEDIN_RE.findall(snippet)
                email = _extract_email(snippet)
                if email:
                    return email, list(set(hints))
    except Exception:
        pass
    return None, list(set(hints))
