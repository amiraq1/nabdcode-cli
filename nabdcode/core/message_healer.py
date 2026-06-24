import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def merge_consecutive_same_role(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges consecutive messages with the same role unless they involve tool calls."""
    merged: List[Dict[str, Any]] = []
    
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        has_tools = bool(msg.get("tool_calls") or msg.get("tool_call_id"))
        
        if merged and merged[-1].get("role") == role and not has_tools and not bool(merged[-1].get("tool_calls")):
            merged[-1] = {**merged[-1], "content": f"{merged[-1].get('content', '')}\n\n{content}".strip()}
        else:
            merged.append(msg.copy())
            
    return merged

def validate_tool_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    valid, pending = [], []
    for m in messages:
        if m.get("role") == "assistant" and "tool_calls" in m:
            valid.append(m.copy()); pending = list(m["tool_calls"])
        elif m.get("role") == "tool" and pending:
            call, patched = pending.pop(0), m.copy()
            if patched.get("tool_call_id") != call["id"]:
                logger.warning(f"Patching tool ID: {patched.get('tool_call_id')} -> {call['id']}")
                patched["tool_call_id"] = call["id"]
            valid.append(patched)
        elif m.get("role") not in {"tool", "assistant"} or m.get("role") == "assistant":
            valid.append(m.copy()); pending.clear()
        else: logger.warning(f"Dropping orphaned tool message: {m.get('tool_call_id')}")
            
    return [m for m in valid if not (m.get("role") == "assistant" and m.get("tool_calls") and not any(t.get("tool_call_id") in [c["id"] for c in m["tool_calls"]] for t in valid if t.get("role") == "tool"))]

def limit_context(msgs: List[Dict[str, Any]], max_users: int) -> List[Dict[str, Any]]:
    res, count, i = [], 0, len(msgs) - 1
    while i >= 0:
        if (m := msgs[i]).get("role") == "user": count += 1
        if count > max_users: break
        res.append(m.copy())
        if m.get("role") == "tool":
            while i > 0 and msgs[i-1].get("role") == "tool": i -= 1; res.append(msgs[i].copy())
            if i > 0 and msgs[i-1].get("role") == "assistant": i -= 1; res.append(msgs[i].copy())
        i -= 1
    return res[::-1]
