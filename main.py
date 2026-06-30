import pyzipper
import time
import os
import shutil
import itertools
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import threading

class ZipCrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ZIP Recovery Tool")
        # Mobile-like aspect ratio (Width x Height)
        self.root.geometry("380x600")
        self.root.configure(bg="#121214")
        self.root.resizable(False, False)
        
        self.selected_file_path = ""
        self.is_running = False
        self.extract_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_extract_temp")

        # Configure Custom Styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Header Section (App Bar Style)
        header_frame = tk.Frame(root, bg="#1a1a1e", height=60)
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="ZIP PASSWORD RECOVERY", font=("Helvetica", 12, "bold"), fg="#00adb5", bg="#1a1a1e")
        title_label.pack(pady=8)
        
        subtitle_label = tk.Label(header_frame, text="AES-256 Support | Character Set: A-Z", font=("Helvetica", 8), fg="#7e7e8c", bg="#1a1a1e")
        subtitle_label.pack()

        # Main Container (Simulating Mobile Screen Content)
        container = tk.Frame(root, bg="#121214", padx=20, pady=15)
        container.pack(fill="both", expand=True)

        # File Selection Card
        file_card = tk.Frame(container, bg="#1e1e24", bd=0)
        file_card.pack(fill="x", pady=10)
        
        self.file_label = tk.Label(file_card, text="No file selected", font=("Helvetica", 10), fg="#a8a8b3", bg="#1e1e24", anchor="w", padx=10, pady=12)
        self.file_label.pack(side="left", fill="x", expand=True)
        
        browse_btn = tk.Button(file_card, text="SELECT", command=self.browse_file, font=("Helvetica", 9, "bold"), fg="#ffffff", bg="#2a2a32", activebackground="#3a3a46", activeforeground="#ffffff", bd=0, padx=15, relief="flat")
        browse_btn.pack(side="right", fill="y")

        # Configuration Card (Length Input)
        config_card = tk.Frame(container, bg="#1e1e24", pady=12, padx=12)
        config_card.pack(fill="x", pady=10)
        
        length_label = tk.Label(config_card, text="Password Length:", font=("Helvetica", 10), fg="#e1e1e6", bg="#1e1e24")
        length_label.pack(side="left")
        
        self.length_entry = tk.Entry(config_card, font=("Helvetica", 11, "bold"), width=6, bg="#121214", fg="#ffffff", bd=0, insertbackground="white", justify="center", highlightthickness=1, highlightbackground="#2a2a32", highlightcolor="#00adb5")
        self.length_entry.pack(side="right")
        self.length_entry.insert(0, "4")

        # Terminal/Output Card
        output_label = tk.Label(container, text="LIVE STATUS LOG", font=("Helvetica", 9, "bold"), fg="#7e7e8c", bg="#121214")
        output_label.pack(anchor="w", pady=(10, 2))
        
        self.output_box = tk.Text(container, font=("Consolas", 10), bg="#000000", fg="#39ff14", bd=0, height=12, highlightthickness=1, highlightbackground="#1e1e24", padx=8, pady=8)
        self.output_box.pack(fill="x")
        self.log_message("System ready. Please select a file to begin...\n")

        # Action Button (Fixed at Bottom Style)
        self.start_btn = tk.Button(container, text="START RECOVERY", command=self.start_cracking_thread, font=("Helvetica", 11, "bold"), fg="#ffffff", bg="#00adb5", activebackground="#007a80", activeforeground="#ffffff", bd=0, pady=12, cursor="hand2")
        self.start_btn.pack(fill="x", side="bottom", pady=10)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")])
        if file_path:
            self.selected_file_path = file_path
            filename = os.path.basename(file_path)
            # Truncate filename if it's too long for the mobile view
            if len(filename) > 22:
                filename = filename[:19] + "..."
            self.file_label.config(text=filename, fg="#ffffff")
            self.log_message(f"[+] Loaded File: {filename}\n")

    def log_message(self, message, replace=False):
        self.output_box.config(state="normal")
        if replace:
            self.output_box.delete("end-2l", "end-1l")
        self.output_box.insert(tk.END, message)
        self.output_box.see(tk.END)
        self.output_box.config(state="disabled")

    def start_cracking_thread(self):
        if self.is_running:
            return
        if not self.selected_file_path:
            messagebox.showerror("Error", "Please select a ZIP file first!")
            return
        try:
            length = int(self.length_entry.get())
            if length <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid password length!")
            return

        self.is_running = True
        self.start_btn.config(state="disabled", bg="#2a2a32", text="PROCESSING...")
        
        # Run in background thread to keep UI responsive
        threading.Thread(target=self.crack_logic, args=(length,), daemon=True).start()

    def crack_logic(self, length):
        self.log_message(f"[+] Starting recovery... Length: {length}\n")
        start_time = time.time()
        attempts = 0
        
        chars = [chr(i) for i in range(65, 91)]  # A-Z
        os.makedirs(self.extract_dir, exist_ok=True)
        
        with pyzipper.AESZipFile(self.selected_file_path) as zf:
            for guess in itertools.product(chars, repeat=length):
                pwd = "".join(guess)
                attempts += 1
                
                if attempts % 50 == 0 or length <= 3:
                    self.root.after(0, self.log_message, f"[{attempts}] Testing: {pwd}\n", True)
                
                try:
                    zf.setpassword(pwd.encode('utf-8'))
                    zf.testzip()  # Efficient validation without disk writes
                    
                    zf.extractall(path=self.extract_dir)
                    end_time = time.time() - start_time
                    
                    success_msg = f"\n{'='*30}\n✅ PASSWORD FOUND: \"{pwd}\"\n⏱️ Time: {end_time:.2f} sec\n📊 Total Attempts: {attempts}\n{'='*30}\n[+] Extracted to: _extract_temp\n"
                    self.root.after(0, self.log_message, success_msg)
                    self.root.after(0, messagebox.showinfo, "Success", f"Password Found: {pwd}")
                    self.cleanup_and_reset()
                    return
                except Exception:
                    continue
                    
        self.root.after(0, self.log_message, "\n[-] Password not found in this combination.\n")
        self.cleanup_and_reset()

    def cleanup_and_reset(self):
        self.is_running = False
        self.start_btn.config(state="normal", bg="#00adb5", text="START RECOVERY")
        shutil.rmtree(self.extract_dir, ignore_errors=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = ZipCrackerApp(root)
    root.mainloop()
