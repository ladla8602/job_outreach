from openai import OpenAI
import config

_PROFILE = (
    "Mohd Gayasuddin, senior full-stack developer "
    "(6.5 yrs, Angular/React/Node/NestJS, fintech & SaaS, "
    "built Payflex BNPL portals serving 100k+ monthly checkouts)"
)

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
        f"You are writing a short cold outreach email on behalf of {_PROFILE}.\n\n"
        "Write a 3-sentence email body:\n"
        "1. Mention the specific role and company.\n"
        "2. Connect one concrete detail from the job description to Mohd's experience.\n"
        "3. Call to action — happy to share resume / jump on a call.\n\n"
        "Tone: direct, warm, no fluff. "
        "Return ONLY the email body — no subject line, no sign-off."
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
