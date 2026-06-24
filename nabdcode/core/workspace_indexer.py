# nabdcode/core/workspace_indexer.py
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class WorkspaceIndexer:
    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path)
        # ملف مخفي داخل المشروع لتتبع حالة الفهرسة
        self.cache_file = self.workspace_path / ".nabd_index_cache.json"
        self.file_mtimes: dict[str, float] = self._load_cache()

    def _load_cache(self) -> dict[str, float]:
        """تحميل الذاكرة السريعة لأوقات التعديل إن وجدت."""
        if not self.cache_file.exists():
            return {}
            
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                return {}
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"ملف كاش الفهرسة تالف أو غير قابل للقرارة، يتم البدء من جديد: {e}")
            return {}

    def _save_cache(self) -> bool:
        """حفظ الحالة الجديدة للملفات بعد انتهاء الفهرسة."""
        try:
            # التأكد من أن مجلد العمل الرئيسي موجود (في حال تم حذفه وإعادة إنشائه)
            self.workspace_path.mkdir(parents=True, exist_ok=True)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_mtimes, f, indent=4)
            return True
        except IOError as e:
            logger.error(f"فشل حفظ ملف كاش الفهرسة ({self.cache_file}): {e}")
            return False

    def cleanup_orphans(self) -> int:
        """
        تنظيف الذاكرة السريعة من الملفات التي لم تعد موجودة في مجلد العمل.
        يُستدعى هذا بعد انتهاء دورة الفهرسة لمنع تضخم ملف الكاش.
        """
        if not self.file_mtimes:
            return 0
            
        orphans_count = 0
        # نسخ المفاتيح لتجنب تعديل القاموس أثناء التكرار (RuntimeError)
        for file_path in list(self.file_mtimes.keys()):
            if not Path(file_path).exists():
                del self.file_mtimes[file_path]
                orphans_count += 1
                
        if orphans_count > 0:
            logger.info(f"تم تنظيف {orphans_count} ملف محذوف من كاش الفهرسة.")
            self._save_cache()
            
        return orphans_count

    def has_file_changed(self, file_path: str | Path) -> bool:
        """التحقق مما إذا كان الملف قد تم تعديله منذ آخر فهرسة."""
        path = Path(file_path)
        if not path.exists():
            return False
            
        current_mtime = path.stat().st_mtime
        last_mtime = self.file_mtimes.get(str(path))
        
        if last_mtime is None or current_mtime > last_mtime:
            self.file_mtimes[str(path)] = current_mtime
            return True
            
        return False
