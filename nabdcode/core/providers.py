import logging
import json
from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import httpx

logger = logging.getLogger(__name__)
_shared_client = None

def _get_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None:
        import os
        proxy_url = os.getenv("CLI_PROXY_URL") # e.g. http://127.0.0.1:8080
        
        async def route_to_proxy(request: httpx.Request):
            if proxy_url:
                proxy = httpx.URL(proxy_url)
                request.url = request.url.copy_with(
                    scheme=proxy.scheme,
                    host=proxy.host,
                    port=proxy.port
                )

        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=60.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            event_hooks={'request': [route_to_proxy]} if proxy_url else None
        )
    return _shared_client

@dataclass
class ProviderConfig:
    api_key: str
    model_id: str
    base_url: str
    temperature: float
    thinking_enabled: bool

class BaseLlmProvider(ABC):
    @abstractmethod
    async def generate_stream(
        self, msgs: List[Dict[str, Any]], cfg: ProviderConfig, tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]: ...

class OpenAiCompatibleProvider(BaseLlmProvider):
    def _format_request(self, msgs: List[Dict[str, Any]], cfg: ProviderConfig, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        payload = {
            "model": cfg.model_id,
            "temperature": cfg.temperature,
            "messages": msgs,
            "stream": True
        }
        if "deepseek" in str(cfg.model_id).lower():
            payload["extra_body"] = {"chat_template_kwargs": {"thinking": False}}

        if tools:
            payload["tools"] = tools
        return payload

    def _build_headers(self, api_key: str) -> dict:
        api_key = str(api_key).strip() if api_key else ""
        if not api_key:
            import os
            api_key = os.getenv("NVIDIA_API_KEY", "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")
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def _resolve_base_url(self, c: ProviderConfig) -> str:
        return c.base_url

    async def generate_stream(
        self, msgs: List[Dict[str, Any]], cfg: ProviderConfig, tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        b = self._resolve_base_url(cfg).rstrip('/')
        url = b if b.endswith("/chat/completions") else f"{b}/chat/completions"
        payload = self._format_request(msgs, cfg, tools)
        
        if tools:
            logger.debug("Payload size=%s bytes", len(json.dumps(payload, ensure_ascii=False).encode("utf-8")))

        tool_calls_accumulator = {}
        max_retries = 3
        yielded_any = False

        for attempt in range(max_retries):
            try:
                logger.debug("Request URL=%s", url)
                async with _get_client().stream("POST", url, headers=self._build_headers(cfg.api_key), json=payload) as r:
                    if r.status_code >= 400:
                        err_text = await r.aread()
                        with open("last_http_error.log", "w") as f:
                            f.write(err_text.decode("utf-8", errors="ignore"))
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line.startswith("data: ") or "[DONE]" in line:
                            continue
                        try:
                            d = json.loads(line[6:]).get("choices", [{}])[0].get("delta", {})
                        except Exception:
                            continue

                        if d.get("reasoning_content"):
                            yielded_any = True
                            yield {"type": "thought", "chunk": d["reasoning_content"]}
                        if d.get("content"):
                            yielded_any = True
                            yield {"type": "content", "chunk": d["content"]}
                        if d.get("tool_calls"):
                            for tc in d["tool_calls"]:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_accumulator:
                                    tool_calls_accumulator[idx] = {"id": "", "function": {"name": "", "arguments": ""}}
                                if tc.get("id"):
                                    tool_calls_accumulator[idx]["id"] += tc["id"]
                                if tc.get("function", {}).get("name"):
                                    tool_calls_accumulator[idx]["function"]["name"] += tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    tool_calls_accumulator[idx]["function"]["arguments"] += tc["function"]["arguments"]
                break  # Success
            except httpx.ReadTimeout as e:
                if yielded_any:
                    logger.error("Timeout occurred after stream started. Cannot safely retry.")
                    from nabdcode.core.llm_client import NetworkError
                    raise NetworkError(504, "Stream interrupted due to timeout.") from e
                
                logger.warning(f"httpx.ReadTimeout (transient) on attempt {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    from nabdcode.core.llm_client import NetworkError
                    raise NetworkError(504, "Provider read timeout. Fallback chain exhaustion.") from e
            except Exception as e:
                logger.error(f"Provider connection error: {e}")
                if attempt == max_retries - 1:
                    raise

        for tc in tool_calls_accumulator.values():
            try:
                args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
            except Exception:
                args = {}
            yield {"type": "tool_call", "id": tc["id"], "name": tc["function"]["name"], "arguments": args}

class OpenRouterProvider(OpenAiCompatibleProvider):
    def _build_headers(self, api_key: str) -> dict:
        api_key = str(api_key).strip() if api_key else ""
        if not api_key:
            import os
            api_key = os.getenv("NVIDIA_API_KEY", "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")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    def _resolve_base_url(self, c: ProviderConfig) -> str:
        url = c.base_url if c.base_url else "https://integrate.api.nvidia.com/v1"
        if "openrouter.ai" in url:
            return "https://openrouter.ai/api/v1"
        return url

class GeminiProvider(BaseLlmProvider):
    def _format_request(self, msgs: List[Dict[str, Any]], cfg: ProviderConfig, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        payload = {"contents": [{"role": "model" if m.get("role") == "assistant" else "user", "parts": [{"text": m.get("content", "")}]} for m in msgs]}
        if tools:
            payload["tools"] = tools
        return payload

    async def generate_stream(
        self, msgs: List[Dict[str, Any]], cfg: ProviderConfig, tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        async with _get_client().stream("POST", f"{cfg.base_url.rstrip('/')}:streamGenerateContent", params={"key": cfg.api_key, "alt": "sse"}, json=self._format_request(msgs, cfg, tools)) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    parts = json.loads(line[6:]).get("candidates", [{}])[0].get("content", {}).get("parts", [{}])
                    if parts and parts[0].get("text"):
                        yield {"type": "content", "chunk": parts[0]["text"]}
                except Exception:
                    continue
