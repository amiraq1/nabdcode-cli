"""
nabdcode/core/agent.py
نواة الوكيل الذكي — REAct loop مع text-based file mutations,
auto-correction, وحماية syntax بـ py_compile، ودعم القراءة التلقائية الذاتية.
"""
import asyncio
import logging
import py_compile
import re
import sys
import subprocess
import time
import os
from typing import Any, Dict, List, Optional, Tuple
from nabdcode.core.tool_scorer import ToolSuccessScorer
from nabdcode.core.telemetry import telemetry

from rich.console import Console
from rich.live import Live
from rich.markup import escape
from rich.text import Text

from nabdcode.core.file_tool import NabdFileEngine
from nabdcode.core.message_healer import (
    limit_context,
    merge_consecutive_same_role,
    validate_tool_messages,
)
from nabdcode.core.context_manager import ContextWindowManager
from nabdcode.core.streaming_parser import NabdStreamingThinkParser
from nabdcode.core.web_search import search_internet

class NabdWebSearch:
    @staticmethod
    def search(query: str) -> str:
        return search_internet(query)

console = Console(file=sys.__stdout__)
logger  = logging.getLogger(__name__)

# ── ثوابت ────────────────────────────────────────────────────────────────────
MAX_CORRECTION_ATTEMPTS = 5

_CONVERSATIONAL_TRIGGERS = frozenset({
    "hi", "hello", "hey", "who are you", "thanks",
    "thank you", "ok", "okay", "مرحبا", "شكرا", "اهلا"
})

_HIDDEN_MARKERS = frozenset({
    "<<< FILE_WRITE:", "<<< SEARCH_REPLACE:", "<<< READ:", "<<< WEB_SEARCH:", "<<< SHELL >>>", "<<< SHELL_END >>>",
    "<<<<<<< SEARCH", "=======", ">>>>>>> REPLACE", "<<< FILE_END >>>", ">>>"
})

