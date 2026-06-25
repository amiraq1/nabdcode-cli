import re

with open("nabdcode/core/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the old _is_conversational logic with the IntentRouter
old_conversational = """        if _is_conversational(text):
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
            return"""

new_router_logic = """        # ── 1. Intent Routing (Prioritizing Chat vs Agentic) ──
        from nabdcode.core.intent_router import IntentRouter, TaskType
        intent = IntentRouter.classify(text)
        
        if not IntentRouter.should_use_tool(intent):
            console.print(f"[bold cyan]💬 [Pure Chat Mode] Intent: {intent.name}[/bold cyan]")
            from nabdcode.core.model_manager import ModelManager
            mm = ModelManager()
            try:
                response = await mm.generate_response_async(
                    system_prompt="You are NabdCode, an expert coding assistant. Answer the user's question directly, clearly, and concisely without attempting to invoke any external file or terminal tools. Provide pure knowledge and code examples.",
                    messages=[{"role": "user", "content": text}],
                    temperature=0.7,
                )
                console.print(f"\\n[bold green]✅ Response:[/bold green]\\n{response}")
            except Exception as exc:
                console.print(f"[bold red]❌ Error: {exc}[/bold red]")
            return
            
        allowed_tools = IntentRouter.get_allowed_tools(intent)
        console.print(f"[bold cyan]🧠 [Agentic Loop] Intent: {intent.name} | Allowed Tools: {', '.join(allowed_tools)}[/bold cyan]")
"""
content = content.replace(old_conversational, new_router_logic)

with open("nabdcode/core/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

