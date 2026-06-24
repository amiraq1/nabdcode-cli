import os
import json
import toml
import logging
import asyncio
import aiohttp
import time
from typing import Optional, Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

logger = logging.getLogger(__name__)

class ModelManager:
    """محرك التوجيه الذكي للتواصل عبر خادم الوكيل المحلي مع تبديل تلقائي (Failover)"""
    
    def __init__(self, config_path: str = "config.toml"):
        try:
            self.config = toml.load(config_path)
            logger.info("Configuration loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = {}

    def generate_response(
        self, 
        system_prompt: str, 
        messages: list, 
        temperature: float = 0.7, 
        max_tokens: int = 4096,
        timeout: int = 30
    ) -> str:
        failover_list = self.config.get("failover", {}).get("priority", [])
        last_error = ""
        
        for provider_name in failover_list:
            provider = self.config.get("providers", {}).get(provider_name)
            
            if not provider or not provider.get("api_key"):
                continue

            try:
                payload = {
                    "model": provider.get("model"),
                    "messages": [{"role": "system", "content": system_prompt}, *messages],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json"
                }

                base_url = provider.get("base_url", "https://integrate.api.nvidia.com/v1").rstrip("/")
                if "openrouter" in base_url and "/api/v1" not in base_url:
                    base_url = base_url.replace("/v1", "/api/v1")
                
                target_url = f"{base_url}/chat/completions"

                response = requests.post(target_url, json=payload, headers=headers, timeout=timeout)
                response.raise_for_status()

                result = response.json()
                self.active_provider_key = provider_name
                return result['choices'][0]['message']['content']

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                continue

        raise RuntimeError(f"All providers failed. Last error: {last_error}")


class SecureModelManager(ModelManager):
    """مدير النماذج مع حماية أمنية إضافية"""
    
    def __init__(self, config_path: str = "config.toml"):
        super().__init__(config_path)
        self._audit_log: List[Dict] = []
        from nabdcode.core.rate_limiter import MultiProviderRateLimiter
        self.rate_limiter = MultiProviderRateLimiter()
    
    def _audit(self, action: str, provider: str, status: str, **kwargs):
        entry = {
            "timestamp": time.time(),
            "action": action,
            "provider": provider,
            "status": status,
            **kwargs
        }
        self._audit_log.append(entry)
        logger.info(f"AUDIT: {action} on {provider} -> {status}")
    
    def _get_circuit_breaker(self, provider_name: str):
        # We fetch it from agent or local scope. Let's create one if not found.
        if not hasattr(self, '_cbs'): self._cbs = {}
        if provider_name not in self._cbs:
            from nabdcode.core.circuit_breaker import CircuitBreaker, CircuitConfig
            self._cbs[provider_name] = CircuitBreaker(CircuitConfig(failure_threshold=5))
        return self._cbs[provider_name]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def generate_response_async(
        self,
        system_prompt: str,
        messages: list,
        **kwargs
    ) -> str:
        providers = self.config.get("failover", {}).get("priority", [])
        last_error = ""
        
        total_chars = len(system_prompt) + sum(len(str(m)) for m in messages)
        if total_chars > 100000:
            raise ValueError("Input too large. Risk of context overflow.")
        
        for provider_name in providers:
            provider = self.config.get("providers", {}).get(provider_name)
            if not provider or not provider.get("api_key"):
                continue
            
            cb = self._get_circuit_breaker(provider_name)
            if cb.state.value == "open":
                self._audit("attempt", provider_name, "blocked", reason="circuit_open")
                continue
            
            allowed, msg = await self.rate_limiter.check_limit(provider_name)
            if not allowed:
                self._audit("attempt", provider_name, "rate_limited", message=msg)
                await asyncio.sleep(1)
                continue
            
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "model": provider["model"],
                        "messages": [{"role": "system", "content": system_prompt}, *messages],
                        "temperature": kwargs.get("temperature", 0.7),
                        "max_tokens": kwargs.get("max_tokens", 4096)
                    }
                    
                    headers = {
                        "Authorization": f"Bearer {provider['api_key']}",
                        "Content-Type": "application/json"
                    }
                    
                    base_url = provider.get("base_url", "").rstrip("/")
                    if "openrouter" in base_url and "/api/v1" not in base_url:
                        base_url = base_url.replace("/v1", "/api/v1")
                        
                    target_url = f"{base_url}/chat/completions"
                    
                    async with session.post(
                        target_url, 
                        json=payload, 
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        
                        self._audit("success", provider_name, "completed")
                        self.active_provider_key = provider_name
                        return result['choices'][0]['message']['content']
                        
            except Exception as e:
                last_error = str(e)
                self._audit("failure", provider_name, "error", error=str(e))
                continue
        
        self._audit("system", "all", "failed", last_error=last_error)
        raise RuntimeError(f"All providers failed. Last error: {last_error}")
    
    def get_audit_log(self) -> List[Dict]:
        return self._audit_log[-100:]

    async def generate_response_with_priorities(
        self,
        system_prompt: str,
        messages: list,
        tool_priorities: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        توليد استجابة مع ترتيب الأدوات حسب الأولوية
        """
        if tool_priorities:
            priority_section = f"\n\nTool Execution Priority (use in this order): {', '.join(tool_priorities)}"
            if system_prompt:
                system_prompt += priority_section
        
        return await self.generate_response_async(
            system_prompt=system_prompt,
            messages=messages,
            **kwargs
        )
