import os
import time
import shutil
import itertools
import threading

import pyzipper

try:
    import py7zr
    HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.spinner import Spinner

EXTRACT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_extract_temp")


# ---------------------------------------------------------------------------
# Core cracking logic (same as original script, just refactored to report
# progress through callbacks instead of print()/input())
# ---------------------------------------------------------------------------

def list_archives(root="."):
    archives = []
    for dirpath, dirnames, filenames in os.walk(root):
        if os.path.abspath(dirpath) == os.path.abspath(EXTRACT_DIR):
            dirnames[:] = []
            continue
        for f in filenames:
            lf = f.lower()
            if lf.endswith('.zip') or lf.endswith('.7z'):
                archives.append(os.path.join(dirpath, f))
    return archives


def archive_type(path):
    return '7z' if path.lower().endswith('.7z') else 'zip'


def get_char_list(choice):
    if choice == "Only Capital Letters (A-Z)":
        return [chr(i) for i in range(65, 91)]
    elif choice == "Only Small Letters (a-z)":
        return [chr(i) for i in range(97, 123)]
    elif choice == "Only Numbers (0-9)":
        return [chr(i) for i in range(48, 58)]
    elif choice == "Letters + Numbers (Mix)":
        return [chr(i) for i in range(65, 91)] + [chr(i) for i in range(97, 123)] + [chr(i) for i in range(48, 58)]
    return []


def try_password_zip(zf, pwd):
    zf.setpassword(pwd.encode('utf-8'))
    try:
        zf.testzip()
        return True
    except (RuntimeError, pyzipper.BadZipFile):
        return False


def try_password_7z(path, pwd):
    """7z has no 'reuse handle, swap password' API like pyzipper, so each
    attempt opens a fresh archive object. Slower than the zip path, but
    that's an inherent 7z/py7zr limitation, not something we can avoid.

    Uses testzip() (CRC32 validation against the archive's stored
    checksums) rather than test(), since test() does not reliably
    detect a wrong password on all py7zr versions/archive types and can
    report false positives."""
    try:
        with py7zr.SevenZipFile(path, mode='r', password=pwd) as archive:
            bad_file = archive.testzip()
            return bad_file is None
    except Exception:
        return False


