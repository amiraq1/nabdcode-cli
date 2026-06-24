from __future__ import annotations
import os
import re
import json
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
import logging
from bs4 import BeautifulSoup
from typing import Any, Callable, Iterable
from datetime import datetime
import math
import struct
from html import escape

logger = logging.getLogger(__name__)

import httpx
import contextlib

_shared_client = None

def get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(timeout=45.0)
    return _shared_client

class GenerationError(Exception, ABC):
    @property
    def retryable(self) -> bool: return False
    @property
    def fatal(self) -> bool: return False
    @abstractmethod
    def user_message(self) -> str: ...
    def to_dict(self) -> dict[str, Any]: return {"type": self.__class__.__name__, "message": self.user_message(), "retryable": self.retryable, "fatal": self.fatal}

@dataclass(slots=True)
class NetworkError(GenerationError):
    status_code: int; message: str
    @property
    def retryable(self) -> bool: return self.status_code in {429, 500, 502, 503, 504}
    @property
    def fatal(self) -> bool: return self.status_code in {401, 403, 404}
    def user_message(self) -> str: return {401: "Authentication failed. Verify API key.", 403: "Access denied by provider.", 404: "Requested model or endpoint not found.", 429: "Rate limit exceeded. Retrying may succeed."}.get(self.status_code, f"Provider server error ({self.status_code})." if self.status_code >= 500 else f"Network error ({self.status_code}): {self.message}")

@dataclass(slots=True)
class ApiError(GenerationError):
    code: str | None; type_: str | None; message: str
    def user_message(self) -> str: return " ".join(filter(None, [self.code, f"[{self.type_}]" if self.type_ else None, self.message]))

@dataclass(slots=True)
class ToolExecutionError(GenerationError):
    tool_name: str; arguments: str; error: str
    def user_message(self) -> str: return f"Tool '{self.tool_name}' execution failed: {self.error}"

@dataclass(slots=True)
class ProviderChainExhausted(GenerationError):
    errors: list[str]
    @property
    def fatal(self) -> bool: return True
    def user_message(self) -> str: return f"All configured providers failed. Attempts: {len(self.errors)}"

@dataclass(slots=True)
class UnknownError(GenerationError):
    exception: Exception
    def user_message(self) -> str: return str(self.exception).strip() or "Unexpected internal error."

def trim_by_tokens_preserving_pairs(messages, token_counter, max_tokens):
    kept, required_ids, current_tokens = [], set(), 0
    for msg in reversed(messages):
        msg_tokens, role = token_counter(msg), msg.get("role")
        tool_calls, tool_call_id = msg.get("tool_calls", []), msg.get("tool_call_id")
        force_keep = (role == "tool") or any(c.get("id") in required_ids for c in tool_calls)
        if role == "tool" and tool_call_id: required_ids.add(tool_call_id)
        if current_tokens + msg_tokens > max_tokens and not force_keep: continue
        kept.append(msg); current_tokens += msg_tokens
        if tool_calls: required_ids.update(c.get("id") for c in tool_calls)
    return kept[::-1]

