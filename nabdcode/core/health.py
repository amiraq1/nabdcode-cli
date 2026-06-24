import asyncio
import logging
from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    component: str
    is_healthy: bool
    last_check: str
    details: Dict[str, Any]

class HealthCheckManager:
    """مراقبة صحة النظام"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.results: List[HealthStatus] = []
    
    def register(self, name: str, check_func: Callable):
        self.checks[name] = check_func
    
    async def run_all_checks(self) -> List[HealthStatus]:
        self.results = []
        for name, check in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check):
                    is_healthy, details = await check()
                else:
                    is_healthy, details = check()
                
                self.results.append(HealthStatus(
                    component=name,
                    is_healthy=is_healthy,
                    last_check=datetime.utcnow().isoformat(),
                    details=details or {}
                ))
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                self.results.append(HealthStatus(
                    component=name,
                    is_healthy=False,
                    last_check=datetime.utcnow().isoformat(),
                    details={"error": str(e)}
                ))
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        healthy = sum(1 for r in self.results if r.is_healthy)
        return {
            "total": len(self.results),
            "healthy": healthy,
            "unhealthy": len(self.results) - healthy,
            "status": "UP" if healthy == len(self.results) else "DEGRADED"
        }
