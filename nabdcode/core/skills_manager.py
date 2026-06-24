import os
import sys
import logging
import importlib
import importlib.util
import hashlib

from pathlib import Path
from typing import Dict, List, Any, Optional

from nabdcode.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

REQUIRED_SKILL_API = "1.0"


class SkillsManager:
    """
    Dynamic Skills & Plugins Manager
    """

    def __init__(
        self,
        registry: ToolRegistry,
        skills_dir: Optional[str] = None
    ):
        self.registry = registry

        self.skills_dir = (
            Path(skills_dir).resolve()
            if skills_dir
            else Path(__file__).resolve().parent.parent / "skills"
        )
        print(f"[DEBUG] Tool Search Path: {self.skills_dir}")

        self.skills_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.loaded_skills: Dict[str, Dict[str, Any]] = {}

    def _validate_skill(
        self,
        module
    ) -> bool:

        if not hasattr(module, "setup_skill"):
            logger.warning(
                "Skill missing setup_skill(): %s",
                module.__name__
            )
            return False

        if not callable(module.setup_skill):
            logger.warning(
                "setup_skill is not callable: %s",
                module.__name__
            )
            return False

        info = getattr(
            module,
            "SKILL_INFO",
            {}
        )

        api_version = info.get(
            "api_version",
            REQUIRED_SKILL_API
        )

        if api_version != REQUIRED_SKILL_API:
            logger.warning(
                "Incompatible skill API version (%s): %s",
                api_version,
                module.__name__
            )
            return False

        return True

    def _check_skill_safety(self, file_path: str) -> bool:
        """فحص أمني متقدم للمهارة قبل تحميلها باستخدام شجرة التراكيب (AST)"""
        import ast
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Check for explicit dangerous names
                if isinstance(node, ast.Name):
                    if node.id in {'eval', 'exec', '__import__'}:
                        logger.warning(f"SECURITY: Skill '{file_path}' uses dangerous built-in: {node.id}")
                        return False
                
                # Check for imports of dangerous modules
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in {'subprocess', 'pty'}:
                            logger.warning(f"SECURITY: Skill '{file_path}' imports dangerous module: {alias.name}")
                            return False
                elif isinstance(node, ast.ImportFrom):
                    if node.module in {'subprocess', 'pty'}:
                        logger.warning(f"SECURITY: Skill '{file_path}' imports from dangerous module: {node.module}")
                        return False
                
                # Check for method calls like os.system or subprocess.run
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in {'system', 'popen', 'run', 'Popen', 'check_output', 'check_call'}:
                            logger.warning(f"SECURITY: Skill '{file_path}' calls dangerous method: {node.func.attr}")
                            return False
                    
                    # Check for shell=True kwargs
                    for kw in node.keywords:
                        if kw.arg == 'shell':
                            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                logger.warning(f"SECURITY: Skill '{file_path}' uses shell=True")
                                return False
                                
            return True
        except SyntaxError:
            logger.error(f"Syntax error in skill file: {file_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking skill safety for {file_path}: {e}")
            return False

    def load_skill_module(
        self,
        module_name: str,
        file_path: str
    ) -> bool:

        if module_name in self.loaded_skills:
            logger.debug(
                "Skill already loaded: %s",
                module_name
            )
            return True

        try:

            spec = importlib.util.spec_from_file_location(
                module_name,
                file_path
            )

            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(
                spec
            )

            sys.modules[module_name] = module

            if not self._check_skill_safety(file_path):
                logger.error(f"Skill {module_name} failed safety check.")
                return False

            spec.loader.exec_module(module)

            if not self._validate_skill(module):
                return False

            skill_name = module_name.split(".")[-1]

            success = module.setup_skill(
                self.registry,
                namespace=skill_name
            )

            if not success:
                return False

            skill_info = getattr(
                module,
                "SKILL_INFO",
                {}
            )

            self.loaded_skills[module_name] = {
                "path": file_path,
                "module": module,
                "info": skill_info
            }

            logger.info(
                "Loaded skill: %s",
                skill_name
            )

            return True

        except Exception as e:

            logger.exception(
                "Failed loading skill %s",
                module_name
            )

            return False

    def load_all_skills(
        self
    ) -> List[str]:

        loaded = []

        if not self.skills_dir.exists():
            return loaded

        for file in self.skills_dir.iterdir():

            if not file.is_file():
                continue

            if file.name.startswith("__"):
                continue

            if file.name.startswith("test_"):
                continue

            if file.name.endswith("_test.py"):
                continue

            if file.suffix != ".py":
                continue

            module_name = (
                f"nabdcode.skills.{file.stem}"
            )

            if self.load_skill_module(
                module_name,
                str(file)
            ):
                loaded.append(file.stem)

        return loaded

    def reload_skill(
        self,
        module_name: str
    ) -> bool:

        if module_name not in self.loaded_skills:
            return False

        try:

            module = self.loaded_skills[
                module_name
            ]["module"]

            importlib.reload(module)

            logger.info(
                "Reloaded skill: %s",
                module_name
            )

            return True

        except Exception:

            logger.exception(
                "Failed to reload skill %s",
                module_name
            )

            return False

    def unload_skill(
        self,
        module_name: str
    ) -> bool:

        if module_name not in self.loaded_skills:
            return False

        try:

            if module_name in sys.modules:
                del sys.modules[module_name]

            del self.loaded_skills[module_name]

            logger.info(
                "Unloaded skill: %s",
                module_name
            )

            return True

        except Exception:

            logger.exception(
                "Failed unloading skill %s",
                module_name
            )

            return False

    def get_loaded_skills_summary(
        self
    ) -> List[Dict[str, Any]]:

        summary = []

        for module_name, data in self.loaded_skills.items():

            info = data.get(
                "info",
                {}
            )

            summary.append({
                "name": info.get(
                    "name",
                    module_name.split(".")[-1]
                ),
                "version": info.get(
                    "version",
                    "unknown"
                ),
                "author": info.get(
                    "author",
                    "unknown"
                ),
                "description": info.get(
                    "description",
                    ""
                ),
                "status": "Active"
            })

        return summary

    def get_skill_count(self) -> int:
        return len(self.loaded_skills)