class NabdLLMClient:
    def __init__(self, config: Any = None, taste_manager: Any = None, **kwargs: Any):
        self.taste_manager = taste_manager
        
        provider = "openmodel"
        model_name = "deepseek-v4-flash"
        api_key = ""
        self.failover_config = {}
        self.providers_config = {}
        
        try:
            import toml
            if os.path.exists("config.toml"):
                with open("config.toml", "r", encoding="utf-8") as f:
                    data = toml.load(f)
                    provider = data.get("provider", provider)
                    model_name = data.get("model", model_name)
                    api_key = data.get("api_key", "").strip() or os.environ.get("NABDCODE_API_KEY", "")
                    self.failover_config = data.get("failover", {})
                    self.providers_config = data.get("providers", {})
        except Exception as e:
            logger.warning(f"تنبيه: فشل قراءة TOML: {e}")

        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = self._resolve_provider_url(self.provider)
        
        logger.info(f"LLM Client Fixed Sync -> Provider: {self.provider}, Model: {self.model_name}")

    def _mask_key(self, key: str) -> str:
        if not key or len(key) < 8: return "***"
        if key.startswith("AIzaSy"): return f"AIzaSy...{key[-4:]}"
        if key.startswith("sk-"): return f"{key[:8]}...{key[-4:]}"
        return f"{key[:4]}...{key[-4:]}"

    def _resolve_provider_url(self, provider: str) -> str:
        p_lower = str(provider).lower()
        # 🚨 الحل الجذري: إضافة السلاش الأخيرة الصارمة /v1/ لتجبر المكتبة على تثبيت مسار التوجيه
        if "openrouter" in p_lower:
            return "https://openrouter.ai/api/v1/"
        elif "openmodel" in p_lower:
            return "https://api.openmodel.ai/v1/"
        elif "nvidia" in p_lower:
            return "https://integrate.api.nvidia.com/v1/"
        elif "ollama" in p_lower:
            return "http://localhost:11434/v1/"
        return "https://api.openmodel.ai/v1/"

    async def _resolve_openmodel_endpoint(self, model_name: str) -> str:
        """
        Dynamically determine the correct endpoint on openmodel.ai based on supported protocols.
        Falls back to safe routing defaults if the models endpoint is unreachable.
        """
        import httpx
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            async with contextlib.nullcontext(get_shared_client()) as client:
                r = await client.get("https://api.openmodel.ai/v1/models", headers=headers, timeout=4.0)
                if r.status_code == 200:
                    data = r.json()
                    for m in data.get("data", []):
                        if m.get("id") == model_name:
                            protocols = m.get("supported_protocols", [])
                            if "messages" in protocols:
                                return "https://api.openmodel.ai/v1/messages"
                            elif "responses" in protocols:
                                return "https://api.openmodel.ai/v1/responses"
        except Exception as e:
            logger.warning(f"Failed to dynamically resolve openmodel endpoint: {e}")
        
        # Static fallback rule based on model prefix
        m_lower = model_name.lower()
        if "deepseek" in m_lower or "claude" in m_lower or "llama" in m_lower or "qwen" in m_lower:
            return "https://api.openmodel.ai/v1/messages"
        elif "gpt" in m_lower:
            return "https://api.openmodel.ai/v1/responses"
        return "https://api.openmodel.ai/v1/messages"

    @property
    def config(self) -> dict[str, Any]:
        return {"provider": self.provider, "model": self.model_name, "api_key": self.api_key}

    @config.setter
    def config(self, new_config: dict[str, Any]) -> None:
        pass

    @property
    def model(self) -> str:
        return self.model_name

    def update_config(self, new_config: dict[str, Any]) -> None:
        pass

    async def generate_response(self, messages: list[dict[str, str]]) -> str:
        import asyncio
        import httpx

        priority = getattr(self, "failover_config", {}).get("priority", [])
        if not priority:
            priority = ["default"]

        error_logs = []
        max_retries = 3
        base_delay = 2.0

        async with contextlib.nullcontext(get_shared_client()) as client:
            for idx, provider_id in enumerate(priority):
                if provider_id == "default":
                    current_api_key = self.api_key
                    current_model = self.model_name
                    current_base_url = self.base_url
                    p_lower = str(self.provider).lower()
                    max_tokens = 64000
                else:
                    prov_data = getattr(self, "failover_config", {}).get(provider_id)
                    if not prov_data:
                        prov_data = getattr(self, "providers_config", {}).get(provider_id, {})
                    current_api_key = prov_data.get("api_key", "")
                    if not current_api_key:
                        env_key = prov_data.get("api_key_env") or f"{provider_id.upper()}_API_KEY"
                        current_api_key = os.environ.get(env_key, "")
                    if not current_api_key:
                        error_logs.append(f"{provider_id}: Missing API key in config and env")
                        if idx + 1 < len(priority):
                            print(f"⚠️ [PROV_FAIL] Switching → {priority[idx+1]}")
                        continue
                    current_model = prov_data.get("model", "")
                    current_base_url = prov_data.get("base_url", "")
                    p_lower = provider_id.lower()
                    max_tokens = prov_data.get("max_tokens", 64000)

                def est_tokens(msg): return len(msg.get("content", "")) // 4
                sys_msg = messages[0] if messages and messages[0].get("role") == "system" else None
                work_msgs = messages[1:] if sys_msg else messages[:]
                
                avail_tokens = max_tokens - (est_tokens(sys_msg) if sys_msg else 0)
                trimmed_msgs = trim_by_tokens_preserving_pairs(work_msgs, est_tokens, avail_tokens)
                
                sliced_messages = ([sys_msg] if sys_msg else []) + trimmed_msgs

                params = None
                is_google = "gemini" in current_model.lower() or "google" in p_lower
                if is_google:
                    headers = {"Content-Type": "application/json"}
                    headers.pop("Authorization", None)
                    params = {"key": current_api_key}
                else:
                    headers = {"Authorization": f"Bearer {current_api_key}", "Content-Type": "application/json"}
                
                if "openmodel" in p_lower and provider_id == "default":
                    endpoint_url = str(httpx.URL(await self._resolve_openmodel_endpoint(current_model)))
                else:
                    base_url = current_base_url if current_base_url.endswith('/') else f"{current_base_url}/"
                    if is_google:
                        endpoint_url = str(httpx.URL(base_url).join(f"v1beta/models/{current_model}:generateContent"))
                    else:
                        endpoint_url = str(httpx.URL(base_url).join("chat/completions"))

                payload = {
                    "model": current_model,
                    "messages": sliced_messages
                }
                
                logger.info(f"Direct Route -> Sending Raw Request to: {endpoint_url} (Model: {current_model}, Key: {self._mask_key(current_api_key)})")
                
                provider_exhausted = False
                for attempt in range(max_retries):
                    try:
                        response = await client.post(endpoint_url, json=payload, headers=headers, params=params)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if "choices" in result and len(result["choices"]) > 0:
                                choice = result["choices"][0]
                                if "message" in choice and "content" in choice["message"]:
                                    return choice["message"]["content"]
                                elif "text" in choice:
                                    return choice["text"]
                            
                            if "content" in result:
                                content_val = result["content"]
                                if isinstance(content_val, list):
                                    text_parts = []
                                    for block in content_val:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text_parts.append(block.get("text", ""))
                                    return "".join(text_parts)
                                elif isinstance(content_val, str):
                                    return content_val
                                    
                            if "output" in result:
                                output_val = result["output"]
                                if isinstance(output_val, list):
                                    text_parts = []
                                    for block in output_val:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text_parts.append(block.get("text", ""))
                                    return "".join(text_parts)
                            
                            return f"⚠️ استجابة غير معروفة البنية من الخادم: {result}"
                        
                        elif response.status_code in [302, 401, 403, 404]:
                            logger.error(f"FATAL {response.status_code} for {provider_id} (Key: {self._mask_key(current_api_key)}). Skipping retries...")
                            error_logs.append(f"{provider_id} [FATAL]: {response.status_code} - {response.text}")
                            provider_exhausted = True
                            break
                        
                        elif response.status_code == 429 or response.status_code >= 500:
                            logger.warning(f"TRANSIENT {response.status_code} on {provider_id}. Retrying...")
                            if attempt < max_retries - 1:
                                import random
                                jitter = random.uniform(0, 0.5)
                                await asyncio.sleep(base_delay * (2 ** attempt) + jitter)
                                continue
                            error_logs.append(f"{provider_id}: {response.status_code} - {response.text}")
                            provider_exhausted = True
                            break
                        else:
                            logger.error(f"Server returned status {response.status_code}: {response.text}")
                            error_logs.append(f"{provider_id}: {response.status_code} - {response.text}")
                            provider_exhausted = True
                            break
                            
                    except (httpx.RequestError, httpx.TimeoutException) as e:
                        logger.warning(f"TRANSIENT Network error on attempt {attempt + 1}/{max_retries}: {e}")
                        if attempt < max_retries - 1:
                            import random
                            jitter = random.uniform(0, 0.5)
                            await asyncio.sleep(base_delay * (2 ** attempt) + jitter)
                            continue
                        error_logs.append(f"{provider_id}: Network error {str(e)}")
                        provider_exhausted = True
                        break
                    except Exception as e:
                        logger.critical(f"LLM Connection Exception: {e}")
                        error_logs.append(f"{provider_id}: Exception {str(e)}")
                        provider_exhausted = True
                        break

                if provider_exhausted and idx + 1 < len(priority):
                    print(f"⚠️ [PROV_FAIL] Switching → {priority[idx+1]}")
                    continue

        raise ProviderChainExhausted(error_logs)

