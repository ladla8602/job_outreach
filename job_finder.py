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
from email.message import EmailMessage
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration  (edit these, or override the email ones via env vars/secrets)
# ---------------------------------------------------------------------------

# Roles you care about — matched against title + description, case-insensitive.
ROLE_KEYWORDS = [
    "software engineer", "software developer", "full stack", "full-stack",
    "fullstack", "frontend", "front-end", "backend", "back-end",
    "web developer", "node", "nestjs", "angular", "react", "next.js",
    "typescript", "javascript", "python", "flutter",
]

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

def _match_role(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ROLE_KEYWORDS)


def _looks_freelance(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in FREELANCE_KEYWORDS)


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
        if not _match_role(blob):
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
        if not _match_role(blob):
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
        if not _match_role(blob):
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
        if not _match_role(blob):
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
            if not text or not _match_role(text) or "remote" not in text.lower():
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
    all_jobs = []
    for fn in (fetch_remoteok, fetch_remotive, fetch_arbeitnow,
               fetch_weworkremotely, fetch_hackernews):
        all_jobs.extend(fn())
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
