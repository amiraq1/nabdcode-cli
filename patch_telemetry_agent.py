import re

with open("nabdcode/core/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add imports
if "import time" not in content:
    content = content.replace("import sys", "import sys\nimport time")
if "from nabdcode.core.telemetry import telemetry" not in content:
    content = content.replace("from nabdcode.core.tool_scorer import ToolSuccessScorer", "from nabdcode.core.tool_scorer import ToolSuccessScorer\nfrom nabdcode.core.telemetry import telemetry")

# Patch FILE_WRITE
old_write = """        for raw_path, code in write_blocks:
            path   = raw_path.strip()
            modified_files.append(path)
            result = NabdFileEngine.safe_write(_resolve(path), code.strip())"""

new_write = """        for raw_path, code in write_blocks:
            path   = raw_path.strip()
            modified_files.append(path)
            
            _t0 = time.time()
            result = NabdFileEngine.safe_write(_resolve(path), code.strip())
            _t_latency = time.time() - _t0"""
content = content.replace(old_write, new_write)

old_write_score = """                score = ToolSuccessScorer.evaluate_file_write(path, len(code.strip()), err)
                if not score.success:"""
new_write_score = """                score = ToolSuccessScorer.evaluate_file_write(path, len(code.strip()), err)
                telemetry.record_tool_call("write", score.success, _t_latency)
                if not score.success:"""
content = content.replace(old_write_score, new_write_score)

old_write_fail = """            else:
                all_passed    = False
                error_report += f"Write Error → {path}: {result.get('error')}\\n" """
new_write_fail = """            else:
                telemetry.record_tool_call("write", False, _t_latency)
                all_passed    = False
                error_report += f"Write Error → {path}: {result.get('error')}\\n" """
content = content.replace(old_write_fail, new_write_fail)

# Patch SEARCH_REPLACE
old_sr = """            search_str, replace_str = match.group(1), match.group(2)
            result = NabdFileEngine.apply_search_replace(_resolve(path), search_str, replace_str)"""
new_sr = """            search_str, replace_str = match.group(1), match.group(2)
            
            _t0 = time.time()
            result = NabdFileEngine.apply_search_replace(_resolve(path), search_str, replace_str)
            _t_latency = time.time() - _t0"""
content = content.replace(old_sr, new_sr)

old_sr_score = """                err = _compile_check(_resolve(path))
                score = ToolSuccessScorer.evaluate_patch(search_str, result.get("content", ""), err)
                if not score.success:"""
new_sr_score = """                err = _compile_check(_resolve(path))
                score = ToolSuccessScorer.evaluate_patch(search_str, result.get("content", ""), err)
                telemetry.record_tool_call("patch", score.success, _t_latency)
                if not score.success:"""
content = content.replace(old_sr_score, new_sr_score)

old_sr_fail = """            else:
                all_passed    = False
                error_report += f"Diff Error → {path}: {result.get('error')}\\n" """
new_sr_fail = """            else:
                telemetry.record_tool_call("patch", False, _t_latency)
                all_passed    = False
                error_report += f"Diff Error → {path}: {result.get('error')}\\n" """
content = content.replace(old_sr_fail, new_sr_fail)

# Patch SHELL RUN
old_shell = """            console.print(f"[bold white on #1e3a8a] SHELL RUN [/bold white on #1e3a8a] [green]$ {cmd}[/green]")
            try:
                import subprocess
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=sandbox_cwd if sandbox_cwd else None)"""
new_shell = """            console.print(f"[bold white on #1e3a8a] SHELL RUN [/bold white on #1e3a8a] [green]$ {cmd}[/green]")
            try:
                import subprocess
                _t0 = time.time()
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=sandbox_cwd if sandbox_cwd else None)
                _t_latency = time.time() - _t0"""
content = content.replace(old_shell, new_shell)

old_shell_score = """                score = ToolSuccessScorer.evaluate_shell(res.stdout, res.stderr)
                
                if res.returncode == 0 and score.success:"""
new_shell_score = """                score = ToolSuccessScorer.evaluate_shell(res.stdout, res.stderr)
                telemetry.record_tool_call("shell", score.success, _t_latency)
                
                if res.returncode == 0 and score.success:"""
content = content.replace(old_shell_score, new_shell_score)

old_shell_timeout = """            except subprocess.TimeoutExpired:"""
new_shell_timeout = """            except subprocess.TimeoutExpired:
                telemetry.record_tool_call("shell", False, 15.0)"""
content = content.replace(old_shell_timeout, new_shell_timeout)

old_shell_exc = """            except Exception as exc:
                all_passed    = False"""
new_shell_exc = """            except Exception as exc:
                telemetry.record_tool_call("shell", False, time.time() - _t0)
                all_passed    = False"""
content = content.replace(old_shell_exc, new_shell_exc)

with open("nabdcode/core/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

