# nabdcode/core/vector_security.py
import pickle
import hmac
import hashlib
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# حجم بصمة SHA256 بالبايت (Magic Number)
HMAC_SIZE = 32

def _get_secret_key() -> bytes:
    """
    جلب المفتاح السري بشكل آمن.
    أولاً يبحث في متغيرات البيئة، إذا لم يجده يولد مفتاحاً ثابتاً معروف للنظام.
    (يُفضل لاحقاً ربطه بشكل كامل بـ ConfigManager).
    """
    # يمكن استبدال هذا لاحقاً بـ config_manager.get('hmac_secret_key')
    return os.getenv("NABDCODE_SECRET_KEY", "nabdcode-secure-agent-os-2026").encode('utf-8')

def save_vectors_securely(data: dict, filepath: str | Path) -> bool:
    """
    يحول قاعدة بيانات المتجهات إلى حزمة بايتات ويغلقها بتوقيع 
    HMAC-SHA256 لمنع التلف والتلاعب.
    """
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. تحويل البيانات إلى حزمة بايتات
        pickled_data = pickle.dumps(data)
        
        # 2. توليد بصمة التشفير (Signature)
        signature = hmac.new(_get_secret_key(), pickled_data, hashlib.sha256).digest()
        
        # 3. حفظ البصمة (32 بايت) متبوعة بالبيانات
        with open(path, 'wb') as f:
            f.write(signature + pickled_data)
            
        return True
    except IOError as e:
        logger.error(f"فشل حفظ قاعدة بيانات المتجهات: {e}")
        return False

def load_vectors_securely(filepath: str | Path) -> dict:
    """
    يتحقق من سلامة قاعدة البيانات قبل إجراء الفك غير الآمن (Unpickling).
    """
    path = Path(filepath)
    if not path.exists():
        return {}
        
    try:
        with open(path, 'rb') as f:
            content = f.read()
            
        if len(content) < HMAC_SIZE:
            raise ValueError("الملف صغير جداً ولا يحتوي على بصمة صالحة.")
            
        # 1. فصل البصمة عن البيانات الحقيقية
        signature = content[:HMAC_SIZE]
        pickled_data = content[HMAC_SIZE:]
        
        # 2. التحقق الصارم من سلامة الملف (Integrity Check)
        expected_signature = hmac.new(_get_secret_key(), pickled_data, hashlib.sha256).digest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("فشل التحقق من نزاهة قاعدة البيانات! الملف تالف أو تم التلاعب به.")
            
        # 3. الفك الآمن بعد ثبوت النزاهة
        return pickle.loads(pickled_data)
        
    except Exception as e:
        logger.critical(f"خطأ في تحميل المتجهات، يتم عزل الملف التالف: {e}")
        
        # عزل الملف التالف بدلاً من حذفه نهائياً (لإمكانية الاسترجاع لاحقاً)
        corrupted_path = path.with_suffix('.bak.corrupted')
        try:
            path.rename(corrupted_path)
            logger.warning(f"تم عزل الملف التالف إلى: {corrupted_path}")
        except OSError:
            pass  # تجاهل الخطأ إذا لم نتمكن من إعادة التسمية
            
        return {}
