from app.ai.rule_based import RuleBasedProvider
from app.models.enums import Category, Priority


def test_billing_keyword_maps_to_billing_category():
    r = RuleBasedProvider().triage("Refund for double charge", "I was billed twice on my invoice")
    assert r.category == Category.billing


def test_password_keyword_maps_to_account_access():
    r = RuleBasedProvider().triage("Cannot login", "I forgot my password and am locked out")
    assert r.category == Category.account_access


def test_critical_keyword_bumps_priority():
    r = RuleBasedProvider().triage("Production down", "Outage, system is completely broken urgent")
    assert r.priority == Priority.critical


def test_unknown_text_defaults_to_general_medium():
    r = RuleBasedProvider().triage("Hello", "Just saying hi")
    assert r.category == Category.general
    assert r.priority == Priority.medium


def test_suggested_response_is_nonempty():
    r = RuleBasedProvider().triage("Bug", "App crashes")
    assert isinstance(r.suggested_response, str) and len(r.suggested_response) > 0
