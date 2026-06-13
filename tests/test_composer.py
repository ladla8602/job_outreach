def _mock_openai_client(response_text: str):
    class FakeMessage:
        content = response_text

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    return FakeClient()


def test_compose_returns_subject_with_title(monkeypatch):
    import composer
    monkeypatch.setattr(composer, "_client", _mock_openai_client("Short email body here."))
    job = {"title": "Senior Engineer", "company": "Acme", "description": "NestJS role"}
    subject, _ = composer.compose(job)
    assert "Senior Engineer" in subject
    assert "remote/contract" in subject


def test_compose_appends_signoff(monkeypatch):
    import composer
    monkeypatch.setattr(composer, "_client", _mock_openai_client("I saw your posting."))
    job = {"title": "Dev", "company": "Co", "description": "Build stuff"}
    _, body = composer.compose(job)
    assert "ladla8602@gmail.com" in body
    assert "+91 86028 38269" in body
    assert "Mohd Gayasuddin" in body


def test_compose_body_contains_ai_text(monkeypatch):
    import composer
    ai_text = "I saw your posting. My NestJS matches perfectly. Happy to chat."
    monkeypatch.setattr(composer, "_client", _mock_openai_client(ai_text))
    job = {"title": "Dev", "company": "Co", "description": "NestJS"}
    _, body = composer.compose(job)
    assert ai_text in body


def test_compose_truncates_description_to_500_chars(monkeypatch):
    import composer
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured["messages"] = kwargs["messages"]

            class FakeMsg:
                content = "body"

            class FakeChoice:
                message = FakeMsg()

            class FakeResp:
                choices = [FakeChoice()]

            return FakeResp()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(composer, "_client", FakeClient())
    job = {"title": "Dev", "company": "Co", "description": "x" * 1000}
    composer.compose(job)
    user_msg = captured["messages"][1]["content"]
    assert "x" * 501 not in user_msg
