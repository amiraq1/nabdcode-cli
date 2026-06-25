import os
import subprocess
import uuid
from typing import Optional

class NabdWorktreeManager:
    """
    إدارة العزل البيئي الموازي باستخدام git worktree.
    يسمح للوكيل بالعمل في بيئة معزولة (Sandbox) دون المساس بالفرع الرئيسي.
    """
    
    @staticmethod
    def create_sandbox(base_dir: str, branch_name: Optional[str] = None) -> str:
        """إنشاء worktree جديد معزول"""
        if not branch_name:
            branch_name = f"nabd-sandbox-{uuid.uuid4().hex[:8]}"
            
        worktrees_dir = os.path.join(base_dir, ".nabd_worktrees")
        os.makedirs(worktrees_dir, exist_ok=True)
        
        sandbox_path = os.path.join(worktrees_dir, branch_name)
        
        # إنشاء الفرع والـ worktree
        cmd = f"git worktree add -b {branch_name} {sandbox_path} HEAD"
        try:
            subprocess.run(cmd, shell=True, cwd=base_dir, check=True, capture_output=True, text=True)
            return sandbox_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create sandbox: {e.stderr}")

    @staticmethod
    def remove_sandbox(base_dir: str, sandbox_path: str, force: bool = True) -> None:
        """إزالة الـ worktree المعزول بعد انتهاء المراجعة أو في حال الرفض"""
        cmd = f"git worktree remove {'-f' if force else ''} {sandbox_path}"
        try:
            subprocess.run(cmd, shell=True, cwd=base_dir, check=True, capture_output=True, text=True)
            # محاولة حذف الفرع إذا لزم الأمر لاحقاً (اختياري)
            branch_name = os.path.basename(sandbox_path)
            subprocess.run(f"git branch -D {branch_name}", shell=True, cwd=base_dir, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to remove sandbox: {e.stderr}")

    @staticmethod
    def commit_and_merge(base_dir: str, sandbox_path: str, target_branch: str = "main") -> None:
        """تطبيق التعديلات بعد الاعتماد من الـ Reviewer"""
        branch_name = os.path.basename(sandbox_path)
        
        # التأكد من عمل commit لأي تعديلات متبقية في الـ sandbox
        subprocess.run("git add . && git commit -m 'Auto-commit from NabdCode Sandbox'", shell=True, cwd=sandbox_path, capture_output=True)
        
        # 1. التخزين المؤقت للتعديلات غير المحفوظة في الفرع الرئيسي لحمايتها
        subprocess.run("git stash push -m 'Auto-stash before NabdCode Sandbox Merge'", shell=True, cwd=base_dir, capture_output=True)
        
        # 2. العودة للمسار الأصلي والدمج المباشر
        merge_cmd = f"git merge {branch_name}"
        try:
            subprocess.run(merge_cmd, shell=True, cwd=base_dir, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            # استعادة التعديلات في حالة فشل الدمج
            subprocess.run("git stash pop", shell=True, cwd=base_dir, capture_output=True)
            raise RuntimeError(f"Failed to merge sandbox changes: {e.stderr}")
            
        # 3. استعادة التعديلات غير المحفوظة بأمان بعد الدمج الناجح
        subprocess.run("git stash pop", shell=True, cwd=base_dir, capture_output=True)
