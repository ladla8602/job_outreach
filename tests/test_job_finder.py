from unittest.mock import MagicMock, patch


def test_fetch_remoteok_includes_description():
    from job_finder import fetch_remoteok

    fake_data = [
        {"legal": True},
        {
            "position": "Senior React Engineer",
            "company": "Acme",
            "description": "We need a React developer with Node experience.",
            "tags": ["react", "node", "remote"],
            "url": "https://remoteok.com/123",
            "location": "Remote",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_data
    mock_resp.raise_for_status = MagicMock()

    with patch("job_finder.requests.get", return_value=mock_resp):
        jobs = fetch_remoteok()

    assert len(jobs) == 1
    assert "description" in jobs[0]
    assert jobs[0]["description"] == "We need a React developer with Node experience."


def test_fetch_remotive_includes_description():
    from job_finder import fetch_remotive

    fake_data = {
        "jobs": [
            {
                "title": "Full Stack Developer",
                "description": "Build our SaaS platform.",
                "company_name": "Startup",
                "candidate_required_location": "Worldwide",
                "url": "https://remotive.com/job/1",
                "job_type": "contract",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_data
    mock_resp.raise_for_status = MagicMock()

    with patch("job_finder.requests.get", return_value=mock_resp):
        jobs = fetch_remotive()

    assert len(jobs) == 1
    assert jobs[0]["description"] == "Build our SaaS platform."
