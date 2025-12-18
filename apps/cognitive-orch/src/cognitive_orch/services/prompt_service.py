"""System prompting & personas service.

Phase 6 goal:
- Build a system prompt that includes:
  - Base LexiqAI persona
  - Firm-specific persona override (if configured)
  - Tool usage policy (if tools are enabled)

Firm persona sources (in priority order):
1) Redis cache (if available)
2) Env-configured JSON mapping (PROMPT_FIRM_PERSONAS_JSON)
3) (Future) Core API firm settings endpoint (not implemented yet)
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import redis.asyncio as redis
import httpx
from pydantic import BaseModel

from cognitive_orch.config import get_settings
from cognitive_orch.utils.logging import get_logger

logger = get_logger("prompt_service")
settings = get_settings()


BASE_PERSONA_PROMPT = """You are LexiqAI, a legal assistant for law firms.

Be concise, accurate, and professional. If a user asks for legal advice, provide general information and recommend
consulting a licensed attorney. Do not claim to be a lawyer.
"""


TOOL_POLICY_PROMPT = """Tool Use Policy:

- Only call tools that are provided to you.
- Use tools for structured actions (availability lookup, booking, lead creation, notifications).
- For side-effect tools (book_appointment, create_lead, send_notification):
  - You MUST ask for explicit user confirmation first.
  - NEVER set confirmed=true unless the user explicitly confirms (e.g., "Yes", "Please do it", "Book it").
- If required fields are missing, ask clarifying questions instead of guessing.
- After tools run, summarize results clearly for the user.
"""


class PromptService:
    """Service that builds a firm-aware system prompt."""

    def __init__(self, redis_pool: Optional[redis.ConnectionPool] = None) -> None:
        self._redis_pool = redis_pool

    def _get_redis(self) -> Optional[redis.Redis]:
        if not self._redis_pool:
            return None
        return redis.Redis(connection_pool=self._redis_pool)

    def _cache_key(self, firm_id: str) -> str:
        return f"firm:{firm_id}:system_prompt"

    def _load_firm_personas_from_env(self) -> Dict[str, str]:
        raw = settings.prompt.firm_personas_json
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning(f"Failed to parse PROMPT_FIRM_PERSONAS_JSON: {e}")
            return {}

        if isinstance(data, dict):
            # firm_id -> prompt string
            return {str(k): str(v) for k, v in data.items() if isinstance(v, (str, int, float))}
        return {}

    async def get_firm_prompt(self, firm_id: str) -> Optional[str]:
        """Return firm-specific persona prompt, if configured."""
        if not firm_id:
            return None

        # 1) Redis cache
        r = self._get_redis()
        if r:
            try:
                cached = await r.get(self._cache_key(firm_id))
                if cached:
                    return cached
            except Exception as e:
                logger.debug(f"Redis firm prompt cache miss/error: {e}")

        # 2) Core API firm persona endpoint (preferred source of truth)
        prompt = await self._fetch_from_core_api(firm_id)

        # 3) Env mapping fallback (useful for local/dev)
        if not prompt:
            env_map = self._load_firm_personas_from_env()
            prompt = env_map.get(firm_id)

        if prompt and r:
            try:
                await r.setex(self._cache_key(firm_id), int(settings.prompt.cache_ttl_seconds), prompt)
            except Exception as e:
                logger.debug(f"Failed to cache firm prompt: {e}")

        return prompt

    async def _fetch_from_core_api(self, firm_id: str) -> Optional[str]:
        """Fetch firm persona from Core API (internal endpoint)."""
        base = settings.integration.core_api_url.rstrip("/")
        url = f"{base}/api/v1/firms/{firm_id}/persona"

        headers: Dict[str, str] = {}
        if settings.integration.core_api_api_key:
            headers["X-Internal-API-Key"] = settings.integration.core_api_api_key

        try:
            async with httpx.AsyncClient(timeout=settings.integration.core_api_timeout) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                prompt = data.get("system_prompt")
                return str(prompt) if prompt else None
            return None
        except Exception as e:
            logger.debug(f"Core API firm persona fetch failed: {e}")
            return None

    async def build_system_prompt(
        self,
        firm_id: Optional[str],
        tools_enabled: bool = True,
    ) -> str:
        """Build the system prompt with optional firm persona and tool policy."""
        parts: list[str] = [settings.prompt.base_persona_prompt.strip() or BASE_PERSONA_PROMPT.strip()]

        if firm_id:
            firm_prompt = await self.get_firm_prompt(firm_id)
            if firm_prompt:
                parts.append("Firm Persona:\n" + firm_prompt.strip())

        if tools_enabled:
            parts.append(settings.prompt.tool_policy_prompt.strip() or TOOL_POLICY_PROMPT.strip())

        return "\n\n".join([p for p in parts if p])


_prompt_service: Optional[PromptService] = None


def get_prompt_service(redis_pool: Optional[redis.ConnectionPool] = None) -> PromptService:
    """Get global PromptService instance (optionally with Redis pool on first init)."""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService(redis_pool=redis_pool)
    return _prompt_service


