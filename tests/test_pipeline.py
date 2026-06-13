import json
import pytest


@pytest.fixture
def patched_pipeline(tmp_path, monkeypatch):
    import config
    jobs_file = tmp_path / "jobs.json"
    monkeypatch.setattr(config, "JOBS_FILE", jobs_file)

    fake_job = {
        "title": "Dev", "company": "Acme", "location": "Remote",
        "url": "https://remoteok.com/1", "source": "RemoteOK",
        "freelance": False, "description": "Python dev needed",
    }

    monkeypatch.setattr("pipeline.collect_jobs", lambda: [fake_job])
    monkeypatch.setattr("pipeline.load_seen", lambda: set())
    monkeypatch.setattr("pipeline.save_seen", lambda s: None)
    monkeypatch.setattr("pipeline.find_email", lambda j: ("hire@acme.com", ["https://linkedin.com/in/jane"]))
    monkeypatch.setattr("pipeline.compose", lambda j: ("Dev — remote/contract", "Hi, I saw your posting..."))

    return jobs_file


def test_pipeline_writes_enriched_jobs(patched_pipeline):
    from pipeline import run
    run()

    result = json.loads(patched_pipeline.read_text())
    assert len(result) == 1
    job = result[0]
    assert job["hiring_email"] == "hire@acme.com"
    assert job["linkedin_hints"] == ["https://linkedin.com/in/jane"]
    assert job["email_draft"] == "Hi, I saw your posting..."
    assert job["status"] == "pending"
    assert job["apply_link"] == "https://remoteok.com/1"


def test_pipeline_preserves_sent_jobs(patched_pipeline, monkeypatch):
    import config

    existing = [{
        "url": "https://remoteok.com/old",
        "title": "Old Job", "company": "Old Co", "location": "Remote",
        "source": "RemoteOK", "freelance": False, "description": "",
        "apply_link": "https://remoteok.com/old",
        "hiring_email": "old@co.com", "linkedin_hints": [],
        "email_subject": "Old Job — remote/contract",
        "email_draft": "Hi...", "status": "sent",
    }]
    patched_pipeline.write_text(json.dumps(existing))

    from pipeline import run
    run()

    result = json.loads(patched_pipeline.read_text())
    statuses = {j["url"]: j["status"] for j in result}
    assert statuses.get("https://remoteok.com/old") == "sent"
    assert statuses.get("https://remoteok.com/1") == "pending"


def test_pipeline_skips_already_seen_jobs(patched_pipeline, monkeypatch):
    monkeypatch.setattr("pipeline.load_seen", lambda: {"https://remoteok.com/1"})

    from pipeline import run
    run()

    result = json.loads(patched_pipeline.read_text())
    assert len(result) == 0
