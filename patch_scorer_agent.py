import re

with open("nabdcode/core/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Import the scorer
if "from nabdcode.core.tool_scorer import ToolSuccessScorer" not in content:
    content = content.replace("from typing import Any, Dict, List, Optional, Tuple", "from typing import Any, Dict, List, Optional, Tuple\nfrom nabdcode.core.tool_scorer import ToolSuccessScorer")

# Patch FILE_WRITE
old_write = """        for raw_path, code in write_blocks:
            path   = raw_path.strip()
            modified_files.append(path)
            result = NabdFileEngine.safe_write(_resolve(path), code.strip())

            if result.get("success"):
                err = _compile_check(_resolve(path))
                if err:
                    all_passed    = False
                    error_report += f"Syntax Error in new file '{path}': {err}\\n"
                    console.print(f"[bold white on red] GUARD [/bold white on red] [bold red]❌ Syntax Error → {path}: {err}[/bold red]")
                else:
                    console.print(f"[bold white on green] GUARD [/bold white on green] [bold green]✔ Created → {path}[/bold green]")
            else:
                all_passed    = False
                error_report += f"Write Error → {path}: {result.get('error')}\\n" """

new_write = """        for raw_path, code in write_blocks:
            path   = raw_path.strip()
            modified_files.append(path)
            result = NabdFileEngine.safe_write(_resolve(path), code.strip())

            if result.get("success"):
                err = _compile_check(_resolve(path))
                # --- Tool Success Scoring ---
                score = ToolSuccessScorer.evaluate_file_write(path, len(code.strip()), err)
                if not score.success:
                    all_passed    = False
                    error_report += f"Tool Scoring Failed (Confidence {score.confidence}): {score.message}\\n"
                    console.print(f"[bold white on red] SCORE: {score.confidence} [/bold white on red] [bold red]❌ {score.message}[/bold red]")
                else:
                    console.print(f"[bold white on green] SCORE: {score.confidence} [/bold white on green] [bold green]✔ Created → {path}[/bold green]")
            else:
                all_passed    = False
                error_report += f"Write Error → {path}: {result.get('error')}\\n" """
content = content.replace(old_write, new_write)

# Patch SEARCH_REPLACE
old_sr = """        for raw_path, block in sr_blocks:
            path  = raw_path.strip()
            modified_files.append(path)
            match = re.search(r"<<<<<<<\\s*SEARCH\\n(.*?)\\n=======\\n(.*?)\\n>>>>>>>\\s*REPLACE", block, re.DOTALL)

            if not match:
                all_passed    = False
                error_report += f"Critical: Invalid SEARCH/REPLACE block format for {path}\\n"
                console.print(f"[bold white on red] DIFF ERROR [/bold white on red] [red]Failed to parse block for {path}[/red]")
                continue

            search_str, replace_str = match.group(1), match.group(2)
            result = NabdFileEngine.apply_search_replace(_resolve(path), search_str, replace_str)

            if result.get("success"):
                err = _compile_check(_resolve(path))
                if err:
                    all_passed    = False
                    error_report += f"Syntax Error after patch '{path}': {err}\\n"
                    console.print(f"[bold white on red] GUARD [/bold white on red] [bold red]❌ Patch Syntax Error → {path}: {err}[/bold red]")
                else:
                    console.print(f"[bold white on green] GUARD [/bold white on green] [bold green]✔ Patch Applied → {path}[/bold green]")
            else:
                all_passed    = False
                error_report += f"Diff Error → {path}: {result.get('error')}\\n" """

new_sr = """        for raw_path, block in sr_blocks:
            path  = raw_path.strip()
            modified_files.append(path)
            match = re.search(r"<<<<<<<\\s*SEARCH\\n(.*?)\\n=======\\n(.*?)\\n>>>>>>>\\s*REPLACE", block, re.DOTALL)

            if not match:
                all_passed    = False
                error_report += f"Critical: Invalid SEARCH/REPLACE block format for {path}\\n"
                console.print(f"[bold white on red] DIFF ERROR [/bold white on red] [red]Failed to parse block for {path}[/red]")
                continue

            search_str, replace_str = match.group(1), match.group(2)
            result = NabdFileEngine.apply_search_replace(_resolve(path), search_str, replace_str)

            if result.get("success"):
                err = _compile_check(_resolve(path))
                score = ToolSuccessScorer.evaluate_patch(search_str, result.get("content", ""), err)
                if not score.success:
                    all_passed    = False
                    error_report += f"Patch Error (Confidence {score.confidence}): {score.message}\\n"
                    console.print(f"[bold white on red] SCORE: {score.confidence} [/bold white on red] [bold red]❌ {score.message}[/bold red]")
                else:
                    if score.confidence < 0.8:
                        error_report += f"Warning: Patch applied with low confidence ({score.confidence}): {score.message}\\n"
                        console.print(f"[bold black on yellow] SCORE: {score.confidence} [/bold black on yellow] [yellow]⚠️ {score.message}[/yellow]")
                    else:
                        console.print(f"[bold white on green] SCORE: {score.confidence} [/bold white on green] [bold green]✔ Patch Applied → {path}[/bold green]")
            else:
                all_passed    = False
                error_report += f"Diff Error → {path}: {result.get('error')}\\n" """
content = content.replace(old_sr, new_sr)

# Patch SHELL RUN
old_shell = """        for raw_cmd in shell_blocks:
            cmd = raw_cmd.strip()
            if not cmd:
                continue
            console.print(f"[bold white on #1e3a8a] SHELL RUN [/bold white on #1e3a8a] [green]$ {cmd}[/green]")
            try:
                import subprocess
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=sandbox_cwd if sandbox_cwd else None)
                shell_out_data.append((cmd, f"STDOUT:\\n{res.stdout}\\nSTDERR:\\n{res.stderr}"))
                if res.returncode == 0:
                    console.print(f"[bold green]✔ Success:[/bold green]\\n[grey70]{res.stdout.strip()}[/grey70]")
                    # توثيق Git Checkpoint خفي عند النجاح الكامل
                    subprocess.run(f"git add {path} && git commit -m 'NabdCode: Auto-checkpoint - [Success] mutated {path}'", shell=True, capture_output=True)
                    console.print("[grey50]📁 Git Checkpoint Created[/grey50]")
                else:
                    all_passed    = False
                    error_report += f"Runtime Error in command '{cmd}':\\n{res.stderr}\\n"
                    console.print(f"[bold white on red] RUNTIME ERROR [/bold white on red]\\n[red]{res.stderr.strip()}[/red]")
            except subprocess.TimeoutExpired:"""

new_shell = """        for raw_cmd in shell_blocks:
            cmd = raw_cmd.strip()
            if not cmd:
                continue
            console.print(f"[bold white on #1e3a8a] SHELL RUN [/bold white on #1e3a8a] [green]$ {cmd}[/green]")
            try:
                import subprocess
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=sandbox_cwd if sandbox_cwd else None)
                shell_out_data.append((cmd, f"STDOUT:\\n{res.stdout}\\nSTDERR:\\n{res.stderr}"))
                
                score = ToolSuccessScorer.evaluate_shell(res.stdout, res.stderr)
                
                if res.returncode == 0 and score.success:
                    if score.confidence < 1.0:
                        console.print(f"[bold black on yellow] SCORE: {score.confidence} [/bold black on yellow] [yellow]⚠️ {score.message}[/yellow]")
                        error_report += f"Shell Warning '{cmd}': {score.message}\\nSTDERR: {res.stderr}\\n"
                    else:
                        console.print(f"[bold white on green] SCORE: {score.confidence} [/bold white on green] [bold green]✔ {score.message}[/bold green]\\n[grey70]{res.stdout.strip()}[/grey70]")
                        
                    # توثيق Git Checkpoint خفي عند النجاح الكامل
                    subprocess.run(f"git add . && git commit -m 'NabdCode: Auto-checkpoint - [Success] Shell command executed'", shell=True, capture_output=True, cwd=sandbox_cwd if sandbox_cwd else None)
                    console.print("[grey50]📁 Git Checkpoint Created[/grey50]")
                else:
                    all_passed    = False
                    error_report += f"Runtime Error in command '{cmd}' (Confidence {score.confidence}):\\n{score.message}\\n{res.stderr}\\n"
                    console.print(f"[bold white on red] SCORE: {score.confidence} [/bold white on red] [red]{res.stderr.strip()}[/red]")
            except subprocess.TimeoutExpired:"""
content = content.replace(old_shell, new_shell)

with open("nabdcode/core/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

