from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class ToolResult:
    success: bool
    confidence: float
    message: str
    action_type: str  # e.g., 'write', 'shell', 'patch'

class ToolSuccessScorer:
    """يُقيّم مخرجات الأدوات ويعطي نسبة ثقة لنجاح التنفيذ (Tool Success Scoring)"""
    
    @staticmethod
    def evaluate_shell(stdout: str, stderr: str) -> ToolResult:
        """تحليل مخرجات التيرمنال لتقدير النجاح"""
        # إذا لم يكن هناك خطأ في stderr
        if not stderr.strip():
            return ToolResult(success=True, confidence=1.0, message="Executed cleanly.", action_type="shell")
            
        # بعض البرامج تكتب تحذيرات أو رسائل عادية في stderr (مثل npm, pip)
        stderr_lower = stderr.lower()
        critical_errors = ["error", "exception", "traceback", "fatal", "failed", "syntaxerror"]
        
        if any(err in stderr_lower for err in critical_errors):
            return ToolResult(success=False, confidence=0.1, message=f"Critical shell errors detected: {stderr.strip()[:100]}", action_type="shell")
            
        # كشف الفشل الوهمي في الاختبارات (Ran 0 tests)
        if "Ran 0 tests" in stderr or "Ran 0 tests" in stdout:
            return ToolResult(success=False, confidence=0.1, message="False positive: Test runner executed but found 0 tests. Fix directory structure or __init__.py", action_type="shell")
            
        # تحذيرات (Warnings) ولكن لم ينفجر الكود
        return ToolResult(success=True, confidence=0.75, message="Executed with warnings in stderr.", action_type="shell")

    @staticmethod
    def evaluate_file_write(path: str, content_length: int, compilation_err: Optional[str] = None) -> ToolResult:
        """تحليل عملية كتابة الملفات، والتأكد من صحة الصياغة (Syntax)"""
        if compilation_err:
            return ToolResult(success=False, confidence=0.0, message=f"Syntax compilation failed: {compilation_err}", action_type="write")
            
        if content_length == 0:
            return ToolResult(success=False, confidence=0.0, message="Attempted to write an empty file.", action_type="write")
            
        return ToolResult(success=True, confidence=1.0, message="File written and compiled successfully.", action_type="write")

    @staticmethod
    def evaluate_patch(search_str: str, file_content: str, patch_err: Optional[str] = None) -> ToolResult:
        """تقييم عملية استبدال الكود (Search/Replace)"""
        if patch_err:
            return ToolResult(success=False, confidence=0.0, message=patch_err, action_type="patch")
            
        # التحقق من أن النص القديم ليس فضفاضاً جداً (Context Too Small)
        lines = search_str.strip().split("\n")
        if len(lines) == 1 and len(search_str) < 15:
            return ToolResult(success=True, confidence=0.6, message="Patch applied, but search context was dangerously small. High risk of wrong replacement.", action_type="patch")
            
        return ToolResult(success=True, confidence=0.95, message="Patch applied precisely.", action_type="patch")
