#!/usr/bin/env python3
"""
Remote / freelance software-engineering job finder.

Pulls listings from job boards that EXPLICITLY allow programmatic access
(public APIs and RSS feeds), filters for software-engineering roles that are
remote and optionally part-time / freelance / contract, then emails YOU a
digest of new matches so you can review and apply with a tailored message.

It deliberately does NOT scrape LinkedIn and does NOT auto-email recruiters.
See README.md for why (both would harm your job search, not help it).
"""

import os
import re
import json
import smtplib
import datetime as dt
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests

# ---------------------------------------------------------------------------
# Configuration  (edit these, or override the email ones via env vars/secrets)
# ---------------------------------------------------------------------------

# Tech the user actually works with — any match is a strong positive signal.
_TECH_KEYWORDS = {
    "angular", "react", "next.js", "nextjs", "vue",
    "node", "nodejs", "nestjs", "express",
    "typescript", "javascript",
    "python", "fastapi", "django", "flask",
    "flutter", "dart",
}

# Generic role titles — kept only when no excluded stack is mentioned.
ROLE_KEYWORDS = [
    "software engineer", "software developer", "full stack", "full-stack",
    "fullstack", "frontend", "front-end", "backend", "back-end",
    "web developer",
]

# The job TITLE must contain at least one of these — prevents non-software
# jobs from slipping in via description/tag noise.
_TITLE_KEYWORDS = {
    "engineer", "developer", "dev", "programmer", "architect",
    "software", "fullstack", "full-stack", "full stack",
    "frontend", "front-end", "backend", "back-end", "web",
    "angular", "react", "vue", "node", "nestjs",
    "typescript", "javascript", "python", "flutter", "next.js",
}

# Stacks NOT in the user's profile — exclude jobs that mention these
# without also mentioning a known tech keyword.
_EXCLUDE_KEYWORDS = [
    ".net", "c#", "asp.net", "dotnet",
    "java ", "spring boot", "spring framework",
    "ruby on rails", " rails", " php", "laravel",
    "golang", " rust ", " scala ", "kotlin",
    "android native", "ios native", "objective-c", " swift ",
    "blazor", "xamarin",
]

# Drop jobs older than this many days (keep if date is missing/unparseable).
_MAX_AGE_DAYS = 30

# True  -> only keep jobs that look part-time / freelance / contract.
# False -> keep all remote software roles, but TAG the freelance-looking ones.
FREELANCE_ONLY = False

FREELANCE_KEYWORDS = [
    "part-time", "part time", "freelance", "freelancer", "contract",
    "contractor", "hourly", "consultant",
]

# Email settings — read from environment variables so secrets stay out of code.
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")        # e.g. ladla8602@gmail.com
SMTP_PASS = os.environ.get("SMTP_PASS", "")        # Gmail *App Password*
EMAIL_TO = os.environ.get("EMAIL_TO", SMTP_USER)   # where the digest is sent

# Remembers jobs already sent so twice-daily runs only show new ones.
SEEN_FILE = Path(os.environ.get("SEEN_FILE", "seen_jobs.json"))

HEADERS = {"User-Agent": "job-finder/1.0 (personal job search)"}
TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match_title(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in _TITLE_KEYWORDS)


def _match_role(text: str) -> bool:
    t = text.lower()
    if any(k in t for k in _TECH_KEYWORDS):
        return True
    if any(k in t for k in ROLE_KEYWORDS):
        return not any(k in t for k in _EXCLUDE_KEYWORDS)
    return False


def _looks_freelance(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in FREELANCE_KEYWORDS)


def _is_recent(date_str: str) -> bool:
    """Return True if within _MAX_AGE_DAYS, or if date is absent/unparseable."""
    if not date_str:
        return True
    import email.utils as _eu
    for parser in (_eu.parsedate_to_datetime, dt.datetime.fromisoformat):
        try:
            d = parser(date_str.strip())
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return (dt.datetime.now(dt.timezone.utc) - d).days <= _MAX_AGE_DAYS
        except Exception:
            continue
    return True


# ---------------------------------------------------------------------------
# Sources (all permit programmatic access via public API or RSS)
# ---------------------------------------------------------------------------

