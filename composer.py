from openai import OpenAI
import config

_PROFILE = """Mohd Gayasuddin — Senior Full-Stack Developer, 6.5+ years, remote from India (IST).

EXPERIENCE:
- Senior Full-Stack Developer, Azilen Technologies (May 2022–present)
- Full-Stack Developer, FxBytes Technologies (Nov 2019–Apr 2022)

STACK:
- Frontend: Angular, ReactJS, Next.js, Flutter (Android/iOS)
- Backend: Node.js, NestJS, FastAPI, Laravel
- Languages: TypeScript, JavaScript, Python, PHP, Dart
- Databases: PostgreSQL, MySQL, MongoDB, Redis, Vector DBs
- Cloud/DevOps: Azure DevOps CI/CD, Docker, AWS, Nginx, PM2
- APIs: REST, GraphQL, WebSockets, gRPC
- AI/ML: OpenAI API, Anthropic, RAG with vector search, Vertex AI

KEY METRICS:
- Cut Node.js/NestJS API latency 40% via REST optimisation at Azilen Technologies
- Led Payflex BNPL portals (Angular + Flutter) serving 100k+ monthly checkouts
- Cut admin processing time 50% at FxBytes via Angular/Laravel admin panels across 100+ endpoints

SELECTED PROJECTS:
- Payflex (BNPL fintech): Lead dev; Customer, Checkout, Merchant portals in Angular; Flutter mobile; JS merchant embed widget; payment provider integrations; Azure DevOps CI/CD
- OrbitDesk (Omnichannel CRM): Architect & lead dev; 7 messaging channels (WhatsApp, Telegram, Instagram, Facebook, Email, SMS, Live Chat); RAG AI chatbots (OpenAI/Anthropic, vector search, tool-calling); AI voice calls (OpenAI Realtime API + Twilio); drag-and-drop automation builder; Stripe & Razorpay subscriptions; AES-256 per-tenant isolation
- AdSpot Pro (Digital Signage SaaS): Product owner + developer; NestJS + React; WebSocket concurrency; smart scheduling; real-time analytics; multi-currency; 15+ languages; published on CodeCanyon
- Vountain (RWA tokenization / blockchain): Next.js frontend; blockchain digital passports; multilingual EN/DE; SEO-optimised
- Eclipse (Banking-as-a-Service): Angular UI + Java Spring Boot REST APIs; tenant onboarding, KYC, payments, fraud monitoring, multi-currency
- ACS Connection System (Payment gateway): Node.js service routing card/wallet transactions via Postilion; real-time authorisation & settlement
- WhatsCRM: Multi-tenant WhatsApp CRM — NestJS, ReactJS, FastAPI microservice
- Online Doctor Appointment: Team lead; NodeJS + Flutter apps; Paytm integration; DigitalOcean hosting"""

_SIGN_OFF = "\n\nBest,\nMohd Gayasuddin · ladla8602@gmail.com · +91 86028 38269"

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def compose(job: dict) -> tuple:
    """Return (subject, full_email_body_with_signoff)."""
    title = job.get("title", "")
    company = job.get("company", "")
    description = (job.get("description", "") or "")[:500]

    subject = f"{title} — available for remote/contract work"

    system = (
        "You are writing a short cold outreach email on behalf of the following candidate:\n\n"
        f"{_PROFILE}\n\n"
        "Write a 3-sentence email body:\n"
        "1. Mention the specific role and company.\n"
        "2. Pick the ONE most relevant project or metric from the candidate profile that matches "
        "a specific requirement or technology mentioned in the job description — name it concretely.\n"
        "3. Call to action — happy to share resume / jump on a call.\n\n"
        "Tone: direct, warm, no fluff. First-person. "
        "Return ONLY the email body — no subject line, no sign-off, no 'Hi [name]' opener."
    )

    user = f"Job: {title} at {company}\nDescription excerpt: {description}"

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=200,
        temperature=0.7,
    )

    body = response.choices[0].message.content.strip()
    return subject, body + _SIGN_OFF
