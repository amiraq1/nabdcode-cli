from rich.console import Console
from rich.theme import Theme
from rich.text import Text
from rich.panel import Panel
from rich import box

# ── 1. استنساخ الألوان من كود React ──
CYAN = "#00f5d4"
GREEN = "#39ff14"
AMBER = "#ffb703"
RED = "#ff4d6d"
PURPLE = "#b48ead"
DIM = "#4a5568"
SURFACE = "#161b22" # للاستخدام في الخلفيات إن أمكن

# ── 2. إعداد شارات الأدوات (Badges) ──
BADGE_STYLES = {
    "LIST": {"bg": "on #1a3a2a", "fg": GREEN},
    "SEARCH": {"bg": "on #1a2a3a", "fg": CYAN},
    "READ": {"bg": "on #2a1a3a", "fg": PURPLE},
    "EDIT": {"bg": "on #3a2a1a", "fg": AMBER},
    "ERROR": {"bg": "on #3a1a1a", "fg": RED},
    "INFO": {"bg": "on #1a1a2a", "fg": "#8899aa"},
}

import sys

# ── 3. تهيئة الكونسول ──
console = Console(file=sys.__stdout__)

class CyberpunkLogo:
    def __init__(self, console: Console):
        self.console = console
        self.logo_lines = [
            "█▄ █ ▄▀█ █▄▀ █▀▄ █▀▀ █▀█ █▀▄ █▀▀",
            "█ ▀█ █▀█ █▄█ █▄▀ █▄▄ █▄█ █▄▀ ██▄"
        ]

    def render(self, provider: str, model: str):
        from rich.align import Align
        logo_text = "\n".join([f"[cyan]{line}[/]" for line in self.logo_lines])
        
        info = (
            f"[dim white]v2.0.0 Beta[/dim white] | "
            f"[dim grey]Platform: {provider}[/dim grey] | "
            f"[dim grey]Model: {model}[/dim grey]"
        )
        
        panel = Panel(
            f"{logo_text}\n\n{info}",
            box=box.HEAVY,
            border_style="cyan",
            padding=(1, 2),
            width=55 
        )
        
        return Align.center(panel)

    def _gradient_logo(self, text: str) -> Text:
        """تدرج حقيقي من أبيض إلى رصاصي — سطر بسطر"""
        result = Text()
        lines = text.split("\n")
        
        # السطر الأول أبيض نقي، الثاني رصاصي
        colors = [255, 160]
        
        for i, line in enumerate(lines):
            val = colors[i] if i < len(colors) else 160
            result.append(line, style=f"rgb({val},{val},{val})")
            if i < len(lines) - 1:
                result.append("\n")
        
        return result

    def _build_layout(self, current_text: str, provider: str, model: str):
        from rich.align import Align
        """بناء الـ layout الكامل مع spacing مريح"""
        output = Text(justify="center")
        
        # مسافة علوية — تعطي الشعار تنفس مثل OpenCode
        output.append("\n\n\n\n")
        
        # الشعار بالتدرج
        logo = self._gradient_logo(current_text)
        logo.justify = "center"
        output.append_text(logo)
        
        # مسافة بين الشعار والمعلومات
        output.append("\n\n")
        
        # معلومات النظام مرتبة بالأسفل وفي المنتصف
        info = Text(justify="center")
        info.append("v2.0.0 Beta", style="dim white")
        info.append("  •  ", style="dim")
        info.append(f"Platform: {provider}", style="dim")
        info.append("  •  ", style="dim")
        info.append(f"Model: {model}", style="dim")
        
        output.append_text(info)
        output.append("\n")
        
        return Align.center(output)

    def animate(self, provider="OpenCode", model="llama-3.1"):
        import time
        from rich.live import Live
        self.console.clear()
        current_text = ""
        
        with Live(self._build_layout("", provider, model), refresh_per_second=10, console=self.console) as live:
            time.sleep(0.3)
            
            for i, line in enumerate(self.logo_lines):
                if i == 0:
                    current_text = line
                else:
                    current_text += "\n" + line
                
                live.update(self._build_layout(current_text, provider, model))
                time.sleep(0.3)
            
            # ثبّت الشاشة بعد الانتهاء
            time.sleep(0.5)

class CyberpunkUI:
    def get_input(self) -> str:
        """ترسم المؤشر السماوي وتنتظر إدخال المستخدم في نفس السطر"""
        return console.input(f"[{CYAN} bold]›[/] ")

    @staticmethod
    def print_system(text: str, sub: str = ""):
        """تحاكي SystemEntry في React"""
        console.print(f"[{CYAN} bold]◆ {text}[/]")
        if sub:
            console.print(f"  [{DIM}]{sub}[/]")
        console.print("") # مسافة صغيرة

    @staticmethod
    def print_user(text: str):
        """تحاكي UserEntry"""
        console.print(f"[{CYAN} bold]›[/] [#e6edf3]{text}[/]")

    @staticmethod
    def print_assistant(text: str):
        """تحاكي AssistantEntry باستخدام Panel لعمل إطار (Border)"""
        # نستخدم Panel لمحاكاة المربع ذو الخلفية الداكنة
        panel = Panel(
            f"[#c9d1d9]{text}[/]", 
            title=f"[{CYAN} dim]◈ agent[/]", 
            title_align="left",
            border_style=DIM,
            padding=(0, 1)
        )
        console.print(panel)
        console.print("")

    @staticmethod
    def print_log_entry(badge_type: str, label: str, result: str, details: list = None):
        """تحاكي LogEntry للشارات ونتائج الأدوات"""
        style = BADGE_STYLES.get(badge_type, BADGE_STYLES["INFO"])
        bg = style["bg"]
        fg = style["fg"]
        
        # طباعة الشارة والمسار
        console.print(f"[{fg} {bg} bold] {badge_type} [/] [#8899aa]{label}[/]")
        
        # طباعة النتيجة مع رمز └
        console.print(f"[{DIM}]└[/] [#c9d1d9]{result}[/]")
        
        # طباعة التفاصيل إن وجدت (expandable details)
        if details:
            for line in details:
                console.print(f"  [{DIM}]│[/] [#768390]{line}[/]")
        console.print("")

# ── تجربة الواجهة ──
if __name__ == "__main__":
    ui = CyberpunkUI()
    
    # 1. طباعة النظام
    ui.print_system("NabdCode CLI Agent v2.0.0 — نبض", "model: meta/llama-3.1-70b-instruct | active_tools: 25")
    
    # 2. إدخال المستخدم
    ui.print_user("Search for 'VectorStore' in files")
    
    # 3. استدعاء أداة (Log Entry)
    ui.print_log_entry(
        badge_type="SEARCH", 
        label='"VectorStore" in files', 
        result="Found 3 matches in 2 files",
        details=[
            "core/vector_db.py:12 — class VectorStore:",
            "core/vector_db.py:47 — store = VectorStore(path)",
            "agents/index_agent.py:8 — from core.vector_db import VectorStore"
        ]
    )
    
    # 4. رد الذكاء الاصطناعي
    ui.print_assistant("I found the `VectorStore` class in `core/vector_db.py`. It seems to be initialized with a path. How would you like to modify it?")
