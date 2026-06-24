import json
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CompressedSegment:
    original_length: int
    compressed_length: int
    summary: str
    importance_score: float

class ContextCompressor:
    """ضاغط ذكي للذاكرة يحافظ على المعلومات الحرجة"""
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.segment_importance: Dict[str, float] = {}
    
    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4
    
    def _calculate_importance(self, message: Dict[str, Any]) -> float:
        role = message.get("role", "")
        content = message.get("content", "")
        
        importance = 0.5
        if role == "system":
            importance = 1.0
        elif role == "user":
            importance = 0.8
        elif role == "tool":
            if "error" in content.lower() or "failed" in content.lower():
                importance = 0.9
            else:
                importance = 0.3
        elif role == "assistant":
            if message.get("tool_calls"):
                importance = 0.9
            else:
                importance = 0.4
        
        return importance
    
    def compress(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not messages:
            return []
        
        scored = []
        for i, msg in enumerate(messages):
            score = self._calculate_importance(msg)
            scored.append((score, i, msg))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        current_tokens = sum(self._estimate_tokens(json.dumps(m)) for m in messages)
        
        compressed = []
        kept_indices = set()
        
        for score, idx, msg in scored:
            msg_tokens = self._estimate_tokens(json.dumps(msg))
            
            if current_tokens + msg_tokens <= self.max_tokens:
                compressed.append(msg)
                kept_indices.add(idx)
                current_tokens += msg_tokens
            elif score > 0.8:
                if current_tokens + 100 <= self.max_tokens:
                    summary_msg = self._summarize_message(msg)
                    compressed.append(summary_msg)
                    kept_indices.add(idx)
                    current_tokens += 100
        
        compressed.sort(key=lambda x: messages.index(x) if x in messages else -1)
        return compressed
    
    def _summarize_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "tool":
            if "error" not in content.lower():
                return {
                    "role": "system",
                    "content": f"[Compressed] Tool result: {content[:100]}..."
                }
        
        return {
            "role": "system",
            "content": f"[Compressed {role}]: {content[:150]}..."
        }
