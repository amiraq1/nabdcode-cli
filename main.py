import sys
import os
import traceback

# إنشاء ملف سجل مخفي
log_file = open(".nabd.log", "a", encoding="utf-8")
# إعادة توجيه مخرجات الأخطاء والسجلات إلى الملف
sys.stderr = log_file
sys.stdout = log_file

import logging
import asyncio
import argparse
from pathlib import Path
from nabdcode.ui.cyberpunk_ui import CyberpunkUI

ui = CyberpunkUI()

# 1. كتم سجلات مكتبة httpx تماماً لمنع طباعة طلبات الـ HTTP
logging.getLogger("httpx").setLevel(logging.WARNING)

# 2. كتم سجلات العميل الداخلي لنواة نبض (llm_client)
logging.getLogger("nabdcode.core.llm_client").setLevel(logging.WARNING)

# 3. إعداد عام للتأكد من أن الكونسول لا يستقبل إلا الأخطاء الحرجة فقط
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

async def _initialize_agent_async():
    import os, tomllib
    from nabdcode.ui.console import ConsoleUI
    from nabdcode.core.agent import NabdAgent
    from nabdcode.core.providers import OpenRouterProvider, ProviderConfig
    from nabdcode.core.tools.registry import NabdToolRegistry
    from nabdcode.tools.registry import ToolRegistry
    from nabdcode.core.skills_manager import SkillsManager

    # ── قراءة config.toml ──────────────────────────────────────
    try:
        with open("config.toml", "rb") as f:
            full_config = tomllib.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read config.toml: {e}")
        full_config = {}

    # تحديد الـ provider النشط من [general]
    general    = full_config.get("general", {})
    providers  = full_config.get("providers", {})
    active     = general.get("active_provider", "nvidia")
    c          = providers.get(active, {})

    if not c:
        print(f"[ERROR] Provider '{active}' not found in config.toml!")
        print(f"[INFO]  Available providers: {list(providers.keys())}")

    # قراءة الـ API Key من الملف فقط — تجاهل env variables تماماً
    k = c.get("api_key", "")
    k = "".join([ch for ch in str(k) if ch.isalnum() or ch in "-_."]).strip()

    if not k:
        print(f"[ERROR] api_key is empty for provider '{active}' in config.toml!")
    else:
        from nabdcode.ui.cyberpunk_ui import CyberpunkLogo, console as ui_console
        CyberpunkLogo(ui_console).animate(provider=active, model=c.get('model', 'N/A'))

    # ── تهيئة الـ Registry ─────────────────────────────────────
    real_registry = ToolRegistry()

    # ── تحميل الـ Skills ───────────────────────────────────────
    skill_manager = SkillsManager(registry=real_registry)
    loaded_skills = skill_manager.load_all_skills()
    print(f"[Boot] Loaded skills: {loaded_skills}")

    # ── Bridge Registry ────────────────────────────────────────
    bridge_registry = NabdToolRegistry(providers=[])
    bridge_registry.legacy_registry = real_registry

    # Clean the model string from any hidden zero-width spaces or garbage
    raw_model = str(c.get("model", "meta/llama-3.1-70b-instruct"))
    clean_model = "".join(ch for ch in raw_model if ch.isprintable() and ord(ch) < 128).strip()

    # ── Provider Config ────────────────────────────────────────
    p_cfg = ProviderConfig(
        api_key         = k,
        model_id        = clean_model,
        base_url        = c.get("base_url", "https://integrate.api.nvidia.com/v1"),
        temperature     = general.get("temperature", 0.7),
        thinking_enabled= False
    )

    agent = NabdAgent(provider=OpenRouterProvider(), registry=bridge_registry)
    agent.tool_registry = real_registry
    agent.ui, agent.p_cfg = ConsoleUI(), p_cfg
    
    # print(f"[DEBUG] MCP Tools Loaded: {len(real_registry.mcp_tools_cache)}")
    from nabdcode.core.tools.registry import GenerationContext
    tools = bridge_registry.get_definitions(GenerationContext())
    # print(f"[DEBUG] FINAL TOOL COUNT: {len(tools)}")
    # print(f"[DEBUG] TOOLS: {[t.get('name') for t in tools]}")
    
    print(f"[Boot] OpenRouter provider active targeting: {p_cfg.model_id}")
    return agent, p_cfg

