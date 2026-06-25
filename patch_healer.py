import re
from difflib import SequenceMatcher

class NabdPatchHealer:
    """معالج الرقع الآلي: يصحح اختلافات المسافات أو المسارات الطفيفة قبل إفشال الـ Patch."""
    
    @staticmethod
    def _normalize_string(s: str) -> str:
        """إزالة المسافات الزائدة لتوحيد المقارنة"""
        return re.sub(r'\s+', '', s)
        
    @staticmethod
    def attempt_fuzzy_patch(file_content: str, search_str: str, replace_str: str) -> tuple[bool, str]:
        """يحاول إيجاد التطابق بنسبة خطأ بسيطة (Fuzzy Matching)"""
        norm_search = NabdPatchHealer._normalize_string(search_str)
        
        # إذا كان النص صغيراً جداً، نرفض الـ Fuzzy Matching لمنع التخريب
        if len(norm_search) < 15:
            return False, file_content
            
        # البحث السريع المباشر بعد التجاهل الدقيق للمسافات
        # في بيئة الإنتاج الحقيقية، يفضل استخدام خوارزميات مثل Myers Diff أو Aho-Corasick.
        # هنا سنستخدم التقريب الخطي المبسط:
        
        lines = file_content.split('\n')
        search_lines = search_str.strip().split('\n')
        
        if not search_lines:
            return False, file_content
            
        first_line_norm = NabdPatchHealer._normalize_string(search_lines[0])
        
        for i in range(len(lines)):
            if NabdPatchHealer._normalize_string(lines[i]) == first_line_norm:
                # تحقق مبدئي، هل بقية الأسطر تتطابق تقريباً؟
                if i + len(search_lines) <= len(lines):
                    chunk = '\n'.join(lines[i:i+len(search_lines)])
                    if SequenceMatcher(None, NabdPatchHealer._normalize_string(chunk), norm_search).ratio() > 0.85:
                        # تطابق مرن ناجح! استبدل الكتلة
                        new_content = '\n'.join(lines[:i]) + '\n' + replace_str + '\n' + '\n'.join(lines[i+len(search_lines):])
                        return True, new_content
                        
        return False, file_content