LLMClient = NabdLLMClient

THINK_OPEN, THINK_CLOSE, MAX_BUFFER_SIZE = "<think>", "</think>", 1024 * 1024

class StreamingThinkTagParser:
    def __init__(self, allow_multiple_think_blocks: bool = True):
        self.state, self.buffer = 0, ""
        self.allow_multiple_think_blocks = allow_multiple_think_blocks
        self.think_blocks_seen = 0

    async def feed(self, chunk: str, thinking_enabled: bool, on_text: Callable[[str], None], on_thought: Callable[[str], None]) -> None:
        if not chunk: return
        self.buffer = (self.buffer + chunk)[-MAX_BUFFER_SIZE:]
        while self.buffer:
            idx, tag = self.buffer.find(THINK_OPEN if self.state == 0 else THINK_CLOSE), THINK_OPEN if self.state == 0 else THINK_CLOSE
            out = on_text if self.state == 0 or not thinking_enabled else on_thought
            if idx >= 0:
                if idx: out(self.buffer[:idx])
                self.buffer = self.buffer[idx+len(tag):]
                if self.state == 0 and not (self.allow_multiple_think_blocks or self.think_blocks_seen == 0): on_text(tag)
                else: self.state, self.think_blocks_seen = 1 - self.state, self.think_blocks_seen + (1 if self.state == 0 else 0)
                continue
            part = next((s for s in range(min(len(self.buffer), len(tag)-1), 0, -1) if tag.startswith(self.buffer[-s:])), 0)
            if part:
                if part < len(self.buffer): out(self.buffer[:-part])
                self.buffer = self.buffer[-part:]
                break
            out(self.buffer); self.buffer = ""; break

    def flush(self, thinking_enabled: bool, on_text: Callable[[str], None], on_thought: Callable[[str], None]) -> None:
        if self.buffer: (on_thought if self.state == 1 and thinking_enabled else on_text)(self.buffer)
        self.buffer = ""

