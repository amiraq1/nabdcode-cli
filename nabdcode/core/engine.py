import json
import os
import time
from typing import Dict, Any, List, Optional
from rich.console import Console

console = Console()


class SemanticMemory:
    """إدارة الذاكرة الدلالية (Semantic Memory) لاسترجاع السياق المعرفي بدلاً من الاعتماد على التاريخ الخام"""
    def __init__(self):
        self.embeddings = {}  # Placeholder for vector embeddings
        
    def retrieve_context(self, task: str) -> str:
        console.print("[dim cyan]🧠 SemanticMemory: Retrieving relevant past context...[/dim cyan]")
        return "Relevant architectural decisions from past tasks."

class ToolSelector:
    """توجيه صارم للأدوات (Strict Tool Routing) لمنع التشتت والعبث خارج النطاق"""
    def __init__(self, all_tools: List[str]):
        self.all_tools = all_tools

    def select_tools_for_task(self, intent_type) -> List[str]:
        console.print("[dim cyan]🛠️ ToolSelector: Enforcing Strict Routing Rules...[/dim cyan]")
        from nabdcode.core.intent_router import TaskType
        if intent_type == TaskType.FILE:
            console.print("[bold red]🔒 SHELL LOCKED[/bold red] [green]FILE TOOLS GRANTED[/green]")
            return ["FILE_WRITE", "SEARCH_REPLACE", "READ"]
        elif intent_type == TaskType.RUN:
            return ["SHELL_RUN", "READ"]
        elif intent_type == TaskType.QA:
            return ["WEB_SEARCH", "READ"]
        return self.all_tools

class ActionVerifier:
    """مُدقق فوري بعد التنفيذ (Action Verifier) للتحقق من سلامة الأداة قبل إرجاع النتيجة"""
    def verify_action(self, action_result: str) -> bool:
        console.print("[dim purple]🛡️ ActionVerifier: Checking execution integrity...[/dim purple]")
        return "error" not in action_result.lower()

class ProjectSpecKit:
    """نظام مواصفات (Spec-Kit) للمشاريع الكبيرة لفرض الهيكلية العامة"""
    @staticmethod
    def load_specs() -> str:
        console.print("[dim cyan]📐 Spec-Kit: Loading global project specifications...[/dim cyan]")
        return "Strict MVC architecture, 100% test coverage required."

class StateMemory:
    """إدارة حالة الوكيل لمنع البدايات الباردة (State Persistence)"""
    def __init__(self, filepath: str = ".nabd_state.json"):
        self.filepath = filepath
        self.state: Dict[str, Any] = {
            "history": [],
            "backlog": [],
            "completed_tasks": [],
            "last_updated": time.time()
        }
        self.load()

    def load(self) -> None:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception as e:
                console.print(f"[yellow]⚠️ Failed to load state memory: {e}[/yellow]")

    def save(self) -> None:
        self.state["last_updated"] = time.time()
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=4, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red]❌ Failed to save state memory: {e}[/red]")

    def add_history(self, role: str, content: str) -> None:
        self.state["history"].append({"role": role, "content": content, "timestamp": time.time()})
        self.save()


class GoalVerification:
    """وكيل المراجعة الحتمي (Grader/Reviewer) المعتمد على العقود الفيزيائية بدلاً من النماذج"""
    def __init__(self, model_manager: Any):
        self.model = model_manager

    async def generate_contract(self, goal: str) -> "GoalContract":
        """يستدعي الموديل مرة واحدة لاستخلاص العقد الحتمي"""
        console.print("[bold purple]📜 GoalVerification: Drafting physical Goal Contract via LLM...[/bold purple]")
        from nabdcode.core.contract import GoalContract
        import re, json
        
        sys_prompt = (
            "You are a strict Goal Contract Generator. Extract the user's objective into a pure JSON contract. "
            "Structure MUST be: {\"files_must_exist\": [\"path\"], \"shell_must_pass\": \"cmd\", \"text_must_exist\": {\"path\": \"text\"}}.\n"
            "Only output the JSON."
        )
        try:
            resp = await self.model.generate_response_async(
                system_prompt=sys_prompt,
                messages=[{"role": "user", "content": goal}],
                temperature=0.1,
                max_tokens=300
            )
            json_str = resp
            match = re.search(r"```json\s*(.*?)\s*```", resp, re.DOTALL)
            if match:
                json_str = match.group(1)
            data = json.loads(json_str)
            return GoalContract(data)
        except Exception as e:
            console.print(f"[yellow]⚠️ Fast LLM Contract drafting failed: {e}. Using empty fallback.[/yellow]")
            return GoalContract({})

    async def verify(self, contract: "GoalContract", sandbox_cwd: str = None) -> tuple[bool, str]:
        from nabdcode.core.contract import DeterministicVerifier
        return DeterministicVerifier.verify(contract, sandbox_cwd)


