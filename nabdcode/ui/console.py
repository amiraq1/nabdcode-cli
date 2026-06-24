import json
import os
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.traceback import Traceback
from rich.live import Live
from rich.spinner import Spinner

console = Console(
    soft_wrap=True,
    highlight=False,
    emoji=True
)

# Try importing arabic reshaper and bidi algorithm safely
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC_SUPPORT = True
except ImportError:
    HAS_ARABIC_SUPPORT = False

def format_bidi_text(text: str) -> str:
    """
    تصحيح تشكيل الحروف العربية وإعادة ترتيب الأسطر المتداخلة 
    مع الكلمات الإنجليزية لتعرض بشكل صحيح في Termux.
    """
    try:
        if HAS_ARABIC_SUPPORT:
            reshaped_text = arabic_reshaper.reshape(text)
            return get_display(reshaped_text)
    except Exception:
        pass
    return text

def fix_arabic_text(text: str) -> str:
    """Reshapes and applies BiDi algorithms to Arabic texts for correct terminal layout."""
    return format_bidi_text(text)


class ConsoleUI:
    """
    Unified TUI Layer for NabdCode
    Handles presentation with Arabic (RTL) detection and stream support.
    """

    def __init__(self):
        self.console = console
        self._stream_text = ""

    def _is_arabic(self, text: str) -> bool:
        """فحص إذا كان النص يحتوي على حروف عربية لضبط اتجاه القراءة."""
        if not text:
            return False
        return any("\u0600" <= char <= "\u06FF" for char in text)

    # --------------------------------------------------
    # HEADER & STATUS
    # --------------------------------------------------
    def print_header(self, provider: str = "Unknown", model: str = ""):
        try:
            modules = ["Agent", "VectorDB", "Tools", "Skills", "MCP"]
            
            if provider is None:
                provider = "Unknown"
            elif not isinstance(provider, str):
                llm_client = provider
                provider = getattr(llm_client, "provider", "Unknown")
                model = getattr(llm_client, "model", getattr(llm_client, "model_name", "Unknown"))
            elif isinstance(provider, str) and not model:
                if "/" in provider:
                    parts = provider.split('/', 1)
                    provider = parts[0]
                    model = parts[1]
                else:
                    model = provider
                    provider = "Unknown"
            
            if not provider: provider = "Unknown"
            if not model: model = "Unknown"
            
            # جلب اسم المشروع الحالي ديناميكياً (اسم المجلد النشط)
            project_name = os.path.basename(os.getcwd()) or "NabdWorkspace"
            
            content = (
                "[bold cyan]⚡ NabdCode CLI[/bold cyan]\n"
                "[dim]v2.0.0 Beta[/dim]\n\n"
                f"[bold purple]📂 Project:[/bold purple] [bright_white]{project_name}[/bright_white]\n"
                f"[bold purple]🌐 Platform:[/bold purple] [spring_green3]{provider}[/spring_green3]\n"
                f"[bold purple]🧠 Model:[/bold purple] [gold1]{model}[/gold1]\n\n"
                f"[dim]Active Modules:[/dim] [grey70]{', '.join(modules)}[/grey70]"
            )

            self.console.print(
                Panel(
                    content,
                    border_style="cyan",
                    padding=(1, 2)
                )
            )
        except Exception:
            print("NabdCode v2.0.0 Beta")

    def print_status(self, provider: str, model: str, memory_enabled: bool):
        try:
            table = Table(show_header=False, expand=True, border_style="cyan")
            table.add_column("Key", style="bold")
            table.add_column("Value")
            table.add_row("Provider", f"[bold cyan]{provider}[/bold cyan]")
            table.add_row("Model", f"[bold purple]{model}[/bold purple]")
            table.add_row("Memory", "[green]Enabled[/green]" if memory_enabled else "[red]Disabled[/red]")
            
            self.console.print(Panel(table, title="⚙️ System Status", border_style="cyan"))
        except Exception:
            pass

    def render_status_dashboard(self, provider: str, model: str, memory_status: str, indexed_files: int, workspace_path: str):
        """بوابة متوافقة لعرض لوحة الحالة كـ Dashboard."""
        self.print_status(provider, model, memory_status.lower() == "enabled")

    def get_prompt_string(self) -> str:
        """ترجيع سطر الأوامر الديناميكي مع عرض المجلد الحالي."""
        cwd = os.path.basename(os.getcwd()) or "root"
        return f"\n[bold purple]┌──[[/bold purple] [bold cyan]NabdCode[/bold cyan] [dim]@{cwd}[/dim] [bold purple]][/bold purple]\n[bold purple]└──►[/bold purple] "

    # --------------------------------------------------
    # MESSAGES (USER & AI)
    # --------------------------------------------------
    def print_user_message(self, message: str):
        try:
            self.console.print(f"\n[bold grey70]● User:[/bold grey70] {message}")
        except Exception:
            print(f"User: {message}")

    def print_ai_message(self, message: str):
        try:
            from nabdcode_ui import print_agent_response
            print_agent_response(message)
        except Exception:
            print(message)

    # --------------------------------------------------
    # STREAMING CONTROL
    # --------------------------------------------------
    def start_stream(self, role: str = "NabdAgent"):
        """بدء جلسة بث جديدة للبث اللحظي للنصوص."""
        self._stream_text = ""
        self.console.print(f"\n[bold cyan]● {role} (Streaming)...[/bold cyan]")

    def append_stream(self, chunk: str):
        """استقبال وجمع أجزاء النص المتبثقة."""
        self._stream_text += chunk
        self.console.print(chunk, end="")

    def finish_stream(self):
        """إنهاء البث وعرض النص النهائي منسقاً بالكامل."""
        self.console.print()  # سطر جديد بعد انتهاء البث
        final_text = self._stream_text
        self._stream_text = ""
        # إعادة طباعة النص منسقاً داخل الصندوق لحفظ المظهر
        if final_text.strip():
            self.print_ai_message(final_text)

    # --------------------------------------------------
    # AGENTIC BEHAVIOR (THINKING & TOOLS)
    # --------------------------------------------------
    def print_agent_thought(self, thought: str):
        try:
            self.console.print(
                Panel(
                    Text(thought.strip(), style="italic", justify="right" if self._is_arabic(thought) else "left"),
                    title="🧠 Thinking Process",
                    border_style="magenta",
                    padding=(0, 1)
                )
            )
        except Exception:
            print(f"[THOUGHT] {thought}")

    def print_tool_call(self, tool_name: str, arguments: dict | None = None):
        try:
            from nabdcode_ui import print_log_entry
            arguments = arguments or {}
            
            # Map tool name to badge type
            t_lower = tool_name.lower()
            if "list" in t_lower or t_lower == "ls":
                badge = "LIST"
            elif "search" in t_lower or "grep" in t_lower:
                badge = "SEARCH"
            elif "view" in t_lower or "read" in t_lower:
                badge = "READ"
            elif "write" in t_lower or "replace" in t_lower or "edit" in t_lower:
                badge = "EDIT"
            else:
                badge = "EXECUTE"
                
            # Format arguments as details list
            details = []
            for k, v in arguments.items():
                try:
                    val_str = json.dumps(v, ensure_ascii=False, default=str)
                except Exception:
                    val_str = str(v)
                if len(val_str) > 120:
                    val_str = val_str[:120] + "..."
                details.append(f"{k}: {val_str}")
                
            print_log_entry(
                badge=badge,
                label=f"[{tool_name}]",
                result="Executing tool successfully" if not details else "Running with parameters:",
                details=details,
                collapsed=False
            )
        except Exception:
            print(f"[TOOL] {tool_name} {arguments}")

    # --------------------------------------------------
    # SIGNALS & FEEDBACK
    # --------------------------------------------------
    def print_success(self, message: str):
        try:
            from nabdcode_ui import print_success_msg
            print_success_msg(message)
        except Exception:
            self.console.print(f"[spring_green3]\u2713[/spring_green3] {message}")

    def print_warning(self, message: str):
        try:
            from nabdcode_ui import print_warning as ui_warning
            ui_warning(message)
        except Exception:
            self.console.print(f"[yellow]\u26a0[/yellow] {message}")

    def print_error(self, message: str):
        try:
            from nabdcode_ui import print_error as ui_error
            ui_error(message)
        except Exception:
            self.console.print(f"[red]\u2717[/red] {message}")

    def print_info(self, message: str):
        self.console.print(f"[bold cyan]ℹ[/bold cyan] {message}")

    def print_system_alert(self, message: str, is_error: bool = False):
        if is_error:
            self.print_error(message)
        else:
            self.print_info(message)

    def print_exception(self):
        try:
            self.console.print(Traceback.from_exception(*os.sys.exc_info()))
        except Exception:
            pass

    def loading(self, message="Thinking..."):
        return Live(Spinner("dots", text=message), refresh_per_second=12)

    def prompt_taste_signal(self):
        try:
            feedback = self.console.input("\n[dim]Feedback[/dim] ([green]a[/green]/[yellow]r[/yellow]/[cyan]e[/cyan]): ").strip().lower()
            mapping = {"a": "ACCEPT", "accept": "ACCEPT", "r": "REJECT", "reject": "REJECT", "e": "EDIT", "edit": "EDIT"}
            return mapping.get(feedback)
        except Exception:
            return None

    def prompt_for_edit_details(self):
        try:
            return self.console.input("[cyan]Correction:[/cyan] ").strip()
        except Exception:
            return ""

# 🤝 تصدير واجهة موحدة كأدوات حرة متوافقة بالكامل مع الاستيرادات السابقة
_ui = ConsoleUI()
print_header = _ui.print_header
print_header_banner = _ui.print_header
print_user_message = _ui.print_user_message
print_ai_message = _ui.print_ai_message
print_agent_thought = _ui.print_agent_thought
print_tool_call = _ui.print_tool_call
print_success = _ui.print_success
print_warning = _ui.print_warning
print_error = _ui.print_error
print_info = _ui.print_info
print_system_alert = _ui.print_system_alert
print_exception = _ui.print_exception
print_status = _ui.print_status
render_status_dashboard = _ui.render_status_dashboard
get_prompt_string = _ui.get_prompt_string
start_stream = _ui.start_stream
append_stream = _ui.append_stream
finish_stream = _ui.finish_stream
prompt_taste_signal = _ui.prompt_taste_signal
prompt_for_edit_details = _ui.prompt_for_edit_details
fix_arabic_text = fix_arabic_text
format_bidi_text = format_bidi_text

