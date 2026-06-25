from typing import List, Dict, Any
from rich.console import Console

console = Console()

class ContextWindowManager:
    """إدارة ذكية لنافذة السياق لتقليل التشويش وتجنب فقدان الهدف الأساسي"""
    
    @staticmethod
    def build_optimal_context(
        messages: List[Dict[str, Any]], 
        recent_limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        يستبدل الاقتصاص الغبي (limit_context) بتركيب ذكي للسياق:
        1. System Prompt (القواعد الثابتة).
        2. Current Task (الهدف الأساسي للمستخدم).
        3. Recent Interactions (آخر N محاولات لتتبع الفشل/النجاح القريب).
        """
        if not messages:
            return []

        # 1. استخراج الـ System Prompt (يكون عادة الرسالة الأولى)
        system_messages = [m for m in messages if m.get("role") == "system"]
        
        # 2. استخراج الـ Current Task (أول رسالة للمستخدم)
        user_messages = [m for m in messages if m.get("role") == "user"]
        initial_task = user_messages[0] if user_messages else None
        
        # 3. استخراج المحادثات التفاعلية الأخيرة (Recent interactions)
        # سنتجاهل الرسالة الأولى للمستخدم والـ system لأننا أخذناهم
        interactive_messages = [m for m in messages if m not in system_messages and m != initial_task]
        
        # الاقتصاص فقط من المحادثات الأخيرة
        recent_interactions = interactive_messages[-recent_limit:] if len(interactive_messages) > recent_limit else interactive_messages
        
        # التجميع النهائي
        optimal_context = []
        optimal_context.extend(system_messages)
        
        if initial_task:
            # تغليف الهدف الرئيسي لضمان عدم نسيانه
            enhanced_task = initial_task.copy()
            enhanced_task["content"] = f"[PRIMARY OBJECTIVE]:\n{initial_task['content']}"
            optimal_context.append(enhanced_task)
            
        if len(interactive_messages) > recent_limit:
            # إضافة إشعار للموديل بأنه تم اقتصاص بعض الخطوات السابقة لتوفير الذاكرة
            optimal_context.append({
                "role": "user", 
                "content": "[SYSTEM]: Past intermediate steps were truncated to save context. Focus on the primary objective and the recent errors/outputs below."
            })
            
        optimal_context.extend(recent_interactions)
        
        # دمج الرسائل المتتالية لنفس الدور (لضمان توافق الـ API)
        optimal_context = ContextWindowManager._merge_consecutive_same_role(optimal_context)
        
        return optimal_context

    @staticmethod
    def _merge_consecutive_same_role(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged = []
        for msg in messages:
            if merged and merged[-1]["role"] == msg["role"]:
                merged[-1]["content"] += f"\n\n{msg['content']}"
            else:
                merged.append(msg.copy())
        return merged
