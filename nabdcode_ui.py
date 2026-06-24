"""
nabdcode_ui.py — NabdCode CLI Agent UI Module
النسخة المدموجة الكاملة والمحسنة (v1 + v2 + الأسلوب الشجري المفتوح)
المطور: عمار التميمي
"""

import time
import sys
import shutil
from typing import List, Dict, Tuple, Optional
from rich.console import Console
from rich.text import Text
from rich.live import Live
from rich.tree import Tree

# ──── إعداد الكونسول بدعم ألوان TrueColor لترمكس ────
console = Console(color_system="truecolor")

# ──── ثيم الألوان النيون والأدوات الاحترافية ────
CYAN       = "#00f5d4"
GREEN      = "#39ff14"
AMBER      = "#ffb703"
RED        = "#ff4d6d"
PURPLE     = "#5856d6"  # اللون البنفسجي المميز والعميق
DIM        = "#4a5568"
TEXT_LIGHT = "#e5e5ea"
TEXT_GRAY  = "#8e8e93"
DIM_LINE   = "#3a3a3c"

# ──── خريطة ألوان الـ Badges (لون النص, لون الخلفية) ────
BADGE_COLORS: Dict[str, Tuple[str, str]] = {
    "LIST":   ("#ffffff", "#1a3a2a"),
    "SEARCH": (CYAN,      "#1a2a3a"),
    "READ":   ("#ffffff", PURPLE),
    "EDIT":   (AMBER,     "#3a2a1a"),
    "EXECUTE":("#ffffff", PURPLE),
    "ERROR":  (RED,       "#3a1a1a"),
    "INFO":   ("#8899aa", "#1a1a2a"),
}

# ══════════════════════════════════════════════
#  1. الترويسة النظامية
# ══════════════════════════════════════════════

def print_system_header(
    version: str = "2.0.0",
    model: str = "deepseek-v4-flash",
    workspace: str = "active",
) -> None:
    """طباعة ترويسة النظام الفاخرة عند إقلاع الأداة"""
    console.print(Text("─" * 52, style=DIM_LINE))
    header = Text()
    header.append(f" ◆ NabdCode CLI Agent v{version} — نبض\n", style=f"bold {CYAN}")
    header.append(
        f" └ platform: termux  |  model: {model}  |  workspace: {workspace}",
        style=DIM,
    )
    console.print(header)
    console.print(Text("─" * 52, style=DIM_LINE))


# ══════════════════════════════════════════════
#  2. كتل الـ Badges
# ══════════════════════════════════════════════

def make_badge(badge_type: str) -> Text:
    """توليد كائن كرتوني ملون للـ Badge حسب نوع الإجراء"""
    key = badge_type.upper()
    color, bg = BADGE_COLORS.get(key, ("#8899aa", "#1a1a2a"))
    return Text(f" {key} ", style=f"bold {color} on {bg}")


def print_badge(badge_type: str, context: str) -> None:
    """طباعة الـ Badge وجانبه النص التوضيحي المباشر"""
    line = make_badge(badge_type)
    line.append_text(Text(f" {context}", style=TEXT_LIGHT))
    console.print(line)


# ══════════════════════════════════════════════
#  3. مخرجات الأدوات الشجرية (Log Entries)
# ══════════════════════════════════════════════

def print_log_entry(
    badge: str,
    label: str,
    result: str,
    details: Optional[List[str]] = None,
    collapsed: bool = True,
    lines_count: Optional[int] = None,
) -> None:
    """
    طباعة مخرجات الأدوات بنمط هيكلي شجري متوافق مع الصورة النظيفة.
    """
    badge_text = make_badge(badge)
    badge_text.append_text(Text(f" {label}", style=TEXT_LIGHT))
    
    tree = Tree(badge_text, guide_style=TEXT_GRAY)
    tree.add(Text(result, style=TEXT_LIGHT))

    if details and not collapsed:
        for line in details:
            tree.add(Text(line, style="#768390"))
            
    elif collapsed and lines_count:
        hint = Text()
        hint.append(f"... +{lines_count} lines ", style=TEXT_GRAY)
        hint.append("[ctrl+o to expand]", style=DIM_LINE)
        tree.add(hint)

    console.print(tree)
    console.print()


