from enum import Enum
import re
from typing import List

class TaskType(Enum):
    CHAT = "chat"
    FILE = "file"
    WEB = "web"
    SHELL = "shell"
    PROJECT = "project"

class IntentRouter:
    """المسؤول عن توجيه النوايا لتجنب الاستخدام العبثي للأدوات (Over-Engineering)"""
    
    # كلمات مفتاحية دلالية قوية (Heuristics)
    _FILE_KW = {"file", "ملف", "read", "اقرأ", "write", "اكتب", "edit", "عدل", "code", "كود"}
    _WEB_KW = {"search", "ابحث", "latest version", "أحدث إصدار", "docs", "توثيق", "ما هو آخر تحديث لـ", "اقرأ توثيق مكتبة", "ابحث في الويب"}
    _SHELL_KW = {"run", "شغل", "execute", "نفذ", "test", "اختبر", "install", "ثبت"}
    _PROJECT_KW = {"build", "ابن", "create app", "أنشئ تطبيق", "fix project", "أصلح المشروع"}
    
    @classmethod
    def classify(cls, user_input: str) -> TaskType:
        """يصنف نية المستخدم لتحديد المسار الأفضل: دردشة مباشرة أم حلقة وكيل؟"""
        text = user_input.lower()
        
        # 1. الأسئلة العامة والدردشة (CHAT)
        # إذا كان النص قصيراً جداً أو يحتوي على كلمات ترحيب/استفهام عامة بدون أفعال تنفيذية
        chat_indicators = {"ما هو", "كيف", "اشرح", "what is", "how to", "explain", "مرحبا", "hi", "الفرق بين"}
        
        # 2. البحث في الويب (الأولوية الأعلى لتجنب تداخل الكلمات مثل "كود" مع "ابحث عن كود")
        if any(kw in text for kw in cls._WEB_KW):
            return TaskType.WEB
            
        # 3. التحقق من وجود نية لمشروع ضخم
        if any(kw in text for kw in cls._PROJECT_KW):
            return TaskType.PROJECT
            
        # 4. التحقق من التعامل مع الملفات
        if any(kw in text for kw in cls._FILE_KW):
            return TaskType.FILE
            
        # 5. التحقق من أوامر النظام
        if any(kw in text for kw in cls._SHELL_KW):
            return TaskType.SHELL

        # إذا كانت البداية استفهامية بحتة
        if any(text.startswith(ind) for ind in chat_indicators):
            return TaskType.CHAT
            
        # الافتراضي للمدخلات البسيطة جداً
        if len(text.split()) < 10 and not any(kw in text for kw in cls._FILE_KW | cls._SHELL_KW | cls._PROJECT_KW):
            return TaskType.CHAT
            
        # الوضع الآمن الافتراضي للوكيل البرمجي
        return TaskType.FILE

    @classmethod
    def should_use_tool(cls, intent: TaskType) -> bool:
        """يمنع استخدام الأدوات تماماً في حالات الدردشة أو الأسئلة النظرية"""
        return intent != TaskType.CHAT

    @classmethod
    def get_allowed_tools(cls, intent: TaskType) -> List[str]:
        """فلترة الأدوات المعروضة للنموذج لتقليل التشويش (Context Overload)"""
        if intent == TaskType.CHAT:
            return []
        elif intent == TaskType.FILE:
            return ["read_file", "write_file", "search_replace"]
        elif intent == TaskType.SHELL:
            return ["execute_command"]
        elif intent == TaskType.WEB:
            return ["web_search"]
        elif intent == TaskType.PROJECT:
            return ["read_file", "write_file", "search_replace", "execute_command", "web_search"]
        return []
