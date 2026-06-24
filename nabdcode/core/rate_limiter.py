import time
import asyncio
import logging
from typing import Dict, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

class TokenBucketRateLimiter:
    """عداد ذكي يعتمد على خوارزمية Bucket"""
    
    def __init__(self, rate: int = 100, per: int = 60):
        self.rate = rate          # عدد الرموز المسموحة
        self.per = per            # في هذه الفترة (ثواني)
        self.tokens = rate
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        async with self._lock:
            now = time.time()
            # إضافة الرموز بناءً على الوقت المنقضي
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / self.per))
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class MultiProviderRateLimiter:
    """عداد لكل مزود على حدة"""
    
    def __init__(self):
        self.limiters: Dict[str, TokenBucketRateLimiter] = defaultdict(
            lambda: TokenBucketRateLimiter(rate=50, per=60)  # 50 طلب/دقيقة
        )
    
    async def check_limit(self, provider_name: str) -> Tuple[bool, str]:
        limiter = self.limiters[provider_name]
        if await limiter.consume():
            return True, ""
        return False, f"Rate limit exceeded for provider {provider_name}"
