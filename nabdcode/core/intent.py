import re
from nabdcode.core.llm_client import GenerationContext

def classify_intent(user_message: str) -> GenerationContext:
    text = user_message.lower()
    
    # 1. CHAT
    chat_patterns = [r'\b(hi|hello|hey|how are you|thanks)\b', r'(كيف|مرحبا|اهلا|شكرا)']
    if any(re.search(p, text) for p in chat_patterns) and len(text) < 50:
        return GenerationContext(shell_enabled=False, web_search_enabled=False)
        
    # 2. SEARCH
    search_patterns = [r'\b(search|find|latest|news|who|what|where|how to)\b', r'(ابحث|من هو|ما هو|كيف)']
    if any(re.search(p, text) for p in search_patterns):
        return GenerationContext(shell_enabled=False, web_search_enabled=True)
        
    # 3. CODING
    coding_patterns = [r'\b(code|script|function|class|bug|fix|error|compile)\b', r'(كود|برمجة|دالة|خطأ)']
    if any(re.search(p, text) for p in coding_patterns):
        return GenerationContext(shell_enabled=True, web_search_enabled=False)
        
    # 4. TOOL / SYSTEM
    tool_patterns = [r'\b(install|pip|npm|git|clone|commit|push)\b', r'(تثبيت|حزمة)']
    if any(re.search(p, text) for p in tool_patterns):
        return GenerationContext(shell_enabled=True, web_search_enabled=True)
        
    # 5. AGENT / GENERAL
    return GenerationContext(shell_enabled=True, web_search_enabled=True)
