"""
معالج الأوامر المحلية (Slash Commands).
تُنفَّذ مباشرة دون إرسال الطلب للنموذج السحابي.
"""
import os
import sys
from prompt_toolkit import HTML, PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from rich.panel import Panel
from rich.table import Table
from nabdcode.ui.console import console
from nabdcode.core.config_manager import TomlConfigManager

# Custom Neon style for prompt_toolkit to match React UI
prompt_style = Style.from_dict({
    'completion-menu.completion': 'bg:#2c2c2c #ffffff',
    'completion-menu.completion.current': 'bg:#00f5d4 #000000',
    'scrollbar.background': 'bg:#1e1e1e',
    'scrollbar.button': 'bg:#00f5d4',
    'prompt-arrow': 'bold #00f5d4',
})

# Popular models for quick selection
POPULAR_MODELS = [
    "deepseek-v4-flash",
    "gpt-4-turbo",
    "gpt-4o",
    "gpt-3.5-turbo",
    "claude-3-opus",
    "claude-3-sonnet",
    "claude-3-haiku",
    "gemini-pro",
    "gemini-flash",
    "llama3-70b",
    "llama3-8b",
    "mistral-large",
    "mistral-medium",
    "mistral-small",
]


def _cmd_status(agent=None, arg=""):
    """عرض لوحة التحكم الحالية مع حالة الذاكرة."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.columns import Columns
    from rich import box

    console.print("\n[bold cyan]📊 Fetching system status...[/bold cyan]\n")

    config_manager = TomlConfigManager()
    active_provider = config_manager.get_active_provider()
    providers = config_manager.list_providers()
    current_provider = active_provider["name"]

    # Create bento-style layout with Columns
    provider_table = Table(show_header=False, box=box.ROUNDED)
    provider_table.add_column("Setting", style="bold #00ffcc")
    provider_table.add_column("Value", style="white")
    provider_table.add_row("Active Provider", f"[cyan]{current_provider}[/cyan]")
    provider_table.add_row("Active Model", f"[magenta]{active_provider['model']}[/magenta]")
    provider_table.add_row("Base URL", active_provider['base_url'] or "[dim]Default[/dim]")
    provider_table.add_row("Auto Mode", "[green]Enabled[/green]" if config_manager.config.get("auto_mode") else "[red]Disabled[/red]")
    provider_table.add_row("Available Providers", f"[yellow]{len(providers)}[/yellow]")

    # Memory status
    memory_table = Table(show_header=False, box=box.ROUNDED)
    memory_table.add_column("Metric", style="bold #00ffcc")
    memory_table.add_column("Value", style="white")
    try:
        from nabdcode.memory.memory_manager import MemoryManager
        db = MemoryManager()
        message_count = db.get_message_count()
        memory_table.add_row("Chat History", f"[yellow]{message_count}[/yellow] messages")
        memory_table.add_row("DB Size", f"[dim]SQLite DB[/dim]")
    except Exception as e:
        memory_table.add_row("Memory Status", f"[red]Error: {str(e)}[/red]")

    # RAG status
    rag_table = Table(show_header=False, box=box.ROUNDED)
    rag_table.add_column("Metric", style="bold #00ffcc")
    rag_table.add_column("Value", style="white")
    try:
        from nabdcode.memory.vector_db import VectorDB
        from nabdcode.memory.embeddings import EmbeddingModel

        vector_db = VectorDB()
        vocab = EmbeddingModel()

        doc_count = vector_db.get_document_count()
        vocab_size = len(vocab.vocab) if hasattr(vocab, 'vocab') else 0

        rag_table.add_row("Indexed Documents", f"[yellow]{doc_count}[/yellow]")
        rag_table.add_row("Vocabulary Size", f"[yellow]{vocab_size}[/yellow]")
        rag_table.add_row("Vector DB", "[green]Active[/green]")
    except Exception as e:
        rag_table.add_row("RAG Status", f"[red]Error: {str(e)}[/red]")

    # Display side-by-side or stacked based on width
    if console.size.width < 80:
        for table in [provider_table, memory_table, rag_table]:
            console.print(table)
    else:
        console.print(Columns([provider_table, memory_table, rag_table], equal=False, expand=True))


def _cmd_models(agent=None, arg=""):
    """تخصيص النموذج (Model) من قائمة المحاكاة أو القائمة الكاملة."""
    config_manager = TomlConfigManager()
    current_model = config_manager.config.get("model", "default-model")
    current_provider = config_manager.config.get("model_provider", "local_ollama")

    # If arg is provided, try to set the model directly
    if arg:
        if arg in POPULAR_MODELS:
            config_manager.config["model"] = arg
            if config_manager.save_config(config_manager.config):
                console.print(f"[bold green]✔ Model updated to: {arg}[/bold green]")
            else:
                console.print("[red]✘ Failed to save model[/red]")
        else:
            console.print(f"[yellow]⚠ Model '{arg}' not in popular models list. Try /models for options.[/yellow]")
        return

    # Interactive mode: show selection menu
    from prompt_toolkit import HTML, PromptSession
    from prompt_toolkit.styles import Style

    model_style = Style.from_dict({
        'prompt': 'bg:#2c2c2c #ffffff',
    })

    session = PromptSession(style=model_style)

    console.print("\n[bold cyan]🤖 Model Selection[/bold cyan]\n")
    console.print(f"[dim]Current model: {current_model}[/dim]\n")

    # Show popular models with numbers
    for idx, model in enumerate(POPULAR_MODELS, 1):
        marker = "← " if model == current_model else "   "
        console.print(f"{marker}[cyan]{idx}.[/cyan] {model}")

    console.print("\n[bold]Enter model number (1-{}) or model name: [/bold]".format(len(POPULAR_MODELS)))
    console.print("[dim]Or type 'back' to return[/dim]\n")

    try:
        choice = session.prompt(HTML(f"""<ansicyan><b>╭─[ NabdCode</b></ansicyan> <style fg="#1a6bff"><b>❖ {os.path.basename(os.getcwd())}</b></style> <ansicyan><b>]</b></ansicyan>\n<b>│ ❯ </b>"""))

        if not choice.strip():
            return

        choice_lower = choice.strip().lower()

        if choice_lower == 'back':
            return

        # Try as number first
        if choice_lower.isdigit():
            idx = int(choice_lower) - 1
            if 0 <= idx < len(POPULAR_MODELS):
                selected_model = POPULAR_MODELS[idx]
                config_manager.config["model"] = selected_model
                if config_manager.save_config(config_manager.config):
                    console.print(f"[bold green]✔ Model updated to: {selected_model}[/bold green]")
                else:
                    console.print("[red]✘ Failed to save model[/red]")
            else:
                console.print("[yellow]⚠ Invalid selection[/yellow]")
        else:
            # Try as model name
            if choice_lower in [m.lower() for m in POPULAR_MODELS]:
                selected_model = next(m for m in POPULAR_MODELS if m.lower() == choice_lower)
                config_manager.config["model"] = selected_model
                if config_manager.save_config(config_manager.config):
                    console.print(f"[bold green]✔ Model updated to: {selected_model}[/bold green]")
                else:
                    console.print("[red]✘ Failed to save model[/red]")
            else:
                console.print(f"[yellow]⚠ Model '{choice}' not found[/yellow]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Cancelled[/dim]")


def _cmd_connect(agent=None, arg=""):
    """تبديل المزود (Provider) بين Google و OpenRouter."""
    config_manager = TomlConfigManager()
    current_provider = config_manager.config.get("model_provider", "local_ollama")
    providers = config_manager.list_providers()

    console.print("\n[bold cyan]🌐 Provider Selection[/bold cyan]\n")
    console.print(f"[dim]Current provider: {current_provider}[/dim]\n")

    # Show available providers with numbers
    for idx, provider in enumerate(providers, 1):
        marker = "← " if provider == current_provider else "   "
        console.print(f"{marker}[cyan]{idx}.[/cyan] {provider}")

    console.print("\n[bold]Enter provider number (1-{}) or provider name: [/bold]".format(len(providers)))
    console.print("[dim]Or type 'back' to return[/dim]\n")

    from prompt_toolkit import HTML, PromptSession
    from prompt_toolkit.styles import Style

    provider_style = Style.from_dict({
        'prompt': 'bg:#2c2c2c #ffffff',
    })

    session = PromptSession(style=provider_style)

    try:
        choice = session.prompt(HTML(f"""<ansicyan><b>╭─[ NabdCode</b></ansicyan> <style fg="#1a6bff"><b>❖ {os.path.basename(os.getcwd())}</b></style> <ansicyan><b>]</b></ansicyan>\n<b>│ ❯ </b>"""))

        if not choice.strip():
            return

        choice_lower = choice.strip().lower()

        if choice_lower == 'back':
            return

        # Try as number first
        if choice_lower.isdigit():
            idx = int(choice_lower) - 1
            if 0 <= idx < len(providers):
                selected_provider = providers[idx]
                config_manager.config["model_provider"] = selected_provider
                if config_manager.save_config(config_manager.config):
                    console.print(f"[bold green]✔ Provider updated to: {selected_provider}[/bold green]")
                else:
                    console.print("[red]✘ Failed to save provider[/red]")
            else:
                console.print("[yellow]⚠ Invalid selection[/yellow]")
        else:
            # Try as provider name
            if choice_lower in [p.lower() for p in providers]:
                selected_provider = next(p for p in providers if p.lower() == choice_lower)
                config_manager.config["model_provider"] = selected_provider
                if config_manager.save_config(config_manager.config):
                    console.print(f"[bold green]✔ Provider updated to: {selected_provider}[/bold green]")
                else:
                    console.print("[red]✘ Failed to save provider[/red]")
            else:
                console.print(f"[yellow]⚠ Provider '{choice}' not found[/yellow]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Cancelled[/dim]")

def _cmd_taste(agent=None, arg=""):
    """إدارة التفضيلات والقيود البرمجية المستمرة"""
    from rich.panel import Panel
    
    if not arg:
        console.print("[yellow]استخدام خاطئ. جرب: /taste add <القاعدة> أو /taste view[/yellow]")
        return

    parts = arg.split(maxsplit=1)
    action = parts[0].lower()

    if action == "view":
        if not agent or not hasattr(agent, "taste_manager"):
            console.print("[red]خطأ: نظام تفضيلات الوكيل غير متاح.[/red]")
            return
        rules = agent.taste_manager.get_tastes()
        if rules:
            console.print(Panel(rules, title="[bold magenta]🧠 قواعد Taste-1 الحالية[/bold magenta]", border_style="magenta"))
        else:
            console.print("[cyan]لا توجد قواعد مسجلة حالياً.[/cyan]")
            
    elif action == "add":
        if not agent or not hasattr(agent, "taste_manager"):
            console.print("[red]خطأ: نظام تفضيلات الوكيل غير متاح.[/red]")
            return
        if len(parts) < 2:
            console.print("[red]يجب كتابة القاعدة بعد الأمر. مثال: /taste add استخدم argparse بدلاً من sys.argv[/red]")
            return
            
        rule = parts[1]
        if agent.taste_manager.add_taste(rule):
            console.print(f"[bold green]✔ تم حفظ القاعدة:[/bold green] {rule}")
        else:
            console.print("[red]✘ فشل حفظ القاعدة.[/red]")
            
    else:
        console.print(f"[red]أمر فرعي غير معروف: {action}[/red]")



def _cmd_clear(agent=None, arg=""):
    """تفريغ سجل المحادثة وإعادة تعيين حالة التخطيط."""
    if agent:
        agent.db.clear_history()
        # إعادة تعيين حالة التخطيط إن كانت مفعّلة
        if hasattr(agent, "state"):
            agent.state = agent.STATE_IDLE
            agent._pending_plan = ""
            agent._pending_plan_input = ""
        console.print("[green]✅ Chat history cleared. State reset to IDLE.[/green]")
    else:
        console.print("[yellow]⚠ No agent instance to clear.[/yellow]")


def _cmd_help(agent=None, arg=""):
    """عرض جدول الأوامر المتاحة."""
    table = Table(title="📋 Slash Commands", border_style="cyan")
    table.add_column("Command", style="bold #00ffcc", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("/taste", "Edit taste preferences (opens nano/vim)")
    table.add_row("/clear", "Clear chat history & reset state")
    table.add_row("/plan", "Toggle PLANNING mode")
    table.add_row("/plan off", "Exit PLANNING mode")
    table.add_row("/goal <text>", "Set session goal (shown with every request)")
    table.add_row("/goal clear", "Clear the session goal")
    table.add_row("/approve", "Approve plan & start EXECUTING (in PLANNING mode)")
    table.add_row("/reject", "Reject plan & return to IDLE")
    table.add_row("/diagnose", "Run deep diagnostics of RAG, DB, and Network")
    table.add_row("/status", "Show current system configuration & memory status")
    table.add_row("/models", "Select AI model from popular models list")
    table.add_row("/connect", "Switch between available AI providers")
    table.add_row("/config", "View, set or reset configuration parameters")
    table.add_row("/help", "Show this help table")
    table.add_row("/exit", "Exit the program")
    table.add_row("/quit", "Exit the program")
    console.print(table)


def _cmd_exit(agent=None, arg=""):
    """إنهاء البرنامج."""
    console.print("\n[bold #ff0055]System terminated. Goodbye! 👋[/bold #ff0055]")
    sys.exit(0)


def _cmd_plan(agent=None, arg=""):
    """تبديل وضع التخطيط."""
    if not agent or not hasattr(agent, "state"):
        console.print("[yellow]⚠ Agent not available.[/yellow]")
        return

    if arg == "off":
        if agent.state != agent.STATE_IDLE:
            agent.state = agent.STATE_IDLE
            agent._pending_plan = ""
            agent._pending_plan_input = ""
        console.print("[yellow]ℹ Plan mode disabled. Returned to IDLE.[/yellow]")
        return

    if agent.state == agent.STATE_PLANNING:
        console.print(f"[yellow]ℹ Already in PLANNING mode.[/yellow]")
        return

    agent.state = agent.STATE_PLANNING
    agent._pending_plan = ""
    agent._pending_plan_input = ""
    console.print("[green]✅ Plan mode enabled. Send your request to generate a plan.[/green]")


def _cmd_goal(agent=None, arg=""):
    """إدارة الهدف العام للجلسة."""
    if not agent or not hasattr(agent, "session_goal"):
        console.print("[yellow]⚠ Agent not available.[/yellow]")
        return

    if arg == "clear":
        agent.session_goal = ""
        console.print("[yellow]ℹ Session goal cleared.[/yellow]")
        return

    if not arg:
        if agent.session_goal:
            console.print(Panel(
                agent.session_goal,
                title="🎯 Current Session Goal",
                border_style="cyan",
            ))
        else:
            console.print("[yellow]ℹ No session goal set. Use /goal <text> to set one.[/yellow]")
        return

    agent.session_goal = arg
    console.print(f"[green]✅ Session goal set:[/green] {arg}")


def _cmd_approve(agent=None, arg=""):
    """اعتماد الخطة والتبديل إلى وضع التنفيذ."""
    if not agent or not hasattr(agent, "state"):
        console.print("[yellow]⚠ Agent not available.[/yellow]")
        return

    if agent.state != agent.STATE_PLANNING:
        console.print("[yellow]⚠ No plan to approve. Use /plan then send your request.[/yellow]")
        return

    if not agent._pending_plan:
        console.print("[yellow]⚠ No plan to approve. Send a request first to generate a plan.[/yellow]")
        return

    agent.approved_plan = agent._pending_plan
    agent.state = agent.STATE_EXECUTING
    console.print("[green]✅ Plan approved! Switching to EXECUTING mode.[/green]")
    console.print("[dim]Send your execution request or type normally to begin.[/dim]")


def _cmd_reject(agent=None, arg=""):
    """رفض الخطة والعودة إلى IDLE."""
    if not agent or not hasattr(agent, "state"):
        console.print("[yellow]⚠ Agent not available.[/yellow]")
        return

    if agent.state != agent.STATE_PLANNING:
        console.print("[yellow]⚠ No plan to reject.[/yellow]")
        return

    agent.state = agent.STATE_IDLE
    agent._pending_plan = ""
    agent._pending_plan_input = ""
    console.print("[yellow]ℹ Plan rejected. Returned to IDLE.[/yellow]")


def _cmd_diagnose(agent=None, arg=""):
    """تشخيص كامل لسلامة النظام والشبكة والذاكرة."""
    from nabdcode.core.diagnostics import SystemDiagnostics
    from rich.panel import Panel
    from rich.table import Table
    from rich.columns import Columns
    from rich import box

    console.print("[bold #00ffcc]⏳ Running System-Wide Diagnostic Integrity Test...[/bold #00ffcc]\n")

    diagnostician = SystemDiagnostics()
    report = diagnostician.run_all_checks()

    # 1. Environment Section
    env = report["environment"]
    env_status = "[bold green]✔ OK[/bold green]" if env["status"] == "OK" else "[bold yellow]⚠ WARNING[/bold yellow]"
    env_table = Table(title=f"💻 Environment ({env_status})", border_style="cyan", box=box.ROUNDED)
    env_table.add_column("Dependency", style="bold white")
    env_table.add_column("Status", style="green")
    for dep, ok in env["installed_deps"].items():
        val = "[green]✔ Installed[/green]" if ok else "[red]✘ Missing[/red]"
        env_table.add_row(dep, val)
    env_table.add_row("System Encoding", f"[cyan]{env['system_encoding']}[/cyan]")
    env_table.add_row("Stdout Encoding", f"[cyan]{env['stdout_encoding']}[/cyan]")

    # 2. Config Section
    cfg = report["config"]
    cfg_status = "[bold green]✔ OK[/bold green]" if cfg["status"] == "OK" else "[bold red]✘ FAIL[/bold red]"
    cfg_table = Table(title=f"⚙️ Config & Auth ({cfg_status})", border_style="cyan", box=box.ROUNDED)
    cfg_table.add_column("Property", style="bold white")
    cfg_table.add_column("Value", style="magenta")
    if cfg["status"] != "FAIL":
        cfg_table.add_row("Active Provider", cfg["active_provider"])
        cfg_table.add_row("Active Model", cfg["model"])
        cfg_table.add_row("Auto Mode", "Enabled" if cfg["auto_mode"] else "Disabled")
        cfg_table.add_row("API Key Token", cfg["masked_key"])

    # 3. Database Section
    db = report["database"]
    db_status = "[bold green]✔ OK[/bold green]" if db["status"] == "OK" else ("[bold yellow]⚠ WARN[/bold yellow]" if db["status"] == "WARNING" else "[bold red]✘ FAIL[/bold red]")
    db_table = Table(title=f"🗄️ SQLite Database ({db_status})", border_style="cyan", box=box.ROUNDED)
    db_table.add_column("Metric", style="bold white")
    db_table.add_column("Value", style="magenta")
    db_table.add_row("DB Size", f"{db['db_size_bytes'] / 1024:.2f} KB")
    db_table.add_row("Total Messages", str(db["message_count"]))
    if db.get("integrity"):
        db_table.add_row("Integrity Status", f"[green]{db['integrity']}[/green]")
    if db.get("last_message"):
        lm = db["last_message"]
        db_table.add_row("Last Entry Timestamp", f"[yellow]{lm['timestamp']}[/yellow]")
        db_table.add_row("Last Sender Role", f"[cyan]{lm['role']}[/cyan]")

    # 4. RAG Section
    rag = report["rag"]
    rag_status = "[bold green]✔ OK[/bold green]" if rag["status"] == "OK" else ("[bold yellow]⚠ WARN[/bold yellow]" if rag["status"] == "WARNING" else "[bold red]✘ FAIL[/bold red]")
    rag_table = Table(title=f"🧠 RAG Vector DB ({rag_status})", border_style="cyan", box=box.ROUNDED)
    rag_table.add_column("Metric", style="bold white")
    rag_table.add_column("Value", style="magenta")
    rag_table.add_row("Vector DB File", "[green]Exists[/green]" if rag.get("vector_db_exists") else "[red]Missing[/red]")
    rag_table.add_row("Vocab Mapping", "[green]Exists[/green]" if rag.get("vocab_exists") else "[red]Missing[/red]")
    rag_table.add_row("Doc Chunks Index", str(rag.get("document_count", 0)))
    rag_table.add_row("Vocabulary Size", str(rag.get("vocab_size", 0)))

    # 5. Network Section
    net = report["network"]
    net_status = "[bold green]✔ OK[/bold green]" if net["status"] == "OK" else "[bold red]✘ FAIL[/bold red]"
    net_table = Table(title=f"🌐 Connectivity ({net_status})", border_style="cyan", box=box.ROUNDED)
    net_table.add_column("Connection Test", style="bold white")
    net_table.add_column("Result", style="magenta")
    net_table.add_row("Local DNS Status", "[green]Resolved[/green]" if net.get("dns_resolved") else "[red]Offline[/red]")
    net_table.add_row("API Host Connected", "[green]Yes[/green]" if net.get("api_endpoint_connected") else "[red]No[/red]")
    if net.get("api_endpoint_connected"):
        net_table.add_row("Ping Latency", f"[green]{net['latency_ms']:.1f} ms[/green]")
        net_table.add_row("Server Host", net["provider_host"])

    # Print tables side-by-side or stacked in Columns layout based on width
    if console.size.width < 80:
        for table in [env_table, cfg_table, db_table, rag_table, net_table]:
            console.print(table)
    else:
        console.print(Columns([env_table, cfg_table, db_table, rag_table, net_table], equal=False, expand=True))

    all_issues = []
    for section_name in ["environment", "config", "database", "rag", "network"]:
        all_issues.extend(report[section_name].get("issues", []))

    if all_issues:
        issue_lines = "\n".join([f"• [bold red]✘[/bold red] {issue}" for issue in all_issues])
        console.print(Panel(
            issue_lines,
            title="[bold red]⚠️ Detected System Anomalies & Issues[/bold red]",
            border_style="red",
            padding=(1, 2)
        ))
    else:
        console.print(Panel(
            "[bold green]✔ System state is stable. All diagnostics passed without warning.[/bold green]",
            title="[bold green]🌟 Final Status[/bold green]",
            border_style="green",
            padding=(1, 1)
        ))


import rich.box
from typing import List, Any
from rich.table import Table
from rich.box import MINIMAL

def _mask_api_key(value: str) -> str:
    """وظيفة مساعدة لتعمية مفتاح الـ API بأمان."""
    if not value:
        return "[dim underline]Not Set[/dim underline]"
    if len(value) <= 16:
        return "********"
    return f"{value[:12]}...{value[-4:]}"

def handle_config_command(args: list[str], agent: Any, ui: Any) -> None:
    """
    معالجة وتحليل خيارات الأمر السريع /config (view, set, reset) 
    وعرض البيانات بكثافة نقطية مثالية تتوافق مع شاشات الهواتف.
    """
    config_manager = agent.config_manager

    # 1. حالة العرض الافتراضي: /config أو /config view
    if not args or args[0] == "view":
        table = Table(title="[bold cyan]⚙ NabdCode System Configuration[/bold cyan]", box=MINIMAL, expand=False)
        table.add_column("Parameter", style="cyan", no_wrap=True)
        table.add_column("Current Value", style="spring_green3")
        table.add_column("Type", style="dim")

        for key, value in config_manager.config.items():
            display_value = str(value)
            # استخدام الدالة المساعدة لتعمية المفتاح بأمان
            if key == "api_key":
                display_value = _mask_api_key(str(value))
            
            # استخدام .get() لمنع انهيار النظام إذا كان هناك مفتاح غير معروف في ملف JSON
            default_val = config_manager.DEFAULT_CONFIG.get(key)
            type_name = type(default_val).__name__ if default_val is not None else "custom"

            table.add_row(key, display_value, type_name)

        ui.console.print("\n")
        ui.console.print(table)
        ui.console.print("[dim]💡 Usage: /config set <key> <value> | /config reset[/dim]\n")
        return

    # 2. حالة إعادة الضبط: /config reset
    if args[0] == "reset":
        if config_manager.reset_to_defaults():
            ui.print_success("System configuration reset to factory defaults successfully.")
            # استدعاء دالة التحديث الساخن في الوكيل لضمان تزامن كل المكونات بأمان
            if hasattr(agent, 'apply_config_update'):
                agent.apply_config_update()
            else:
                agent.config = config_manager.config
        else:
            ui.print_error("Failed to reset configuration database.")
        return

    # 3. حالة التعديل الديناميكي: /config set <key> <value>
    if args[0] == "set":
        if len(args) < 3:
            ui.print_warning("Missing parameters. Syntax: [bold]/config set <key> <value>[/bold]")
            return
        
        key = args[1]
        # دعم تجميع الأسماء المركبة للنماذج البرمجية (مثل: gpt-4-turbo preview)
        value = " ".join(args[2:])

        if key not in config_manager.DEFAULT_CONFIG:
            ui.print_error(f"Unknown configuration parameter: '[bold]{key}[/bold]'.")
            return

        if config_manager.set(key, value):
            # دمج ميزة الـ Hot-Reload لتهيئة المكونات في نفس ثانية التشغيل
            if hasattr(agent, 'apply_config_update'):
                agent.apply_config_update()
            else:
                agent.config = config_manager.config
            ui.print_success(f"Parameter '[bold]{key}[/bold]' permanently updated.")
        else:
            ui.print_error(f"Data type mismatch error for parameter '[bold]{key}[/bold]'.")
        return

    # 4. أمر غير معروف
    ui.print_warning(f"Unknown sub-command '[bold]{args[0]}[/bold]'. Available: view, set, reset")


def _cmd_config(agent=None, arg=""):
    """عرض وتعديل إعدادات الوكيل ديناميكياً."""
    if not agent:
        console.print("[red]❌ خطأ: لا يوجد وكيل نشط لتحديث الإعدادات له.[/red]")
        return
    
    # تقسيم الوسائط: "set provider openrouter" -> ["set", "provider", "openrouter"]
    args = arg.strip().split()
    from nabdcode.ui.console import ConsoleUI
    ui = agent.ui if hasattr(agent, 'ui') and agent.ui else ConsoleUI()
    handle_config_command(args, agent, ui)


SLASH_COMMANDS = {
    "taste": _cmd_taste,
    "clear": _cmd_clear,
    "help": _cmd_help,
    "exit": _cmd_exit,
    "quit": _cmd_exit,
    "plan": _cmd_plan,
    "goal": _cmd_goal,
    "approve": _cmd_approve,
    "reject": _cmd_reject,
    "diagnose": _cmd_diagnose,
    "status": _cmd_status,
    "models": _cmd_models,
    "connect": _cmd_connect,
    "config": _cmd_config,
}


def handle_slash_command(text: str, agent=None) -> bool:
    """
    تنفيذ أمر slash محلياً.

    text:    النص المدخل (يبدأ بـ /)
    agent:   كائن الوكيل (يُمرَّر عند الحاجة للوصول إلى الذاكرة)
    return:  True إذا كان الأمر معروفاً ونُفّذ، False إذا كان غير معروف.
    """
    raw = text.strip()
    if not raw.startswith("/"):
        return False

    # فصل الأمر عن الوسائط: "/plan off" → cmd="plan", arg="off"
    parts = raw.lstrip("/").split(None, 1)
    if not parts:
        return
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    handler = SLASH_COMMANDS.get(cmd)

    if handler:
        handler(agent, arg)
        return True

    if cmd:
        console.print("[yellow]⚠ أمر غير معروف. اكتب /help لعرض الأوامر.[/yellow]")
        return False

    return False


def interactive_menu(agent=None, ui=None):
    """
    حلقة الأوامر التفاعلية مع دعم autocomplete واستخدام prompt_toolkit.
    """
    file_completions = []
    try:
        valid_exts = ('.py', '.kt', '.md', '.sh', '.java', '.js', '.json', '.xml', '.ts', '.tsx', '.jsx', '.rs', '.cpp', '.h', '.hpp', '.c', '.cc')
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.venv')]
            for file in files:
                if file.endswith(valid_exts):
                    rel_path = os.path.relpath(os.path.join(root, file), '.')
                    file_completions.append(f"@{rel_path}")
    except Exception:
        pass

    commands_list = list(SLASH_COMMANDS.keys()) + file_completions

    completer = WordCompleter(
        commands_list,
        ignore_case=True
    )

    session = PromptSession(
        completer=completer,
        style=prompt_style,
        complete_while_typing=True,
        enable_history_search=True
    )

    from prompt_toolkit.patch_stdout import patch_stdout

    while True:
        try:
            with patch_stdout():
                user_input = session.prompt(
                    HTML("\n<prompt-arrow><b>›</b></prompt-arrow> ")
                )

            user_input = user_input.strip()

            if not user_input:
                continue

            # أوامر الخروج
            if user_input.lower() in (
                "/exit",
                "/quit",
                "exit",
                "quit"
            ):
                console.print(
                    "\n[bold red]Exiting NabdCode...[/bold red]"
                )
                break

            # أوامر Slash
            if user_input.startswith("/"):
                handled = handle_slash_command(
                    user_input,
                    agent
                )

                if not handled:
                    console.print(
                        "[yellow]⚠ Unknown command. Type /help[/yellow]"
                    )

                continue

            # رسائل الوكيل العادية
            if agent:
                try:
                    agent.process_request_sync(
                        user_input
                    )

                except Exception as e:
                    console.print(
                        f"[red]Agent Error:[/red] {e}"
                    )
            else:
                console.print(
                    "[red]No active agent available.[/red]"
                )

        except KeyboardInterrupt:
            console.print(
                "\n[yellow]Interrupted.[/yellow]"
            )

        except EOFError:
            console.print(
                "\n[bold red]Exiting NabdCode...[/bold red]"
            )
            break

        except Exception as e:
            console.print(
                f"[red]Unexpected Error:[/red] {e}"
            )