def print_tool_result(
    tool_name: str,
    result: str,
    is_error: bool = False,
    max_lines: int = 8,
) -> None:
    """
    طباعة نتيجة تنفيذ الأداة بنمط شجري نظيف.
    يعرض أول N سطر ويطوي البقية لمنع إغراق الطرفية.
    """
    if is_error:
        status_icon = "✗"
        status_color = RED
    else:
        status_icon = "✓"
        status_color = GREEN

    # Badge صغير لاسم الأداة
    badge = Text(f" {status_icon} ", style=f"bold {status_color}")
    badge.append_text(Text(f"{tool_name}", style=f"bold {TEXT_LIGHT}"))
    
    tree = Tree(badge, guide_style=TEXT_GRAY)

    if not result or not result.strip():
        tree.add(Text("(no output)", style=TEXT_GRAY))
        console.print(tree)
        console.print()
        return

    lines = result.strip().split('\n')
    visible = lines[:max_lines]
    hidden = len(lines) - max_lines

    visible_text = "\n".join(visible)
    tree.add(Text(visible_text, style=TEXT_GRAY))

    if hidden > 0:
        hint = Text()
        hint.append(f"... +{hidden} lines ", style=TEXT_GRAY)
        hint.append("[collapsed]", style=DIM_LINE)
        tree.add(hint)

    console.print(tree)
    console.print()


def print_read_entry(file_path: str, lines_count: int) -> None:
    """طباعة بادج READ المطور"""
    line = make_badge("READ")
    line.append_text(Text(f" [{file_path}]", style=TEXT_LIGHT))
    line.append_text(Text(f"  {lines_count} lines", style=TEXT_GRAY))
    console.print(line)


# ══════════════════════════════════════════════
#  4. حركات وخطوات التفكير
# ══════════════════════════════════════════════

def print_thought_step(
    seconds: Optional[int] = None,
    lines: Optional[int] = None,
    is_thinking: bool = False,
) -> None:
    """طباعة علامة تفكير النموذج القابلة للتوسيع"""
    thought = Text()
    if is_thinking and lines:
        thought.append(f" ٭ Thinking... ({lines} lines) ", style=TEXT_LIGHT)
    elif seconds:
        thought.append(f" ٭ Thought for {seconds} second{'s' if seconds != 1 else ''} ", style=TEXT_LIGHT)
    thought.append("[ctrl+o to expand]", style=DIM_LINE)
    console.print(thought)
    console.print()


def show_thinking_animation(duration: float = 1.5) -> None:
    """تأثير وميض حركي يتم تطهيره تلقائياً لمنع ازدحام سجلات الطرفية"""
    frames = [
        " ◈ جاري المعالجة دلالياً .",
        " ◈ جاري المعالجة دلالياً ..",
        " ◈ جاري المعالجة دلالياً ...",
    ]
    with Live(Text(frames[0], style=DIM), refresh_per_second=5, transient=True) as live:
        start = time.time()
        i = 0
        while time.time() - start < duration:
            live.update(Text(frames[i % 3], style=CYAN))
            time.sleep(0.3)
            i += 1


# ══════════════════════════════════════════════
#  5. رد الوكيل الشجري المفتوح (حل أزمة التقطيع)
# ══════════════════════════════════════════════

def print_agent_response(text: str) -> None:
    """
    طباعة رد الوكيل بنمط شجري مفتوح ونظيف يحمي سلامة وانسيابية الحروف العربية
    ويمنع تماماً مشاكل التقطيع الناتجة عن الصناديق المغلقة في ترمكس عبر استخدام Rich Tree.
    """
    agent_badge = Text(" ◈ NabdAgent ", style=f"bold #ffffff on {PURPLE}")
    tree = Tree(agent_badge, guide_style=TEXT_LIGHT)
    
    if text.strip():
        tree.add(Text(text.strip(), style=TEXT_LIGHT))
        
    console.print(tree)
    console.print()