class NabdDDGScraper:
    CAPTCHA_REGEX = re.compile(r"(anomaly-modal|challenge-form|captcha|Unfortunately.*bots)", re.I | re.S)
    def __init__(self, timeout: float = 15.0):
        self.timeout, self.headers = timeout, {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}
    def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        try:
            with httpx.Client(headers=self.headers, timeout=self.timeout, follow_redirects=True) as c: r = c.get(f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote_plus(query)}")
            r.raise_for_status()
            if self.CAPTCHA_REGEX.search(r.text or ""): raise RuntimeError("DuckDuckGo CAPTCHA detected")
            res, soup = [], BeautifulSoup(r.text, "html.parser")
            for link in soup.select("a.result-link")[:max_results]:
                t, h = re.sub(r"\s+", " ", link.get_text() or "").strip(), (link.get("href") or "").strip()
                if not t or not h: continue
                u = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(h).query).get("uddg", [h])[0]) if "uddg=" in h else (f"https:{h}" if h.startswith("//") else h)
                ptr = link.find_parent("tr"); nxt = ptr.find_next_sibling("tr") if ptr else None
                sc = nxt.find("td", class_="result-snippet") if nxt else None
                s = re.sub(r"\s+", " ", sc.get_text(" ", strip=True) if sc else "").strip()
                res.append({"title": t, "url": u, "snippet": s})
            return res
        except Exception: return []

