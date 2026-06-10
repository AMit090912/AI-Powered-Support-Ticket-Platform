import logging

from app.ai.base import TriageProvider, TriageResult
from app.ai.rule_based import RuleBasedProvider
from app.ai.gemini import GeminiProvider

logger = logging.getLogger(__name__)


def get_triage_provider(api_key: str, model: str) -> TriageProvider:
    """Return Gemini when a key is configured, else the rule-based fallback."""
    if not api_key:
        logger.info("No GEMINI_API_KEY set; using RuleBasedProvider.")
        return RuleBasedProvider()
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        return GeminiProvider(client=client, model=model)
    except Exception as exc:  # import or client init failure
        logger.warning("Gemini init failed (%s); using RuleBasedProvider.", exc)
        return RuleBasedProvider()


class SafeTriageProvider(TriageProvider):
    """Wraps a primary provider; on ANY failure falls back to rule-based."""

    def __init__(self, primary: TriageProvider):
        self._primary = primary
        self._fallback = RuleBasedProvider()

    def triage(self, title: str, description: str) -> TriageResult:
        try:
            return self._primary.triage(title, description)
        except Exception as exc:
            logger.warning("Triage primary failed (%s); falling back.", exc)
            return self._fallback.triage(title, description)
