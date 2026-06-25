"""
nabdcode/core/profiler.py
محرك تحليل الأداء والـ Inference (Local Profiler & Token Analytics)
يقيس سرعة التوليد، وقت الاستجابة، واستهلاك الموارد اللحظي بشكل سيبربانكي.
"""
import time
import os
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

console = Console()

class Profiler:
    def __init__(self):
        self.start_time: float = 0.0
        self.first_token_time: Optional[float] = None
        self.end_time: float = 0.0
        self.token_count: float = 0.0
        self._start_cpu = (0.0, 0.0)
        self._end_cpu = (0.0, 0.0)
        self.engine_name: str = "LiteRT Native"

    def start(self):
        self.start_time = time.time()
        self.first_token_time = None
        self.end_time = 0.0
        self.token_count = 0.0
        self._start_cpu = self._read_cpu_times()

    def record_chunk(self, chunk: str):
        if not chunk:
            return
            
        if self.first_token_time is None and chunk.strip():
            self.first_token_time = time.time()
            
        # تقدير تقريبي للتوكنز (1 توكن ≈ 4 حروف تقريباً للغة الإنجليزية والرموز البرمجية)
        self.token_count += len(chunk) / 4.0

    def stop(self):
        self.end_time = time.time()
        self._end_cpu = self._read_cpu_times()

    def _read_cpu_times(self):
        """يقرأ أوقات المعالج مباشرة من نظام Termux/Linux (دون الحاجة لـ psutil)."""
        try:
            with open('/proc/stat', 'r') as f:
                for line in f:
                    if line.startswith('cpu '):
                        parts = [float(p) for p in line.split()[1:]]
                        idle = parts[3] + parts[4]  # idle + iowait
                        total = sum(parts)
                        return total, idle
        except Exception:
            pass
        return 0.0, 0.0

    def _get_ram_info(self) -> str:
        """يقرأ استهلاك الذاكرة العشوائية بصمت وبدقة من /proc/meminfo."""
        try:
            mem = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split()
                    mem[parts[0].strip(':')] = int(parts[1])
                    
            total_kb = mem.get('MemTotal', 0)
            free_kb = mem.get('MemFree', 0)
            buffers_kb = mem.get('Buffers', 0)
            cached_kb = mem.get('Cached', 0)
            
            used_kb = total_kb - free_kb - buffers_kb - cached_kb
            if total_kb > 0:
                percent = (used_kb / total_kb) * 100
                used_mb = used_kb / 1024.0
                total_mb = total_kb / 1024.0
                return f"{used_mb:.1f} MB / {total_mb:.1f} MB ({percent:.1f}%)"
        except Exception:
            pass
            
        # Fallback
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            mb = usage / 1024.0
            return f"{mb:.2f} MB (App RSS)"
        except Exception:
            return "N/A"

    def _calculate_cpu_percent(self) -> str:
        t1, i1 = self._start_cpu
        t2, i2 = self._end_cpu
        
        if t1 == 0.0 or t2 == 0.0:
            return "N/A"
            
        delta_total = t2 - t1
        delta_idle = i2 - i1
        
        if delta_total > 0:
            percent = (1.0 - (delta_idle / delta_total)) * 100.0
            return f"{percent:.1f}%"
        return "N/A"



    def display_report(self):
        if not self.start_time or not self.end_time:
            return

        total_time = self.end_time - self.start_time
        ttft = (self.first_token_time - self.start_time) if self.first_token_time else 0.0
        generation_time = (self.end_time - self.first_token_time) if self.first_token_time else total_time
        tps = (self.token_count / generation_time) if generation_time > 0 else 0.0

        ttft_ms = int(ttft * 1000)
        cpu_load = self._calculate_cpu_percent()
        
        # تبسيط مساحة الرام لتناسب المربع الصغير
        ram_info = self._get_ram_info().split(" / ")[0] if " / " in self._get_ram_info() else self._get_ram_info()

        grid = Table(box=None, show_header=False, padding=(0, 4))
        grid.add_column("Col1", justify="left")
        grid.add_column("Col2", justify="left")

        grid.add_row(
            f"🚀 [bold cyan]TTFT:[/bold cyan] {ttft_ms}ms",
            f"⚡ [bold yellow]Velocity:[/bold yellow] {tps:.1f} T/s"
        )
        grid.add_row(
            f"🧠 [bold magenta]RAM Peak:[/bold magenta] {ram_info}",
            f"⚙️ [bold green]CPU Load:[/bold green] {cpu_load}"
        )
        grid.add_row(
            f"💎 [bold blue]Token Cost:[/bold blue] {int(self.token_count):,}",
            f"🛡️ [bold white]Engine:[/bold white] {self.engine_name}"
        )

        console.print()
        console.print(Panel(
            grid, 
            title="[bold white]NABD PERF PROFILER[/bold white]",
            border_style="cyan",
            expand=False
        ))

# مثيل عام للاستخدام المتكرر
profiler = Profiler()
