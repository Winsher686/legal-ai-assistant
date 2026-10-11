"""LLM 客户端封装（OpenAI 兼容协议，支持 DeepSeek / Qwen / OpenAI / Mock）。

含指数退避重试 + 熔断降级：外部服务抖动时自动重试，连续失败触发熔断快速失败。
"""
from typing import List, Optional

from app.core.config import settings
from app.core.logger import logger
from app.utils.retry import get_llm_breaker, retry_call

_client = None


class LLMClient:
    """统一大模型接口。所有模型走 OpenAI 兼容协议，切换供应商只需改配置。"""

    def __init__(self):
        self._client = None

    def _load(self):
        if self._client is not None:
            return self._client
        if settings.USE_MOCK or settings.LLM_PROVIDER == "mock":
            self._client = "mock"
            return self._client
        from openai import OpenAI

        kwargs = {"api_key": settings.LLM_API_KEY}
        if settings.LLM_BASE_URL:
            kwargs["base_url"] = settings.LLM_BASE_URL
        self._client = OpenAI(**kwargs)
        return self._client

    def chat(self, messages: List[dict], temperature: Optional[float] = None,
             json_mode: bool = False) -> str:
        client = self._load()
        if client == "mock":
            return self._mock_chat(messages, json_mode)

        kwargs = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            breaker = get_llm_breaker()

            def _call():
                resp = client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""

            return breaker(lambda: retry_call(_call))
        except get_llm_breaker().CircuitOpenError:
            logger.error("LLM circuit open, fast-fail")
            raise
        except Exception as e:
            logger.error("LLM call failed after retries: %s", e)
            raise

    def _mock_chat(self, messages: List[dict], json_mode: bool) -> str:
        """Mock 回答：回显用户问题，用于本地验证链路。"""
        import json

        user_msg = ""
        for m in messages:
            if m.get("role") == "user":
                user_msg = m.get("content", "")
        if json_mode:
            return json.dumps(
                {"answer": f"[mock] 根据知识库，针对问题「{user_msg[:50]}」的回答。",
                 "reasoning": "mock 推理"},
                ensure_ascii=False,
            )
        return f"[mock] 这是针对「{user_msg[:50]}」的模拟回答，请在生产环境配置真实 LLM。"


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
