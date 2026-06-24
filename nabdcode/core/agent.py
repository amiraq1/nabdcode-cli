import asyncio
import logging
import sys
from rich.console import Console
from nabdcode.core.message_healer import limit_context, merge_consecutive_same_role
from nabdcode.core.streaming_parser import NabdStreamingThinkParser

console = Console(file=sys.__stdout__)

class NabdAgent:
    def __init__(self, provider, registry=None):
        self.p = provider
        # موجه نقي يركز على الكفاءة والسرعة بالإنجليزية
        self.REACTIVE_SYSTEM_PROMPT = "You are Nabd OS, a minimalist local AI agent operating inside Termux. Provide clean, highly optimized, production-ready code or concise technical answers directly in English without preambles."

    async def process_request(self, text: str, cfg) -> None:
        text = text.strip()
        
        # معالجة فورية للمحادثات العادية البسيطة لتقليل التكاليف والتوكنز
        conversational_indicators = ["hi", "hello", "hey", "who are you", "thanks", "thank you", "ok", "okay"]
        if any(indicator in text.lower() for indicator in conversational_indicators) and len(text) < 20:
            console.print(f"[bold cyan]💬 [Conversational Mode]: {text}[/bold cyan]")
            from nabdcode.core.model_manager import ModelManager
            mm = ModelManager()
            response = await asyncio.to_thread(
                mm.generate_response,
                system_prompt="You are NabdCode. Answer directly and briefly in English.",
                messages=[{"role": "user", "content": text}],
                temperature=0.6
            )
            console.print(f"\n[bold green]✅ Response:[/bold green] {response}")
            return

        console.print(f"[bold cyan]🧠 [Processing]: {text[:50]}...[/bold cyan]")
        
        messages = [
            {"role": "system", "content": self.REACTIVE_SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]
        
        pipe = merge_consecutive_same_role(limit_context(messages, 25))
        parser = NabdStreamingThinkParser()
        full_content = []

        def on_text(text_chunk: str):
            full_content.append(text_chunk)
            sys.__stdout__.write(text_chunk)
            sys.__stdout__.flush()

        console.print("[bold green]🚀 Starting reactive generation...[/bold green]\n")
        try:
            # استدعاء النموذج مباشرة بدون تمرير أي مصفوفة أدوات (Pure Text Mode)
            async for range_stream in self.p.generate_stream(pipe, cfg, None):
                c_type = range_stream.get("type", "content")
                if c_type == "content":
                    parser.feed(range_stream.get("chunk", ""), getattr(cfg, 'thinking_enabled', False), on_text, lambda x: None)
            parser.flush(on_text, lambda x: None)
        except Exception as e:
            console.print(f"\n[bold red]❌ Generation Error: {e}[/bold red]")
            return

        console.print("\n\n[bold green]🎯 Done.[/bold green]")

    def get_security_report(self):
        return {"status": "secured", "mode": "pure_generation"}
