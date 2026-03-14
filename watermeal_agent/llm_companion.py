from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import error, request


LOGGER = logging.getLogger(__name__)
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


class LLMCompanion:
    def __init__(self, model: str | None = None) -> None:
        self.model = (os.getenv("WATERMEAL_LLM_MODEL") or model or DEFAULT_MODEL).strip()
        self.base_url = (
            os.getenv("WATERMEAL_OPENAI_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.api_key = (
            os.getenv("WATERMEAL_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        ).strip()
        self.last_error = ""

    def is_available(self) -> bool:
        return bool(self.api_key and self.model)

    def reconfigure(self, model: str) -> None:
        self.model = (os.getenv("WATERMEAL_LLM_MODEL") or model or DEFAULT_MODEL).strip()
        self.api_key = (
            os.getenv("WATERMEAL_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        ).strip()
        self.base_url = (
            os.getenv("WATERMEAL_OPENAI_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.last_error = ""

    def reply(self, history: list[dict[str, str]]) -> str | None:
        if not self.is_available():
            self.last_error = "缺少 API Key 或 model（检查 OPENAI_API_KEY / WATERMEAL_OPENAI_API_KEY）"
            return None

        payload = {
            "model": self.model,
            "messages": [self._system_prompt(), *history[-12:]],
            "temperature": 0.8,
            "max_tokens": 140,
        }
        data = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        req = request.Request(
            url=url,
            method="POST",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=18) as resp:
                body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            text = self._extract_text(parsed)
            if not text:
                self.last_error = "模型返回为空"
                return None
            self.last_error = ""
            return text
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            LOGGER.warning("LLM HTTPError: %s %s", exc.code, detail[:300])
            self.last_error = self._extract_error_message(exc.code, detail)
            return None
        except Exception:
            LOGGER.exception("LLM request failed")
            self.last_error = "请求失败（网络或服务异常）"
            return None

    def _extract_text(self, parsed: dict[str, Any]) -> str | None:
        choices = parsed.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
            return text or None
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = str(item.get("text", "")).strip()
                    if text:
                        chunks.append(text)
            if chunks:
                return "\n".join(chunks)
        return None

    def _extract_error_message(self, code: int, detail: str) -> str:
        try:
            payload = json.loads(detail)
            message = ((payload.get("error") or {}).get("message") or "").strip()
            if message:
                return f"HTTP {code}: {message}"
        except Exception:
            pass
        compact = detail.strip().replace("\n", " ")
        if compact:
            return f"HTTP {code}: {compact[:200]}"
        return f"HTTP {code}: 请求被拒绝"

    @staticmethod
    def _system_prompt() -> dict[str, str]:
        return {
            "role": "system",
            "content": (
                "你是一只温柔的桌宠猫猫，只做情绪陪伴聊天，不做设置指令。"
                "请用简体中文回复，每次1到2句，口吻自然、贴近对方输入。"
                "避免空话、避免重复模板。"
            ),
        }
