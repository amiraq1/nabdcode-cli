#!/usr/bin/env python3
"""
NabdCode TUI - مشابه لـ OpenCode باستخدام prompt_toolkit
"""
import os
import sys
import threading
import pyfiglet
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML, ANSI
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.widgets import TextArea, Frame, Box
from prompt_toolkit.application.current import get_app

# =================== الشعار ===================
def get_logo():
    try:
        import pyfiglet
        logo = pyfiglet.figlet_format('nabdcode', font='digital')
        return logo
    except:
        return 'nabdcode'

# =================== الستايل ===================
STYLE = Style.from_dict({
    'logo':           '#00ffcc bold',
    'chat-area':      '#e0e0e0',
    'user-msg':       '#00ffcc bold',
    'ai-msg':         '#4da6ff',
    'system-msg':     '#888888 italic',
    'input-box':      'bg:#111111 #ffffff',
    'input-border':   '#1a6bff bold',
    'info-bar':       'bg:#111111 #888888',
    'info-mode':      'bg:#111111 #1a6bff bold',
    'info-model':     'bg:#111111 #ffffff bold',
    'info-provider':  'bg:#111111 #555555',
    'shortcuts':      '#444444',
    'status-bar':     '#333333',
    'frame':          '#1a6bff',
})

class NabdCodeTUI:
    def __init__(self, agent=None, config_manager=None):
        self.agent = agent
        self.is_processing = False
        self.messages = []
        self._get_provider_info(config_manager)
        self._build_ui()

    def _get_provider_info(self, config_manager):
        try:
            if config_manager:
                p = config_manager.get_active_provider()
                self.provider_name = p.get("name", "OpenRouter")
                self.model_name = p.get("model", "gemma-4-31b")
            else:
                self.provider_name = "OpenRouter"
                self.model_name = "google/gemma-4-31b"
        except:
            self.provider_name = "OpenRouter"
            self.model_name = "gemma-4-31b"
        self.mode_name = "Build"

    def _get_chat_text(self):
        if not self.messages:
            return HTML('<system-msg>● NabdCode جاهز. اكتب طلبك أو /help للأوامر</system-msg>')
        
        lines = []
        for msg in self.messages:
            if msg['role'] == 'user':
                lines.append(f'<user-msg>▶ أنت</user-msg>')
                lines.append(f'{msg["content"]}')
                lines.append('')
            elif msg['role'] == 'ai':
                lines.append(f'<ai-msg>◀ NabdCode</ai-msg>')
                lines.append(f'{msg["content"]}')
                lines.append('')
            elif msg['role'] == 'system':
                lines.append(f'<system-msg>{msg["content"]}</system-msg>')
        
        return HTML('\n'.join(lines))

    def _get_info_bar(self):
        return HTML(
            f'<info-mode> {self.mode_name} </info-mode>'
            f'<info-bar> · </info-bar>'
            f'<info-model>{self.model_name}</info-model>'
            f'<info-bar> </info-bar>'
            f'<info-provider>{self.provider_name}</info-provider>'
        )

    def _get_shortcuts(self):
        return HTML(
            '<shortcuts>  tab</shortcuts> agents  '
            '<shortcuts>ctrl+p</shortcuts> commands  '
            '<shortcuts>ctrl+c</shortcuts> quit'
        )

    def _get_status(self):
        cwd = os.getcwd()
        return HTML(f'<status-bar>{cwd}  v2.0.0</status-bar>')

    def _get_logo(self):
        return HTML(f'<logo>{get_logo()}</logo>')

    def _build_ui(self):
        # حقل الإدخال
        self.input_buffer = Buffer(
            multiline=False,
            accept_handler=self._on_submit,
        )

        # تحديث المحادثة
        self.chat_control = FormattedTextControl(
            text=self._get_chat_text,
            focusable=False,
        )

        # Layout
        self.layout = Layout(
            HSplit([
                # الشعار
                Window(
                    content=FormattedTextControl(self._get_logo),
                    height=D(preferred=6, max=6),
                    align='center',
                ),
                # منطقة المحادثة
                Window(
                    content=self.chat_control,
                    wrap_lines=True,
                    scroll_offsets=None,
                    right_margins=[ScrollbarMargin()],
                ),
                # حقل الإدخال مع إطار أزرق
                Frame(
                    body=HSplit([
                        Window(
                            content=BufferControl(buffer=self.input_buffer),
                            height=1,
                            style='class:input-box',
                        ),
                        Window(
                            content=FormattedTextControl(self._get_info_bar),
                            height=1,
                            style='class:info-bar',
                        ),
                    ]),
                    style='class:frame',
                ),
                # اختصارات
                Window(
                    content=FormattedTextControl(self._get_shortcuts),
                    height=1,
                    align='right',
                ),
                # شريط الحالة
                Window(
                    content=FormattedTextControl(self._get_status),
                    height=1,
                    style='class:status-bar',
                ),
            ])
        )

        # Key bindings
        kb = KeyBindings()

        @kb.add('c-c')
        @kb.add('c-q')
        def _exit(event):
            event.app.exit()

        @kb.add('c-p')
        def _commands(event):
            self._show_commands()

        @kb.add('escape')
        def _clear(event):
            self.input_buffer.text = ''

        self.app = Application(
            layout=self.layout,
            key_bindings=kb,
            style=STYLE,
            full_screen=True,
            mouse_support=True,
            color_depth=None,
        )

    def _on_submit(self, buffer):
        text = buffer.text.strip()
        if not text:
            return
        
        buffer.text = ''

        if text.lower() in ['exit', 'quit', 'خروج']:
            self.app.exit()
            return

        if text.startswith('/'):
            self._handle_command(text)
            return

        self.messages.append({'role': 'user', 'content': text})

        if not self.is_processing:
            self.is_processing = True
            threading.Thread(
                target=self._process,
                args=(text,),
                daemon=True
            ).start()

    def _process(self, text):
        self.messages.append({'role': 'system', 'content': '●●● NabdCode يحلل...'})
        try:
            if self.agent:
                response = self.agent.process_request(text)
            else:
                response = f'[تجريبي] استلمت: {text}'
            
            # احذف رسالة التحليل
            self.messages = [m for m in self.messages if m['content'] != '●●● NabdCode يحلل...']
            self.messages.append({'role': 'ai', 'content': response})

        except Exception as e:
            self.messages = [m for m in self.messages if m['content'] != '●●● NabdCode يحلل...']
            self.messages.append({'role': 'system', 'content': f'✗ خطأ: {str(e)}'})
        finally:
            self.is_processing = False
            try:
                self.app.invalidate()
            except:
                pass

    def _handle_command(self, cmd):
        if cmd == '/help':
            self._show_commands()
        elif cmd == '/clear':
            self.messages = []
        else:
            self.messages.append({'role': 'system', 'content': f'أمر غير معروف: {cmd}'})

    def _show_commands(self):
        self.messages.append({'role': 'system', 'content': '''
━━━ الأوامر ━━━
/help    مساعدة
/clear   مسح المحادثة
/plan    وضع التخطيط
exit     خروج
'''})

    def run(self):
        self.app.run()


def launch_tui(agent=None, config_manager=None):
    tui = NabdCodeTUI(agent=agent, config_manager=config_manager)
    tui.run()


if __name__ == '__main__':
    launch_tui()
