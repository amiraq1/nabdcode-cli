import re

with open("nabdcode/core/worktree.py", "r", encoding="utf-8") as f:
    content = f.read()

old_merge = """        # العودة للمسار الأصلي والدمج
        merge_cmd = f"git checkout {target_branch} && git merge {branch_name}"
        try:
            subprocess.run(merge_cmd, shell=True, cwd=base_dir, check=True, capture_output=True, text=True)"""

new_merge = """        # العودة للمسار الأصلي والدمج مباشرة في الفرع النشط (لتجنب تعارض Checkout مع التعديلات غير المحفوظة)
        merge_cmd = f"git merge {branch_name}"
        try:
            subprocess.run(merge_cmd, shell=True, cwd=base_dir, check=True, capture_output=True, text=True)"""

content = content.replace(old_merge, new_merge)

with open("nabdcode/core/worktree.py", "w", encoding="utf-8") as f:
    f.write(content)

