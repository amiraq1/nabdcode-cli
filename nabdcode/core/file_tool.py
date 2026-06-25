"""
nabdcode/core/file_tool.py
محرك الملفات الآمن — كتابة ذرية، diff guards، نسخ احتياطية تلقائية.
"""
import os
import shutil
import time
from typing import Dict, Any

from rich.console import Console
from difflib import SequenceMatcher
from nabdcode.core.ignore_manager import ignore_checker

class NabdPatchHealer:
    """معالج الرقع الآلي: يصحح اختلافات المسافات أو المسارات الطفيفة قبل إفشال الـ Patch."""
    
    @staticmethod
    def _normalize_string(s: str) -> str:
        """إزالة المسافات الزائدة لتوحيد المقارنة"""
        import re
        return re.sub(r'\s+', '', s)
        
    @staticmethod
    def attempt_fuzzy_patch(file_content: str, search_str: str, replace_str: str) -> tuple[bool, str]:
        """يحاول إيجاد التطابق بنسبة خطأ بسيطة (Fuzzy Matching)"""
        norm_search = NabdPatchHealer._normalize_string(search_str)
        
        if len(norm_search) < 15:
            return False, file_content
            
        lines = file_content.split('\n')
        search_lines = search_str.strip().split('\n')
        
        if not search_lines:
            return False, file_content
            
        first_line_norm = NabdPatchHealer._normalize_string(search_lines[0])
        
        for i in range(len(lines)):
            if NabdPatchHealer._normalize_string(lines[i]) == first_line_norm:
                if i + len(search_lines) <= len(lines):
                    chunk = '\n'.join(lines[i:i+len(search_lines)])
                    if SequenceMatcher(None, NabdPatchHealer._normalize_string(chunk), norm_search).ratio() > 0.85:
                        new_content = '\n'.join(lines[:i])
                        if new_content:
                            new_content += '\n'
                        new_content += replace_str + '\n' + '\n'.join(lines[i+len(search_lines):])
                        return True, new_content
                        
        return False, file_content

console = Console()

# ── ثوابت ────────────────────────────────────────────────────────────────────
_MAX_BACKUP_AGE_DAYS = 7   # حد عمر النسخ الاحتياطية (للتنظيف المستقبلي)
_TMP_SUFFIX          = ".nabdtmp"
_BAK_SUFFIX          = ".bak"


def _backup(file_path: str) -> str | None:
    """يأخذ نسخة احتياطية مختومة بالوقت. يعيد المسار أو None إذا لم يكن الملف موجوداً."""
    if not os.path.exists(file_path):
        return None
    backup = f"{file_path}.{int(time.time())}{_BAK_SUFFIX}"
    shutil.copy2(file_path, backup)
    return backup


def _atomic_write(file_path: str, content: str) -> None:
    """كتابة ذرية: يكتب في ملف مؤقت ثم يستبدل الأصلي دفعة واحدة."""
    tmp = file_path + _TMP_SUFFIX
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, file_path)  # عملية ذرية على Linux


