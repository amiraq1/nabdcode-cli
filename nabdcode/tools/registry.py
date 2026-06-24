class ToolRegistry:
    def __init__(self, *args, **kwargs): pass
    def get_definitions(self, *args, **kwargs): return []
    def dispatch(self, *args, **kwargs): return {"success": False, "error": "No tools available"}
    def set_memory_manager(self, *args, **kwargs): pass
