import os
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from nabdcode.memory.vector_db import VectorDB

class TasteManager:
    """إدارة تفضيلات المستخدم والقيود البرمجية (Taste-1)"""
    def __init__(self, taste_dir=".commandcode/taste"):
        self.taste_dir = taste_dir
        self.taste_file = os.path.join(taste_dir, "taste.md")
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.taste_dir):
            os.makedirs(self.taste_dir)
        if not os.path.exists(self.taste_file):
            with open(self.taste_file, 'w', encoding='utf-8') as f:
                f.write("# 🧠 التفضيلات والقيود البرمجية (Taste-1)\n")
                f.write("يلتزم الوكيل بهذه القواعد بشكل صارم في كل الردود:\n\n")

    def get_tastes(self) -> str:
        """قراءة التفضيلات لحقنها في الـ System Prompt"""
        try:
            with open(self.taste_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                # إرجاع المحتوى فقط إذا كان يحتوي على قواعد فعلية غير العنوان
                if len(content.split('\n')) > 3: 
                    return content
                return ""
        except Exception:
            return ""

    def add_taste(self, rule: str) -> bool:
        """إضافة قيد برمجي جديد"""
        try:
            with open(self.taste_file, 'a', encoding='utf-8') as f:
                f.write(f"- {rule.strip()}\n")
            return True
        except Exception:
            return False

from nabdcode.memory.taste_profile import TasteProfileManager
