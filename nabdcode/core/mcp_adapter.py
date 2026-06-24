import json
import asyncio
import logging
from typing import Dict, Any, List, Optional


class MCPClientAdapter:
    """
    Production-ready MCP client adapter for NabdCode.
    Communicates with external MCP servers via stdio transport.
    """

    REQUEST_TIMEOUT = 30

    def __init__(
        self,
        server_path: str,
        server_args: Optional[List[str]] = None,
    ):
        self.server_path = server_path
        self.server_args = server_args or []

        self.process: Optional[
            asyncio.subprocess.Process
        ] = None

        self.request_id = 1

        self._initialized = False
        self._tools_cache: Optional[
            List[Dict[str, Any]]
        ] = None

        self._request_lock = asyncio.Lock()

        self._stderr_task = None

    # --------------------------------------------------
    # Startup
    # --------------------------------------------------

    async def start_server(self) -> bool:

        try:

            self.process = (
                await asyncio.create_subprocess_exec(
                    self.server_path,
                    *self.server_args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )

            self._stderr_task = (
                asyncio.create_task(
                    self._monitor_stderr()
                )
            )

            initialized = (
                await self.initialize()
            )

            return initialized

        except Exception:
            return False

    # --------------------------------------------------
    # Handshake
    # --------------------------------------------------

    async def initialize(self) -> bool:

        if self._initialized:
            return True

        try:

            response = await self._send_request(
                "initialize",
                {
                    "clientInfo": {
                        "name": "NabdCode",
                        "version": "0.1.0"
                    }
                }
            )

            if "error" in response:
                return False

            self._initialized = True

            return True

        except Exception:
            return False

    # --------------------------------------------------
    # STDERR Monitor
    # --------------------------------------------------

    async def _monitor_stderr(self):

        if (
            not self.process
            or not self.process.stderr
        ):
            return

        try:

            while True:

                line = (
                    await self.process.stderr.readline()
                )

                if not line:
                    break

                message = (
                    line.decode(
                        "utf-8",
                        errors="ignore"
                    )
                    .strip()
                )

                print(
                    f"[MCP STDERR] {message}"
                )

        except Exception:
            pass

    # --------------------------------------------------
    # JSON-RPC Core
    # --------------------------------------------------

    async def _send_request(
        self,
        method: str,
        params: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:

        if (
            not self.process
            or not self.process.stdin
            or not self.process.stdout
        ):
            raise RuntimeError(
                "MCP server is not running."
            )

        async with self._request_lock:

            current_id = self.request_id
            self.request_id += 1

            payload = {
                "jsonrpc": "2.0",
                "id": current_id,
                "method": method,
                "params": params or {},
            }

            request = (
                json.dumps(payload)
                + "\n"
            )

            self.process.stdin.write(
                request.encode("utf-8")
            )

            await self.process.stdin.drain()

            response_line = (
                await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=self.REQUEST_TIMEOUT,
                )
            )

            if not response_line:
                raise RuntimeError(
                    "MCP server closed connection."
                )

            response = json.loads(
                response_line.decode("utf-8")
            )

            response_id = response.get("id")

            if (
                response_id is not None
                and response_id != current_id
            ):
                raise RuntimeError(
                    f"JSON-RPC ID mismatch "
                    f"({current_id} != "
                    f"{response_id})"
                )

            return response

    # --------------------------------------------------
    # Tools
    # --------------------------------------------------

    async def list_tools(
        self,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:

        if (
            use_cache
            and self._tools_cache
        ):
            return self._tools_cache

        try:

            response = (
                await self._send_request(
                    "tools/list"
                )
            )

            if "error" in response:
                return []

            tools = (
                response
                .get("result", {})
                .get("tools", [])
            )

            self._tools_cache = tools

            return tools

        except Exception:
            return []

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:

        try:

            response = (
                await self._send_request(
                    "tools/call",
                    {
                        "name": tool_name,
                        "arguments": arguments,
                    }
                )
            )

            if "error" in response:

                return {
                    "success": False,
                    "error": response[
                        "error"
                    ],
                }

            return {
                "success": True,
                "result": response.get(
                    "result",
                    {}
                ),
            }

        except asyncio.TimeoutError:

            return {
                "success": False,
                "error": "Tool call timeout",
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e),
            }

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------

    async def ping(self) -> bool:

        try:

            response = (
                await self._send_request(
                    "ping"
                )
            )

            return "error" not in response

        except Exception:
            return False

    async def get_server_info(
        self,
    ) -> Dict[str, Any]:

        try:

            response = (
                await self._send_request(
                    "server/info"
                )
            )

            return response.get(
                "result",
                {}
            )

        except Exception:

            return {}

    # --------------------------------------------------
    # Shutdown
    # --------------------------------------------------

    async def stop_server(self):

        if not self.process:
            return

        try:

            self.process.terminate()

            await asyncio.wait_for(
                self.process.wait(),
                timeout=5,
            )

        except asyncio.TimeoutError:

            self.process.kill()

            await self.process.wait()

        except Exception:
            pass

        finally:

            if self._stderr_task:
                self._stderr_task.cancel()

            self.process = None

            self._initialized = False

            self._tools_cache = None


class MCPAdapter:
    """
    المحول الأساسي: يقوم بتكييف سجل أدوات NabdCode لتتوافق مع 
    معيار بروتوكول سياق النموذج (MCP) عبر JSON-RPC 2.0.
    """
    def __init__(self, tool_registry: Any):
        self.registry = tool_registry
        # MCP تعتمد على async/await، لذا يجب أن يكون المحول متزامناً بالكامل
        self.logger = logging.getLogger(__name__)

    async def process_payload(self, payload: str) -> str:
        """يحلل حمولة MCP الواردة (JSON-RPC) ويوجهها ديناميكياً."""
        request = None
        try:
            request = json.loads(payload)
            req_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            # مسار توجيه بروتوكول MCP القياسي
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "nabdcode-mcp-server",
                        "version": "0.1.0"
                    }
                }
            elif method == "notifications/initialized":
                # Notification has no response
                return ""
            elif method == "tools/list":
                result = self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(params)
            else:
                # If it's a notification (no ID), just ignore it silently
                if req_id is None:
                    return ""
                return self._build_error(req_id, -32601, f"Method not found: {method}")

            return self._build_response(req_id, result)

        except json.JSONDecodeError:
            # خطأ في بناء جملة JSON
            return self._build_error(None, -32700, "Parse error: Invalid JSON")
        except Exception as e:
            logger.error(f"MCP Internal Error: {e}", exc_info=True)
            req_id = request.get("id") if isinstance(request, dict) else None
            return self._build_error(req_id, -32603, f"Internal server error: {str(e)}")

    def _handle_list_tools(self) -> dict[str, Any]:
        """يترجم أدوات السجل المحلي ديناميكياً إلى صيغة MCP."""
        tools_list = []
        for name, tool_data in self.registry.get_all_tools().items():
            tools_list.append({
                "name": name,
                "description": tool_data.get("description", ""),
                "inputSchema": tool_data.get("args_schema", {})
            })
        return {"tools": tools_list}

    async def _handle_call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        """ينفذ الأداة عبر السجل ويغلف المخرجات بأمان (يدعم Async Tools)."""
        name = params.get("name")
        args = params.get("arguments", {})
        
        # 1. التحقق من الإدخالات (Validation)
        if not name:
            # خطأ معياري: معاملات غير صالحة
            return {
                "content": [{"type": "text", "text": "Error: 'name' parameter is required."}],
                "isError": True
            }
        
        try:
            # 2. تنفيذ الأداة (باستخدام await لأن MCP يتطلب async I/O)
            output = await self.registry.execute_tool(name, args)
            
            # 3. تحويل المخرجة بأمان (إذا كانت JSON أو Dict، يتم تحويلها لنص)
            if isinstance(output, (dict, list)):
                output_text = json.dumps(output, ensure_ascii=False)
            else:
                output_text = str(output)
                
            return {
                "content": [{"type": "text", "text": output_text}],
                "isError": False
            }
        except Exception as e:
            # حماية حلقة ReAct عبر إرسال الخطأ كاستجابة معيارية وليس كانهيار
            logger.error(f"Tool execution failed via MCP: {name} - {e}")
            return {
                "content": [{"type": "text", "text": f"Execution Error: {str(e)}"}],
                "isError": True
            }

    def _build_response(self, req_id: Any, result: dict[str, Any]) -> str:
        """يبني استجابة JSON-RPC 2.0 ناجحة."""
        response = {"jsonrpc": "2.0", "id": req_id, "result": result}
        return json.dumps(response, ensure_ascii=False)

    def _build_error(self, req_id: Any, code: int, message: str) -> str:
        """يبني استجابة JSON-RPC 2.0 خطأ."""
        error = {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
        return json.dumps(error, ensure_ascii=False)
