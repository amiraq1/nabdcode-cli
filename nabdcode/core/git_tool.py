import subprocess
from typing import Optional

def git_commit_push(commit_message: str, push: bool = False) -> str:
    """
    أداة لإضافة جميع التغييرات، عمل Commit، ورفعها (Push) اختيارياً.
    """
    if not commit_message.strip():
        commit_message = "Auto-commit by NabdCode Agent"

    try:
        # 1. التحقق من أن المجلد الحالي هو مستودع Git
        check_repo = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True
        )
        if check_repo.returncode != 0:
            return "[SYSTEM: GIT ERROR]\nالمجلد الحالي ليس مستودع Git."

        # 2. التحقق من وجود تعديلات فعلية
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True
        )
        if not status.stdout.strip():
            return "[SYSTEM: GIT INFO]\nلا توجد أي تغييرات لعمل Commit لها."

        # 3. إضافة جميع التعديلات (git add .)
        subprocess.run(["git", "add", "."], check=True)

        # 4. عمل Commit
        commit_res = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True, text=True
        )
        output = f"[SYSTEM: GIT COMMIT SUCCESS]\n{commit_res.stdout.strip()}"

        # 5. عمل Push إذا طلب الوكيل ذلك
        if push:
            push_res = subprocess.run(
                ["git", "push"],
                capture_output=True, text=True, stderr=subprocess.STDOUT
            )
            if push_res.returncode == 0:
                output += f"\n\n[SYSTEM: GIT PUSH SUCCESS]\nتم رفع التغييرات بنجاح.\n{push_res.stdout.strip()}"
            else:
                output += f"\n\n[SYSTEM: GIT PUSH WARNING]\nنجح الـ Commit ولكن فشل الـ Push (قد تحتاج لضبط الـ Upstream).\n{push_res.stdout.strip()}"

        return output

    except subprocess.CalledProcessError as e:
        return f"[SYSTEM: GIT ERROR]\nفشل تنفيذ أمر Git:\n{e.stderr or e.stdout}"
    except Exception as e:
        return f"[SYSTEM: GIT ERROR]\nخطأ غير متوقع: {type(e).__name__}: {e}"
