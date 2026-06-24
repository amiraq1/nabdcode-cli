import ast
import re
import os
from nabdcode.core.logger import logger

class CodeIndexer:
    @staticmethod
    def extract_structure(filepath):
        """تحليل هيكلية الكود (AST/Regex) لاستخراج الكلاسات والدوال متعددة اللغات"""
        ext = os.path.splitext(filepath)[1].lower()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            if ext == '.py':
                tree = ast.parse(content)
                structure = []
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        structure.append(f"Class: {node.name}")
                    elif isinstance(node, ast.FunctionDef):
                        structure.append(f"Function: {node.name}")
                return "\n".join(structure)
            
            elif ext in ('.kt', '.kts'):
                pattern = r'^\s*(class|fun|interface|object)\s+([a-zA-Z0-9_]+)'
                structure = [f"{'Class' if m.group(1) in ('class', 'interface', 'object') else 'Function'}: {m.group(2)}" 
                             for m in re.finditer(pattern, content, re.MULTILINE)]
                return "\n".join(structure)
                
            elif ext in ('.cpp', '.cc', '.cxx', '.hpp', '.h', '.hxx', '.c'):
                pattern = r'^\s*(class|struct|void|int|float|double|bool|auto|string)\s+([a-zA-Z0-9_]+)\s*(\([^)]*\)|\{{|\:)'
                structure = []
                for m in re.finditer(pattern, content, re.MULTILINE):
                    typ = m.group(1)
                    name = m.group(2)
                    if typ in ['class', 'struct']:
                        structure.append(f"Class: {name}")
                    else:
                        structure.append(f"Function: {name}")
                return "\n".join(structure)
                
            elif ext in ('.js', '.jsx', '.ts', '.tsx'):
                # دعم كلاسات ودوال جافاسكريبت وتايب سكريبت
                structure = []
                # 1. استخراج الكلاسات: export class Name { ...
                class_pattern = r'^\s*(?:export\s+)?class\s+([a-zA-Z0-9_]+)'
                for m in re.finditer(class_pattern, content, re.MULTILINE):
                    structure.append(f"Class: {m.group(1)}")
                
                # 2. استخراج الدوال التقليدية: export async function name() { ...
                func_pattern = r'^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)'
                for m in re.finditer(func_pattern, content, re.MULTILINE):
                    structure.append(f"Function: {m.group(1)}")
                
                # 3. استخراج الدوال السهمية المعرفة كـ ثابت: export const name = (..) => ...
                arrow_pattern = r'^\s*(?:export\s+)?const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'
                for m in re.finditer(arrow_pattern, content, re.MULTILINE):
                    structure.append(f"Function (Arrow): {m.group(1)}")
                
                return "\n".join(structure)

            elif ext == '.rs':
                # دعم لغة Rust: Structs, Enums, Traits, Functions
                structure = []
                # 1. استخراج الهياكل والتراكيب: pub struct Name, enum Name, trait Name
                struct_pattern = r'^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([a-zA-Z0-9_]+)'
                for m in re.finditer(struct_pattern, content, re.MULTILINE):
                    structure.append(f"Struct/Trait: {m.group(1)}")
                
                # 2. استخراج الدوال: pub async fn name(...)
                fn_pattern = r'^\s*(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)'
                for m in re.finditer(fn_pattern, content, re.MULTILINE):
                    structure.append(f"Function: {m.group(1)}")
                
                return "\n".join(structure)

            elif ext == '.java':
                # دعم لغة Java: Classes, Interfaces, Methods
                structure = []
                # 1. استخراج الكلاسات والواجهات: public class Name, interface Name
                class_pattern = r'^\s*(?:public|protected|private)?\s*(?:static\s+)?(?:class|interface|enum)\s+([a-zA-Z0-9_]+)'
                for m in re.finditer(class_pattern, content, re.MULTILINE):
                    structure.append(f"Class: {m.group(1)}")
                
                # 2. استخراج الميثودز (طريقة مبسطة): public void name(args) {
                method_pattern = r'^\s*(?:public|protected|private)?\s*(?:static\s+)?(?:void|[a-zA-Z0-9_<>\s\[\]]+)\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?:\{|\bthrows\b)'
                for m in re.finditer(method_pattern, content, re.MULTILINE):
                    name = m.group(1)
                    if name not in ['if', 'for', 'while', 'switch', 'catch', 'synchronized']:
                        structure.append(f"Method: {name}")
                
                return "\n".join(structure)

            else:
                return f"Unsupported file type: {ext}"
                
        except Exception as e:
            return f"Error parsing {filepath}: {e}"