class ReActEngine:
    """محرك الحلقة المغلقة (Thought -> Action -> Observation)"""
    def __init__(self, model_manager: Any, max_loops: int = 5):
        self.model = model_manager
        self.state_memory = StateMemory()
        self.semantic_memory = SemanticMemory()
        self.tool_selector = ToolSelector(["FILE_WRITE", "SEARCH_REPLACE", "SHELL_RUN", "WEB_SEARCH"])
        self.action_verifier = ActionVerifier()
        self.goal_verifier = GoalVerification(model_manager)
        self.max_loops = max_loops

    async def execute_loop(self, goal: str) -> bool:
        console.print(f"\n[bold cyan]🔄 Initializing Closed-Loop Engine for:[/bold cyan] {goal}")
        
        self.state_memory.add_history("user", f"GOAL: {goal}")
        
        # 1. Spec-Kit & Semantic Memory
        project_specs = ProjectSpecKit.load_specs()
        semantic_context = self.semantic_memory.retrieve_context(goal)
        
        # صياغة العقد قبل دخول الحلقة (Contract Drafting)
        contract = await self.goal_verifier.generate_contract(goal)
        
        # 2. Tool Selector (Minimize exposed tools)
        active_tools = self.tool_selector.select_tools_for_task(goal)
        console.print(f"[dim]🔧 Active Tools: {', '.join(active_tools)}[/dim]")
        
        for iteration in range(1, self.max_loops + 1):
            console.print(f"\n[bold yellow]🔁 ReAct Loop Iteration {iteration}/{self.max_loops}[/bold yellow]")
            
            # Thought & Action (Model with restricted tools)
            action_plan = await self._generate_thought_and_action()
            self.state_memory.add_history("assistant", action_plan)
            
            # Observation (Execution)
            raw_observation = self._execute_actions(action_plan)
            
            # 3. Action Verifier (Immediate post-tool check)
            if not self.action_verifier.verify_action(raw_observation):
                raw_observation += "\n[SYSTEM WARNING]: Action failed structural verification."
                
            self.state_memory.add_history("system", f"OBSERVATION:\n{raw_observation}")
            
            # Goal Verification (Deterministic Physical Check)
            is_approved, error_report = await self.goal_verifier.verify(contract, sandbox_cwd=None)
            
            if is_approved:
                console.print("\n[bold green]🎯 Goal Contract fully verified. Exiting loop.[/bold green]")
                self.state_memory.state["completed_tasks"].append(goal)
                self.state_memory.save()
                return True
                
        console.print(f"\n[bold red]❌ Max iterations ({self.max_loops}) reached without absolute approval.[/bold red]")
        return False

    async def _generate_thought_and_action(self) -> str:
        # Mocking generation for architectural representation
        console.print("[dim cyan]🧠 ReAct: Generating Thought and determining Action...[/dim cyan]")
        return "Thought: Analyzing current state.\nAction: Executing command."

    def _execute_actions(self, action_plan: str) -> str:
        # Mocking physical execution observation
        console.print("[dim blue]🛠️ ReAct: Executing action and recording Observation...[/dim blue]")
        return "Command executed successfully. No errors reported."
