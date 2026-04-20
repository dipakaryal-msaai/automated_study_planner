"""
Optional AI service for advisory study guidance via local Ollama.
"""

import json
import os
from datetime import datetime
from typing import Optional
from urllib import error as urllib_error
from urllib import request as urllib_request


class AIInsightsService:
    """Generate advisory dashboard insights from a local Ollama model."""

    def __init__(self):
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        self.timeout_seconds = max(5, int(os.getenv('OLLAMA_REQUEST_TIMEOUT_SECONDS', '30')))
        self.json_retry_attempts = max(1, int(os.getenv('OLLAMA_JSON_RETRY_ATTEMPTS', '2')))
        self.temperature = float(os.getenv('OLLAMA_TEMPERATURE', '0.2'))

    @staticmethod
    def is_enabled() -> bool:
        """Return True when AI insights are enabled by configuration."""
        return os.getenv('AI_INSIGHTS_ENABLED', '0') == '1'

    def generate_insights(self, context: dict) -> dict:
        """Return structured dashboard insights from the configured Ollama model."""
        parsed = self._generate_json(self._build_prompt(context), max_output_tokens=320)
        return self._normalize_insights(parsed)

    def optimize_schedule(self, context: dict, retry_reason: Optional[str] = None) -> dict:
        """Return an optimized pending schedule that respects explicit workload bounds."""
        parsed = self._generate_json(
            self._build_schedule_prompt(context, retry_reason=retry_reason),
            max_output_tokens=640,
        )
        return self._normalize_optimized_schedule(parsed)

    def generate_chat_reply(self, context: dict, history: list, message: str) -> dict:
        """Return a planner-aware chat reply for the dashboard assistant."""
        parsed = self._generate_json(
            self._build_chat_prompt(context, history, message),
            max_output_tokens=420,
        )
        return self._normalize_chat_response(parsed)

    def _generate_json(self, prompt: str, max_output_tokens: int) -> dict:
        """Send a JSON-only generation request to Ollama and parse the response."""
        retry_prompt = prompt

        for attempt in range(self.json_retry_attempts):
            payload = {
                'model': self.model,
                'prompt': retry_prompt,
                'stream': False,
                'format': 'json',
                'options': {
                    'temperature': self.temperature,
                    'num_predict': max_output_tokens,
                },
            }

            request = urllib_request.Request(
                f'{self.base_url}/api/generate',
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )

            try:
                with urllib_request.urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = json.loads(response.read().decode('utf-8'))
            except urllib_error.URLError as exc:
                raise RuntimeError(
                    'Could not reach Ollama. Start Ollama locally and verify OLLAMA_BASE_URL.'
                ) from exc

            model_response = raw.get('response', '').strip()
            if not model_response:
                if attempt == self.json_retry_attempts - 1:
                    raise RuntimeError('Ollama returned an empty response.')
                retry_prompt = (
                    f'{prompt}\n'
                    'IMPORTANT: Your previous reply was empty. '
                    'Return exactly one valid JSON object matching the required schema.'
                )
                continue

            try:
                return json.loads(model_response)
            except json.JSONDecodeError as exc:
                if attempt == self.json_retry_attempts - 1:
                    raise RuntimeError('Ollama returned invalid JSON.') from exc
                retry_prompt = (
                    f'{prompt}\n'
                    'IMPORTANT: Your previous reply was not valid JSON. '
                    'Return exactly one valid JSON object with double-quoted keys and no extra text.'
                )

        raise RuntimeError('Ollama returned invalid JSON.')

    def _build_prompt(self, context: dict) -> str:
        """Build a concise JSON-only prompt for dashboard insights."""
        snapshot = json.dumps(context, separators=(',', ':'))
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
            "Keep the summary and risk note to at most 2 sentences each.\n"
            "Keep the advice specific, practical, and grounded in the snapshot. "
            "Avoid inventing data.\n\n"
            f"Planner snapshot:\n{snapshot}\n"
        )

    def _build_schedule_prompt(self, context: dict, retry_reason: Optional[str] = None) -> str:
        """Build a JSON-only prompt for schedule optimization."""
        snapshot = json.dumps(context, separators=(',', ':'))
        prompt = (
            "You are optimizing a study schedule for a study planning application.\n"
            "Return only valid JSON with no markdown fences.\n"
            "You may change pending session dates, durations, and the number of pending sessions.\n"
            "You must keep the total planned pending study time within the provided min and max minute bounds.\n"
            "Do not schedule sessions before today.\n"
            "Do not schedule a session after the latest due date for the matching subject and task type.\n"
            "Prefer spreading workload more evenly, prioritizing difficult and urgent work earlier, and avoiding heavy clustering.\n"
            "Return an object with this exact shape:\n"
            "{\n"
            '  "summary": "short paragraph",\n'
            '  "changes": ["change 1", "change 2"],\n'
            '  "study_sessions": [\n'
            "    {\n"
            '      "date": "YYYY-MM-DD",\n'
            '      "start_time": "HH:MM",\n'
            '      "subject": "course name",\n'
            '      "task_type": "Exam",\n'
            '      "duration": 90,\n'
            '      "difficulty": 4\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"Planner snapshot:\n{snapshot}\n"
        )

        if retry_reason:
            prompt += (
                "\nThe previous optimization failed validation for this reason:\n"
                f"{retry_reason}\n"
                "Fix that exact issue and return a revised schedule that satisfies every constraint.\n"
            )

        return prompt

    def _build_chat_prompt(self, context: dict, history: list, message: str) -> str:
        """Build a JSON-only prompt for the planner-aware chat assistant."""
        snapshot = json.dumps(context, separators=(',', ':'))
        conversation = json.dumps(history[-6:], separators=(',', ':'))
        return (
            "You are a study planning assistant inside a study planner dashboard.\n"
            "Answer the user's question using the current planner snapshot when relevant.\n"
            "You may also give general study advice, but do not invent planner facts that are not present.\n"
            "If the snapshot is sparse or missing details, say that briefly and still be helpful.\n"
            "Keep the reply concise, practical, and under 6 sentences.\n"
            "Return only valid JSON with no markdown fences.\n"
            "Return an object with this exact shape:\n"
            "{\n"
            '  "reply": "direct answer to the user",\n'
            '  "suggested_follow_up": "short optional follow-up question prompt or empty string"\n'
            "}\n\n"
            f"Planner snapshot:\n{snapshot}\n"
            f"Recent conversation:\n{conversation}\n"
            f"User message:\n{message}\n"
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

    @staticmethod
    def _normalize_optimized_schedule(parsed: dict) -> dict:
        """Normalize optimized schedule output from Ollama."""
        def normalize_list(value):
            if not isinstance(value, list):
                return []
            return [str(item).strip() for item in value if str(item).strip()][:6]

        summary = str(parsed.get('summary', '')).strip()
        raw_sessions = parsed.get('study_sessions')
        if not summary:
            raise RuntimeError('AI optimizer response did not include a summary.')
        if not isinstance(raw_sessions, list) or not raw_sessions:
            raise RuntimeError('AI optimizer response did not include study sessions.')

        normalized_sessions = []
        for item in raw_sessions:
            if not isinstance(item, dict):
                continue
            normalized_sessions.append({
                'date': str(item.get('date', '')).strip(),
                'start_time': str(item.get('start_time', '18:00')).strip() or '18:00',
                'subject': str(item.get('subject', '')).strip(),
                'task_type': str(item.get('task_type', '')).strip(),
                'duration': item.get('duration'),
                'difficulty': item.get('difficulty'),
            })

        if not normalized_sessions:
            raise RuntimeError('AI optimizer returned no usable study sessions.')

        return {
            'summary': summary,
            'changes': normalize_list(parsed.get('changes')),
            'study_sessions': normalized_sessions,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'model': os.getenv('OLLAMA_MODEL', 'llama3.2'),
        }

    @staticmethod
    def _normalize_chat_response(parsed: dict) -> dict:
        """Normalize planner-aware chat output from Ollama."""
        reply = str(parsed.get('reply', '')).strip()
        follow_up = str(parsed.get('suggested_follow_up', '')).strip()

        if not reply:
            raise RuntimeError('AI chat response did not include a reply.')

        return {
            'reply': reply,
            'suggested_follow_up': follow_up,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'model': os.getenv('OLLAMA_MODEL', 'llama3.2'),
        }