class PredefinedVariables:
    CURRENT_DATE, CURRENT_TIME, ACTIVE_MEMORY = "{CURRENT_DATE}", "{CURRENT_TIME}", "{ACTIVE_MEMORY}"

class NabdSystemPrompt:
    MAX_MEMORY_CHARS = 12000
    @staticmethod
    def get_template() -> str: return "You are NabdCode CLI, an advanced autonomous coding agent running inside Termux on Android.\n\n<current_date>{CURRENT_DATE}</current_date>\n<current_time>{CURRENT_TIME}</current_time>\n\n<active_memory_context>\n{ACTIVE_MEMORY}\n</active_memory_context>\n\nShell and device files:\nYou have secure access to the configured shell server or Local Sandbox via Termux CLI tools."
    @classmethod
    def compile_system_prompt(cls, active_memory: str) -> str:
        now, prompt = datetime.now(), cls.get_template()
        for k, v in {PredefinedVariables.CURRENT_DATE: now.strftime("%Y-%m-%d"), PredefinedVariables.CURRENT_TIME: now.strftime("%H:%M:%S"), PredefinedVariables.ACTIVE_MEMORY: active_memory.strip()[:cls.MAX_MEMORY_CHARS]}.items(): prompt = prompt.replace(k, v)
        return prompt
    @staticmethod
    def wrap_user_message(user_text: str) -> str:
        return f'<nabd_user_message\n    sent_date="{datetime.now():%Y-%m-%d}"\n    sent_time="{datetime.now():%H:%M:%S}">\n{escape(user_text, quote=False)}\n</nabd_user_message>'

class NabdEmbeddingIndexer:
    FLOAT_SIZE = 4
    @staticmethod
    def floats_to_bytes(floats: Iterable[float]) -> bytes:
        v = tuple(floats)
        return struct.pack(f"<{len(v)}f", *v) if v else b""
    @staticmethod
    def bytes_to_floats(b: bytes) -> list[float]:
        if not b: return []
        if len(b) % 4: raise ValueError("Corrupted embedding stream.")
        return list(struct.unpack(f"<{len(b)//4}f", b))
    @staticmethod
    def vector_norm(v: list[float]) -> float: return math.sqrt(sum(x*x for x in v))
    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a: return 0.0
        na, nb = NabdEmbeddingIndexer.vector_norm(a), NabdEmbeddingIndexer.vector_norm(b)
        return sum(x*y for x, y in zip(a, b)) / (na * nb) if na > 1e-12 and nb > 1e-12 else 0.0

class ModelId:
    def __init__(self, provider_name: str, model_name: str): self.provider_name, self.model_name = provider_name.strip(), model_name.strip()
    @property
    def prefixed(self) -> str: return f"{self.provider_name}:{self.model_name}"
    @property
    def api_model_name(self) -> str: return self.model_name[7:] if self.model_name.startswith("models/") else self.model_name
    def __repr__(self) -> str: return f"ModelId({self.prefixed!r})"
    def __eq__(self, o: object) -> bool: return self.prefixed == o.prefixed if isinstance(o, ModelId) else NotImplemented
    @staticmethod
    def parse(r: str) -> 'ModelId':
        if not r or not (r := r.strip()): raise ValueError("ModelId.parse: raw_id cannot be empty")
        if ":" in r: return ModelId(*r.partition(":")[::2])
        ml = r.lower()
        if re.match(r"^(gpt-|o[1-9]\d*-)", ml): return ModelId("OpenAI", r)
        p = "Anthropic" if ml.startswith("claude-") else "DeepSeek" if "deepseek" in ml else "Qwen" if "qwen" in ml else "Google" if "gemini" in ml or ml.startswith("models/") else "Unknown"
        return ModelId(p, r)

@dataclass
class ShellDeviceConfig: name: str; server_url: str

@dataclass
class GenerationContext:
    access_saved_memories: bool = True; access_active_memory: bool = True
    web_search_enabled: bool = True; access_past_conversations: bool = True; shell_enabled: bool = True
    shell_devices: list[ShellDeviceConfig] = field(default_factory=list)