async def start_interactive_shell_async(agent, cfg):
    """
    حلقة تفاعلية غير متزامنة بالكامل (Native Async REPL) ومتوافقة مع الـ BiDi.
    تستخدم Rich للمخرجات لضمان سلامة وتنسيق النص العربي.
    """
    from rich.console import Console
    from nabdcode.ui.console import fix_arabic_text
    
    console = Console(file=sys.__stdout__)
    from rich.align import Align
    console.print(Align.center("[bold white]FUTURE PULSE[/bold white]"))
    console.print("")
    
    # جلب حلقة الحدث الحالية
    loop = asyncio.get_running_loop()
    
    interrupt_count = 0
    while True:
        try:
            # 1. إدخال المستخدم
            user_input = await loop.run_in_executor(
                None, ui.get_input
            )
            user_input = user_input.strip()
            
            # شروط الخروج
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit', 'خروج']:
                console.print(fix_arabic_text("\n👋 [bold cyan]وداعاً! تم إغلاق نبض كود بأمان.[/bold cyan]"))
                break
                
            interrupt_count = 0  # Reset on successful input
            
            try:
                # توجيه الطلب إلى العقل الاستراتيجي (الوكيل) عبر المرحلتين (التخطيط ثم التنفيذ)
                with console.status("◈ nabdcode...", spinner="dots", spinner_style="cyan"):
                    await agent.process_request(user_input, cfg)
            except Exception as e:
                logger.critical(f"Agent Error: {e}", exc_info=True)
                console.print(fix_arabic_text(f"\n❌ [bold red][SYSTEM ERROR] حدث خطأ أثناء المعالجة: {e}[/bold red]\n"))
            
        except KeyboardInterrupt:
            interrupt_count += 1
            if interrupt_count >= 2:
                console.print(fix_arabic_text("\n👋 [bold cyan]تم استلام إشارة الخروج النهائي. وداعاً![/bold cyan]"))
                break
            console.print(fix_arabic_text("\n\n⚠️ [bold orange3]تم إلغاء المهمة الحالية. اضغط Ctrl+C مرة أخرى للخروج النهائي.[/bold orange3]"))
            continue
        except EOFError:
            console.print(fix_arabic_text("\n👋 [bold cyan]تم استلام إشارة الخروج. وداعاً![/bold cyan]"))
            break
        except Exception as e:
            logger.error(f"REPL Loop Error: {e}")
            console.print(fix_arabic_text(f"\n⚠️ [bold red]خطأ في واجهة الاستقبال: {e}[/bold red]\n"))

import contextlib