def fetch_remoteok():
    jobs = []
    try:
        r = requests.get("https://remoteok.com/api", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[remoteok] error: {e}")
        return jobs
    for item in data:
        if not isinstance(item, dict) or "position" not in item:
            continue  # first element is a legal notice, skip non-job objects
        title = item.get("position", "")
        desc = item.get("description", "") or ""
        tags = item.get("tags", []) or []
        blob = " ".join([title, desc, " ".join(tags)])
        if not _match_title(title) or not _match_role(blob) or not _is_recent(item.get("date")):
            continue
        jobs.append({
            "title": title,
            "company": item.get("company", ""),
            "location": item.get("location") or "Remote",
            "url": item.get("url") or item.get("apply_url", ""),
            "source": "RemoteOK",
            "freelance": _looks_freelance(blob),
            "description": desc,
        })
    return jobs


def fetch_remotive():
    jobs = []
    try:
        r = requests.get("https://remotive.com/api/remote-jobs",
                         params={"search": "software"}, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json().get("jobs", [])
    except Exception as e:
        print(f"[remotive] error: {e}")
        return jobs
    for item in data:
        title = item.get("title", "")
        desc = item.get("description", "") or ""
        jtype = (item.get("job_type", "") or "")
        blob = " ".join([title, desc, jtype])
        if not _match_title(title) or not _match_role(blob) or not _is_recent(item.get("publication_date")):
            continue
        jobs.append({
            "title": title,
            "company": item.get("company_name", ""),
            "location": item.get("candidate_required_location") or "Remote",
            "url": item.get("url", ""),
            "source": "Remotive",
            "freelance": _looks_freelance(blob) or "contract" in jtype.lower() or "part" in jtype.lower(),
            "description": desc,
        })
    return jobs


def fetch_arbeitnow():
    jobs = []
    try:
        r = requests.get("https://www.arbeitnow.com/api/job-board-api",
                         headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception as e:
        print(f"[arbeitnow] error: {e}")
        return jobs
    for item in data:
        if not item.get("remote", False):
            continue
        title = item.get("title", "")
        desc = item.get("description", "") or ""
        tags = item.get("tags", []) or []
        jtypes = item.get("job_types", []) or []
        blob = " ".join([title, desc, " ".join(tags), " ".join(jtypes)])
        if not _match_title(title) or not _match_role(blob) or not _is_recent(item.get("created_at")):
            continue
        jobs.append({
            "title": title,
            "company": item.get("company_name", ""),
            "location": "Remote",
            "url": item.get("url", ""),
            "source": "Arbeitnow",
            "freelance": _looks_freelance(blob) or any(
                "part" in j.lower() or "contract" in j.lower() for j in jtypes),
            "description": desc,
        })
    return jobs


def fetch_weworkremotely():
    jobs = []
    url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"[weworkremotely] error: {e}")
        return jobs
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "")
        blob = " ".join([title, desc])
        if not _match_title(title) or not _match_role(blob) or not _is_recent(item.findtext("pubDate")):
            continue
        company, _, jobtitle = title.partition(":")  # WWR title: "Company: Role"
        jobs.append({
            "title": (jobtitle or title).strip(),
            "company": company.strip(),
            "location": "Remote",
            "url": link,
            "source": "WeWorkRemotely",
            "freelance": _looks_freelance(blob),
            "description": desc,
        })
    return jobs


def fetch_jobicy():
    """Jobicy — tech-focused remote job board with a public API."""
    _TAGS = ("react", "angular", "typescript", "python", "full-stack", "javascript")

    def _fetch_tag(tag):
        r = requests.get("https://jobicy.com/api/v2/remote-jobs",
                         params={"count": 20, "tag": tag},
                         headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("jobs", [])

    raw: list = []
    with ThreadPoolExecutor(max_workers=len(_TAGS)) as pool:
        futures = {pool.submit(_fetch_tag, tag): tag for tag in _TAGS}
        for fut in as_completed(futures):
            try:
                raw.extend(fut.result())
            except Exception as e:
                print(f"[jobicy:{futures[fut]}] error: {e}")

    jobs = []
    seen_urls: set = set()
    for item in raw:
        url = item.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = item.get("jobTitle", "")
        desc = (item.get("jobDescription") or item.get("jobExcerpt", ""))
        jtype = " ".join(item.get("jobType") or [])
        blob = " ".join([title, desc, jtype])
        if not _match_title(title) or not _match_role(blob) or not _is_recent(item.get("pubDate")):
            continue
        jobs.append({
            "title": title,
            "company": item.get("companyName", ""),
            "location": item.get("jobGeo") or "Remote",
            "url": url,
            "source": "Jobicy",
            "freelance": _looks_freelance(blob) or "part" in jtype.lower() or "contract" in jtype.lower(),
            "description": desc,
        })
    return jobs


def fetch_hackernews():
    """Latest 'Ask HN: Who is hiring?' thread — great for remote/contract gigs."""
    jobs = []
    try:
        s = requests.get("https://hn.algolia.com/api/v1/search_by_date",
                         params={"query": "Ask HN: Who is hiring?", "tags": "story"},
                         headers=HEADERS, timeout=TIMEOUT)
        s.raise_for_status()
        story_id = None
        for h in s.json().get("hits", []):
            if "who is hiring" in (h.get("title", "") or "").lower():
                story_id = h.get("objectID")
                break
        if not story_id:
            return jobs
        item = requests.get(f"https://hn.algolia.com/api/v1/items/{story_id}",
                            headers=HEADERS, timeout=TIMEOUT).json()
        for c in item.get("children", []):
            text = c.get("text") or ""
            if not text or not _match_role(text) or "remote" not in text.lower() or not _is_recent(c.get("created_at")):
                continue
            clean = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", text)).strip()
            jobs.append({
                "title": clean[:200],
                "company": c.get("author", "HN poster"),
                "location": "Remote",
                "url": f"https://news.ycombinator.com/item?id={c.get('id')}",
                "source": "HN Who-is-hiring",
                "freelance": _looks_freelance(clean),
                "description": clean,
            })
    except Exception as e:
        print(f"[hackernews] error: {e}")
    return jobs


_LI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
_LI_SEARCHES = [
    "software engineer remote",
    "full stack developer remote",
    "frontend developer remote",
    "backend developer remote",
    "python developer remote",
    "react developer remote",
]


def fetch_linkedin():
    """LinkedIn public guest job search API — no login required."""
    from bs4 import BeautifulSoup

    _requests = [
        (kw, start)
        for kw in _LI_SEARCHES
        for start in (0, 25)
    ]

    def _fetch_page(kw, start):
        r = requests.get(
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
            params={"keywords": kw, "f_WT": "2", "start": str(start)},
            headers=_LI_HEADERS,
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.select("li .job-search-card")

    all_cards = []
    with ThreadPoolExecutor(max_workers=len(_requests)) as pool:
        futures = {pool.submit(_fetch_page, kw, start): (kw, start) for kw, start in _requests}
        for fut in as_completed(futures):
            try:
                all_cards.extend(fut.result())
            except Exception as e:
                kw, start = futures[fut]
                print(f"[linkedin] error ({kw} start={start}): {e}")

    seen_urls: set = set()
    jobs = []
    for card in all_cards:
        a = card.select_one("a.base-card__full-link")
        if not a:
            continue
        parsed = urlparse(a["href"])
        url = urlunparse(parsed._replace(query="", fragment=""))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = (card.select_one(".base-search-card__title") or {}).get_text(strip=True)
        company = (card.select_one(".base-search-card__subtitle") or {}).get_text(strip=True)
        location = (card.select_one(".job-search-card__location") or {}).get_text(strip=True)
        t = card.select_one("time")
        date_str = t.get("datetime", "") if t else ""

        if not title or not _match_title(title):
            continue
        blob = f"{title} {company} {location}".lower()
        if not _match_role(blob):
            continue
        if not _is_recent(date_str):
            continue

        jobs.append({
            "title": title,
            "company": company,
            "url": url,
            "location": location,
            "date": date_str,
            "source": "linkedin",
            "freelance": _looks_freelance(blob),
        })

    print(f"[linkedin] {len(jobs)} jobs")
    return jobs


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def load_seen():
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_seen(seen):
    try:
        SEEN_FILE.write_text(json.dumps(sorted(seen)))
    except Exception as e:
        print(f"[seen] could not save: {e}")


def collect_jobs():
    fetchers = (fetch_remoteok, fetch_remotive, fetch_arbeitnow,
                fetch_weworkremotely, fetch_hackernews, fetch_jobicy,
                fetch_linkedin)
    all_jobs = []
    with ThreadPoolExecutor(max_workers=len(fetchers)) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in fetchers}
        for fut in as_completed(futures):
            try:
                all_jobs.extend(fut.result())
            except Exception as e:
                print(f"[{futures[fut]}] error: {e}")
    if FREELANCE_ONLY:
        all_jobs = [j for j in all_jobs if j["freelance"]]
    unique = {j["url"]: j for j in all_jobs if j["url"]}  # dedupe by URL
    return list(unique.values())


def build_email(new_jobs):
    freelance = [j for j in new_jobs if j["freelance"]]
    others = [j for j in new_jobs if not j["freelance"]]

    def render(group):
        rows = []
        for j in group:
            tag = " 🟢 freelance/part-time" if j["freelance"] else ""
            rows.append(
                f'<li><a href="{j["url"]}">{j["title"]}</a> — '
                f'{j["company"] or "?"} · {j["location"]} '
                f'<small>[{j["source"]}]</small>{tag}</li>'
            )
        return "\n".join(rows)

    return f"""
    <h2>Remote software jobs — {dt.date.today():%d %b %Y}</h2>
    <p>{len(new_jobs)} new matches.</p>
    <h3>Freelance / part-time / contract ({len(freelance)})</h3>
    <ul>{render(freelance) or "<li>None today</li>"}</ul>
    <h3>Other remote roles ({len(others)})</h3>
    <ul>{render(others) or "<li>None today</li>"}</ul>
    <hr>
    <p style="color:#888">Apply individually with a short, tailored note + your resume.</p>
    """


def send_email(html, count):
    if not SMTP_USER or not SMTP_PASS:
        print("SMTP_USER / SMTP_PASS not set — printing digest instead of emailing.\n")
        print(html)
        return
    msg = EmailMessage()
    msg["Subject"] = f"[Job digest] {count} new remote software roles"
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.set_content("Open in an HTML-capable client to see the job links.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    print(f"Sent digest with {count} jobs to {EMAIL_TO}")


def main():
    seen = load_seen()
    jobs = collect_jobs()
    new_jobs = [j for j in jobs if j["url"] not in seen]
    print(f"Found {len(jobs)} matching jobs, {len(new_jobs)} are new.")
    if not new_jobs:
        print("Nothing new — no email sent.")
        return
    send_email(build_email(new_jobs), len(new_jobs))
    seen.update(j["url"] for j in new_jobs)
    save_seen(seen)


if __name__ == "__main__":
    main()
