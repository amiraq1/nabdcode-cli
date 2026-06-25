import json
import os
import subprocess
from typing import Dict, List, Any
from rich.console import Console

console = Console()

class GoalContract:
    """عقد الهدف الحتمي الذي يجب الوفاء به قبل الاعتماد"""
    def __init__(self, contract_data: Dict[str, Any]):
        self.files_must_exist: List[str] = contract_data.get("files_must_exist", [])
        self.shell_must_pass: str = contract_data.get("shell_must_pass", "")
        self.text_must_exist: Dict[str, str] = contract_data.get("text_must_exist", {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files_must_exist": self.files_must_exist,
            "shell_must_pass": self.shell_must_pass,
            "text_must_exist": self.text_must_exist
        }

class DeterministicVerifier:
    """محرك التحقق الحتمي: لا يعتمد على هلوسات النموذج، بل على وجود فيزيائي للأدلة"""
    
    @staticmethod
    def verify(contract: GoalContract, sandbox_cwd: str = None) -> tuple[bool, str]:
        console.print("\n[bold purple]⚖️ Deterministic Verification: Enforcing Goal Contract...[/bold purple]")
        
        errors = []
        
        # 1. التحقق من وجود الملفات
        for filepath in contract.files_must_exist:
            target = os.path.join(sandbox_cwd, filepath) if sandbox_cwd else filepath
            if not os.path.exists(target):
                errors.append(f"Missing mandatory file: {filepath}")
                
        # 2. التحقق من وجود نصوص معينة (مثل أسماء الكلاسات أو الدوال المطلوبة)
        for filepath, required_text in contract.text_must_exist.items():
            target = os.path.join(sandbox_cwd, filepath) if sandbox_cwd else filepath
            if os.path.exists(target):
                try:
                    with open(target, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if required_text not in content:
                            errors.append(f"Required text '{required_text}' not found in {filepath}")
                except Exception as e:
                    errors.append(f"Failed to read {filepath} for text verification: {e}")
            else:
                errors.append(f"Cannot check text in missing file: {filepath}")
                
        # 3. التحقق الفيزيائي من أوامر الـ Shell (مثل نجاح الاختبارات)
        if contract.shell_must_pass:
            console.print(f"[dim]Running physical verification command: {contract.shell_must_pass}[/dim]")
            try:
                res = subprocess.run(
                    contract.shell_must_pass, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    cwd=sandbox_cwd if sandbox_cwd else None
                )
                if res.returncode != 0:
                    errors.append(f"Mandatory shell test failed. STDERR: {res.stderr.strip()[:100]}")
                elif "Ran 0 tests" in res.stderr or "Ran 0 tests" in res.stdout:
                    errors.append("Mandatory shell test passed but 'Ran 0 tests' detected (False Positive).")
            except Exception as e:
                errors.append(f"Failed to execute verification command: {e}")
                
        if not errors:
            console.print("[bold green]✔ Deterministic Verification: PASSED (100% Contract Fulfillment).[/bold green]")
            return True, "Goal Contract verified physically."
        else:
            error_report = "\n".join([f" - {err}" for err in errors])
            console.print(f"[bold red]❌ Deterministic Verification: FAILED.[/bold red]\n{error_report}")
            return False, error_report
