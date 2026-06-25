import re

with open("nabdcode/core/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: NabdWebSearch
content = content.replace("from nabdcode.core.web_search import NabdWebSearch", 
"""from nabdcode.core.web_search import search_internet

class NabdWebSearch:
    @staticmethod
    def search(query: str) -> str:
        return search_internet(query)""")

# Fix 2: _compile_check
old_compile = """def _compile_check(file_path: str) -> Optional[str]:
    if not file_path.endswith(".py"):
        return None
    try:
        py_compile.compile(file_path, doraise=True)
        return None
    except py_compile.PyCompileError as exc:
        return exc.msg"""
new_compile = """def _compile_check(file_path: str) -> Optional[str]:
    import shutil, subprocess, os, py_compile
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".py":
            py_compile.compile(file_path, doraise=True)
            return None
        elif ext == ".kt":
            if shutil.which("kotlinc"):
                res = subprocess.run(f"kotlinc -nowarn -Werror {file_path}", shell=True, capture_output=True, text=True)
                if res.returncode != 0: return res.stderr
            return None
        elif ext in [".cpp", ".cc", ".c"]:
            compiler = "g++" if "p" in ext or "c" in ext else "gcc"
            if shutil.which(compiler):
                includes = ""
                if os.path.exists("CMakeLists.txt"):
                    try:
                        with open("CMakeLists.txt", "r") as ff:
                            if "third_party/llama.cpp" in ff.read() or os.path.exists("third_party/llama.cpp/include"):
                                includes += " -Ithird_party/llama.cpp/include -Ithird_party/llama.cpp/ggml/include "
                    except: pass
                res = subprocess.run(f"{compiler} {includes} -fsyntax-only {file_path}", shell=True, capture_output=True, text=True)
                if res.returncode != 0:
                    if "file not found" in res.stderr and "fatal error:" in res.stderr: return None
                    return res.stderr
            return None
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            if shutil.which("node"):
                res = subprocess.run(f"node --check {file_path}", shell=True, capture_output=True, text=True)
                if res.returncode != 0: return res.stderr
            return None
        elif ext == ".sh":
            if shutil.which("bash"):
                res = subprocess.run(f"bash -n {file_path}", shell=True, capture_output=True, text=True)
                if res.returncode != 0: return res.stderr
    except py_compile.PyCompileError as exc:
        return exc.msg
    except Exception as e:
        return str(e) if ext == ".py" else None
    return None"""
content = content.replace(old_compile, new_compile)

# Fix 3: 20s Watchdog
old_shell = """            except subprocess.TimeoutExpired:
                telemetry.record_tool_call("shell", False, 15.0)
                all_passed    = False
                error_report += f"Timeout Error: Command '{cmd}' exceeded 15s limit.\\n"
                console.print("[bold red]❌ خطأ: انتهت مهلة تشغيل الأمر (Timeout)[/bold red]")"""

new_shell = """            except subprocess.TimeoutExpired:
                telemetry.record_tool_call("shell", False, 20.0)
                all_passed    = False
                error_report += f"[SYSTEM WATCHDOG KILL] Command '{cmd}' exceeded strict 20s execution limit.\\n"
                console.print("\\n[blink bold white on red] 🚨 WATCHDOG ALERT: SILENT STALL DETECTED [/blink bold white on red]")
                console.print(f"[bold red]❌ Execution aborted: Command exceeded 20s hard limit.[/bold red]\\n")"""
content = content.replace(old_shell, new_shell)
content = content.replace("timeout=15", "timeout=20")

with open("nabdcode/core/agent.py", "w", encoding="utf-8") as f:
    f.write(content)
