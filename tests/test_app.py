import json
import pytest


SAMPLE_JOB = {
    "url": "https://example.com/job/1",
    "title": "Engineer",
    "company": "Acme",
    "location": "Remote",
    "source": "RemoteOK",
    "freelance": False,
    "apply_link": "https://example.com/job/1",
    "hiring_email": "cto@acme.com",
    "linkedin_hints": [],
    "email_subject": "Engineer — available for remote/contract work",
    "email_draft": "Hi,\n\nI saw your posting.\n\nBest,\nMohd",
    "status": "pending",
}


@pytest.fixture
def jobs_file(tmp_path):
    f = tmp_path / "jobs.json"
    f.write_text(json.dumps([SAMPLE_JOB]))
    return f


@pytest.fixture
def client(jobs_file, tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "JOBS_FILE", jobs_file)
    monkeypatch.setattr(config, "RESUME_PATH", tmp_path / "resume.pdf")

    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200


def test_index_shows_pending_job(client):
    r = client.get("/")
    assert b"Acme" in r.data
    assert b"Engineer" in r.data


def test_index_shows_counts(client):
    r = client.get("/")
    assert b"pending" in r.data


def test_skip_marks_job_skipped(client, jobs_file):
    r = client.post("/skip", data={"url": "https://example.com/job/1"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    jobs = json.loads(jobs_file.read_text())
    assert jobs[0]["status"] == "skipped"


def test_skip_unknown_url_returns_404(client):
    r = client.post("/skip", data={"url": "https://no-such-job.com"})
    assert r.status_code == 404


def test_send_calls_smtp_and_marks_sent(client, jobs_file, monkeypatch):
    import smtplib
    sent = []

    class FakeSMTP:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def login(self, *a): pass
        def send_message(self, msg): sent.append(msg)

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr("config.SMTP_USER", "ladla8602@gmail.com")
    monkeypatch.setattr("config.SMTP_PASS", "apppassword")

    r = client.post("/send", data={
        "url": "https://example.com/job/1",
        "subject": "Engineer role",
        "body": "Hi, I want this job.",
    })

    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    assert len(sent) == 1
    assert sent[0]["Subject"] == "Engineer role"
    assert sent[0]["To"] == "cto@acme.com"

    jobs = json.loads(jobs_file.read_text())
    assert jobs[0]["status"] == "sent"


def test_send_returns_400_when_no_hiring_email(client, jobs_file, monkeypatch):
    jobs = json.loads(jobs_file.read_text())
    jobs[0]["hiring_email"] = None
    jobs_file.write_text(json.dumps(jobs))

    r = client.post("/send", data={"url": "https://example.com/job/1"})
    assert r.status_code == 400
