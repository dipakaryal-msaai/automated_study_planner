"""
Optional AI insights service for advisory study guidance via local Ollama.
"""

import json
import os
from datetime import datetime
from urllib import error as urllib_error
from urllib import request as urllib_request


class AIInsightsService:
    """Generate advisory dashboard insights from a local Ollama model."""

    def __init__(self):
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3.2')

    @staticmethod
    def is_enabled() -> bool:
        """Return True when AI insights are enabled by configuration."""
        return os.getenv('AI_INSIGHTS_ENABLED', '0') == '1'

    def generate_insights(self, context: dict) -> dict:
        """Return structured dashboard insights from the configured Ollama model."""
        prompt = self._build_prompt(context)
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'format': 'json',
        }

        request = urllib_request.Request(
            f'{self.base_url}/api/generate',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )

        try:
            with urllib_request.urlopen(request, timeout=45) as response:
                raw = json.loads(response.read().decode('utf-8'))
        except urllib_error.URLError as exc:
            raise RuntimeError(
                'Could not reach Ollama. Start Ollama locally and verify OLLAMA_BASE_URL.'
            ) from exc

        model_response = raw.get('response', '').strip()
        if not model_response:
            raise RuntimeError('Ollama returned an empty response.')

        try:
            parsed = json.loads(model_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError('Ollama returned invalid JSON for AI insights.') from exc

        return self._normalize_insights(parsed)

    def _build_prompt(self, context: dict) -> str:
        """Build a concise JSON-only prompt for dashboard insights."""
        snapshot = json.dumps(context, indent=2)
        return (
            "You are an academic study coach for a study planning application.\n"
            "Analyze the provided planner snapshot and return only valid JSON.\n"
            "Do not include markdown fences or commentary.\n"
            "Return an object with this exact shape:\n"
            "{\n"
            '  "summary": "short paragraph",\n'
            '  "deadline_risk": "short paragraph about urgency and risks",\n'
            '  "weekly_priorities": ["priority 1", "priority 2", "priority 3"],\n'
            '  "study_tips": ["tip 1", "tip 2", "tip 3"]\n'
            "}\n"
            "Keep the advice specific, practical, and grounded in the snapshot. "
            "Avoid inventing data.\n\n"
            f"Planner snapshot:\n{snapshot}\n"
        )

    @staticmethod
    def _normalize_insights(parsed: dict) -> dict:
        """Normalize AI output to the structure expected by the dashboard."""
        def normalize_list(value):
            if not isinstance(value, list):
                return []
            return [str(item).strip() for item in value if str(item).strip()][:5]

        summary = str(parsed.get('summary', '')).strip()
        deadline_risk = str(parsed.get('deadline_risk', '')).strip()
        weekly_priorities = normalize_list(parsed.get('weekly_priorities'))
        study_tips = normalize_list(parsed.get('study_tips'))

        if not summary:
            raise RuntimeError('AI insights response did not include a summary.')

        return {
            'summary': summary,
            'deadline_risk': deadline_risk,
            'weekly_priorities': weekly_priorities,
            'study_tips': study_tips,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'model': os.getenv('OLLAMA_MODEL', 'llama3.2'),
        }
