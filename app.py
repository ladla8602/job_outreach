import json
import smtplib
from email.message import EmailMessage

from flask import Flask, render_template, request, jsonify
import config

app = Flask(__name__)


def _read_jobs():
    if not config.JOBS_FILE.exists():
        return []
    return json.loads(config.JOBS_FILE.read_text())


def _write_jobs(jobs):
    config.JOBS_FILE.write_text(json.dumps(jobs, indent=2))


def _update_status(url: str, status: str) -> bool:
    jobs = _read_jobs()
    for job in jobs:
        if job["url"] == url:
            job["status"] = status
            _write_jobs(jobs)
            return True
    return False


@app.route("/")
def index():
    all_jobs = _read_jobs()
    counts = {
        "pending": sum(1 for j in all_jobs if j.get("status") == "pending"),
        "sent": sum(1 for j in all_jobs if j.get("status") == "sent"),
        "skipped": sum(1 for j in all_jobs if j.get("status") == "skipped"),
    }
    pending = [j for j in all_jobs if j.get("status") == "pending"]
    resume_name = config.RESUME_PATH.name if config.RESUME_PATH and config.RESUME_PATH.exists() else None
    return render_template("index.html", jobs=pending, counts=counts, resume_name=resume_name)


@app.route("/skip", methods=["POST"])
def skip_job():
    url = request.form.get("url", "")
    if not _update_status(url, "skipped"):
        return jsonify({"error": "job not found"}), 404
    return jsonify({"ok": True})


@app.route("/send", methods=["POST"])
def send_email():
    url = request.form.get("url", "")
    body = request.form.get("body", "")
    subject = request.form.get("subject", "")

    jobs = _read_jobs()
    job = next((j for j in jobs if j["url"] == url), None)
    if not job:
        return jsonify({"error": "job not found"}), 404

    to_email = job.get("hiring_email")
    if not to_email:
        return jsonify({"error": "no hiring email for this job"}), 400

    msg = EmailMessage()
    msg["Subject"] = subject or job["email_subject"]
    msg["From"] = config.SMTP_USER
    msg["To"] = to_email
    msg.set_content(body or job["email_draft"])

    if config.RESUME_PATH and config.RESUME_PATH.exists():
        with open(config.RESUME_PATH, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=config.RESUME_PATH.name,
            )

    try:
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.send_message(msg)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    _update_status(url, "sent")
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
