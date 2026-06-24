from typing import Callable

class NabdStreamingThinkParser:
    def __init__(self): self.reset()
    def reset(self): self.in_thinking = self.in_discarding = False; self.buf = ""
    
    def flush(self, on_text: Callable[[str], None], on_thought: Callable[[str], None]):
        if self.buf and not self.in_discarding: (on_thought if self.in_thinking else on_text)(self.buf)
        self.buf = ""
        
    def feed(self, chunk: str, enable_thinking: bool, on_text: Callable[[str], None], on_thought: Callable[[str], None]):
        self.buf += chunk
        while self.buf:
            if self.in_discarding:
                if "</think>" in self.buf: self.buf, self.in_discarding = self.buf.split("</think>", 1)[1], False
                elif (p := next((s for s in ["</think", "</thin", "</thi", "</th", "</t", "</", "<"] if self.buf.endswith(s)), "")): self.buf = p; break
                else: self.buf = ""; break
            elif not self.in_thinking:
                if "<think>" in self.buf: a, self.buf = self.buf.split("<think>", 1); on_text(a); self.in_thinking, self.in_discarding = enable_thinking, not enable_thinking
                elif (p := next((s for s in ["<think", "<thin", "<thi", "<th", "<t", "<"] if self.buf.endswith(s)), "")): on_text(self.buf[:-len(p)]); self.buf = p; break
                else: on_text(self.buf); self.buf = ""; break
            else:
                if "</think>" in self.buf: a, self.buf = self.buf.split("</think>", 1); on_thought(a); self.in_thinking = False
                elif (p := next((s for s in ["</think", "</thin", "</thi", "</th", "</t", "</", "<"] if self.buf.endswith(s)), "")): on_thought(self.buf[:-len(p)]); self.buf = p; break
                else: on_thought(self.buf); self.buf = ""; break
