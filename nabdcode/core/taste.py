"""
Taste Engine — طبقة تفضيلات دائمة للوكيل.
"""
import os
from nabdcode.core.logger import logger
from nabdcode.core.taste_manager import TasteManager


def load_all_preferences(root_dir: str = ".") -> str:
    """
    تحميل جميع مصادر التفضيلات والسياق ودمجها في نص واحد.
    """
    manager = TasteManager(taste_dir=os.path.join(root_dir, ".commandcode/taste"))
    tastes = manager.get_tastes()
    if tastes:
        return f"\n\n--- User Taste / Preferences ---\n{tastes}"
    return ""
