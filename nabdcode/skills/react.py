import os
import subprocess
import time
import shutil
import atexit
import signal
import logging
from typing import Any, Dict

_active_processes: Dict[str, subprocess.Popen] = {}


def cleanup_background_processes() -> None:
    """
    Gracefully terminate all tracked background servers.
    """

    for workspace, process in list(_active_processes.items()):
        try:
            pgid = os.getpgid(process.pid)

            os.killpg(
                pgid,
                signal.SIGTERM
            )

            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(
                    pgid,
                    signal.SIGKILL
                )

        except Exception:
            pass

    _active_processes.clear()


atexit.register(cleanup_background_processes)

SKILL_INFO: Dict[str, str] = {
    "name": "React Developer Companion",
    "version": "1.1.0",
    "author": "NabdCode",
    "description": "Advanced tools for initializing, building, running, and managing React projects.",
    "api_version": "1.0"
}


def setup_skill(registry: Any, namespace: str = "react") -> bool:
    """
    Register React development tools in the centralized tool registry.
    """
    try:
        @registry.register_local_tool(
            name=f"{namespace}__create",
            desc="Create a new React project using Vite in a subdirectory and install dependencies.",
            args_schema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "The directory name for the new React project."
                    },
                    "template": {
                        "type": "string",
                        "description": "Vite template to use (e.g. react, react-ts). Default is react-ts."
                    }
                },
                "required": ["project_name"]
            }
        )
        def create(project_name: str, template: str = "react-ts") -> str:
            npm_bin = shutil.which("npm")
            if not npm_bin:
                return "Error: npm binary not found in PATH. Please install Node.js."

            project_dir = os.path.abspath(project_name)
            if os.path.exists(project_dir):
                return f"Error: Target directory '{project_name}' already exists."

            # Initialize project using Vite template
            cmd = [npm_bin, "create", "vite@latest", project_name, "--", "--template", template]
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=90
                )
                if result.returncode != 0:
                    return f"Failed to initialize Vite template: {result.stderr or result.stdout}"

                # Install npm packages automatically
                install_result = subprocess.run(
                    [npm_bin, "install"],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if install_result.returncode != 0:
                    return f"Vite project '{project_name}' created, but package installation failed: {install_result.stderr or install_result.stdout}"

                return f"Success: React project '{project_name}' initialized with template '{template}' and packages installed."
            except subprocess.TimeoutExpired:
                return "Error: React project initialization timed out."
            except Exception as e:
                return f"Error during project creation: {str(e)}"

        @registry.register_local_tool(
            name=f"{namespace}__build",
            desc="Build the React project for production using npm run build.",
            args_schema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the React project directory. Default is current directory."
                    }
                }
            }
        )
        def build(project_path: str = ".") -> str:
            npm_bin = shutil.which("npm")
            if not npm_bin:
                return "Error: npm binary not found in PATH."

            target_dir = os.path.abspath(project_path)
            if not os.path.exists(target_dir):
                return f"Error: Project directory '{project_path}' does not exist."

            cmd = [npm_bin, "run", "build"]
            try:
                result = subprocess.run(
                    cmd,
                    cwd=target_dir,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                if result.returncode != 0:
                    return f"Build failed: {result.stderr or result.stdout}"
                return f"Build succeeded:\n{result.stdout}"
            except subprocess.TimeoutExpired:
                return "Error: Build process timed out."
            except Exception as e:
                return f"Error during build execution: {str(e)}"

        @registry.register_local_tool(
            name=f"{namespace}__install",
            desc="Install npm packages/dependencies in the React project.",
            args_schema={
                "type": "object",
                "properties": {
                    "packages": {
                        "type": "string",
                        "description": "Space-separated list of npm packages to install (e.g. react-router-dom axios)."
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Path to the React project directory. Default is current directory."
                    }
                },
                "required": ["packages"]
            }
        )
        def install(packages: str, project_path: str = ".") -> str:
            npm_bin = shutil.which("npm")
            if not npm_bin:
                return "Error: npm binary not found in PATH."

            target_dir = os.path.abspath(project_path)
            if not os.path.exists(target_dir):
                return f"Error: Project directory '{project_path}' does not exist."

            pkg_list = [p.strip() for p in packages.split() if p.strip()]
            if not pkg_list:
                return "Error: No packages specified."

            cmd = [npm_bin, "install"] + pkg_list
            try:
                result = subprocess.run(
                    cmd,
                    cwd=target_dir,
                    capture_output=True,
                    text=True,
                    timeout=240
                )
                if result.returncode != 0:
                    return f"Package installation failed: {result.stderr or result.stdout}"
                return f"Installation succeeded:\n{result.stdout}"
            except subprocess.TimeoutExpired:
                return "Error: Package installation timed out."
            except Exception as e:
                return f"Error during package installation: {str(e)}"

        @registry.register_local_tool(
            name=f"{namespace}__start_dev",
            desc="Start the local React development server in the background.",
            args_schema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the React project directory. Default is current directory."
                    },
                    "port": {
                        "type": "string",
                        "description": "Optional port override (e.g., 5173)."
                    }
                }
            }
        )
        def start_dev(project_path: str = ".", port: str | None = None) -> str:
            npm_bin = shutil.which("npm")
            if not npm_bin:
                return "Error: npm binary not found in PATH."

            workspace_path = os.path.abspath(project_path)
            if not os.path.exists(workspace_path):
                return f"Error: Project directory '{project_path}' does not exist."

            if workspace_path in _active_processes:
                process = _active_processes[workspace_path]

                if process.poll() is None:
                    return (
                        f"Development server already running "
                        f"(PID: {process.pid})"
                    )

            try:
                log_path = os.path.join(
                    workspace_path,
                    "dev_server.log"
                )

                log_file = open(
                    log_path,
                    "a",
                    encoding="utf-8",
                    buffering=1
                )

                cmd = [npm_bin, "run", "dev"]
                if port:
                    cmd += ["--", "--port", port]

                process = subprocess.Popen(
                    cmd,
                    cwd=workspace_path,
                    stdout=log_file,
                    stderr=log_file,
                    start_new_session=True
                )

                _active_processes[workspace_path] = process

                return (
                    f"Development server started.\n"
                    f"PID: {process.pid}\n"
                    f"Log: {log_path}"
                )

            except Exception as e:
                return f"Failed to start dev server: {e}"

        return True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to setup skill 'react': {e}")
        return False
