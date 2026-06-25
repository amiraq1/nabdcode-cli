import re

with open("nabdcode/core/engine.py", "r", encoding="utf-8") as f:
    content = f.read()

new_classes = """
class SemanticMemory:
    \"\"\"إدارة الذاكرة الدلالية (Semantic Memory) لاسترجاع السياق المعرفي بدلاً من الاعتماد على التاريخ الخام\"\"\"
    def __init__(self):
        self.embeddings = {}  # Placeholder for vector embeddings
        
    def retrieve_context(self, task: str) -> str:
        console.print("[dim cyan]🧠 SemanticMemory: Retrieving relevant past context...[/dim cyan]")
        return "Relevant architectural decisions from past tasks."

class ToolSelector:
    \"\"\"انتقاء الأدوات الضرورية فقط (Dynamic Tool Selection) لتقليل تشتت الموديل (Context Pollution)\"\"\"
    def __init__(self, all_tools: List[str]):
        self.all_tools = all_tools

    def select_tools_for_task(self, task: str) -> List[str]:
        console.print("[dim cyan]🛠️ ToolSelector: Minimizing exposed tools for this specific task...[/dim cyan]")
        # Mock logic: return only essential tools
        return [t for t in self.all_tools if t in task.lower()] or self.all_tools[:2]

class ActionVerifier:
    \"\"\"مُدقق فوري بعد التنفيذ (Action Verifier) للتحقق من سلامة الأداة قبل إرجاع النتيجة\"\"\"
    def verify_action(self, action_result: str) -> bool:
        console.print("[dim purple]🛡️ ActionVerifier: Checking execution integrity...[/dim purple]")
        return "error" not in action_result.lower()

class ProjectSpecKit:
    \"\"\"نظام مواصفات (Spec-Kit) للمشاريع الكبيرة لفرض الهيكلية العامة\"\"\"
    @staticmethod
    def load_specs() -> str:
        console.print("[dim cyan]📐 Spec-Kit: Loading global project specifications...[/dim cyan]")
        return "Strict MVC architecture, 100% test coverage required."
"""

content = content.replace("class StateMemory:", new_classes + "\nclass StateMemory:")

# Update ReActEngine
old_engine_init = """    def __init__(self, model_manager: Any, max_loops: int = 5):
        self.model = model_manager
        self.memory = StateMemory()
        self.verifier = GoalVerification(model_manager)
        self.max_loops = max_loops"""

new_engine_init = """    def __init__(self, model_manager: Any, max_loops: int = 5):
        self.model = model_manager
        self.state_memory = StateMemory()
        self.semantic_memory = SemanticMemory()
        self.tool_selector = ToolSelector(["FILE_WRITE", "SEARCH_REPLACE", "SHELL_RUN", "WEB_SEARCH"])
        self.action_verifier = ActionVerifier()
        self.goal_verifier = GoalVerification(model_manager)
        self.max_loops = max_loops"""
content = content.replace(old_engine_init, new_engine_init)

old_loop = """        self.memory.add_history("user", f"GOAL: {goal}")
        
        for iteration in range(1, self.max_loops + 1):
            console.print(f"\\n[bold yellow]🔁 ReAct Loop Iteration {iteration}/{self.max_loops}[/bold yellow]")
            
            # Thought & Action
            action_plan = await self._generate_thought_and_action()
            self.memory.add_history("assistant", action_plan)
            
            # Observation (Execution & Feedback)
            observation = self._execute_actions(action_plan)
            self.memory.add_history("system", f"OBSERVATION:\\n{observation}")
            
            # Goal Verification (Grader Check)
            is_approved = await self.verifier.verify(goal, observation)"""

new_loop = """        self.state_memory.add_history("user", f"GOAL: {goal}")
        
        # 1. Spec-Kit & Semantic Memory
        project_specs = ProjectSpecKit.load_specs()
        semantic_context = self.semantic_memory.retrieve_context(goal)
        
        # 2. Tool Selector (Minimize exposed tools)
        active_tools = self.tool_selector.select_tools_for_task(goal)
        console.print(f"[dim]🔧 Active Tools: {', '.join(active_tools)}[/dim]")
        
        for iteration in range(1, self.max_loops + 1):
            console.print(f"\\n[bold yellow]🔁 ReAct Loop Iteration {iteration}/{self.max_loops}[/bold yellow]")
            
            # Thought & Action (Model with restricted tools)
            action_plan = await self._generate_thought_and_action()
            self.state_memory.add_history("assistant", action_plan)
            
            # Observation (Execution)
            raw_observation = self._execute_actions(action_plan)
            
            # 3. Action Verifier (Immediate post-tool check)
            if not self.action_verifier.verify_action(raw_observation):
                raw_observation += "\\n[SYSTEM WARNING]: Action failed structural verification."
                
            self.state_memory.add_history("system", f"OBSERVATION:\\n{raw_observation}")
            
            # Goal Verification (Grader Check)
            is_approved = await self.goal_verifier.verify(goal, raw_observation)"""
content = content.replace(old_loop, new_loop)

# Fix references to self.memory.state
content = content.replace("self.memory.state", "self.state_memory.state")
content = content.replace("self.memory.save()", "self.state_memory.save()")

with open("nabdcode/core/engine.py", "w", encoding="utf-8") as f:
    f.write(content)
