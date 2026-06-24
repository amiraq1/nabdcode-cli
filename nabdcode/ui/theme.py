from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

def print_neon_tag(tag_type: str, main_text: str, sub_details: str = ""):
    """
    تطبع الأوسمة النيونية الجراحية (LIST, SEARCH, READ) بنفس نمط الصورة.
    """
    tag_styles = {
        "LIST": ("قائمة", "black on #00f0ff"),      # النيون الفيروزي
        "SEARCH": ("SEARCH", "black on #00f0ff"),    # النيون الأزرق
        "READ": ("READ", "black on #00e5ff")         # نيون القراءة الآمن
    }
    
    arabic_tag, style_str = tag_styles.get(tag_type, (tag_type, "black on white"))
    
    # بناء السطر الأول الحاضن للوسم
    msg = Text()
    msg.append(f" {arabic_tag} ", style=style_str)
    msg.append(f" {main_text}\n", style="bold #ffffff")
    
    # بناء التفاصيل الداخلية مع خط الربط العمودي 
    if sub_details:
        for line in sub_details.strip().split('\n'):
            msg.append("│  ", style="#ff00f0") # خط الربط الوردي/البنفسجي
            msg.append(f"{line}\n", style="#ffcc00") # تفاصيل باللون الأصفر الذهبي
            
    console.print(msg)

def print_neon_thought(thought_text: str):
    """
    تطبع تعليقات التفكير والنبض البيني باللون البنفسجي المضيء.
    """
    console.print(f"[bold #ff00f0]* {thought_text}[/bold #ff00f0]")

def print_neon_status(status_text: str):
    """
    تطبع مؤشر الاستكشاف والنبض السفلي الحرج.
    """
    console.print(f" [black on #00f0ff] {status_text} [/black on #00f0ff] [dim #ffffff]9.2k[/dim #ffffff]")