@contextlib.asynccontextmanager
async def lifespan_manager():
    """Master Orchestrator to manage background services lifecycle."""
    from rich.console import Console
    console = Console(file=sys.__stderr__)
    console.print("\n[bold cyan]◈ Igniting Subsystem Services...[/bold cyan]")
    
    # 1. Start Telemetry API
    telemetry_process = await asyncio.create_subprocess_exec(
        sys.executable, "telemetry_api.py",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    
    # 2. Start Proxy Server (Mockup command - adjust as needed)
    proxy_process = await asyncio.create_subprocess_shell(
        "cd CLIProxyAPI && npm run start",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    
    try:
        yield
    finally:
        console.print("\n[bold cyan]◈ Terminating Subsystems gracefully...[/bold cyan]")
        for process in [telemetry_process, proxy_process]:
            if process.returncode is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
        await asyncio.gather(telemetry_process.wait(), proxy_process.wait())

def main():
    # 1. استخدام argparse لتحليل الأوامر بشكل احترافي وآمن
    parser = argparse.ArgumentParser(description="NabdCode CLI - Personalized AI Coding Assistant")
    parser.add_argument("--mcp", action="store_true", help="Run NabdCode as a silent MCP server via Stdio")
    args = parser.parse_args()

    if args.mcp:
        # ==========================================
        # مسار الخادم الصامت (MCP Server Mode)
        # ==========================================
        # Surgical Fix: تحويل sys.stdout إلى sys.stderr فوراً لمنع أي تلوث للمخرج القياسي
        original_stdout = sys.stdout
        sys.stdout = sys.stderr

        # إجبار بايثون على توجيه كافة السجلات المستقبلية إلى stderr حصراً
        logging.basicConfig(stream=sys.stderr, level=logging.INFO, force=True)
        logger.info("Starting NabdCode in MCP Server Mode...")
        
        async def run_mcp_server_async():
            try:
                # تهيئة الوكيل بشكل غير متزامن (خفيف وسريع)
                agent, cfg = await _initialize_agent_async()
                
                # الفهرسة الكسولة في الخلفية (Background Lazy Indexing)
                import threading
                workspace = os.getcwd()
                
                def background_index():
                    try:
                        if hasattr(agent, 'memory_manager') and agent.memory_manager:
                            logger.info("Starting background workspace indexing...")
                            agent.memory_manager.index_workspace(workspace, silent=True)
                            logger.info("Background indexing completed successfully.")
                    except Exception as e:
                        logger.warning(f"Background indexing failed: {e}")
     
                # تشغيل الفهرسة كـ Daemon Thread يموت تلقائياً عند إغلاق الخادم
                index_thread = threading.Thread(target=background_index, daemon=True)
                index_thread.start()
                
                # تشغيل المحول وخادم الـ Stdio فوراً دون انتظار الفهرسة
                from nabdcode.core.mcp_adapter import MCPAdapter
                from nabdcode.core.mcp_stdio import run_mcp_stdio_server
                
                adapter = MCPAdapter(agent.tool_registry)
                await run_mcp_stdio_server(adapter, original_stdout=original_stdout)
                
            except KeyboardInterrupt:
                logger.info("MCP Server stopped by user.")
            except Exception as e:
                logger.critical(f"Failed to start MCP Server: {e}", exc_info=True)
                sys.exit(1)

        asyncio.run(run_mcp_server_async())
        sys.exit(0)

    else:
        # ==========================================
        # المسار التفاعلي البشري (Interactive CLI Mode)
        # ==========================================
        try:
            async def run_interactive_async():
                async with lifespan_manager():
                    agent, cfg = await _initialize_agent_async()
                    # الفهرسة في الخلفية (غير حاجبة) لتسريع الإقلاع
                    if hasattr(agent, 'memory_manager') and agent.memory_manager:
                        asyncio.create_task(asyncio.to_thread(
                            agent.memory_manager.index_workspace, os.getcwd()
                        ))
                    
                    # بدء حلقة المحادثة (REPL) هنا مستقبلاً
                    await start_interactive_shell_async(agent, cfg)
                    
                    # الإغلاق الآمن للأنظمة (حفظ الذاكرة)
                    if hasattr(agent, 'memory_manager') and agent.memory_manager and hasattr(agent.memory_manager, 'vector_db') and hasattr(agent.memory_manager.vector_db, 'close'):
                        agent.memory_manager.vector_db.close()

            asyncio.run(run_interactive_async())
            
        except BaseException as boot_error:
            print(f"\n🚨 [تم اصطياد الخروج المخفي]: {type(boot_error).__name__} - {boot_error}")
            print("🔍 تفاصيل مسار الانهيار (Traceback):")
            traceback.print_exc()
            logger.critical(f"CLI Startup Error: {boot_error}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    main()
