from app.ai.base import TriageProvider, TriageResult
from app.models.enums import Category, Priority

_CATEGORY_KEYWORDS = {
    Category.billing: ["bill", "invoice", "charge", "refund", "payment", "subscription", "price"],
    Category.account_access: ["login", "log in", "password", "locked", "access", "2fa", "sign in"],
    Category.technical: ["error", "bug", "crash", "broken", "not working", "fail", "outage", "500"],
    Category.feature_request: ["feature", "request", "would be nice", "suggest", "add support", "enhancement"],
}

_PRIORITY_KEYWORDS = {
    Priority.critical: ["urgent", "critical", "outage", "down", "asap", "immediately", "data loss"],
    Priority.high: ["important", "blocked", "cannot", "can't", "broken", "error"],
    Priority.low: ["question", "wondering", "minor", "typo", "cosmetic", "whenever"],
}

_RESPONSES = {
    Category.billing: "Thanks for reaching out about your billing concern. We're reviewing your account and will follow up with details shortly.",
    Category.account_access: "Sorry you're having trouble accessing your account. We're looking into it and will help you regain access as soon as possible.",
    Category.technical: "Thanks for the report. Our technical team is investigating the issue and we'll keep you updated on progress.",
    Category.feature_request: "Thanks for the suggestion! We've logged your feature request and will share it with our product team.",
    Category.general: "Thanks for contacting support. We've received your request and will get back to you shortly.",
}


class RuleBasedProvider(TriageProvider):
    """Deterministic fallback used when Gemini is unavailable; also the test double."""

    def triage(self, title: str, description: str) -> TriageResult:
        text = f"{title} {description}".lower()
        category = self._match_category(text)
        priority = self._match_priority(text)
        return TriageResult(
            category=category,
            priority=priority,
            suggested_response=_RESPONSES[category],
        )

    def _match_category(self, text: str) -> Category:
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if any(k in text for k in keywords):
                return category
        return Category.general

    def _match_priority(self, text: str) -> Priority:
        for priority, keywords in _PRIORITY_KEYWORDS.items():
            if any(k in text for k in keywords):
                return priority
        return Priority.medium
