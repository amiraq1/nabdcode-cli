# nabdcode/core/path_security.py
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def resolve_safe_path(workspace_root: str | os.PathLike, requested_path: str) -> Path:
    """
    يحل ويتحقق من أن مسار الملف المطلوب يقع تماماً داخل حدود مساحة العمل المسموح بها،
    مما يمنع ثغرات Path Traversal و Symlink Attacks.
    
    Returns:
        Path: كائن مسار آمن (Pathlib object) جاهز للاستخدام.
    """
    if not requested_path or not requested_path.strip():
        raise ValueError("مسار الملف المطلوب فارغ.")

    try:
        # 1. تحويل المسار الجذري إلى كائن Path وحله بالكامل (يتبع الروابط الرمزية)
        safe_root = Path(workspace_root).resolve(strict=False)

        # 2. دمج المسار المطلوب مع الجذري
        # استخدام resolve(strict=False) يحل رموز ../ ويتبع الـ Symlinks بشكل آمن
        target_path = (safe_root / requested_path).resolve(strict=False)

        # 3. نقطة التفتيش الأمنية (The Sandbox Check)
        # التحقق مما إذا كان target_path هو نفس safe_root أو بداخله
        if target_path != safe_root and safe_root not in target_path.parents:
            # تسجيل محاولة الاختراق للأمان (Security Audit)
            logger.warning(
                f"SECURITY ALERT: Path traversal attempt detected! "
                f"Requested: '{requested_path}', Resolved: '{target_path}'"
            )
            raise PermissionError(
                "SECURITY ALERT: Path traversal attempt detected and blocked! "
                f"Cannot access path outside workspace: {requested_path}"
            )

        return target_path

    except PermissionError:
        raise  # إعادة رمي الخطأ الأمني ليتم التقاطه من قبل الـ Agent
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من أمان المسار '{requested_path}': {e}")
        raise ValueError(f"مسار غير صالح: {requested_path}") from e
