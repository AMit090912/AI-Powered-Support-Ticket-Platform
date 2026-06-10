import json

from app.ai.base import TriageProvider, TriageResult
from app.models.enums import Category, Priority

_PROMPT = """You are a support-ticket triage assistant. Classify the ticket and draft a short, professional response.

Return ONLY a JSON object with exactly these keys:
- "category": one of ["billing","technical","account_access","feature_request","general"]
- "priority": one of ["low","medium","high","critical"]
- "suggested_response": a 1-3 sentence draft reply to the customer

Ticket title: {title}
Ticket description: {description}
"""


class GeminiProvider(TriageProvider):
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def triage(self, title: str, description: str) -> TriageResult:
        prompt = _PROMPT.format(title=title, description=description)
        resp = self._client.models.generate_content(model=self._model, contents=prompt)
        return self._parse(resp.text)

    def _parse(self, text: str) -> TriageResult:
        cleaned = self._strip_fences(text)
        try:
            data = json.loads(cleaned)
            return TriageResult(
                category=Category(data["category"]),
                priority=Priority(data["priority"]),
                suggested_response=str(data["suggested_response"]),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise ValueError(f"Gemini returned unparseable triage output: {exc}") from exc

    @staticmethod
    def _strip_fences(text: str) -> str:
        t = text.strip()
        if t.startswith("```"):
            t = t.split("\n", 1)[1] if "\n" in t else t
            t = t.replace("```json", "").replace("```", "").strip()
        return t
