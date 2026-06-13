# Job Outreach

A personal job-search automation tool that scrapes **7 remote job boards in parallel**, discovers hiring contact emails, drafts tailored cold-outreach emails with GPT-4o-mini, surfaces everything in a clean Flask web UI — and notifies you instantly on **Telegram and WhatsApp** when new jobs are found.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=flat&logo=flask)
![OpenAI](https://img.shields.io/badge/GPT--4o--mini-OpenAI-412991?style=flat&logo=openai)
![Telegram](https://img.shields.io/badge/Telegram-notifications-26A5E4?style=flat&logo=telegram)
![Tests](https://img.shields.io/badge/tests-31%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## How it works

```
┌─────────────────────────────────────────────────────────┐
│                     pipeline.py                         │
│                                                         │
│  collect_jobs()          find_email()     compose()     │
│  ┌─────────────┐        ┌───────────┐   ┌───────────┐  │
│  │ RemoteOK    │──┐     │ 1. Parse  │   │ GPT-4o    │  │
│  │ Remotive    │  │     │    desc   │   │   mini    │  │
│  │ Arbeitnow   │  ├────▶│ 2. Scrape │──▶│           │  │
│  │ WeWorkRemo  │  │     │    page   │   │ tailored  │  │
│  │ HN Hiring   │  │     │ 3. DDG    │   │  draft    │  │
│  │ Jobicy      │  │     │    search │   └───────────┘  │
│  │ LinkedIn    │──┘     └───────────┘         │        │
│  └─────────────┘                              ▼        │
│  ThreadPoolExecutor                      jobs.json      │
│  (~1-2s wall-clock)                           │        │
└──────────────────────────────┬────────────────┼────────┘
                               │                │
                               ▼                ▼
                ┌──────────────────┐   ┌─────────────────┐
                │   app.py (Flask) │   │   notifier.py   │
                │                  │   │                 │
                │  Job review card │   │ 📱 Telegram     │
                │  ┌────────────┐  │   │ 💬 WhatsApp     │
                │  │ AI draft   │  │   │  (Evolution API)│
                │  │ (editable) │  │   └─────────────────┘
                │  └────────────┘  │
                │  [Send] [Apply]  │
                │  [Gmail] [Skip]  │
                └──────────────────┘
```

---

## Features

- **7 job sources scraped in parallel** — RemoteOK, Remotive, Arbeitnow, We Work Remotely, Hacker News "Who is hiring?", Jobicy, LinkedIn public search
- **3-step email discovery** — extracts emails from job description → scrapes the apply page → falls back to DuckDuckGo search
- **AI-drafted cold outreach** — GPT-4o-mini writes a concise 3-sentence email matched to the job description and your tech profile
- **Smart deduplication** — `seen_jobs.json` ensures only genuinely new listings are processed on each run
- **Keyword filtering** — title-level and description-level filters keep only relevant software engineering roles; exclusions drop stacks outside your profile
- **Instant notifications** — Telegram bot and/or WhatsApp (Evolution API) message with job titles, companies, apply links, and contact emails as soon as a run completes
- **Flask web UI** — job review cards with editable AI draft, one-click SMTP send with resume attached, Gmail compose fallback when SMTP is not configured, skip button, live background refresh
- **Headless pipeline** — run `pipeline.py` from cron or GitHub Actions without a browser
- **31 tests** — full pytest coverage across all modules

---

## Tech stack

| Layer | Tech |
|-------|------|
| Job scraping | `requests`, `BeautifulSoup4`, `xml.etree`, concurrent `ThreadPoolExecutor` |
| Email discovery | regex, BeautifulSoup4 page scrape, `ddgs` (DuckDuckGo) |
| AI composition | OpenAI `gpt-4o-mini` via `openai` SDK |
| Notifications | Telegram Bot API, WhatsApp via Evolution API |
| Web UI | Flask, Jinja2, Tailwind CSS (CDN) |
| Config | `python-dotenv` |
| Tests | `pytest` |

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/ladla8602/job_outreach.git
cd job_outreach
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
RESUME_PATH=/absolute/path/to/your_resume.pdf
OPENAI_API_KEY=sk-...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=you@gmail.com
SMTP_PASS=xxxx-xxxx-xxxx-xxxx        # Gmail App Password (16 chars)

# Notifications — omit any block to skip that channel
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# WhatsApp via Evolution API (optional)
EVOLUTION_API_URL=https://your-evolution-instance.com
EVOLUTION_API_KEY=your-api-key
EVOLUTION_INSTANCE=your-instance-name
EVOLUTION_PHONE=919876543210@s.whatsapp.net
```

> **Gmail App Password:** Google Account → Security → 2-Step Verification → App passwords → create one for "Mail".

> **Telegram bot:** Create one via [@BotFather](https://t.me/botfather), then get your chat ID by sending any message to the bot and calling `https://api.telegram.org/bot<TOKEN>/getUpdates`.

### 4. Customize your profile

Open [composer.py](composer.py) and replace `_PROFILE` with your own experience, tech stack, and key metrics. This is what GPT-4o-mini uses to write your cold emails — specificity here directly improves output quality.

Also review the keyword lists in [job_finder.py](job_finder.py):

```python
_TECH_KEYWORDS    # stacks you work with — positive signal
_EXCLUDE_KEYWORDS # stacks you don't work with — exclusion filter
ROLE_KEYWORDS     # job titles that qualify
FREELANCE_ONLY    # set True to keep only contract/part-time roles
```

---

## Usage

### Web UI (recommended)

```bash
python app.py
# Open http://localhost:8000
```

On first run the job list will be empty. Click **Fetch Jobs** — the pipeline runs in the background (~30s) and the page auto-refreshes when done.

For each job card you can:
- **Edit** the AI-drafted email inline
- **Send** — delivers via SMTP with your resume attached *(shown when SMTP is configured)*
- **Open in Gmail** — opens Gmail compose in a new tab with To, Subject, and body pre-filled *(shown when SMTP is not configured)*
- **Apply** — opens the original listing in a new tab
- **Skip** — removes the card and marks it as seen

### Pipeline (headless / cron)

```bash
python pipeline.py
```

Fetches, enriches, writes to `jobs.json`, and fires Telegram + WhatsApp notifications. Ideal for scheduled runs without a browser open.

### Legacy digest emailer

```bash
python job_finder.py
```

Emails you an HTML digest of new jobs without GPT drafts or notifications. Useful for simple cron-only setups.

---

## Notifications

When `pipeline.py` completes, **notifier.py** fires simultaneously to all configured channels.

**Telegram** — formatted HTML message with job title, company, location, source, contact email, and a direct apply link for each new job.

**WhatsApp (Evolution API)** — same content as plain text sent to your number via your self-hosted Evolution instance.

Both channels are independently optional — configure only the ones you need by setting the corresponding env vars.

---

## Running tests

```bash
pytest           # 31 tests
pytest -v        # with output
```

---

## Scheduling (run twice a day)

**GitHub Actions (recommended — free, nothing to keep running)**

Push to your repo, then add these secrets under *Settings → Secrets → Actions*:

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI key for email drafts |
| `SMTP_USER` | Gmail address to send from |
| `SMTP_PASS` | Gmail App Password |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `EVOLUTION_API_URL` | Evolution API base URL *(optional)* |
| `EVOLUTION_API_KEY` | Evolution API key *(optional)* |
| `EVOLUTION_INSTANCE` | Evolution instance name *(optional)* |
| `EVOLUTION_PHONE` | WhatsApp number e.g. `919876543210@s.whatsapp.net` *(optional)* |

The included [`.github/workflows/job-finder.yml`](.github/workflows/job-finder.yml) runs `pipeline.py` at **06:00 & 18:00 UTC** (11:30 AM & 11:30 PM IST). You can also trigger it manually from the Actions tab.

**cron (local machine)**

```cron
0 9,21 * * * cd /path/to/job_outreach && venv/bin/python pipeline.py >> run.log 2>&1
```

---

## Project structure

```
job_outreach/
├── app.py            # Flask web UI + REST endpoints
├── pipeline.py       # Orchestrator: fetch → find email → compose → notify → save
├── job_finder.py     # Job board scrapers (7 sources) + legacy digest emailer
├── email_finder.py   # 3-step hiring email discovery
├── composer.py       # GPT-4o-mini cold outreach composer
├── notifier.py       # Telegram + WhatsApp (Evolution API) notifications
├── config.py         # Env var loading
├── templates/
│   └── index.html    # Tailwind job review UI
├── tests/            # pytest suite (31 tests)
├── .github/
│   └── workflows/
│       └── job-finder.yml   # GitHub Actions scheduled runner
├── .env.example
└── requirements.txt
```

---

## License

MIT