class NabdFileEngine:
    """محرك الملفات الآمن — كل عملية ذرية ومحمية بنسخة احتياطية."""

    # ── الكتابة الكاملة ───────────────────────────────────────────────────────

    @staticmethod
    def safe_write(file_path: str, content: str) -> Dict[str, Any]:
        """
        يكتب محتوى كامل لملف بأمان تام:
        1. ينشئ المجلدات المفقودة
        2. يأخذ نسخة احتياطية
        3. يكتب ذرياً عبر ملف مؤقت
        """
        try:
            file_path = file_path.strip()
            if not file_path:
                return {"success": False, "error": "file_path فارغ"}

            if ignore_checker.is_ignored(file_path):
                msg = f"محظور: هذا الملف محمي بواسطة قواعد الخصوصية (.nabdignore)"
                console.print(f"\n[bold red]🚫 Privacy Guard: {msg} -> {file_path}[/bold red]")
                return {"success": False, "error": msg}

            parent = os.path.dirname(file_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            backup = _backup(file_path)
            _atomic_write(file_path, content)

            return {
                "success":       True,
                "file":          file_path,
                "lines_changed": len(content.splitlines()),
                "backup":        backup,
            }

        except OSError as exc:
            console.print(f"\n[bold red]❗ File Engine Error ({file_path}): {exc}[/bold red]")
            return {"success": False, "file": file_path, "error": str(exc)}

    # ── الاستبدال الجراحي ─────────────────────────────────────────────────────

    @staticmethod
    def apply_search_replace(
        file_path: str,
        search_str: str,
        replace_str: str,
    ) -> Dict[str, Any]:
        """
        يطبّق SEARCH/REPLACE جراحياً:
        - يرفض إذا لم يجد الكتلة (حتى بعد تطبيع الفراغات)
        - يرفض إذا لم يتغير المحتوى
        - نسخة احتياطية قبل أي تعديل
        """
        try:
            file_path = file_path.strip()

            if ignore_checker.is_ignored(file_path):
                msg = f"محظور: هذا الملف محمي بواسطة قواعد الخصوصية (.nabdignore)"
                console.print(f"\n[bold red]🚫 Privacy Guard: {msg} -> {file_path}[/bold red]")
                return {"success": False, "error": msg}

            if not os.path.exists(file_path):
                msg = f"الملف غير موجود: {file_path}"
                console.print(f"\n[bold red]❗ Diff Guard: {msg}[/bold red]")
                return {"success": False, "error": msg}

            with open(file_path, "r", encoding="utf-8") as f:
                original = f.read()

            # محاولة المطابقة المباشرة أولاً
            if search_str in original:
                updated = original.replace(search_str, replace_str, 1)
            else:
                # تطبيع الفراغات الخلفية كحل بديل
                def _norm(text: str) -> str:
                    return "\n".join(line.rstrip() for line in text.splitlines())

                norm_search  = _norm(search_str)
                norm_original = _norm(original)

                if norm_search not in norm_original:
                    # ── التفعيل الجراحي للمعالج الآلي (Patch Self-Healer) ──
                    is_healed, healed_content = NabdPatchHealer.attempt_fuzzy_patch(original, search_str, replace_str)
                    if is_healed:
                        updated = healed_content
                        console.print(
                            f"\n[bold white on green] 🩹 SELF-HEALER [/bold white on green] [bold green]Patch applied via fuzzy sequence matching for: {file_path}[/bold green]"
                        )
                    else:
                        msg = f"كتلة SEARCH غير موجودة في: {file_path}"
                        console.print(f"\n[bold red]❗ Diff Guard: {msg}[/bold red]")
                        return {"success": False, "error": "Target SEARCH block not found (even after fuzzy healing)"}
                else:
                    # تطبيق على النص الأصلي بعد العثور عليه في النسخة المُطبَّعة
                    start = norm_original.index(norm_search)
                    end   = start + len(norm_search)
                    updated = original[:start] + replace_str + original[end:]
                    console.print(
                        f"\n[bold yellow]⚠ Diff Guard: whitespace مختلف — تم التطبيق بعد التطبيع.[/bold yellow]"
                    )

            if updated == original:
                msg = "المحتوى لم يتغير بعد الاستبدال"
                console.print(f"\n[bold yellow]⚠ Diff Guard: {msg} — {file_path}[/bold yellow]")
                return {"success": False, "error": msg}

            backup = _backup(file_path)
            _atomic_write(file_path, updated)

            lines_delta = abs(len(updated.splitlines()) - len(original.splitlines()))
            lines_changed = lines_delta or len(replace_str.splitlines())

            return {
                "success":       True,
                "file":          file_path,
                "lines_changed": lines_changed,
                "backup":        backup,
            }

        except OSError as exc:
            console.print(f"\n[bold red]❗ Diff Engine Exception ({file_path}): {exc}[/bold red]")
            return {"success": False, "error": str(exc)}
