"""
Job Aggregator Setup Wizard Installer GUI.
Builds into JobAggregatorSetup.exe for one-click typical Windows installation.
"""

import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import zipfile
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

# High-DPI Awareness for crisp rendering on modern Windows displays
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def get_desktop_path() -> str:
    user_profile = os.environ.get("USERPROFILE", "")
    onedrive = os.environ.get("OneDrive", "")
    candidates = [
        os.path.join(onedrive, "Desktop"),
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "OneDrive", "Desktop"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return os.path.expanduser("~/Desktop")


def get_start_menu_path() -> str:
    appdata = os.environ.get("APPDATA", "")
    programs = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
    folder = os.path.join(programs, "Job Aggregator")
    os.makedirs(folder, exist_ok=True)
    return folder


def create_shortcut(target_exe: str, shortcut_path: str, icon_path: str = None):
    """Create standard Windows .lnk shortcut targeting JobAggregator.exe directly."""
    target_exe = os.path.abspath(target_exe)
    install_dir = os.path.dirname(target_exe)
    shortcut_path = os.path.abspath(shortcut_path)

    icon_target = os.path.abspath(icon_path) if icon_path and os.path.exists(icon_path) else target_exe

    ps_script = (
        f'$WshShell = New-Object -ComObject WScript.Shell; '
        f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); '
        f'$Shortcut.TargetPath = "{target_exe}"; '
        f'$Shortcut.WorkingDirectory = "{install_dir}"; '
        f'$Shortcut.IconLocation = "{icon_target}"; '
        f'$Shortcut.Save()'
    )

    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            check=True,
            creationflags=flags,
        )
    except Exception:
        pass


def unblock_directory(dir_path: str):
    """Remove Zone.Identifier alternate data streams to prevent Windows Security blocks."""
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                f"Get-ChildItem -Path '{dir_path}' -Recurse | Unblock-File",
            ],
            creationflags=flags,
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


def register_uninstaller(install_dir: str, exe_path: str):
    """Register Job Aggregator's uninstaller in the Windows Registry under Current User."""
    try:
        import winreg

        uninstaller_exe = os.path.join(install_dir, "uninstall.exe")

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\JobAggregator"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Job Aggregator")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, exe_path)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_exe}"')
            winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'"{uninstaller_exe}"')
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Yasiru Kaveeshwara")
            winreg.SetValueEx(key, "Contact", 0, winreg.REG_SZ, "kaveeshwaray@gmail.com")
            winreg.SetValueEx(key, "HelpLink", 0, winreg.REG_SZ, "https://github.com/YasiruKaveeshwara/Job-Aggregator")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.1")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass


def ensure_job_aggregator_folder(path: str) -> str:
    """Ensure destination path ends with JobAggregator folder."""
    clean_path = path.strip().rstrip("\\/")
    folder_name = os.path.basename(clean_path).lower()
    if folder_name not in ("jobaggregator", "job aggregator", "job-aggregator"):
        return os.path.join(clean_path, "JobAggregator")
    return clean_path


class SetupWizardGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Job Aggregator Setup")
        self.root.geometry("600x470")
        self.root.resizable(False, False)
        self.root.configure(bg="#f8fafc")

        # TTK Style configuration
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor="#e2e8f0",
            background="#6366f1",
            bordercolor="#e2e8f0",
            lightcolor="#6366f1",
            darkcolor="#6366f1",
        )

        default_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "JobAggregator"
        )
        self.install_dir_var = tk.StringVar(value=default_dir)
        self.desktop_shortcut_var = tk.BooleanVar(value=True)
        self.start_menu_var = tk.BooleanVar(value=True)
        self.debug_mode_var = tk.BooleanVar(value=False)
        self.launch_now_var = tk.BooleanVar(value=True)

        self.ui_queue = queue.Queue()
        self.installing = False

        self._build_welcome_view()
        self.root.after(100, self._process_ui_queue)

    def _build_welcome_view(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        # Header Hero Banner
        header = tk.Frame(self.root, bg="#0f172a", height=80)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        top_header = tk.Frame(header, bg="#0f172a")
        top_header.pack(fill="x", padx=24, pady=(14, 0))

        lbl_header = tk.Label(
            top_header,
            text="Job Aggregator Setup",
            font=("Segoe UI", 15, "bold"),
            bg="#0f172a",
            fg="#ffffff",
        )
        lbl_header.pack(side="left")

        badge = tk.Label(
            top_header,
            text="● STEP 1 OF 3",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            padx=8,
            pady=2,
        )
        badge.pack(side="right")

        lbl_sub = tk.Label(
            header,
            text="Developed by Yasiru Kaveeshwara (kaveeshwaray@gmail.com) — Setup Wizard",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8",
        )
        lbl_sub.pack(anchor="w", padx=24, pady=(2, 0))

        # Main Body Frame
        body = tk.Frame(self.root, bg="#f8fafc", padx=24, pady=20)
        body.pack(fill="both", expand=True)

        # Destination Card
        card_dir = tk.LabelFrame(
            body,
            text=" Installation Destination ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            padx=16,
            pady=14,
            bd=1,
            relief="solid",
        )
        card_dir.pack(fill="x", pady=(0, 16))

        dir_frame = tk.Frame(card_dir, bg="#ffffff")
        dir_frame.pack(fill="x", pady=(4, 6))

        entry_dir = tk.Entry(
            dir_frame,
            textvariable=self.install_dir_var,
            font=("Segoe UI", 9),
            bd=1,
            relief="solid",
            bg="#f8fafc",
            fg="#0f172a",
        )
        entry_dir.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)

        btn_browse = tk.Button(
            dir_frame,
            text="Browse...",
            command=self._browse_dir,
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9",
            fg="#0f172a",
            bd=1,
            relief="solid",
            width=10,
            activebackground="#e2e8f0",
            cursor="hand2",
        )
        btn_browse.pack(side="right")

        lbl_hint = tk.Label(
            card_dir,
            text="💡 Custom paths will automatically append \\JobAggregator.",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#64748b",
        )
        lbl_hint.pack(anchor="w")

        # Shortcuts & Debug Options Card
        card_opts = tk.LabelFrame(
            body,
            text=" Installation Options ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            padx=16,
            pady=14,
            bd=1,
            relief="solid",
        )
        card_opts.pack(fill="x")

        cb_desktop = tk.Checkbutton(
            card_opts,
            text="Create Desktop shortcut",
            variable=self.desktop_shortcut_var,
            font=("Segoe UI", 9),
            bg="#ffffff",
            activebackground="#ffffff",
        )
        cb_desktop.pack(anchor="w", pady=(0, 4))

        cb_start = tk.Checkbutton(
            card_opts,
            text="Create Start Menu shortcut",
            variable=self.start_menu_var,
            font=("Segoe UI", 9),
            bg="#ffffff",
            activebackground="#ffffff",
        )
        cb_start.pack(anchor="w", pady=(0, 4))

        cb_debug = tk.Checkbutton(
            card_opts,
            text="Enable Developer Mode (Console Inspector & F12 DevTools)",
            variable=self.debug_mode_var,
            font=("Segoe UI", 9, "bold"),
            fg="#4f46e5",
            bg="#ffffff",
            activebackground="#ffffff",
        )
        cb_debug.pack(anchor="w", pady=(4, 0))

        # Footer Action Bar
        footer = tk.Frame(self.root, bg="#ffffff", height=60, bd=1, relief="solid")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        btn_install = tk.Button(
            footer,
            text="Install Now",
            font=("Segoe UI", 10, "bold"),
            bg="#4f46e5",
            fg="#ffffff",
            activebackground="#4338ca",
            activeforeground="#ffffff",
            bd=0,
            width=14,
            height=2,
            cursor="hand2",
            command=self._start_installation_thread,
        )
        btn_install.pack(side="right", padx=24, pady=12)

        btn_cancel = tk.Button(
            footer,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#64748b",
            bd=1,
            relief="solid",
            width=10,
            height=2,
            cursor="hand2",
            command=self.root.quit,
        )
        btn_cancel.pack(side="right", padx=(0, 10), pady=12)

    def _browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir_var.get())
        if chosen:
            formatted = ensure_job_aggregator_folder(chosen)
            self.install_dir_var.set(os.path.abspath(formatted))

    def _find_payload_source(self):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        exe_dir = os.path.dirname(sys.executable)
        curr_dir = os.path.dirname(os.path.abspath(__file__))

        # Check zip payload first (high compression)
        zip_candidates = [
            os.path.join(base_dir, "payload.zip"),
            os.path.join(base_dir, "payload", "payload.zip"),
            os.path.join(exe_dir, "payload.zip"),
            os.path.join(curr_dir, "dist", "payload.zip"),
            os.path.join(curr_dir, "payload.zip"),
        ]
        for z in zip_candidates:
            if os.path.isfile(z):
                return ("zip", z)

        # Check dir payload fallback (uncompressed dev mode)
        dir_candidates = [
            os.path.join(base_dir, "payload"),
            os.path.join(exe_dir, "payload"),
            os.path.join(curr_dir, "dist", "JobAggregator"),
            os.path.join(curr_dir, "payload"),
        ]
        for d in dir_candidates:
            if os.path.isdir(d):
                return ("dir", d)

        return (None, None)

    def _start_installation_thread(self):
        target_dir = ensure_job_aggregator_folder(self.install_dir_var.get().strip())
        self.install_dir_var.set(target_dir)

        if not target_dir:
            messagebox.showerror("Error", "Please select a valid installation directory.")
            return

        payload_type, payload_path = self._find_payload_source()
        if not payload_type:
            messagebox.showerror(
                "Installation Error",
                "Could not locate JobAggregator application bundle package.",
            )
            return

        self._build_installing_view()

        threading.Thread(
            target=self._do_installation, args=(payload_type, payload_path, target_dir), daemon=True
        ).start()

    def _build_installing_view(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        header = tk.Frame(self.root, bg="#0f172a", height=75)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        top_header = tk.Frame(header, bg="#0f172a")
        top_header.pack(fill="x", padx=24, pady=(12, 0))

        lbl_header = tk.Label(
            top_header,
            text="Installing Job Aggregator...",
            font=("Segoe UI", 14, "bold"),
            bg="#0f172a",
            fg="#ffffff",
        )
        lbl_header.pack(side="left")

        badge = tk.Label(
            top_header,
            text="● STEP 2 OF 3",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            padx=8,
            pady=2,
        )
        badge.pack(side="right")

        self.lbl_status = tk.Label(
            header,
            text="Copying application files...",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8",
        )
        self.lbl_status.pack(anchor="w", padx=24, pady=(2, 0))

        body = tk.Frame(self.root, bg="#f8fafc", padx=24, pady=18)
        body.pack(fill="both", expand=True)

        self.progress_bar = ttk.Progressbar(
            body, orient="horizontal", mode="determinate", style="Accent.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=(0, 12))

        lbl_log = tk.Label(body, text="Installation Log Output:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#0f172a")
        lbl_log.pack(anchor="w", pady=(0, 4))

        self.log_box = ScrolledText(
            body, height=11, font=("Consolas", 8), bg="#090d16", fg="#38bdf8", bd=1, relief="solid"
        )
        self.log_box.pack(fill="both", expand=True)

        footer = tk.Frame(self.root, bg="#ffffff", height=60, bd=1, relief="solid")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self.btn_cancel_install = tk.Button(
            footer, text="Installing...", state="disabled", font=("Segoe UI", 9, "bold"), bg="#e2e8f0", fg="#94a3b8", width=14, height=2
        )
        self.btn_cancel_install.pack(side="right", padx=24, pady=12)

    def _log(self, message: str, status: str = None):
        self.ui_queue.put(("log", message, status))

    def _set_progress(self, percent: float):
        self.ui_queue.put(("progress", percent))

    def _process_ui_queue(self):
        while not self.ui_queue.empty():
            item = self.ui_queue.get_nowait()
            kind = item[0]

            if kind == "log":
                msg, status = item[1], item[2]
                self.log_box.insert(tk.END, f"{msg}\n")
                self.log_box.see(tk.END)
                if status:
                    self.lbl_status.config(text=status)

            elif kind == "progress":
                self.progress_bar["value"] = item[1]

            elif kind == "finish":
                self._build_finish_view(item[1])

            elif kind == "error":
                messagebox.showerror("Installation Error", item[1])
                self._build_welcome_view()

        self.root.after(100, self._process_ui_queue)

    def _do_installation(self, payload_type: str, payload_path: str, target_dir: str):
        try:
            self._log(f"[INIT] Target Directory: {target_dir}", "Initializing target directory...")
            self._set_progress(5)

            os.makedirs(target_dir, exist_ok=True)

            if payload_type == "zip":
                self._log(f"[PAYLOAD] Unpacking compressed application archive: {os.path.basename(payload_path)}", "Extracting application binaries...")
                with zipfile.ZipFile(payload_path, "r") as zf:
                    infolist = zf.infolist()
                    total_items = len(infolist)
                    extracted_count = 0

                    for member in infolist:
                        zf.extract(member, target_dir)
                        extracted_count += 1
                        pct = 10 + (extracted_count / max(1, total_items)) * 75
                        self._set_progress(pct)
                        if extracted_count % 15 == 0 or extracted_count == total_items:
                            self._log(f"[EXTRACT] {member.filename}", f"Extracting {os.path.basename(member.filename)}...")
            else:
                all_files = []
                for root_dir, _, files in os.walk(payload_path):
                    for f in files:
                        all_files.append(os.path.join(root_dir, f))

                total_items = len(all_files)
                self._log(f"[PAYLOAD] Copying {total_items} application bundle files...", "Copying application files...")

                copied_count = 0
                for item in os.listdir(payload_path):
                    s = os.path.join(payload_path, item)
                    d = os.path.join(target_dir, item)

                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)

                        for root_d, _, files in os.walk(s):
                            rel = os.path.relpath(root_d, s)
                            dest_sub = os.path.join(d, rel)
                            os.makedirs(dest_sub, exist_ok=True)

                            for f in files:
                                src_f = os.path.join(root_d, f)
                                dst_f = os.path.join(dest_sub, f)
                                shutil.copy2(src_f, dst_f)
                                copied_count += 1
                                pct = 10 + (copied_count / max(1, total_items)) * 75
                                self._set_progress(pct)
                                if copied_count % 15 == 0 or copied_count == total_items:
                                    self._log(f"[COPY] {os.path.relpath(dst_f, target_dir)}", f"Copying {f}...")
                    else:
                        shutil.copy2(s, d)
                        copied_count += 1
                        pct = 10 + (copied_count / max(1, total_items)) * 75
                        self._set_progress(pct)
                        self._log(f"[COPY] {item}", f"Copying {item}...")

            exe_path = os.path.join(target_dir, "JobAggregator.exe")
            icon_path = os.path.join(target_dir, "_internal", "icon.ico")
            if not os.path.exists(icon_path):
                icon_path = exe_path

            # Clean up old run.vbs if present
            old_vbs = os.path.join(target_dir, "run.vbs")
            if os.path.exists(old_vbs):
                try:
                    os.remove(old_vbs)
                except Exception:
                    pass

            self._log("[SECURITY] Unblocking binary alternate data streams...", "Unblocking files for Windows Security...")
            unblock_directory(target_dir)

            # Configure Debug Mode flag file
            debug_flag_file = os.path.join(target_dir, "debug_mode.flag")
            if self.debug_mode_var.get():
                self._log("[CONFIG] Enabling Developer Mode (DevTools / Console Inspector)...", "Configuring Developer Mode...")
                with open(debug_flag_file, "w", encoding="utf-8") as f:
                    f.write("DEBUG_ENABLED=1\n")
            else:
                self._log("[CONFIG] Production Mode configured (no terminal window).", "Finalizing installation...")
                if os.path.exists(debug_flag_file):
                    try:
                        os.remove(debug_flag_file)
                    except Exception:
                        pass

            self._set_progress(88)

            # Desktop shortcut
            if self.desktop_shortcut_var.get():
                self._log("[SHORTCUT] Creating Desktop shortcut...", "Creating Desktop shortcut...")
                desktop = get_desktop_path()
                shortcut_path = os.path.join(desktop, "Job Aggregator.lnk")
                create_shortcut(exe_path, shortcut_path, icon_path)

            self._set_progress(94)

            # Start Menu shortcut
            if self.start_menu_var.get():
                self._log("[SHORTCUT] Creating Start Menu shortcut...", "Creating Start Menu shortcut...")
                start_menu = get_start_menu_path()
                shortcut_path = os.path.join(start_menu, "Job Aggregator.lnk")
                create_shortcut(exe_path, shortcut_path, icon_path)

            self._set_progress(98)

            # Register in Add/Remove Programs
            self._log("[REGISTRY] Registering uninstaller in Windows Control Panel...", "Registering uninstaller...")
            register_uninstaller(target_dir, exe_path)

            self._set_progress(100)
            self._log("[COMPLETE] Installation completed successfully!", "Installation Finished!")
            time.sleep(0.4)

            self.ui_queue.put(("finish", exe_path))

        except Exception as exc:
            self.ui_queue.put(("error", str(exc)))

    def _build_finish_view(self, installed_exe: str):
        self.installed_exe = installed_exe
        for widget in self.root.winfo_children():
            widget.destroy()

        header = tk.Frame(self.root, bg="#10b981", height=75)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        top_header = tk.Frame(header, bg="#10b981")
        top_header.pack(fill="x", padx=24, pady=(12, 0))

        lbl_header = tk.Label(
            top_header,
            text="Installation Complete!",
            font=("Segoe UI", 14, "bold"),
            bg="#10b981",
            fg="#ffffff",
        )
        lbl_header.pack(side="left")

        badge = tk.Label(
            top_header,
            text="● STEP 3 OF 3: COMPLETE",
            font=("Segoe UI", 8, "bold"),
            bg="#047857",
            fg="#ffffff",
            padx=8,
            pady=2,
        )
        badge.pack(side="right")

        lbl_sub = tk.Label(
            header,
            text="Job Aggregator is ready to launch on your computer.",
            font=("Segoe UI", 9),
            bg="#10b981",
            fg="#ecfdf5",
        )
        lbl_sub.pack(anchor="w", padx=24, pady=(2, 0))

        body = tk.Frame(self.root, bg="#f8fafc", padx=24, pady=24)
        body.pack(fill="both", expand=True)

        card_info = tk.LabelFrame(
            body,
            text=" Installed Target Folder ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            padx=16,
            pady=14,
            bd=1,
            relief="solid",
        )
        card_info.pack(fill="x", pady=(0, 16))

        lbl_msg = tk.Label(
            card_info,
            text=os.path.dirname(installed_exe),
            font=("Segoe UI", 9, "bold"),
            justify="left",
            fg="#4f46e5",
            bg="#ffffff",
        )
        lbl_msg.pack(anchor="w")

        if self.debug_mode_var.get():
            lbl_debug_info = tk.Label(
                body,
                text="⚡ Developer Mode Enabled: Press F12 or right-click to inspect DevTools.",
                font=("Segoe UI", 9, "bold"),
                fg="#4f46e5",
                bg="#f8fafc",
            )
            lbl_debug_info.pack(anchor="w", pady=(0, 12))

        cb_launch = tk.Checkbutton(
            body,
            text="Launch Job Aggregator immediately",
            variable=self.launch_now_var,
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
            activebackground="#f8fafc",
        )
        cb_launch.pack(anchor="w")

        footer = tk.Frame(self.root, bg="#ffffff", height=60, bd=1, relief="solid")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        btn_finish = tk.Button(
            footer,
            text="Finish & Exit",
            font=("Segoe UI", 10, "bold"),
            bg="#0f172a",
            fg="#ffffff",
            activebackground="#1e293b",
            activeforeground="#ffffff",
            bd=0,
            width=14,
            height=2,
            cursor="hand2",
            command=self._on_finish,
        )
        btn_finish.pack(side="right", padx=24, pady=12)

    def _on_finish(self):
        if self.launch_now_var.get() and hasattr(self, "installed_exe"):
            install_dir = os.path.dirname(self.installed_exe)
            subprocess.Popen([self.installed_exe], cwd=install_dir)
        self.root.quit()


def main():
    root = tk.Tk()
    app = SetupWizardGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
