import time
import logging
import asyncio
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # طبيعي
    OPEN = "open"          # مقفل (فشل متكرر)
    HALF_OPEN = "half_open"  # اختبار الإعادة

@dataclass
class CircuitConfig:
    failure_threshold: int = 3       # عدد الأخطاء قبل الفتح
    recovery_timeout: float = 30.0   # انتظار قبل الاختبار
    half_open_max_calls: int = 2     # عدد المحاولات في النصف مفتوح

class CircuitBreaker:
    """حماية من الفشل المتتالي للمزودين"""
    
    def __init__(self, config: Optional[CircuitConfig] = None):
        self.config = config or CircuitConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.success_count = 0
        self.half_open_calls = 0
    
    def _should_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        return False
    
    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful recovery.")
    
    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker opened after half-open failure.")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker OPENED after {self.failure_count} failures.")
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        if not self._should_attempt():
            raise Exception("Circuit breaker is OPEN. Provider is unavailable.")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
