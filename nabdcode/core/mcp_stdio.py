# nabdcode/core/mcp_stdio.py
import sys
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

async def run_mcp_stdio_server(adapter, original_stdout=None) -> None:
    """
    طبقة النقل عبر Stdio لبروتوكول MCP.
    تؤسس حلقة أحداث مستمرة وصامتة على المخرجات القياسية (stdout).
    تمنع بشكل صارم أي طباعة غير JSON للحفاظ على سلامة البروتوكول.
    """
    # حفظ المخرج القياسي الأصلي للبروتوكول وتحويل sys.stdout القياسي إلى stderr لمنع أي تشويش
    if original_stdout is None:
        original_stdout = sys.stdout
    sys.stdout = sys.stderr

    # 1. إيقاف التخزين المؤقت (Buffering) لضمان استجابة لحظية للطلبات
    try:
        original_stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass  # تجاهل في الأنظمة التي لا تدعم reconfigure

    # 2. توجيه سجلات النظام إلى stderr بدلاً من إيقافها
    # (بروتوكول MCP يسمح لـ stderr بالمرور للـ Debugging دون كسر الـ stdout)
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("MCP Stdio Server started (Async). Waiting for JSON-RPC payloads...")

    loop = asyncio.get_running_loop()

    def get_line():
        return sys.stdin.readline()

    # 3. حلقة القراءة المستمرة (Event Loop)
    while True:
        try:
            line = await loop.run_in_executor(None, get_line)
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            # المعالجة المباشرة ضمن نفس الـ Event Loop المستمر
            response_json = await adapter.process_payload(line)
            
            # 4. الطباعة النظيفة للمخرج القياسي الأصلي وفلوش فوري
            if response_json:
                original_stdout.write(response_json + "\n")
                original_stdout.flush()
            
        except KeyboardInterrupt:
            logger.info("MCP Server shutting down gracefully (Ctrl+C).")
            break
            
        except Exception as e:
            # تغليف أي انهيار قاتل في استجابة MCP معيارية لكي لا ينكسر الـ Client
            logger.critical(f"Transport Error: {e}", exc_info=True)
            fallback_error = {
                "jsonrpc": "2.0",
                "id": None,  # ID غير معروف لأن الخطأ حدث قبل المعالجة
                "error": {"code": -32603, "message": f"Transport Error: {str(e)}"}
            }
            original_stdout.write(json.dumps(fallback_error) + "\n")
            original_stdout.flush()

    logger.info("MCP Stdio Server stopped.")
