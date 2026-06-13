def test_extract_email_finds_address_in_text():
    from email_finder import _extract_email
    assert _extract_email("Contact us at hiring@acme.com for details") == "hiring@acme.com"


def test_extract_email_ignores_example_domains():
    from email_finder import _extract_email
    assert _extract_email("send to user@example.com") is None


def test_extract_email_returns_none_when_absent():
    from email_finder import _extract_email
    assert _extract_email("No email in this text at all") is None


def test_extract_email_returns_first_valid():
    from email_finder import _extract_email
    result = _extract_email("a@test.com or real@company.io")
    assert result == "real@company.io"


from unittest.mock import patch, MagicMock


def test_scan_page_extracts_mailto_href():
    from email_finder import _scan_page

    mock_resp = MagicMock()
    mock_resp.text = '<html><a href="mailto:hire@co.com?subject=apply">Apply</a></html>'
    mock_resp.raise_for_status = MagicMock()

    with patch("email_finder.requests.get", return_value=mock_resp):
        email, hints = _scan_page("https://co.com/jobs")

    assert email == "hire@co.com"
    assert hints == []


def test_scan_page_falls_back_to_text_scan():
    from email_finder import _scan_page

    mock_resp = MagicMock()
    mock_resp.text = "<html><p>Email us at careers@widget.io to apply.</p></html>"
    mock_resp.raise_for_status = MagicMock()

    with patch("email_finder.requests.get", return_value=mock_resp):
        email, hints = _scan_page("https://widget.io/jobs")

    assert email == "careers@widget.io"


def test_scan_page_returns_none_on_request_error():
    from email_finder import _scan_page

    with patch("email_finder.requests.get", side_effect=Exception("timeout")):
        email, hints = _scan_page("https://co.com/jobs")

    assert email is None
    assert hints == []


def test_scan_page_returns_none_for_empty_url():
    from email_finder import _scan_page
    email, hints = _scan_page("")
    assert email is None
    assert hints == []


def _fake_ddgs(results):
    class FakeDDGS:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def text(self, q, max_results=5): return results
    return FakeDDGS


def test_ddg_search_extracts_email_from_snippet(monkeypatch):
    from email_finder import _ddg_search
    results = [{"body": "Reach our team at recruit@acme.com for roles.", "href": ""}]
    monkeypatch.setattr("email_finder.DDGS", _fake_ddgs(results))
    email, hints = _ddg_search("Acme", "Software Engineer")
    assert email == "recruit@acme.com"


def test_ddg_search_collects_linkedin_hints(monkeypatch):
    from email_finder import _ddg_search
    results = [{"body": "See profile.", "href": "https://linkedin.com/in/jane-recruiter"}]
    monkeypatch.setattr("email_finder.DDGS", _fake_ddgs(results))
    email, hints = _ddg_search("Corp", "Dev")
    assert email is None
    assert any("jane-recruiter" in h for h in hints)


def test_ddg_search_returns_none_for_empty_company(monkeypatch):
    from email_finder import _ddg_search
    email, hints = _ddg_search("", "Dev")
    assert email is None
    assert hints == []


def test_find_email_uses_description_first(monkeypatch):
    from email_finder import find_email
    monkeypatch.setattr("email_finder._scan_page", lambda url: (None, []))
    monkeypatch.setattr("email_finder._ddg_search", lambda c, t: (None, []))
    job = {"description": "Apply at boss@startup.io", "url": "", "company": "S", "title": "Dev"}
    email, _ = find_email(job)
    assert email == "boss@startup.io"


def test_find_email_falls_back_to_page(monkeypatch):
    from email_finder import find_email
    monkeypatch.setattr("email_finder._scan_page", lambda url: ("page@co.com", []))
    monkeypatch.setattr("email_finder._ddg_search", lambda c, t: (None, []))
    job = {"description": "No email", "url": "https://co.com/job", "company": "Co", "title": "Dev"}
    email, _ = find_email(job)
    assert email == "page@co.com"


def test_find_email_falls_back_to_ddg(monkeypatch):
    from email_finder import find_email
    monkeypatch.setattr("email_finder._scan_page", lambda url: (None, []))
    monkeypatch.setattr("email_finder._ddg_search", lambda c, t: ("ddg@co.com", []))
    job = {"description": "No email", "url": "https://co.com/job", "company": "Co", "title": "Dev"}
    email, _ = find_email(job)
    assert email == "ddg@co.com"


def test_find_email_returns_none_when_all_fail(monkeypatch):
    from email_finder import find_email
    monkeypatch.setattr("email_finder._scan_page", lambda url: (None, []))
    monkeypatch.setattr("email_finder._ddg_search", lambda c, t: (None, []))
    job = {"description": "No email", "url": "https://co.com", "company": "Co", "title": "Dev"}
    email, hints = find_email(job)
    assert email is None
    assert hints == []
