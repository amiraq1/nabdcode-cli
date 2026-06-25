import re

with open("nabdcode/core/tool_scorer.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add zero tests detection
old_shell = """        if any(err in stderr_lower for err in critical_errors):
            return ToolResult(success=False, confidence=0.1, message=f"Critical shell errors detected: {stderr.strip()[:100]}", action_type="shell")
            
        # تحذيرات (Warnings) ولكن لم ينفجر الكود"""
new_shell = """        if any(err in stderr_lower for err in critical_errors):
            return ToolResult(success=False, confidence=0.1, message=f"Critical shell errors detected: {stderr.strip()[:100]}", action_type="shell")
            
        # كشف الفشل الوهمي في الاختبارات (Ran 0 tests)
        if "Ran 0 tests" in stderr or "Ran 0 tests" in stdout:
            return ToolResult(success=False, confidence=0.1, message="False positive: Test runner executed but found 0 tests. Fix directory structure or __init__.py", action_type="shell")
            
        # تحذيرات (Warnings) ولكن لم ينفجر الكود"""

content = content.replace(old_shell, new_shell)

with open("nabdcode/core/tool_scorer.py", "w", encoding="utf-8") as f:
    f.write(content)