# ══════════════════════════════════════════════
#  5.5. رسائل النظام الشجرية (Warning / Error / Success)
# ══════════════════════════════════════════════

def print_warning(message: str) -> None:
    """طباعة تحذير نظامي بنمط شجري"""
    line = Text()
    line.append(" ⚠ ", style=f"bold {AMBER}")
    line.append(message, style=AMBER)
    console.print(line)


def print_error(message: str) -> None:
    """طباعة خطأ نظامي بنمط شجري"""
    line = Text()
    line.append(" ✗ ", style=f"bold {RED}")
    line.append(message, style=RED)
    console.print(line)


def print_success_msg(message: str) -> None:
    """طباعة رسالة نجاح بنمط شجري"""
    line = Text()
    line.append(" ✓ ", style=f"bold {GREEN}")
    line.append(message, style=TEXT_LIGHT)
    console.print(line)


# ══════════════════════════════════════════════
#  6. مؤشر الإدخال الآمن (REPL Prompt)
# ══════════════════════════════════════════════

def print_user_prompt() -> None:
    """طباعة خط الإدخال الاستباقي لمحاكاة التيرمينال الكاملة"""
    console.print(Text("─" * 52, style=DIM_LINE))
    arrow = Text(" ❯ ", style=f"bold {CYAN}")
    cursor = Text("█", style=CYAN)
    console.print(arrow + cursor)


def get_user_input() -> str:
    """
    استقبال الأوامر مع رندرة نيونية حية فورية ومحصنة بالكامل ضد مشاكل الـ Buffering.
    تتعامل مع الاختصارات وإشارات الخروج (Ctrl+C) بشكل آمن.
    """
    console.print(Text("─" * 52, style=DIM_LINE))
    prompt_arrow = f"\033[1;36m ❯ \033[0m"
    
    try:
        sys.stdout.flush()
        user_input = input(prompt_arrow)
        console.print(Text("  ? for shortcuts", style=TEXT_GRAY))
        return user_input.strip()
    except (KeyboardInterrupt, EOFError):
        return "exit"


# ══════════════════════════════════════════════
#  فحص تشغيل البنية الكاملة
# ══════════════════════════════════════════════

if __name__ == "__main__":
    console.clear()

    # 1. الترويسة
    print_system_header()

    # 2. الأوامر الشجرية
    print_log_entry("LIST", "[nabdcode]", "Found 7 items (6 dirs, 1 file)", lines_count=8, collapsed=True)
    print_log_entry("LIST", "[nabdcode-cli]", "Found 18 items (5 dirs, 13 files)", lines_count=19, collapsed=True)
    
    print_thought_step(seconds=1)
    
    print_log_entry(
        badge="SEARCH",
        label='"VectorStore" in files',
        result="Found 9 matches in 3 files",
        details=[
            "core/vector_db.py:12  — class VectorStore:",
            "core/vector_db.py:47  — store = VectorStore(path)"
        ],
        collapsed=False,
    )
    
    print_thought_step(seconds=1)

    print_read_entry("nabdcode/memory/embeddings.py", 112)
    print_read_entry("nabdcode/core/agent.py", 528)
    console.print()

    print_thought_step(lines=12, is_thinking=True)
    show_thinking_animation(1.2)

    # 3. الرد النهائي والمؤشر المطور
    print_agent_response(
        "أهلاً عمار! فحصت المستودع بالكامل.\n"
        "وجدت مصفوفة الذاكرة الدلالية مستقرة والهيكل البصري موحد شجرياً.\n"
        "جاهز لأي اختبار أو تعديل."
    )

    print_user_prompt()