_SYSTEM_PROMPT = (
    "You are Nabd OS, an elite autonomous AI agent inside Termux. "
    "You have full system authority to mutate files.\n\n"

    "Choose the correct block based on the scenario:\n\n"

    "1. FOR NEW FILES:\n"
    "<<< FILE_WRITE: path/file.py >>>\n"
    "complete code here\n"
    "<<< FILE_END >>>\n\n"

    "2. FOR EXISTING FILES (PREFERRED — preserves architecture):\n"
    "If you don't know the exact file structure, you MUST issue a READ block first to fetch it:\n"
    "<<< READ: path/file.py >>>\n"
    "Once you have the content, use the SEARCH_REPLACE block:\n"
    "<<< SEARCH_REPLACE: path/file.py >>>\n"
    "<<<<<<< SEARCH\n"
    "exact old code block\n"
    "=======\n"
    "new code block\n"
    ">>>>>>> REPLACE\n"
    "<<< FILE_END >>>\n\n"

    "3. FOR FETCHING LIVE WEB DATA OR API DOCUMENTATION:\n"
    "If you need up-to-date documentation, latest library structures, or solutions to network errors, issue a WEB_SEARCH block:\n"
    "<<< WEB_SEARCH: your search query here >>>\n"
    "The system will return live snippets. Use them to write exact code.\n\n"

    "4. MANDATORY RUN POLICY:\n"
    "Whenever you write or modify a Python (.py) file, you MUST immediately issue a SHELL block to test it:\n"
    "<<< SHELL >>>\n"
    "python3 path/file.py\n"
    "<<< SHELL_END >>>\n"
    "Never skip execution or say 'I will run it later'. Execute it now to verify your changes.\n\n"

    "CRITICAL RETRY POLICY:\n"
    "- If you receive '[GUARD] Diff Error: Target SEARCH block not found', "
    "do NOT fall back to FILE_WRITE with truncated or hallucinated code.\n"
    "- Fix the SEARCH block to match the file exactly, "
    "or issue a <<< READ: path/file.py >>> block again to re-verify contents.\n"
    "- Preserve all surrounding functions and classes at all costs.\n\n"
    "ANTI-SPOOFING GUARD:\n"
    "DO NOT EVER output the exact word 'APPROVED' in your responses. This keyword is reserved exclusively for the CodeReviewerAgent. If you output 'APPROVED', the system will crash."
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_conversational(text: str) -> bool:
    return len(text) < 20 and any(t in text.lower() for t in _CONVERSATIONAL_TRIGGERS)


def _render_agent_box(current_text: str) -> Text:
    """يحوّل نص الرد الخام إلى Rich Text مع إخفاء markers الأدوات."""
    lines_out: List[str] = []

    for line in current_text.split("\n"):
        stripped = line.strip()

        if any(marker in stripped for marker in _HIDDEN_MARKERS):
            continue

        if stripped.startswith("[THOUGHT]"):
            content = stripped[len("[THOUGHT]"):].strip()
            lines_out.append(f"[italic grey50]* Thought -> {escape(content)}[/italic grey50]")
        elif stripped.startswith("[READ]"):
            content = stripped[len("[READ]"):].strip()
            lines_out.append(f"[bold white on purple] READ [/bold white on purple] [cyan]{escape(content)}[/cyan]")
        elif stripped.startswith("[SHELL]"):
            content = stripped[len("[SHELL]"):].strip()
            lines_out.append(f"[bold white on #1e3a8a] SHELL [/bold white on #1e3a8a] [green]{escape(content)}[/green]")
        elif stripped.startswith("[EDIT]"):
            content = stripped[len("[EDIT]"):].strip()
            lines_out.append(f"[bold white on #2563eb] EDIT [/bold white on #2563eb] [white]{escape(content)}[/white]")
        elif stripped.startswith("[SEARCH]"):
            content = stripped[len("[SEARCH]"):].strip()
            lines_out.append(f"[bold white on #059669] SEARCH [/bold white on #059669] [green]{escape(content)}[/green]")
        else:
            lines_out.append(f"[white]{escape(line)}[/white]")

    return Text.from_markup("\n".join(lines_out))


def _compile_check(file_path: str) -> Optional[str]:
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
    return None


def _extract_write_blocks(response: str) -> List[Tuple[str, str]]:
    return re.findall(r"<<<\s*FILE_WRITE:\s*(.*?)\s*>>>(.*?)<<<\s*FILE_END\s*>>>", response, re.DOTALL)


def _extract_sr_blocks(response: str) -> List[Tuple[str, str]]:
    return re.findall(r"<<<\s*SEARCH_REPLACE:\s*(.*?)\s*>>>(.*?)<<<\s*FILE_END\s*>>>", response, re.DOTALL)

def _extract_read_blocks(response: str) -> List[str]:
    return re.findall(r"<<<\s*READ:\s*(.*?)\s*>>>", response, re.DOTALL)

def _extract_shell_blocks(response: str) -> List[str]:
    return re.findall(r"<<<\s*SHELL\s*>>>(.*?)<<<\s*SHELL_END\s*>>>", response, re.DOTALL)

def _extract_search_blocks(response: str) -> List[str]:
    return re.findall(r"<<<\s*WEB_SEARCH:\s*(.*?)\s*>>>", response, re.DOTALL)



# ── الوكلاء الفرعيون ──────────────────────────────────────────────────────────

class CodeWriterAgent:
    def __init__(self, provider):
        self.provider = provider
        
    async def generate_stream(self, pipeline, cfg, *args):
        async for item in self.provider.generate_stream(pipeline, cfg, *args):
            yield item

class CodeReviewerAgent:
    def __init__(self):
        from nabdcode.core.model_manager import ModelManager
        self.model = ModelManager()

    async def review(self, task: str, modified_files: List[str], shell_outputs: List[Tuple[str, str]], sandbox_cwd: Optional[str] = None) -> Tuple[bool, str]:
        if not modified_files and not shell_outputs:
            return True, ""
            
        console.print("\n[bold purple]🧐 CodeReviewerAgent: Inspecting the changes...[/bold purple]")
        
        content = f"Original Task: {task}\n\n"
        if modified_files:
            content += "Modified Files:\n"
            for path in set(modified_files):
                actual_path = os.path.join(sandbox_cwd, path) if sandbox_cwd else path
                if os.path.exists(actual_path):
                    try:
                        with open(actual_path, "r", encoding="utf-8") as f:
                            content += f"--- {path} ---\n{f.read()}\n\n"
                    except Exception as e:
                        content += f"--- {path} (Error reading: {e}) ---\n\n"
                        
        if shell_outputs:
            content += "Shell Execution Outputs:\n"
            for cmd, out in shell_outputs:
                content += f"$ {cmd}\n{out}\n\n"
                
        sys_prompt = (
            "You are CodeReviewerAgent, a strict AI code reviewer. "
            "Review the modifications and shell execution outputs against the original task.\n"
            "If the implementation perfectly solves the task with NO logic errors, syntax errors, or unhandled edge cases, reply EXACTLY with: 'APPROVED'.\n"
            "If there are any issues, bugs, or the task is incomplete, reply with 'REJECTED: ' followed by a concise, critical bug report for the CodeWriterAgent to fix."
        )
        
        skill_path = os.path.join(os.getcwd(), "SKILL.md")
        if os.path.exists(skill_path):
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    skill_content = f.read()
                sys_prompt += f"\n\n[PROJECT SKILL RULES/IDENTITY]\n{skill_content}"
            except Exception:
                pass
        
        try:
            resp = await self.model.generate_response_async(
                system_prompt=sys_prompt,
                messages=[{"role": "user", "content": content}],
                temperature=0.1,
                max_tokens=800
            )
            resp = resp.strip()
            if resp.startswith("APPROVED") or resp == "APPROVED":
                console.print("[bold green]✔ CodeReviewerAgent: APPROVED changes.[/bold green]")
                return True, ""
            else:
                console.print(f"[bold red]❌ CodeReviewerAgent: REJECTED.[/bold red] {resp[:150]}...")
                return False, resp
        except Exception as e:
            console.print(f"[bold yellow]⚠️ CodeReviewerAgent unavailable: {e}. Bypassing review.[/bold yellow]")
            return True, ""

# ── الوكيل ────────────────────────────────────────────────────────────────────


class NabdAgent:
    def __init__(self, provider: Any, registry: Any = None) -> None:
        self.provider = provider
        self.writer = CodeWriterAgent(provider)
        self.reviewer = CodeReviewerAgent()
        self.registry = registry

    async def _stream_response(self, messages: List[Dict[str, Any]], cfg: Any) -> str:
        optimal_messages = ContextWindowManager.build_optimal_context(messages, recent_limit=6)
        pipeline = validate_tool_messages(optimal_messages)
        parser         = NabdStreamingThinkParser()
        response_parts: List[str] = []

        console.print("[bold green]🚀 Starting reactive generation...[/bold green]\n")

        with Live(_render_agent_box(""), refresh_per_second=10, console=console) as live:
            def _update(chunk: str) -> None:
                response_parts.append(chunk)
                live.update(_render_agent_box("".join(response_parts)))

            async for item in self.writer.generate_stream(pipeline, cfg, None):
                if item.get("type") == "content":
                    parser.feed(item.get("chunk", ""), getattr(cfg, "thinking_enabled", False), _update, lambda x: None)
            parser.flush(_update, lambda x: None)
            live.update(_render_agent_box("".join(response_parts)))

        return "".join(response_parts)

    def _apply_mutations(self, response: str, messages: List[Dict[str, Any]], sandbox_cwd: Optional[str] = None) -> Tuple[bool, str, List[str], List[Tuple[str, str]]]:
        def _resolve(p): return os.path.join(sandbox_cwd, p) if sandbox_cwd else p
        write_blocks  = _extract_write_blocks(response)
        sr_blocks     = _extract_sr_blocks(response)
        read_blocks   = _extract_read_blocks(response)
        shell_blocks  = _extract_shell_blocks(response)
        search_blocks = _extract_search_blocks(response)

        if not write_blocks and not sr_blocks and not read_blocks and not shell_blocks and not search_blocks:
            return True, "", [], []

        modified_files = []
        shell_out_data = []

        # ── 🚨 فخ التفتيش والتشغيل الإجباري (Mandatory Execution Guard) ──────────────────
        # إذا تم كشف عملية كتابة أو تعديل لملف بايثون، ولم يتم إرفاق أمر تشغيل Shell
        has_python_mutation = any(p.endswith(".py") for p, _ in write_blocks) or any(p.endswith(".py") for p, _ in sr_blocks)
        if has_python_mutation and not shell_blocks:
            console.print("\n[bold white on #b91c1c] 🚫 EXECUTION GUARD ALERT [/bold white on #b91c1c] [red]Model tried to skip testing the code![/red]")
            return False, "[GUARD] Procedural Error: You wrote/modified Python code but failed to provide a <<< SHELL >>> execution block. You MUST execute the script using a SHELL block to verify there are no ModuleNotFoundError or syntax collapses.", modified_files, shell_out_data

        console.print("\n[bold yellow]⚡ Executing physical code mutations & tools...[/bold yellow]")
        all_passed   = True
        error_report = ""

        # ── 1. بروتوكول القراءة الآلية (Automated READ Protocol) ─────────────────
        for raw_path in read_blocks:
            path = raw_path.strip()
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                    console.print(f"[bold white on purple] READ AUTO [/bold white on purple] [bold green]✔ Loaded -> {path}[/bold green]")
                    # حقن البيانات في الجلسة وإجبار النواة على إكمال الدورة في المحاولة التالية
                    messages.append({
                        "role": "user",
                        "content": f"[SYSTEM FEEDBACK] Read successful. Here is the current content of '{path}':\n\n{file_content}\n\nNow issue your SEARCH_REPLACE block based on this state."
                    })
                    all_passed = False # لضمان استمرار الـ Auto-Correction Loop
                except Exception as exc:
                    all_passed    = False
                    error_report += f"Read Error → {path}: {exc}\n"
            else:
                all_passed    = False
                error_report += f"Read Error → {path}: File does not exist\n"

        # ── 1.5 WEB_SEARCH ───────────────────────────────────────────────────
        for raw_query in search_blocks:
            query = raw_query.strip()
            if not query:
                continue
                
            console.print(f"[bold white on #0d9488] WEB SEARCH [/bold white on #0d9488] [cyan]🔍 Searching for: '{query}'[/cyan]")
            try:
                from nabdcode.core.web_search import search_internet
                search_results_str = search_internet(query)
                
                # صياغة تقرير المخرجات لحقنه في ذاكرة الجلسة
                feedback = f"[SYSTEM FEEDBACK] Web search results for '{query}':\n\n{search_results_str}\n\n"
                
                console.print(f"[bold green]✔ Search Done.[/bold green]")
                
                # إرجاع المخرجات للنموذج وإجبار الحلقة على الاستمرار لتحليل البيانات
                messages.append({
                    "role": "user",
                    "content": feedback + "Now analyze these results and write/modify the code accordingly."
                })
                all_passed = False # لمواصلة حلقة التصحيح الذاتي والتوليد
            except Exception as exc:
                all_passed = False
                error_report += f"Web Search Exception: {str(exc)}\n"

        # ── 2. FILE_WRITE ────────────────────────────────────────────────────
        for raw_path, code in write_blocks:
            path   = raw_path.strip()
            modified_files.append(path)
            
            _t0 = time.time()
            result = NabdFileEngine.safe_write(_resolve(path), code.strip())
            _t_latency = time.time() - _t0

            if result.get("success"):
                err = _compile_check(_resolve(path))
                if err:
                    all_passed    = False
                    error_report += f"Syntax Error in new file '{path}': {err}\n"
                    console.print(f"[bold white on red] GUARD [/bold white on red] [bold red]❌ Syntax Error → {path}: {err}[/bold red]")
                else:
                    console.print(f"[bold white on green] GUARD [/bold white on green] [bold green]✔ Created → {path}[/bold green]")
            else:
                all_passed    = False
                error_report += f"Write Error → {path}: {result.get('error')}\n"

        # ── 3. SEARCH_REPLACE ────────────────────────────────────────────────
        for raw_path, block in sr_blocks:
            path  = raw_path.strip()
            modified_files.append(path)
            match = re.search(r"<<<<<<<\s*SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>>\s*REPLACE", block, re.DOTALL)

            if not match:
                all_passed    = False
                error_report += f"Critical: Invalid SEARCH/REPLACE block format for {path}\n"
                console.print(f"[bold white on red] DIFF ERROR [/bold white on red] [red]Failed to parse block for {path}[/red]")
                continue

            search_str, replace_str = match.group(1), match.group(2)
            
            _t0 = time.time()
            result = NabdFileEngine.apply_search_replace(_resolve(path), search_str, replace_str)
            _t_latency = time.time() - _t0

            if result.get("success"):
                err = _compile_check(_resolve(path))
                if err:
                    all_passed    = False
                    error_report += f"Syntax Error after patch '{path}': {err}\n"
                    console.print(f"[bold white on red] GUARD [/bold white on red] [bold red]❌ Patch Syntax Error → {path}: {err}[/bold red]")
                else:
                    console.print(f"[bold white on green] GUARD [/bold white on green] [bold green]✔ Patch Applied → {path}[/bold green]")
            else:
                all_passed    = False
                error_report += f"Diff Error → {path}: {result.get('error')}\n"

        # ── 4. SHELL RUN ─────────────────────────────────────────────────────
        for raw_cmd in shell_blocks:
            cmd = raw_cmd.strip()
            if not cmd:
                continue
            console.print(f"[bold white on #1e3a8a] SHELL RUN [/bold white on #1e3a8a] [green]$ {cmd}[/green]")
            try:
                import subprocess
                _t0 = time.time()
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20, cwd=sandbox_cwd if sandbox_cwd else None)
                _t_latency = time.time() - _t0
                shell_out_data.append((cmd, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"))
                
                score = ToolSuccessScorer.evaluate_shell(res.stdout, res.stderr)
                telemetry.record_tool_call("shell", score.success, _t_latency)
                
                if res.returncode == 0 and score.success:
                    if score.confidence < 1.0:
                        console.print(f"[bold black on yellow] SCORE: {score.confidence} [/bold black on yellow] [yellow]⚠️ {score.message}[/yellow]")
                        error_report += f"Shell Warning '{cmd}': {score.message}\nSTDERR: {res.stderr}\n"
                    else:
                        console.print(f"[bold white on green] SCORE: {score.confidence} [/bold white on green] [bold green]✔ {score.message}[/bold green]\n[grey70]{res.stdout.strip()}[/grey70]")
                        
                    # توثيق Git Checkpoint خفي عند النجاح الكامل
                    subprocess.run(f"git add . && git commit -m 'NabdCode: Auto-checkpoint - [Success] Shell command executed'", shell=True, capture_output=True, cwd=sandbox_cwd if sandbox_cwd else None)
                    console.print("[grey50]📁 Git Checkpoint Created[/grey50]")
                else:
                    all_passed    = False
                    error_report += f"Runtime Error in command '{cmd}' (Confidence {score.confidence}):\n{score.message}\n{res.stderr}\n"
                    console.print(f"[bold white on red] SCORE: {score.confidence} [/bold white on red] [red]{res.stderr.strip()}[/red]")
            except subprocess.TimeoutExpired:
                telemetry.record_tool_call("shell", False, 20.0)
                all_passed    = False
                error_report += f"[SYSTEM WATCHDOG KILL] Command '{cmd}' exceeded strict 20s execution limit.\n"
                console.print("\n[blink bold white on red] 🚨 WATCHDOG ALERT: SILENT STALL DETECTED [/blink bold white on red]")
                console.print(f"[bold red]❌ Execution aborted: Command exceeded 20s hard limit.[/bold red]\n")
            except Exception as exc:
                telemetry.record_tool_call("shell", False, time.time() - _t0)
                all_passed    = False
                error_report += f"Execution Exception: {str(exc)}\n"

        return all_passed, error_report, modified_files, shell_out_data

    async def process_request(self, text: str, cfg: Any) -> None:
        text = text.strip()
        if not text:
            return

        # ── 1. Intent Routing (Prioritizing Chat vs Agentic) ──
        from nabdcode.core.intent_router import IntentRouter, TaskType
        intent = IntentRouter.classify(text)
        
        if not IntentRouter.should_use_tool(intent):
            console.print(f"[bold cyan]💬 [Pure Chat Mode] Intent: {intent.name}[/bold cyan]")
            from nabdcode.core.model_manager import SecureModelManager
            mm = SecureModelManager()
            try:
                response = await mm.generate_response_async(
                    system_prompt="You are NabdCode, an expert coding assistant. Answer the user's question directly, clearly, and concisely without attempting to invoke any external file or terminal tools. Provide pure knowledge and code examples.",
                    messages=[{"role": "user", "content": text}],
                    temperature=0.7,
                )
                console.print(f"\n[bold green]✅ Response:[/bold green]\n{response}")
            except Exception as exc:
                console.print(f"[bold red]❌ Error: {exc}[/bold red]")
            return
            
        allowed_tools = IntentRouter.get_allowed_tools(intent)
        console.print(f"[bold cyan]🧠 [Agentic Loop] Intent: {intent.name} | Allowed Tools: {', '.join(allowed_tools)}[/bold cyan]")


        console.print(f"[bold cyan]🧠 [Processing]: {text[:60]}...[/bold cyan]")

        system_prompt = _SYSTEM_PROMPT
        
        skill_path = os.path.join(os.getcwd(), "SKILL.md")
        if os.path.exists(skill_path):
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    skill_content = f.read()
                system_prompt += f"\n\n[PROJECT SKILL RULES/IDENTITY]\n{skill_content}"
                console.print("[dim cyan]📎 Injected SKILL.md into context.[/dim cyan]")
            except Exception as e:
                pass

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": text},
        ]
        
        from nabdcode.core.worktree import NabdWorktreeManager
        base_dir = os.getcwd()
        repo_root = None
        sandbox_path = None
        sandbox_cwd = None
        
        git_check = subprocess.run("git rev-parse --show-toplevel", shell=True, capture_output=True, text=True)
        if git_check.returncode == 0:
            repo_root = git_check.stdout.strip()
            try:
                sandbox_path = NabdWorktreeManager.create_sandbox(repo_root)
                rel_path = os.path.relpath(base_dir, repo_root)
                sandbox_cwd = os.path.join(sandbox_path, rel_path) if rel_path != "." else sandbox_path
                console.print(f"[bold cyan]🌱 NabdWorktreeManager:[/bold cyan] Isolated environment active.")
            except Exception as e:
                console.print(f"[yellow]⚠️ Could not create sandbox: {e}[/yellow]")


        for attempt in range(MAX_CORRECTION_ATTEMPTS):
            if attempt > 0:
                console.print(f"\n[bold yellow]🔄 [Auto-Correction Loop]: Attempt {attempt + 1}/{MAX_CORRECTION_ATTEMPTS}...[/bold yellow]")

            try:
                response = await self._stream_response(messages, cfg)
            except Exception as exc:
                console.print(f"\n[bold red]❌ Generation Error: {exc}[/bold red]")
                return

            # تمرير الـ messages لـ _apply_mutations لتمكين التغذية العكسية للقراءة والأدوات
            all_passed, error_report, modified_files, shell_out_data = self._apply_mutations(response, messages, sandbox_cwd)

            if all_passed:
                if modified_files or shell_out_data:
                    rev_passed, rev_feedback = await self.reviewer.review(text, modified_files, shell_out_data, sandbox_cwd)
                    if not rev_passed:
                        all_passed = False
                        error_report = f"[CodeReviewerAgent REJECTION]\n{rev_feedback}\nPlease fix the issues mentioned by the reviewer."
                        
            if all_passed:
                if sandbox_path and repo_root:
                    console.print("[bold green]🔄 Merging sandbox changes into main...[/bold green]")
                    try:
                        NabdWorktreeManager.commit_and_merge(repo_root, sandbox_path)
                        console.print("[bold green]✔ Changes successfully merged.[/bold green]")
                    except Exception as e:
                        console.print(f"[bold red]❌ Sandbox merge failed: {e}[/bold red]")
                break
                
            if attempt == 3:
                console.print(f"\n[bold yellow]⚠️ Anti-Stall Ping-Pong Tracker Alert![/bold yellow]")
                console.print(f"[red]The agent has reached attempt 4/{MAX_CORRECTION_ATTEMPTS} without Reviewer approval.[/red]")
                user_choice = console.input("[cyan]Action required (Ammar): [M]odify Prompt / [P]ass Manually / [S]top Loop ? [/cyan]").strip().lower()
                if user_choice == 'p':
                    console.print("[green]Passing manually...[/green]")
                    if sandbox_path and repo_root:
                        try:
                            NabdWorktreeManager.commit_and_merge(repo_root, sandbox_path)
                        except Exception as e:
                            console.print(f"[bold red]❌ Sandbox merge failed: {e}[/bold red]")
                    break
                elif user_choice == 's':
                    console.print("[red]Loop stopped by user.[/red]")
                    if sandbox_path and repo_root:
                        NabdWorktreeManager.remove_sandbox(repo_root, sandbox_path)
                    return
                elif user_choice == 'm':
                    new_prompt = console.input("[cyan]Enter new instructions to guide the agent: [/cyan]")
                    error_report += f"\n[USER INTERVENTION]: {new_prompt}"


            # إذا لم تكن هناك أخطاء مسجلة ولكن all_passed=False (حالة قراءة ناجحة)، نقوم بحقن الرد فقط لمواصلة الحلقة
            if not error_report:
                messages.append({"role": "assistant", "content": response})
                continue

            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": f"[GUARD] Validation Failed:\n{error_report}\nFollow the retry policy strictly. Do NOT wipe file logic.",
            })
        else:
            console.print(f"\n[bold red]❌ Guard Alert: Max correction attempts ({MAX_CORRECTION_ATTEMPTS}) reached.[/bold red]")

        if sandbox_path and repo_root:
            try:
                NabdWorktreeManager.remove_sandbox(repo_root, sandbox_path)
                console.print("[dim]🗑️ Sandbox removed.[/dim]")
            except Exception as e:
                pass

        console.print("\n[bold green]🎯 Done.[/bold green]")

    def index_workspace(self, *args: Any, **kwargs: Any) -> None: pass
    @property
    def llm_client(self) -> Any: return self.provider
