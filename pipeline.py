import json
import config
from job_finder import collect_jobs, load_seen, save_seen
from email_finder import find_email
from composer import compose


def run():
    seen = load_seen()
    all_jobs = collect_jobs()
    new_jobs = [j for j in all_jobs if j["url"] not in seen]
    print(f"Scraped {len(all_jobs)} jobs, {len(new_jobs)} are new.")

    existing_by_url = {}
    if config.JOBS_FILE.exists():
        try:
            for j in json.loads(config.JOBS_FILE.read_text()):
                existing_by_url[j["url"]] = j
        except Exception:
            pass

    results = [j for j in existing_by_url.values() if j.get("status") in ("sent", "skipped")]

    for i, job in enumerate(new_jobs, 1):
        print(f"[{i}/{len(new_jobs)}] {job['title']} @ {job['company']}")
        email, hints = find_email(job)
        subject, draft = compose(job)
        results.append({
            **job,
            "apply_link": job["url"],
            "hiring_email": email,
            "linkedin_hints": hints,
            "email_subject": subject,
            "email_draft": draft,
            "status": "pending",
        })
        seen.add(job["url"])

    config.JOBS_FILE.write_text(json.dumps(results, indent=2))
    save_seen(seen)
    print(f"Done. {len(new_jobs)} new jobs saved to {config.JOBS_FILE}")


if __name__ == "__main__":
    run()
