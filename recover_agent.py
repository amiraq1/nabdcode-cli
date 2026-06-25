import json

found = False
with open("/data/data/com.termux/files/home/.gemini/antigravity-cli/brain/83546499-394a-4542-a0a8-dcb0d044f412/.system_generated/logs/transcript_full.jsonl", "r") as f:
    for line in f:
        data = json.loads(line)
        if data.get("type") in ["TOOL_RESPONSE", "RUN_COMMAND", "VIEW_FILE"]:
            content = data.get("content", "")
            if "Showing lines 1 to 386" in content:
                with open("temp_dump.txt", "w", encoding="utf-8") as out:
                    out.write(content)
                found = True
                print("Found!")
                break
if not found:
    print("Not found.")
