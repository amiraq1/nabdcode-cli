import os
import re

with open("nabdcode/core/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("MAX_CORRECTION_ATTEMPTS = 3", "MAX_CORRECTION_ATTEMPTS = 5")

sp_old = "    \"- Preserve all surrounding functions and classes at all costs.\"\n)"
sp_new = """    "- Preserve all surrounding functions and classes at all costs.\\n\\n"
    "ANTI-SPOOFING GUARD:\\n"
    "DO NOT EVER output the exact word 'APPROVED' in your responses. This keyword is reserved exclusively for the CodeReviewerAgent. If you output 'APPROVED', the system will crash."
)"""
content = content.replace(sp_old, sp_new)

agents_code = """
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
            
        console.print("\\n[bold purple]🧐 CodeReviewerAgent: Inspecting the changes...[/bold purple]")
        
        content = f"Original Task: {task}\\n\\n"
        if modified_files:
            content += "Modified Files:\\n"
            for path in set(modified_files):
                actual_path = os.path.join(sandbox_cwd, path) if sandbox_cwd else path
                if os.path.exists(actual_path):
                    try:
                        with open(actual_path, "r", encoding="utf-8") as f:
                            content += f"--- {path} ---\\n{f.read()}\\n\\n"
                    except Exception as e:
                        content += f"--- {path} (Error reading: {e}) ---\\n\\n"
                        
        if shell_outputs:
            content += "Shell Execution Outputs:\\n"
            for cmd, out in shell_outputs:
                content += f"$ {cmd}\\n{out}\\n\\n"
                
        sys_prompt = (
            "You are CodeReviewerAgent, a strict AI code reviewer. "
            "Review the modifications and shell execution outputs against the original task.\\n"
            "If the implementation perfectly solves the task with NO logic errors, syntax errors, or unhandled edge cases, reply EXACTLY with: 'APPROVED'.\\n"
            "If there are any issues, bugs, or the task is incomplete, reply with 'REJECTED: ' followed by a concise, critical bug report for the CodeWriterAgent to fix."
        )
        
        skill_path = os.path.join(os.getcwd(), "SKILL.md")
        if os.path.exists(skill_path):
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    skill_content = f.read()
                sys_prompt += f"\\n\\n[PROJECT SKILL RULES/IDENTITY]\\n{skill_content}"
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
"""
content = content.replace("# ── الوكيل ────────────────────────────────────────────────────────────────────", agents_code)

content = content.replace("def __init__(self, provider: Any, registry: Any = None) -> None:\n        self.provider = provider", "def __init__(self, provider: Any, registry: Any = None) -> None:\n        self.provider = provider\n        self.writer = CodeWriterAgent(provider)\n        self.reviewer = CodeReviewerAgent()")

content = content.replace("async for item in self.provider.generate_stream(pipeline, cfg, None):", "async for item in self.writer.generate_stream(pipeline, cfg, None):")

old_apply_def = '    def _apply_mutations(self, response: str, messages: List[Dict[str, Any]]) -> Tuple[bool, str]:\n        """يطبّق كتل التعديل، والأوامر، وقراءة الملفات مع التغذية الراجعة الذاتية للتكامل المفتوح."""'
new_apply_def = '    def _apply_mutations(self, response: str, messages: List[Dict[str, Any]], sandbox_cwd: Optional[str] = None) -> Tuple[bool, str, List[str], List[Tuple[str, str]]]:\n        def _resolve(p): return os.path.join(sandbox_cwd, p) if sandbox_cwd else p\n        write_blocks  = _extract_write_blocks(response)\n        sr_blocks     = _extract_sr_blocks(response)\n        read_blocks   = _extract_read_blocks(response)\n        shell_blocks  = _extract_shell_blocks(response)\n        search_blocks = _extract_search_blocks(response)\n\n        if not write_blocks and not sr_blocks and not read_blocks and not shell_blocks and not search_blocks:\n            return True, "", [], []\n\n        modified_files = []\n        shell_out_data = []\n'
content = content.replace('    def _apply_mutations(self, response: str, messages: List[Dict[str, Any]]) -> Tuple[bool, str]:\n        """يطبّق كتل التعديل، والأوامر، وقراءة الملفات مع التغذية الراجعة الذاتية للتكامل المفتوح."""\n        write_blocks  = _extract_write_blocks(response)\n        sr_blocks     = _extract_sr_blocks(response)\n        read_blocks   = _extract_read_blocks(response)\n        shell_blocks  = _extract_shell_blocks(response)\n        search_blocks = _extract_search_blocks(response)\n\n        if not write_blocks and not sr_blocks and not read_blocks and not shell_blocks and not search_blocks:\n            return True, ""\n', new_apply_def)

content = content.replace("return False, \"[GUARD] Procedural Error", "return False, \"[GUARD] Procedural Error")
content = content.replace("or syntax collapses.\"", "or syntax collapses.\", modified_files, shell_out_data")

content = content.replace("for raw_path, code in write_blocks:\n            path   = raw_path.strip()\n            result = NabdFileEngine.safe_write(path, code.strip())", "for raw_path, code in write_blocks:\n            path   = raw_path.strip()\n            modified_files.append(path)\n            result = NabdFileEngine.safe_write(_resolve(path), code.strip())")
content = content.replace("err = _compile_check(path)", "err = _compile_check(_resolve(path))")

content = content.replace("for raw_path, block in sr_blocks:\n            path  = raw_path.strip()\n            match = re.search(r\"<<<<<<<\\s*SEARCH\\n(.*?)\\n=======\\n(.*?)\\n>>>>>>>\\s*REPLACE\", block, re.DOTALL)", "for raw_path, block in sr_blocks:\n            path  = raw_path.strip()\n            modified_files.append(path)\n            match = re.search(r\"<<<<<<<\\s*SEARCH\\n(.*?)\\n=======\\n(.*?)\\n>>>>>>>\\s*REPLACE\", block, re.DOTALL)")
content = content.replace("result = NabdFileEngine.apply_search_replace(path, search_str, replace_str)", "result = NabdFileEngine.apply_search_replace(_resolve(path), search_str, replace_str)")

content = content.replace("res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)", "res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=sandbox_cwd if sandbox_cwd else None)\n                shell_out_data.append((cmd, f\"STDOUT:\\n{res.stdout}\\nSTDERR:\\n{res.stderr}\"))")

content = content.replace("return all_passed, error_report", "return all_passed, error_report, modified_files, shell_out_data")

old_process = '    async def process_request(self, text: str, cfg: Any) -> None:\n        text = text.strip()\n        if not text:\n            return\n\n        if _is_conversational(text):\n            console.print(f"[bold cyan]💬 [Conversational Mode]: {text}[/bold cyan]")\n            from nabdcode.core.model_manager import ModelManager\n            mm = ModelManager()\n            try:\n                response = await mm.generate_response_async(\n                    system_prompt="You are NabdCode. Answer briefly and directly.",\n                    messages=[{"role": "user", "content": text}],\n                    temperature=0.6,\n                )\n                console.print(f"\\n[bold green]✅ Response:[/bold green] {response}")\n            except Exception as exc:\n                console.print(f"[bold red]❌ Error: {exc}[/bold red]")\n            return\n\n        console.print(f"[bold cyan]🧠 [Processing]: {text[:60]}...[/bold cyan]")\n\n        messages: List[Dict[str, Any]] = [\n            {"role": "system", "content": _SYSTEM_PROMPT},\n            {"role": "user",   "content": text},\n        ]'

new_process = """    async def process_request(self, text: str, cfg: Any) -> None:
        text = text.strip()
        if not text:
            return

        if _is_conversational(text):
            console.print(f"[bold cyan]💬 [Conversational Mode]: {text}[/bold cyan]")
            from nabdcode.core.model_manager import ModelManager
            mm = ModelManager()
            try:
                response = await mm.generate_response_async(
                    system_prompt="You are NabdCode. Answer briefly and directly.",
                    messages=[{"role": "user", "content": text}],
                    temperature=0.6,
                )
                console.print(f"\\n[bold green]✅ Response:[/bold green] {response}")
            except Exception as exc:
                console.print(f"[bold red]❌ Error: {exc}[/bold red]")
            return

        console.print(f"[bold cyan]🧠 [Processing]: {text[:60]}...[/bold cyan]")

        system_prompt = _SYSTEM_PROMPT
        
        skill_path = os.path.join(os.getcwd(), "SKILL.md")
        if os.path.exists(skill_path):
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    skill_content = f.read()
                system_prompt += f"\\n\\n[PROJECT SKILL RULES/IDENTITY]\\n{skill_content}"
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
"""
content = content.replace(old_process, new_process)

content = content.replace("all_passed, error_report = self._apply_mutations(response, messages)", "all_passed, error_report, modified_files, shell_out_data = self._apply_mutations(response, messages, sandbox_cwd)")

content = content.replace('if all_passed:\n                break', """if all_passed:
                if modified_files or shell_out_data:
                    rev_passed, rev_feedback = await self.reviewer.review(text, modified_files, shell_out_data, sandbox_cwd)
                    if not rev_passed:
                        all_passed = False
                        error_report = f"[CodeReviewerAgent REJECTION]\\n{rev_feedback}\\nPlease fix the issues mentioned by the reviewer."
                        
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
                console.print(f"\\n[bold yellow]⚠️ Anti-Stall Ping-Pong Tracker Alert![/bold yellow]")
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
                    error_report += f"\\n[USER INTERVENTION]: {new_prompt}"
""")

# replace final done block with cleanup
content = content.replace("""        else:\n            console.print(f\"\\n[bold red]❌ Guard Alert: Max correction attempts ({MAX_CORRECTION_ATTEMPTS}) reached.[/bold red]\")\n\n        console.print(\"\\n[bold green]🎯 Done.[/bold green]\")""", """        else:\n            console.print(f\"\\n[bold red]❌ Guard Alert: Max correction attempts ({MAX_CORRECTION_ATTEMPTS}) reached.[/bold red]\")\n\n        if sandbox_path and repo_root:\n            try:\n                NabdWorktreeManager.remove_sandbox(repo_root, sandbox_path)\n                console.print("[dim]🗑️ Sandbox removed.[/dim]")\n            except Exception as e:\n                pass\n\n        console.print(\"\\n[bold green]🎯 Done.[/bold green]\")""")

with open("nabdcode/core/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

