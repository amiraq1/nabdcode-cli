import json
import os
import time
from typing import Dict, Any

class AgentTelemetry:
    """وحدة القياسات عن بعد (Telemetry) لتسجيل جودة استدعاءات الأدوات وزمن الوصول"""
    
    _instance = None
    _filepath = ".nabd_telemetry.json"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.stats = {
            "total_calls": 0,
            "successes": 0,
            "failures": 0,
            "tools": {
                "shell": {"calls": 0, "successes": 0, "failures": 0, "total_latency": 0.0},
                "write": {"calls": 0, "successes": 0, "failures": 0, "total_latency": 0.0},
                "patch": {"calls": 0, "successes": 0, "failures": 0, "total_latency": 0.0},
                "web": {"calls": 0, "successes": 0, "failures": 0, "total_latency": 0.0},
            }
        }
        self.load()

    def load(self):
        if os.path.exists(self._filepath):
            try:
                with open(self._filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge to preserve new structure if updated
                    for key in ["total_calls", "successes", "failures"]:
                        if key in data:
                            self.stats[key] = data[key]
                    if "tools" in data:
                        for tool_name, tool_data in data["tools"].items():
                            if tool_name in self.stats["tools"]:
                                self.stats["tools"][tool_name].update(tool_data)
            except Exception:
                pass

    def save(self):
        try:
            with open(self._filepath, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=4)
        except Exception:
            pass

    def record_tool_call(self, tool_name: str, success: bool, latency: float):
        if tool_name not in self.stats["tools"]:
            tool_name = "shell"  # fallback
            
        self.stats["total_calls"] += 1
        self.stats["tools"][tool_name]["calls"] += 1
        self.stats["tools"][tool_name]["total_latency"] += latency
        
        if success:
            self.stats["successes"] += 1
            self.stats["tools"][tool_name]["successes"] += 1
        else:
            self.stats["failures"] += 1
            self.stats["tools"][tool_name]["failures"] += 1
            
        self.save()

    def get_report(self) -> str:
        """يولد تقريراً مختصراً لمقاييس الأداء"""
        total = self.stats["total_calls"]
        if total == 0:
            return "No telemetry data available yet."
            
        success_rate = (self.stats["successes"] / total) * 100
        report = f"📊 Agent Telemetry Report\nTotal Calls: {total} | Success Rate: {success_rate:.1f}%\n"
        
        for tool_name, metrics in self.stats["tools"].items():
            calls = metrics["calls"]
            if calls > 0:
                t_success = (metrics["successes"] / calls) * 100
                avg_latency = metrics["total_latency"] / calls
                report += f" - {tool_name.upper()}: {calls} calls, {t_success:.1f}% success, avg {avg_latency:.2f}s latency\n"
        return report

# Singleton access
telemetry = AgentTelemetry()