_SAVED_MEMORY_TOOLS = [{"type": "function", "function": {"name": "list_memory_files", "description": "List all saved memory files", "parameters": {"type": "object", "properties": {}, "required": []}}}, {"type": "function", "function": {"name": "read_memory_file", "description": "Read content of a specific memory file", "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}}]
_ACTIVE_MEMORY_TOOL = {"type": "function", "function": {"name": "update_active_memory", "description": "Update active memory context", "parameters": {"type": "object", "properties": {"content": {"type": "string"}, "mode": {"type": "string", "enum": ["append", "replace"]}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["content", "mode"]}}}
_ALL_TOOL_NAMES = {"list_memory_files", "read_memory_file", "create_memory_file", "edit_memory_file", "delete_memory_file", "update_active_memory"}

class MemoryToolProvider:
    def __init__(self, memory_manager): self.memory_manager = memory_manager
    def definitions(self, ctx: GenerationContext) -> list[dict]: return (_SAVED_MEMORY_TOOLS if ctx.access_saved_memories else []) + ([_ACTIVE_MEMORY_TOOL] if ctx.access_active_memory else [])
    def handles(self, tool_name: str) -> bool: return tool_name in _ALL_TOOL_NAMES
    async def execute(self, t: str, args: dict[str, Any], ctx: GenerationContext) -> str:
        if not self.handles(t): return f"Unknown tool: '{t}'"
        if (t == "update_active_memory" and not ctx.access_active_memory) or (t != "update_active_memory" and not ctx.access_saved_memories): return f"Error: {'Active' if t == 'update_active_memory' else 'Saved'} Memory access is disabled."
        try:
            if t == "list_memory_files": return f"Files: {await self.memory_manager.list_files()}"
            if t == "read_memory_file": return await self.memory_manager.read_file(args["name"]) if args.get("name", "").strip() else "Error: 'name' is required."
            if t == "update_active_memory": return await self.memory_manager.update_active_memory(args["content"], args.get("mode", "append"), args.get("old_string"), args.get("new_string")) if args.get("content", "").strip() else "Error: 'content' is required."
        except Exception as e: return f"Tool execution failed [{t}]: {type(e).__name__}: {e}"

_STATIC_SHELL_TOOLS = [
    {"type": "function", "function": {"name": "list_shells", "description": "List all active sandbox sessions", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "file_read", "description": "Read local source code files", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "file_write", "description": "Write fresh content to a local file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "file_edit", "description": "Apply a patch to an existing file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"]}}},
    {"type": "function", "function": {"name": "file_glob", "description": "Find file paths matching a glob pattern", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "file_grep", "description": "Search for a regex pattern across workspace files", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}}}
]

def _build_execute_shell_tool(d: list[ShellDeviceConfig]) -> dict[str, Any]:
    p, r = {"command": {"type": "string", "description": "Shell command to execute"}}, ["command"]
    if len(d) > 1: p["server"] = {"type": "string", "enum": [x.name for x in d]}; r.append("server")
    return {"type": "function", "function": {"name": "execute_shell_command", "description": "Execute a terminal shell command securely", "parameters": {"type": "object", "properties": p, "required": r}}}

class ShellToolProvider:
    _SUPPORTED = frozenset({"list_shells", "execute_shell_command", "file_read", "file_write", "file_edit", "file_glob", "file_grep"})
    def definitions(self, ctx: GenerationContext) -> list[dict[str, Any]]: return [*_STATIC_SHELL_TOOLS, _build_execute_shell_tool(ctx.shell_devices)] if ctx.shell_enabled and ctx.shell_devices else []
    def handles(self, name: str) -> bool: return isinstance(name, str) and name in self._SUPPORTED

@dataclass
class TextSpan: content: str; is_latex: bool; display: bool = False
_LATEX_PATTERN, _CODE_BLOCK_RE = re.compile(r"(\$\$[\s\S]+?\$\$)|(\$(?!\s)(?:[^$\\\n]|\\.)+?\$(?!\d))", re.DOTALL), re.compile(r"```[\s\S]*?```")
class NabdLatexParser:
    @staticmethod
    def parse_spans(t: str) -> list[TextSpan]:
        p = {}
        def rep(x): p[k := f"\x00C{len(p)}\x00"] = x.group(0); return k
        m, s, l = _CODE_BLOCK_RE.sub(rep, t), [], 0
        for x in _LATEX_PATTERN.finditer(m):
            if x.start() > l: s.append(TextSpan(m[l:x.start()], False))
            if x.group(1): s.append(TextSpan(x.group(1)[2:-2].strip(), True, True))
            elif any('\u4e00' <= ch <= '\u9fff' for ch in x.group(2)): s.append(TextSpan(x.group(0), False))
            else: s.append(TextSpan(x.group(2)[1:-1].strip(), True, False))
            l = x.end()
        if l < len(m): s.append(TextSpan(m[l:], False))
        for span in (x for x in s if not x.is_latex):
            for k, v in p.items(): span.content = span.content.replace(k, v)
        return s

class NabdStrings:
    SEARCH_NO_RESULTS, SEARCH_FOUND_RESULTS = "No results found", "Found {count} results for '{query}'"
    SHELL_RESULT_COMMAND, SHELL_RESULT_EXIT_CODE, SHELL_RESULT_ERROR = "Command: {command}", "Exit code: {code}", "Error: {error}"

class NabdSearchResultFormatter:
    @staticmethod
    def is_raw_search_result(t: str) -> bool:
        try: return bool(t and t.startswith("{") and t.endswith("}") and "type" in json.loads(t))
        except Exception: return False
    @staticmethod
    def format_result(t: str) -> str:
        if not NabdSearchResultFormatter.is_raw_search_result(t): return t
        try:
            d = json.loads(t)
            if d.get("type") == "web_search": r = d.get("results", []); return "\n".join([NabdStrings.SEARCH_FOUND_RESULTS.format(count=len(r), query=d.get("query", "unknown"))] + [f"  [{i}] {x.get('title')} -> {x.get('url')}\n      {x.get('description', '')}\n" for i, x in enumerate(r, 1)]) if not d.get("error") and r else NabdStrings.SEARCH_NO_RESULTS
            if d.get("type") == "execute_shell_command": return "\n".join([NabdStrings.SHELL_RESULT_COMMAND.format(command=d.get("command", "")), NabdStrings.SHELL_RESULT_EXIT_CODE.format(code=d.get("exit_code", 0))] + ([NabdStrings.SHELL_RESULT_ERROR.format(error=e)] if (e := d.get("stderr")) else []) + ([f"\nOutput:\n{o}"] if (o := d.get("stdout")) else []))
            return t
        except Exception: return t

@dataclass
class ChatMessage: id: str; parent_id: str | None; text: str; participant: str; status: str = "COMPLETED"; created_at: float = 0.0; is_synthetic: bool = False

class NabdConversationUiState:
    @staticmethod
    def resolve_path(db: list[ChatMessage], stm: ChatMessage | None = None, sel: dict[str, str] | None = None) -> list[ChatMessage]:
        if not db and not stm: return []
        sel, cmap, p, vis, cp = sel or {}, {}, [], set(), None
        for m in (m for m in db if not m.is_synthetic): cmap.setdefault(m.parent_id, []).append(m)
        for s in cmap.values(): s.sort(key=lambda x: x.created_at)
        while (sib := cmap.get(cp, [])):
            if (ch := next((s for s in sib if s.id == sel.get(cp)), sib[-1])).id in vis: break
            vis.add(ch.id); p.append(ch); cp = ch.id
        if stm:
            if (idx := next((i for i, m in enumerate(p) if m.id == stm.id), -1)) >= 0: p[idx] = stm
            elif (not stm.parent_id and not p) or (p and p[-1].id == stm.parent_id): p.append(stm)
        return p

class NabdMessageTemplater:
    @staticmethod
    def apply_user_template_to_messages(m: list[ChatMessage], p: str, s: str) -> list[ChatMessage]:
        return [replace(x, text=f"{p}{x.text}{s}") if x.participant == "USER" and not x.is_synthetic else replace(x) for x in m]
