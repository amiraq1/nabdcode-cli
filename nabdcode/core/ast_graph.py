"""
nabdcode/core/ast_graph.py
محرك الفهرسة البنيوية الخفيف يعتمد على AST (Abstract Syntax Tree)
يقوم بمسح ملفات بايثون وبناء خريطة شجرية للكلاسات والدوال لتوفير التوكنز ومنح الموديل وعياً معمارياً.
"""
import ast
import os
from typing import Dict, Any, List
from rich.console import Console

from nabdcode.core.ignore_manager import ignore_checker

console = Console()

class ASTGraphEngine:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = os.path.abspath(workspace_root)
        self.graph: Dict[str, Any] = {}

    def _parse_file(self, file_path: str) -> Dict[str, Any]:
        """يحلل ملف بايثون ويستخرج الكلاسات والدوال بدقة وسرعة."""
        file_map = {"classes": [], "functions": [], "imports": []}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=file_path)
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    methods = []
                    for n in node.body:
                        if isinstance(n, ast.FunctionDef) or isinstance(n, ast.AsyncFunctionDef):
                            methods.append(n.name)
                    
                    class_info = {
                        "name": node.name,
                        "methods": methods
                    }
                    file_map["classes"].append(class_info)
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    file_map["functions"].append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        file_map["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        file_map["imports"].append(node.module)

        except SyntaxError:
            file_map["error"] = "Syntax Error"
        except Exception as e:
            file_map["error"] = str(e)
            
        return file_map

    def build_graph(self) -> Dict[str, Any]:
        """يمسح بيئة العمل بالكامل متجاوزاً الملفات والمجلدات المحظورة."""
        self.graph.clear()
        
        for root, dirs, files in os.walk(self.workspace_root):
            # إزالة المجلدات المحظورة مباشرة من عملية البحث لتسريع الأداء وتوفير البطارية
            dirs[:] = [d for d in dirs if not ignore_checker.is_ignored(os.path.join(root, d))]
            
            for file in files:
                if not file.endswith(".py"):
                    continue
                    
                file_path = os.path.join(root, file)
                if ignore_checker.is_ignored(file_path):
                    continue
                    
                rel_path = os.path.relpath(file_path, self.workspace_root).replace("\\", "/")
                self.graph[rel_path] = self._parse_file(file_path)
                
        return self.graph
        
    def get_summary_text(self) -> str:
        """يولد نصاً مضغوطاً وجاهزاً للحقن في الـ System Prompt ليكون كخريطة ذهنية للموديل."""
        if not self.graph:
            return ""
            
        lines = ["\n[WORKSPACE AST GRAPH] (Use this to know exactly which file to SEARCH_REPLACE without reading everything):"]
        for file, data in sorted(self.graph.items()):
            if "error" in data:
                continue
            
            classes = [f"{c['name']}({','.join(c['methods'])})" for c in data.get("classes", [])]
            funcs = data.get("functions", [])
            
            if not classes and not funcs:
                continue
                
            line = f"📄 {file} -> "
            if classes:
                line += f"Classes: {', '.join(classes)}. "
            if funcs:
                line += f"Funcs: {', '.join(funcs)}."
            lines.append(line)
            
        return "\n".join(lines)

# مثيل عام للاستخدام المتكرر لتقليل استهلاك الذاكرة
graph_engine = ASTGraphEngine()
