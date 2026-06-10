from unittest.mock import MagicMock
from app.ai.gemini import GeminiProvider
from app.ai.factory import get_triage_provider, SafeTriageProvider
from app.ai.rule_based import RuleBasedProvider
from app.models.enums import Category, Priority


def _fake_client(text: str):
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=text)
    return client


def test_gemini_parses_valid_json():
    client = _fake_client(
        '{"category": "billing", "priority": "high", "suggested_response": "We will help."}'
    )
    p = GeminiProvider(client=client, model="x")
    r = p.triage("Charge", "Double billed")
    assert r.category == Category.billing
    assert r.priority == Priority.high
    assert r.suggested_response == "We will help."


def test_gemini_strips_markdown_fences():
    client = _fake_client(
        '```json\n{"category":"technical","priority":"low","suggested_response":"ok"}\n```'
    )
    r = GeminiProvider(client=client, model="x").triage("t", "d")
    assert r.category == Category.technical


def test_gemini_invalid_json_raises():
    client = _fake_client("not json at all")
    p = GeminiProvider(client=client, model="x")
    try:
        p.triage("t", "d")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_factory_without_key_returns_rule_based():
    provider = get_triage_provider(api_key="", model="x")
    assert isinstance(provider, RuleBasedProvider)


class _Boom:
    def triage(self, title, description):
        raise RuntimeError("api down")


def test_safe_provider_falls_back_on_error():
    r = SafeTriageProvider(_Boom()).triage("urgent outage", "system down")
    assert r.priority == Priority.critical  # came from rule-based fallback
