import re

with open("nabdcode/core/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the import from message_healer
content = content.replace(
    "from nabdcode.core.message_healer import (\n    limit_context,\n    merge_consecutive_same_role,\n    validate_tool_messages,\n)",
    "from nabdcode.core.message_healer import (\n    limit_context,\n    merge_consecutive_same_role,\n    validate_tool_messages,\n)\nfrom nabdcode.core.context_manager import ContextWindowManager"
)
# If it's on one line
content = content.replace(
    "from nabdcode.core.message_healer import limit_context, merge_consecutive_same_role, validate_tool_messages",
    "from nabdcode.core.message_healer import limit_context, merge_consecutive_same_role, validate_tool_messages\nfrom nabdcode.core.context_manager import ContextWindowManager"
)

# Update the context limiting inside _stream_response
old_pipeline = "pipeline = validate_tool_messages(merge_consecutive_same_role(limit_context(messages, MAX_CONTEXT_MESSAGES)))"
new_pipeline = "optimal_messages = ContextWindowManager.build_optimal_context(messages, recent_limit=6)\n        pipeline = validate_tool_messages(optimal_messages)"
content = content.replace(old_pipeline, new_pipeline)

# Remove unused MAX_CONTEXT_MESSAGES
content = content.replace("MAX_CONTEXT_MESSAGES    = 25\n", "")

with open("nabdcode/core/agent.py", "w", encoding="utf-8") as f:
    f.write(content)
