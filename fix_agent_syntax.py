import re

with open("nabdcode/core/agent.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.startswith("class NabdWebSearch:"):
        # We need to remove the broken un-indented class definition
        pass
    new_lines.append(line)

with open("nabdcode/core/agent.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
