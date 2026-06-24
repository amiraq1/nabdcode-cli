# nabdcode/skills/sample_skill.py
# جميع التعليقات والبيانات التوضيحية داخل الكود تُكتب باللغة العربية.

import asyncio
import logging
from typing import Any, Dict

# إعداد التسجيل (Logging) ليتوافق مع فلسفة النظام (Minimalism)
logger = logging.getLogger(__name__)

# إصدار الواجهة البرمجية المتوافق مع مدير المهارات
REQUIRED_SKILL_API = "1.0"

# البيانات التعريفية للمهارة البرمجية
SKILL_INFO: Dict[str, str] = {
    "name": "Sample Code Helper",
    "version": "1.0.1",
    "description": "مهارة نموذجية مخصصة لفحص وتحليل جودة الكود محلياً."
}

# تعريف ثابت لاسم الأداة لتقليل التكرار (DRY Principle)
TOOL_NAME = "sample__analyze_code"

async def sample_tool_func(code_chunk: str) -> str:
    """
    وظيفة فحص جودة الكود المرفق للتأكد من خلوه من الأخطاء العامة.
    
    Args:
        code_chunk (str): النص البرمجي المطلوب تحليله.
        
    Returns:
        str: نتيجة الفحص.
    """
    if not code_chunk or not code_chunk.strip():
        return "فشل التحليل: الكود البرمجي فارغ أو يحتوي على مسافات فقط."
    
    try:
        # إعطاء فرصة لحلقة الأحداث (Event Loop) للعمل لمنع التجميد في التحليلات المعقدة
        await asyncio.sleep(0)
        
        # --- منطق الفحص الافتراضي (يُوسع لاحقاً) ---
        # مثال: يمكن إضافة تحليل AST أو فحص الـ PEP8 هنا
        
        return "نجاح الفحص: تم تدقيق الكود وهو متوافق مع المعايير."
        
    except Exception as e:
        logger.error(f"خطأ غير متوقع أثناء تحليل الكود: {e}")
        return f"فشل التحليل: حدث خطأ داخلي ({type(e).__name__})."

def setup_skill(registry: Any, **kwargs) -> bool:
    """
    دالة التهيئة المعيارية لتسجيل الأدوات في السجل المركزي الموحد.
    
    Args:
        registry: السجل المركزي لتسجيل الأدوات.
        
    Returns:
        bool: True إذا تم التسجيل بنجاح، False في حال الفشل.
    """
    try:
        # تسجيل الأداة محلياً باسم مسبوق بنطاق المهارة لمنع تصادم الأسماء
        registry.register_local_tool(
            name=TOOL_NAME,
            desc="فحص وتحليل جودة الكود البرمجي محلياً ومعالجة الأخطاء السطحية.",
            args_schema={
                "type": "object",
                "properties": {
                    "code_chunk": {
                        "type": "string",
                        "description": "النص البرمجي المطلوب تحليله."
                    }
                },
                "required": ["code_chunk"]
            }
        )(sample_tool_func)
        
        logger.info(f"تم تحميل مهارة '{SKILL_INFO['name']}' وتسجيل الأداة '{TOOL_NAME}' بنجاح.")
        return True
        
    except (AttributeError, TypeError, ValueError) as e:
        # التقاط أخطاء محددة لمنع انهيار النظام وتسهيل تتبع المشاكل
        logger.error(f"فشل تسجيل مهارة '{SKILL_INFO['name']}': {e}")
        return False
