import sys
with open("temp_dump.txt", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

code = []
capture = False
for line in lines:
    if line.startswith("1: ") and '"""' in line:
        capture = True
    if line.startswith("The above content shows the entire, complete file contents"):
        capture = False
    
    if capture:
        parts = line.split(": ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            code.append(parts[1])
        else:
            code.append(line[line.find(": ")+2:])

with open("nabdcode/core/agent.py", "w", encoding="utf-8") as f:
    f.write("\n".join(code))
