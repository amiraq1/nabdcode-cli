"""
nabdcode/core/ignore_manager.py
نظام حارس الخصوصية — يمنع الوكيل من الوصول للملفات الحساسة
"""
import os
import fnmatch
from typing import List

class IgnoreManager:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = os.path.abspath(workspace_root)
        self.ignore_file = os.path.join(self.workspace_root, ".nabdignore")
        self.rules: List[str] = [
            ".git", ".git/*",
            "__pycache__", "__pycache__/*",
            "*.pyc",
            "config.toml",
            ".env",
            "venv", "venv/*",
            "node_modules", "node_modules/*",
            "*.bak",
            "*.nabdtmp"
        ]
        self._load_rules()

    def _load_rules(self) -> None:
        if os.path.exists(self.ignore_file):
            try:
                with open(self.ignore_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if line.endswith("/"):
                                self.rules.append(line[:-1])
                                self.rules.append(line + "*")
                            else:
                                self.rules.append(line)
            except Exception:
                pass

    def is_ignored(self, file_path: str) -> bool:
        abs_path = os.path.abspath(file_path)
        try:
            rel_path = os.path.relpath(abs_path, self.workspace_root)
        except ValueError:
            return True # حظر الوصول لخارج مجلد العمل
            
        rel_path = rel_path.replace("\\", "/")
        parts = rel_path.split("/")
        
        for rule in self.rules:
            # Check full relative path
            if fnmatch.fnmatch(rel_path, rule):
                return True
            # Check individual parts
            for part in parts:
                if fnmatch.fnmatch(part, rule):
                    return True
            # Directory match
            clean_rule = rule.replace("/*", "/")
            if clean_rule.endswith("/") and rel_path.startswith(clean_rule):
                return True
                
        return False

# مثيل عام جاهز للاستخدام في جميع أنحاء النظام
ignore_checker = IgnoreManager()