class Cracker:
    """Runs in a background thread. Calls back into the UI via Clock.schedule_once."""

    def __init__(self, zip_path, log_cb, done_cb, progress_cb):
        self.zip_path = zip_path
        self.log_cb = log_cb        # log_cb(text)
        self.done_cb = done_cb      # done_cb(success: bool, pwd: str|None)
        self.progress_cb = progress_cb  # progress_cb(attempts:int, current_pwd:str)
        self._stop = False

    def stop(self):
        self._stop = True

    def _log(self, text):
        Clock.schedule_once(lambda dt: self.log_cb(text))

    def _progress(self, attempts, pwd):
        Clock.schedule_once(lambda dt: self.progress_cb(attempts, pwd))

    def _finish(self, success, pwd, attempts=0, start_time=0):
        if success:
            os.makedirs(EXTRACT_DIR, exist_ok=True)
            try:
                if archive_type(self.zip_path) == '7z':
                    with py7zr.SevenZipFile(self.zip_path, mode='r', password=pwd) as archive:
                        archive.extractall(path=EXTRACT_DIR)
                else:
                    with pyzipper.AESZipFile(self.zip_path) as zf:
                        zf.setpassword(pwd.encode('utf-8'))
                        zf.extractall(path=EXTRACT_DIR)
            except Exception as e:
                self._log(f"\n[!] Password found but extraction failed: {e}")
            elapsed = time.time() - start_time
            self._log(f"\n✅ Password found: \"{pwd}\"")
            self._log(f"⏱️ Time: {elapsed:.2f}s | 📊 Attempts: {attempts}")
        Clock.schedule_once(lambda dt: self.done_cb(success, pwd))

    def run_manual(self, char_choice, length):
        chars = get_char_list(char_choice)
        atype = archive_type(self.zip_path)

        if atype == '7z' and not HAS_PY7ZR:
            self._log("\n[-] py7zr not installed. Run: pip install py7zr")
            self._finish(False, None)
            return

        self._log(f"[+] Cracking started ({atype}): {char_choice}, length {length}...")
        start_time = time.time()
        attempts = 0
        try:
            if atype == 'zip':
                with pyzipper.AESZipFile(self.zip_path) as zf:
                    for guess in itertools.product(chars, repeat=length):
                        if self._stop:
                            self._log("\n[-] Stopped by user.")
                            self._finish(False, None)
                            return
                        pwd = "".join(guess)
                        attempts += 1
                        if attempts % 200 == 0 or attempts == 1:
                            self._progress(attempts, pwd)
                        if try_password_zip(zf, pwd):
                            self._finish(True, pwd, attempts, start_time)
                            return
            else:
                for guess in itertools.product(chars, repeat=length):
                    if self._stop:
                        self._log("\n[-] Stopped by user.")
                        self._finish(False, None)
                        return
                    pwd = "".join(guess)
                    attempts += 1
                    if attempts % 50 == 0 or attempts == 1:
                        self._progress(attempts, pwd)
                    if try_password_7z(self.zip_path, pwd):
                        self._finish(True, pwd, attempts, start_time)
                        return
            self._log("\n[-] No password found within this range.")
            self._finish(False, None)
        except Exception as e:
            self._log(f"\n[-] Error: {e}")
            self._finish(False, None)

    def run_auto_numeric(self, with_leading_zeros):
        atype = archive_type(self.zip_path)

        if atype == '7z' and not HAS_PY7ZR:
            self._log("\n[-] py7zr not installed. Run: pip install py7zr")
            self._finish(False, None)
            return

        self._log(f"[+] AUTO MODE ({atype}): numeric passwords, lengths 1-7 ...")
        start_time = time.time()
        attempts = 0
        progress_every = 500 if atype == 'zip' else 50
        try:
            zf = pyzipper.AESZipFile(self.zip_path) if atype == 'zip' else None
            try:
                if not with_leading_zeros:
                    for number in range(0, 10_000_000):
                        if self._stop:
                            self._log("\n[-] Stopped by user.")
                            self._finish(False, None)
                            return
                        pwd = str(number)
                        attempts += 1
                        if attempts % progress_every == 0 or attempts == 1:
                            self._progress(attempts, pwd)
                        found = try_password_zip(zf, pwd) if atype == 'zip' else try_password_7z(self.zip_path, pwd)
                        if found:
                            self._finish(True, pwd, attempts, start_time)
                            return
                else:
                    for length in range(1, 8):
                        max_value = 10 ** length
                        self._log(f"\n[+] Trying length {length} (0 to {max_value - 1}) ...")
                        for number in range(0, max_value):
                            if self._stop:
                                self._log("\n[-] Stopped by user.")
                                self._finish(False, None)
                                return
                            pwd = str(number).zfill(length)
                            attempts += 1
                            if attempts % progress_every == 0 or attempts == 1:
                                self._progress(attempts, pwd)
                            found = try_password_zip(zf, pwd) if atype == 'zip' else try_password_7z(self.zip_path, pwd)
                            if found:
                                self._finish(True, pwd, attempts, start_time)
                                return
            finally:
                if zf is not None:
                    zf.close()
            self._log("\n[-] No password found in range 0 to 9999999.")
            self._finish(False, None)
        except Exception as e:
            self._log(f"\n[-] Error: {e}")
            self._finish(False, None)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_zip = None
        self.cracker = None
        self.thread = None

        root = BoxLayout(orientation="vertical", padding=10, spacing=10)

        root.add_widget(Label(text="ZIP / 7z Password Cracker", font_size=22, size_hint_y=0.08))

        # --- Archive selection ---
        zip_row = BoxLayout(size_hint_y=0.08, spacing=10)
        self.zip_spinner = Spinner(text="Scan for .zip / .7z files", values=[])
        refresh_btn = Button(text="Scan", size_hint_x=0.3)
        refresh_btn.bind(on_release=self.scan_zips)
        zip_row.add_widget(self.zip_spinner)
        zip_row.add_widget(refresh_btn)
        root.add_widget(zip_row)

        # --- Mode selection ---
        root.add_widget(Label(text="Mode", size_hint_y=0.05))
        self.mode_spinner = Spinner(
            text="Manual (char type + length)",
            values=[
                "Manual (char type + length)",
                "Auto - numeric, no leading zeros",
                "Auto - numeric, with leading zeros",
            ],
            size_hint_y=0.08,
        )
        self.mode_spinner.bind(text=self.on_mode_change)
        root.add_widget(self.mode_spinner)

        # --- Manual options (char type + length) ---
        self.manual_box = GridLayout(cols=2, size_hint_y=0.16, spacing=10)
        self.manual_box.add_widget(Label(text="Character type:"))
        self.char_spinner = Spinner(
            text="Letters + Numbers (Mix)",
            values=[
                "Only Capital Letters (A-Z)",
                "Only Small Letters (a-z)",
                "Only Numbers (0-9)",
                "Letters + Numbers (Mix)",
            ],
        )
        self.manual_box.add_widget(self.char_spinner)
        self.manual_box.add_widget(Label(text="Password length:"))
        self.length_input = TextInput(text="4", multiline=False, input_filter="int")
        self.manual_box.add_widget(self.length_input)
        root.add_widget(self.manual_box)

        # --- Controls ---
        ctrl_row = BoxLayout(size_hint_y=0.08, spacing=10)
        self.start_btn = Button(text="Start Cracking")
        self.start_btn.bind(on_release=self.start_crack)
        self.stop_btn = Button(text="Stop", disabled=True)
        self.stop_btn.bind(on_release=self.stop_crack)
        ctrl_row.add_widget(self.start_btn)
        ctrl_row.add_widget(self.stop_btn)
        root.add_widget(ctrl_row)

        self.status_label = Label(text="Attempts: 0 | Current: -", size_hint_y=0.06)
        root.add_widget(self.status_label)

        # --- Log output ---
        scroll = ScrollView(size_hint_y=0.41)
        self.log_label = Label(text="", size_hint_y=None, valign="top", halign="left")
        self.log_label.bind(texture_size=self._update_log_height)
        self.log_label.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
        scroll.add_widget(self.log_label)
        root.add_widget(scroll)

        self.add_widget(root)
        self.scan_zips(None)

    def _update_log_height(self, instance, size):
        instance.height = size[1]

    # -- archive scanning --
    def scan_zips(self, instance):
        zips = list_archives(".")
        if not zips:
            self.zip_spinner.values = []
            self.zip_spinner.text = "No .zip/.7z files found"
            self.selected_zip = None
            self.zip_name_to_path = {}
            return

        # Build display-name -> full-path map. If two files share a name,
        # disambiguate the display label by appending the parent folder.
        from collections import Counter
        names = [os.path.basename(z) for z in zips]
        counts = Counter(names)
        display_names = []
        for z, n in zip(zips, names):
            if counts[n] > 1:
                parent = os.path.basename(os.path.dirname(z)) or "."
                display_names.append(f"{n}  ({parent})")
            else:
                display_names.append(n)

        self.zip_name_to_path = dict(zip(display_names, zips))
        self.zip_spinner.values = display_names
        self.zip_spinner.text = display_names[0]
        self.selected_zip = zips[0]
        self.zip_spinner.bind(
            text=lambda inst, val: setattr(self, 'selected_zip', self.zip_name_to_path.get(val))
        )

    def on_mode_change(self, instance, value):
        self.manual_box.disabled = value != "Manual (char type + length)"
        self.manual_box.opacity = 1 if not self.manual_box.disabled else 0.4

    # -- logging helpers --
    def append_log(self, text):
        self.log_label.text += ("\n" if self.log_label.text else "") + text

    def update_progress(self, attempts, pwd):
        self.status_label.text = f"Attempts: {attempts} | Current: {pwd}"

    def show_popup(self, title, msg):
        Popup(title=title, content=Label(text=msg), size_hint=(0.7, 0.4)).open()

    # -- start/stop --
    def start_crack(self, instance):
        if not self.selected_zip or not os.path.exists(self.selected_zip):
            self.show_popup("Error", "Please scan and select a valid archive file first.")
            return

        if archive_type(self.selected_zip) == '7z' and not HAS_PY7ZR:
            self.show_popup(
                "Missing dependency",
                "py7zr is not installed.\nIn Pydroid, open Pip and install: py7zr",
            )
            return

        self.log_label.text = ""
        self.status_label.text = "Attempts: 0 | Current: -"
        self.start_btn.disabled = True
        self.stop_btn.disabled = False

        self.cracker = Cracker(
            self.selected_zip,
            log_cb=self.append_log,
            done_cb=self.on_done,
            progress_cb=self.update_progress,
        )

        mode = self.mode_spinner.text
        if mode == "Manual (char type + length)":
            try:
                length = int(self.length_input.text)
                if length <= 0:
                    raise ValueError
            except ValueError:
                self.show_popup("Error", "Enter a valid password length.")
                self.start_btn.disabled = False
                self.stop_btn.disabled = True
                return
            char_choice = self.char_spinner.text
            self.thread = threading.Thread(
                target=self.cracker.run_manual, args=(char_choice, length), daemon=True
            )
        elif mode == "Auto - numeric, no leading zeros":
            self.thread = threading.Thread(
                target=self.cracker.run_auto_numeric, args=(False,), daemon=True
            )
        else:
            self.thread = threading.Thread(
                target=self.cracker.run_auto_numeric, args=(True,), daemon=True
            )

        self.thread.start()

    def stop_crack(self, instance):
        if self.cracker:
            self.cracker.stop()
        self.stop_btn.disabled = True

    def on_done(self, success, pwd):
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        if success:
            self.show_popup("Success", f'Password found: "{pwd}"\nExtracted to:\n{EXTRACT_DIR}')
        else:
            self.show_popup("Done", "Cracking finished (no password found or stopped).")


class ZipCrackerApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        return sm

    def on_stop(self):
        if os.path.exists(EXTRACT_DIR):
            shutil.rmtree(EXTRACT_DIR, ignore_errors=True)


if __name__ == "__main__":
    ZipCrackerApp().run()