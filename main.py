import socket
import threading
import re
from urllib.parse import urlparse

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

# ---------- Background Colors ----------
Window.clearcolor = get_color_from_hex("#0d1117")

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "TELNET", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 443: "HTTPS",
    1433: "MSSQL", 3306: "MYSQL", 8080: "HTTP-ALT"
}


def is_valid_domain(domain):
    if not domain:
        return False
    pattern = re.compile(r"^[a-zA-Z0-9.-]+$")
    return bool(pattern.match(domain))


class ScannerLayout(BoxLayout):
    pass


class PortScannerApp(App):
    def build(self):
        self.title = "AYUSH Port Scanner"
        root = BoxLayout(orientation='vertical', padding=15, spacing=10)

        # ---------- Header ----------
        header = Label(
            text="[b]AYUSH PORT SCANNER[/b]",
            markup=True,
            font_size='22sp',
            size_hint=(1, 0.08),
            color=get_color_from_hex("#58a6ff")
        )
        root.add_widget(header)

        # ---------- Input Row ----------
        input_row = BoxLayout(orientation='horizontal', size_hint=(1, 0.08), spacing=10)
        self.url_input = TextInput(
            hint_text="वेबसाइट का नाम या URL डालें (जैसे: google.com)",
            multiline=False,
            size_hint=(0.7, 1),
            background_color=get_color_from_hex("#161b22"),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1),
            padding=[10, 10, 10, 10]
        )
        input_row.add_widget(self.url_input)

        self.scan_btn = Button(
            text="SCAN",
            size_hint=(0.3, 1),
            background_color=get_color_from_hex("#238636"),
            background_normal=''
        )
        self.scan_btn.bind(on_press=self.start_scan_thread)
        input_row.add_widget(self.scan_btn)

        root.add_widget(input_row)

        # ---------- Output Area (Scrollable) ----------
        scroll = ScrollView(size_hint=(1, 0.84))
        self.output_label = Label(
            text="यहाँ रिजल्ट दिखेगा...\n",
            size_hint_y=None,
            font_size='14sp',
            markup=True,
            halign='left',
            valign='top',
            color=(0.85, 0.85, 0.85, 1)
        )
        self.output_label.bind(
            width=lambda *x: self.output_label.setter('text_size')(
                self.output_label, (self.output_label.width, None)
            ),
            texture_size=lambda *x: self.output_label.setter('height')(
                self.output_label, self.output_label.texture_size[1]
            )
        )
        scroll.add_widget(self.output_label)
        root.add_widget(scroll)

        return root

    def start_scan_thread(self, instance):
        user_input = self.url_input.text.strip()
        if not user_input:
            self.update_output("[color=ff5555][-] पहले कोई URL या डोमेन डालें![/color]")
            return

        self.scan_btn.disabled = True
        self.update_output("[color=ffd33d][+] स्कैनिंग शुरू हो रही है, कृपया प्रतीक्षा करें...[/color]\n")

        t = threading.Thread(target=self.get_info_from_url, args=(user_input,))
        t.daemon = True
        t.start()

    @mainthread
    def update_output(self, text, append=True):
        if append:
            self.output_label.text += text + "\n"
        else:
            self.output_label.text = text + "\n"

    def get_info_from_url(self, url):
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        try:
            parsed_url = urlparse(url)
            domain = parsed_url.hostname if parsed_url.hostname else parsed_url.path

            if domain and ":" in domain:
                domain = domain.split(":")[0]
            if domain and "/" in domain:
                domain = domain.split("/")[0]

            if not is_valid_domain(domain):
                self.update_output("[color=ff5555][-] गलत URL/डोमेन फॉर्मेट! स्पेलिंग चेक करें।[/color]")
                self.enable_button()
                return

            self.update_output(f"[color=00e5ff][+] स्कैन हो रहा है: [b]{domain.upper()}[/b][/color]")

            try:
                ip_address = socket.gethostbyname(domain)
            except socket.gaierror:
                self.update_output("[color=ff5555][-] डोमेन मौजूद नहीं है! IP नहीं मिला।[/color]")
                self.enable_button()
                return

            self.update_output(f"[color=7ee787][+] IP एड्रेस मिला: [b]{ip_address}[/b][/color]\n")
            self.update_output("[color=8b949e]" + "-" * 40 + "[/color]")
            self.update_output(f"[b]{'PORT':<8}{'SERVICE':<12}STATUS[/b]")
            self.update_output("[color=8b949e]" + "-" * 40 + "[/color]")

            open_ports = []
            threads = []
            lock = threading.Lock()

            for port, service in COMMON_PORTS.items():
                t = threading.Thread(
                    target=self.scan_single_port,
                    args=(ip_address, port, service, open_ports, lock)
                )
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            for port, service in COMMON_PORTS.items():
                if (port, service) in open_ports:
                    self.update_output(
                        f"{port:<8}{service:<12}[color=3fb950][OPEN][/color]"
                    )
                else:
                    self.update_output(
                        f"{port:<8}{service:<12}[color=f85149][CLOSED][/color]"
                    )

            self.update_output("[color=8b949e]" + "-" * 40 + "[/color]")
            self.update_output("[color=ffd33d][+] स्कैन पूरा हुआ![/color]\n")

        except Exception as e:
            self.update_output(f"[color=ff5555][-] कुछ गड़बड़ हुई: {e}[/color]")
        finally:
            self.enable_button()

    @mainthread
    def enable_button(self):
        self.scan_btn.disabled = False

    def scan_single_port(self, ip_address, port, service, open_ports, lock):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            result = sock.connect_ex((ip_address, port))
            if result == 0:
                with lock:
                    open_ports.append((port, service))
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    PortScannerApp().run()
