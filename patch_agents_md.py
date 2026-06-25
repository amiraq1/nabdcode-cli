import os
with open("nabdcode/core/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add AGENTS.md injection to CodeReviewerAgent
reviewer_skill_code = """        skill_path = os.path.join(os.getcwd(), "SKILL.md")
        if os.path.exists(skill_path):
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    skill_content = f.read()
                sys_prompt += f"\\n\\n[PROJECT SKILL RULES/IDENTITY]\\n{skill_content}"
            except Exception:
                pass"""

reviewer_agents_code = reviewer_skill_code + """
        
        agents_md_path = os.path.join(os.getcwd(), "AGENTS.md")
        if os.path.exists(agents_md_path):
            try:
                with open(agents_md_path, "r", encoding="utf-8") as f:
                    agents_content = f.read()
                sys_prompt += f"\\n\\n[PROJECT KNOWLEDGE INDEX (AGENTS.md)]\\n{agents_content}\\nIf reviewing complex architectural changes, ensure they align with the documentation mapped above."
            except Exception:
                pass"""

content = content.replace(reviewer_skill_code, reviewer_agents_code)

# Add AGENTS.md injection to CodeWriterAgent (process_request)
writer_skill_code = """        skill_path = os.path.join(os.getcwd(), "SKILL.md")
        if os.path.exists(skill_path):
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    skill_content = f.read()
                system_prompt += f"\\n\\n[PROJECT SKILL RULES/IDENTITY]\\n{skill_content}"
                console.print("[dim cyan]📎 Injected SKILL.md into context.[/dim cyan]")
            except Exception as e:
                pass"""

writer_agents_code = writer_skill_code + """
        
        agents_md_path = os.path.join(os.getcwd(), "AGENTS.md")
        if os.path.exists(agents_md_path):
            try:
                with open(agents_md_path, "r", encoding="utf-8") as f:
                    agents_content = f.read()
                system_prompt += f"\\n\\n[PROJECT KNOWLEDGE INDEX (AGENTS.md)]\\n{agents_content}\\n(Use the <<< READ: path/to/doc >>> block to dynamically fetch detailed context from docs/ if your task touches these domains)."
                console.print("[dim cyan]📎 Injected AGENTS.md Knowledge Bridge.[/dim cyan]")
            except Exception as e:
                pass"""

content = content.replace(writer_skill_code, writer_agents_code)

with open("nabdcode/core/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

