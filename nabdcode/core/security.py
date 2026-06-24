import re
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class SecurityValidator:
    """مدقق أمني لمدخلات وأرجاع الأدوات"""
    
    # أنماط خطرة في أوامر الشيل
    DANGEROUS_SHELL_PATTERNS = [
        r'rm\s+-rf\s+/',
        r'sudo\s+',
        r'chmod\s+777',
        r'curl\s+\|\s*bash',
        r'wget\s+\|\s*sh',
        r'>\s*/dev/null',
        r'exec\s*\(',
        r'eval\s*\(',
        r'__import__\s*\(',
        r'subprocess\.',
        r'os\.system',
    ]
    
    # أنماط حقن JSON
    JSON_INJECTION_PATTERNS = [
        r'__proto__',
        r'constructor',
        r'prototype',
        r'function\s*\(',
    ]

    ERROR_PATTERNS = [
        r"Error executing tool",
        r"'success':\s*false",
        r"'success':\s*False",
        r"permission denied",
        r"no such file",
        r"command not found",
        r"timeout",
        r"connection refused"
    ]
    
    @classmethod
    def is_tool_error(cls, content: str) -> bool:
        """فحص إذا كانت نتيجة الأداة تحتوي على خطأ"""
        content_lower = str(content).lower()
        return any(re.search(p, content_lower) for p in cls.ERROR_PATTERNS)
    
    @classmethod
    def validate_tool_arguments(cls, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """فحص صحة وسلامة معاملات الأدوات"""
        errors = []
        
        # فحص الأوامر الخطرة
        if tool_name in ["execute_command", "run_shell", "shell"]:
            cmd = str(arguments.get("command", ""))
            for pattern in cls.DANGEROUS_SHELL_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    errors.append(f"Dangerous command pattern detected: {pattern}")
        
        # فحص حقن JSON
        json_str = json.dumps(arguments)
        for pattern in cls.JSON_INJECTION_PATTERNS:
            if re.search(pattern, json_str):
                errors.append(f"Potential JSON injection: {pattern}")
        
        # فحص المسارات (Path Traversal)
        for key, value in arguments.items():
            if isinstance(value, str):
                if ".." in value or value.startswith("/"):
                    if tool_name not in ["read_file", "write_file"]:
                        errors.append(f"Suspicious path in {key}: {value}")
        
        if errors:
            logger.warning(f"Security validation failed for {tool_name}: {errors}")
            raise ValueError(f"Security violation: {'; '.join(errors)}")
        
        return arguments
    
    @classmethod
    def sanitize_output(cls, output: str) -> str:
        """تنظيف المخرجات من المعلومات الحساسة"""
        # إزالة المفاتيح API
        output = re.sub(r'(api[_-]?key|token|secret|password)\s*[:=]\s*[\w-]+', 
                       r'\1: [REDACTED]', output, flags=re.IGNORECASE)
        # إزالة عناوين IP الداخلية
        output = re.sub(r'\b(?:10|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b',
                       '[INTERNAL_IP]', output)
        return output
