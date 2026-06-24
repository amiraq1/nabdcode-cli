import argparse
import sys
import os
from dotenv import load_dotenv

# تحميل المتغيرات البيئية من ملف .env قبل تشغيل أي مكون آخر
load_dotenv()

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from nabdcode.ui.console import console, ConsoleUI
from nabdcode.core.agent import NabdAgent
from nabdcode.core.commands import handle_slash_command, interactive_menu

# اسم مستعار للتوافق مع بنية الطلب
Agent = NabdAgent

# Legacy function - replaced by interactive_menu from commands.py
# def start_interactive_loop(agent, ui):
#     """حلقة التشغيل التفاعلية الافتراضية للعميل"""
#     #console.print("[dim]Type 'exit' to quit. System is fully operational.[/dim]\n")
#     while True:
#         try:
#             cwd_name = os.path.basename(os.getcwd())
#             console.print(f"[bold #333333]╭─[[/bold #333333][bold white] NabdCode [/bold white][bold #1a6bff]❖ {cwd_name} [/bold #1a6bff][bold #333333]][/bold #333333]")
#             req = ui.input("[bold #333333]│[/bold #333333] [bold #1a6bff]❯[/bold #1a6bff] ")
#             console.print("[bold #333333]╰──────────────────────────────[/bold #333333]")
#             if not req.strip():
#                 continue

#             if req.strip().startswith("/"):
#                 handle_slash_command(req, agent)
#                 continue

#             if req.strip().lower() in ['exit', 'quit']:
#                 console.print("\n[bold #ff0055]System terminated. Goodbye! 👋[/bold #ff0055]")
#                 break
#             if req.strip().lower() == 'settings':
#                 agent.settings_loop()
#                 continue

#             reply = agent.process_request(req)

#         except KeyboardInterrupt:
#             console.print("\n[bold #ff0055]Force quit.[/bold #ff0055]")
#             break


def main():
    parser = argparse.ArgumentParser(
        description="NabdCode CLI - OS Agent for Code Generation and Management",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("-t", "--task", type=str, help="المهمة البرمجية المطلوب تنفيذها مباشرة")
    parser.add_argument("--headless", action="store_true", help="تشغيل الوكيل في الخلفية بدون واجهة تفاعلية")
    parser.add_argument("--out", type=str, help="مسار ملف لحفظ النتيجة (اختياري)")
    parser.add_argument("--auto", action="store_true", help="Enable autonomous execution mode without human confirmation")
    parser.add_argument("--version", action="version", version="0.1.0")
    parser.add_argument("--index", action="store_true", help="Force re-indexing of workspace (ignore cached index)")
    parser.add_argument("--mcp", action="store_true", help="Start the NabdCode agent as an MCP stdio server")

    args = parser.parse_args()
    
    original_stdout = None
    if args.mcp:
        # Surgical Fix: تحويل sys.stdout إلى sys.stderr فوراً لمنع أي تلوث للمخرج القياسي
        import sys
        original_stdout = sys.stdout
        sys.stdout = sys.stderr
        
        # Surgical Fix: توجيه كافة السجلات إلى stderr لتفادي إفساد بروتوكول MCP
        import logging
        logging.basicConfig(stream=sys.stderr, level=logging.INFO, force=True)
    
    ui = ConsoleUI()
    agent = Agent(auto_mode=args.auto, ui=ui)

    if args.mcp:
        # 2. ⚡ الفهرسة الكسولة في الخلفية (Background Lazy Indexing)
        import threading
        
        def background_index():
            try:
                logger.info("Starting background workspace indexing...")
                agent.index_workspace(force=args.index, silent=True)
                logger.info("Background indexing completed successfully.")
            except Exception as e:
                logger.warning(f"Background indexing failed: {e}")
                
        # Only run background indexing if needed (e.g. forced or not loaded)
        if args.index or not agent.vector_db.load_index():
            index_thread = threading.Thread(target=background_index, daemon=True)
            index_thread.start()
        
        from nabdcode.core.mcp_adapter import MCPAdapter
        from nabdcode.core.mcp_stdio import run_mcp_stdio_server
        
        adapter = MCPAdapter(agent.tool_registry)
        import asyncio
        asyncio.run(run_mcp_stdio_server(adapter, original_stdout=original_stdout))
        sys.exit(0)

    if args.headless:
        if not args.task:
            console.print("[bold red]❌ خطأ: الوضع بدون رأس (--headless) يتطلب تمرير مهمة عبر المعامل --task أو -t[/bold red]")
            sys.exit(1)

        console.print(f"[bold cyan]🤖 المهمة المطلوبة:[/bold cyan] {args.task}")

        # استخدام Status من Rich لإظهار تقدم العمل
        with console.status("[bold yellow]جاري تهيئة الوكيل وفهم الطلب...[/bold yellow]", spinner="dots") as status:

            status.update("[bold blue]جاري تحميل الذاكرة RAG...[/bold blue]")
            if args.index or not agent.vector_db.load_index():
                status.update("[bold blue]جاري فهرسة بيئة العمل وبناء الذاكرة RAG...[/bold blue]")
                agent.index_workspace(force=True)

            status.update("[bold blue]جاري تشغيل المعالجة والبحث في الملفات...[/bold blue]")
            response = agent.process_request_sync(args.task)

            status.update("[bold green]✔ تم الانتهاء من توليد الكود![/bold green]")

        # معالجة المخرجات بعد انتهاء المؤشر
        if args.out:
            try:
                with open(args.out, 'w', encoding='utf-8') as f:
                    f.write(response)
                console.print(f"[bold green]💾 تم حفظ النتيجة بنجاح في:[/bold green] {args.out}")
            except Exception as e:
                console.print(f"[bold red]❌ حدث خطأ أثناء حفظ الملف:[/bold red] {e}")
                console.print("\n[bold cyan]النتيجة المستخرجة:[/bold cyan]\n")
                console.print(response)
        else:
            console.print("\n[bold cyan]النتيجة:[/bold cyan]\n")
            console.print(response)

        sys.exit(0)
        
    else:
        # الوضع التفاعلي الطبيعي
        # with Live(Spinner("dots", text="[cyan]Booting Agent OS...[/cyan]"), refresh_per_second=10):
        # محاولة تحميل الفهرس المحفوظ أولاً
        if args.index or not agent.vector_db.load_index():
            # إذا لم يكن هناك فهرس محفوظ أو تم تمرير --index، قم بالفهرسة
            # with Live(Spinner("dots", text="[cyan]Indexing Workspace...[/cyan]"), refresh_per_second=10):
                agent.index_workspace()

        if args.auto:
            ui.print_system_alert("⚠️ [WARNING]: AUTONOMOUS MODE ENGAGED. Commands will execute without confirmation.")

        #console.print("[bold green]🚀 بدء تشغيل NabdCode التفاعلي...[/bold green]")
        ui.print_header(agent.llm_client)
        interactive_menu(agent, ui)


if __name__ == "__main__":
    main()
