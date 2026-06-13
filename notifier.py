"""Send job-found notifications via Telegram and/or WhatsApp (Evolution API)."""

import requests
import config

_TIMEOUT = 10
_MAX_JOBS_IN_MSG = 10


def _telegram(text: str) -> None:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=_TIMEOUT,
        )
    except Exception as e:
        print(f"[notifier:telegram] error: {e}")


def _whatsapp(text: str) -> None:
    if not config.EVOLUTION_API_URL or not config.EVOLUTION_API_KEY \
            or not config.EVOLUTION_INSTANCE or not config.EVOLUTION_PHONE:
        return
    try:
        requests.post(
            f"{config.EVOLUTION_API_URL.rstrip('/')}/message/sendText/{config.EVOLUTION_INSTANCE}",
            headers={"apikey": config.EVOLUTION_API_KEY, "Content-Type": "application/json"},
            json={"number": config.EVOLUTION_PHONE, "text": text},
            timeout=_TIMEOUT,
        )
    except Exception as e:
        print(f"[notifier:whatsapp] error: {e}")


def _build_message(new_jobs: list, total_scraped: int) -> tuple:
    count = len(new_jobs)
    shown = new_jobs[:_MAX_JOBS_IN_MSG]
    overflow = count - len(shown)

    # --- Telegram (HTML) ---
    lines_tg = [f"🔍 <b>Job Finder — {count} new job{'s' if count != 1 else ''}</b>\n"]
    for i, job in enumerate(shown, 1):
        title = job.get("title", "Unknown role")
        company = job.get("company") or "?"
        location = job.get("location") or "Remote"
        source = job.get("source", "")
        url = job.get("url", "")
        email = job.get("hiring_email", "")
        tag = " · 🟢 contract" if job.get("freelance") else ""

        lines_tg.append(
            f"{i}. <b>{title}</b> @ {company}\n"
            f"   📍 {location} · {source}{tag}\n"
            + (f"   ✉️ {email}\n" if email else "")
            + (f"   🔗 <a href=\"{url}\">Apply</a>\n" if url else "")
        )

    if overflow:
        lines_tg.append(f"\n…and <b>{overflow} more</b> in the app.")

    lines_tg.append(f"\n<i>Scraped {total_scraped} total listings.</i>")
    tg_text = "\n".join(lines_tg)

    # --- WhatsApp (plain text) ---
    lines_wa = [f"🔍 Job Finder — {count} new job{'s' if count != 1 else ''}\n"]
    for i, job in enumerate(shown, 1):
        title = job.get("title", "Unknown role")
        company = job.get("company") or "?"
        location = job.get("location") or "Remote"
        source = job.get("source", "")
        url = job.get("url", "")
        email = job.get("hiring_email", "")
        tag = " · 🟢 contract" if job.get("freelance") else ""

        lines_wa.append(
            f"{i}. {title} @ {company}\n"
            f"   📍 {location} · {source}{tag}\n"
            + (f"   ✉️ {email}\n" if email else "")
            + (f"   🔗 {url}\n" if url else "")
        )

    if overflow:
        lines_wa.append(f"\n…and {overflow} more in the app.")

    lines_wa.append(f"\nScraped {total_scraped} total listings.")
    wa_text = "\n".join(lines_wa)

    return tg_text, wa_text


def notify(new_jobs: list, total_scraped: int) -> None:
    if not new_jobs:
        return
    tg_text, wa_text = _build_message(new_jobs, total_scraped)
    _telegram(tg_text)
    _whatsapp(wa_text)
