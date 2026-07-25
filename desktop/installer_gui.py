"""
Job Aggregator Setup Wizard Installer GUI.
Builds into JobAggregatorSetup.exe for one-click typical Windows installation.
"""

import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


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


def create_shortcut_vbs(target_path: str, shortcut_path: str, icon_path: str = None):
    import tempfile
    import uuid

    target_path = os.path.abspath(target_path)
    shortcut_path = os.path.abspath(shortcut_path)
    working_dir = os.path.dirname(target_path)

    vbs_lines = [
        'Set WshShell = CreateObject("WScript.Shell")',
        f'Set shortcut = WshShell.CreateShortcut("{shortcut_path}")',
        f'shortcut.TargetPath = "{target_path}"',
        f'shortcut.WorkingDirectory = "{working_dir}"',
    ]
    if icon_path and os.path.exists(icon_path):
        icon_path = os.path.abspath(icon_path)
        vbs_lines.append(f'shortcut.IconLocation = "{icon_path}"')
    vbs_lines.append('shortcut.Save()')

    vbs_content = "\n".join(vbs_lines)
    vbs_file = os.path.join(tempfile.gettempdir(), f"create_lnk_{uuid.uuid4().hex[:8]}.vbs")
    try:
        with open(vbs_file, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(["wscript.exe", vbs_file], check=True, creationflags=flags)
    except Exception:
        pass
    finally:
        if os.path.exists(vbs_file):
            try:
                os.remove(vbs_file)
            except Exception:
                pass


def register_uninstaller(install_dir: str, exe_path: str):
    """Register Uninstaller in Windows Registry under Current User."""
    try:
        import winreg

        uninstaller_script = os.path.join(install_dir, "uninstall.bat")
        with open(uninstaller_script, "w", encoding="utf-8") as f:
            f.write(
                "@echo off\n"
                "echo Uninstalling Job Aggregator...\n"
                f'rmdir /s /q "{install_dir}"\n'
                'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\JobAggregator" /f >nul 2>&1\n'
                "echo Uninstallation complete.\n"
            )

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\JobAggregator"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Job Aggregator")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, exe_path)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_script}"')
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Job Aggregator")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
    except Exception:
        pass


class SetupWizardGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Job Aggregator Setup")
        self.root.geometry("540x380")
        self.root.resizable(False, False)

        default_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "JobAggregator"
        )
        self.install_dir_var = tk.StringVar(value=default_dir)
        self.desktop_shortcut_var = tk.BooleanVar(value=True)
        self.start_menu_var = tk.BooleanVar(value=True)
        self.launch_now_var = tk.BooleanVar(value=True)

        self._build_welcome_view()

    def _build_welcome_view(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        # Header banner
        header = tk.Frame(self.root, bg="#0f172a", height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        lbl_header = tk.Label(
            header,
            text="Job Aggregator Setup",
            font=("Segoe UI", 14, "bold"),
            bg="#0f172a",
            fg="#ffffff",
        )
        lbl_header.pack(anchor="w", padx=20, pady=12)

        lbl_sub = tk.Label(
            header,
            text="Install Job Aggregator on your computer",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8",
        )
        lbl_sub.pack(anchor="w", padx=20)

        # Body frame
        body = tk.Frame(self.root, padx=20, pady=20)
        body.pack(fill="both", expand=True)

        lbl_dir = tk.Label(body, text="Destination Folder:", font=("Segoe UI", 9, "bold"))
        lbl_dir.pack(anchor="w")

        dir_frame = tk.Frame(body)
        dir_frame.pack(fill="x", pady=6)

        entry_dir = tk.Entry(dir_frame, textvariable=self.install_dir_var, font=("Segoe UI", 9))
        entry_dir.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_browse = tk.Button(dir_frame, text="Browse...", command=self._browse_dir, width=10)
        btn_browse.pack(side="right")

        lbl_opts = tk.Label(body, text="Shortcut & Registry Options:", font=("Segoe UI", 9, "bold"))
        lbl_opts.pack(anchor="w", pady=(14, 4))

        cb_desktop = tk.Checkbutton(
            body, text="Create a Desktop shortcut", variable=self.desktop_shortcut_var
        )
        cb_desktop.pack(anchor="w")

        cb_start = tk.Checkbutton(
            body, text="Create a Start Menu shortcut", variable=self.start_menu_var
        )
        cb_start.pack(anchor="w")

        # Footer controls
        footer = tk.Frame(self.root, bg="#f8fafc", height=50)
        footer.pack(fill="x", side="bottom")

        btn_install = tk.Button(
            footer,
            text="Install",
            font=("Segoe UI", 9, "bold"),
            bg="#0f172a",
            fg="#ffffff",
            width=12,
            command=self._start_installation,
        )
        btn_install.pack(side="right", padx=20, pady=10)

        btn_cancel = tk.Button(footer, text="Cancel", width=10, command=self.root.quit)
        btn_cancel.pack(side="right", padx=(0, 8), pady=10)

    def _browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir_var.get())
        if chosen:
            self.install_dir_var.set(os.path.abspath(chosen))

    def _start_installation(self):
        target_dir = self.install_dir_var.get().strip()
        if not target_dir:
            messagebox.showerror("Error", "Please select a valid installation directory.")
            return

        # Find source dist payload
        source_payload = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "JobAggregator")
        if not os.path.isdir(source_payload):
            # Check if running bundled
            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            source_payload = os.path.join(base_dir, "payload")

        if not os.path.isdir(source_payload):
            messagebox.showerror(
                "Installation Error",
                f"Could not locate JobAggregator application payload at:\n{source_payload}",
            )
            return

        try:
            os.makedirs(target_dir, exist_ok=True)
            # Copy payload files
            for item in os.listdir(source_payload):
                s = os.path.join(source_payload, item)
                d = os.path.join(target_dir, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

            exe_path = os.path.join(target_dir, "JobAggregator.exe")
            icon_path = os.path.join(target_dir, "_internal", "icon.ico")
            if not os.path.exists(icon_path):
                icon_path = exe_path

            # Desktop shortcut
            if self.desktop_shortcut_var.get():
                desktop = get_desktop_path()
                shortcut_path = os.path.join(desktop, "Job Aggregator.lnk")
                create_shortcut_vbs(exe_path, shortcut_path, icon_path)

            # Start Menu shortcut
            if self.start_menu_var.get():
                start_menu = get_start_menu_path()
                shortcut_path = os.path.join(start_menu, "Job Aggregator.lnk")
                create_shortcut_vbs(exe_path, shortcut_path, icon_path)

            # Register in Add/Remove Programs
            register_uninstaller(target_dir, exe_path)

            self._build_finish_view(exe_path)

        except Exception as exc:
            messagebox.showerror("Installation Error", f"Failed to install Job Aggregator:\n\n{exc}")

    def _build_finish_view(self, installed_exe: str):
        self.installed_exe = installed_exe
        for widget in self.root.winfo_children():
            widget.destroy()

        header = tk.Frame(self.root, bg="#10b981", height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        lbl_header = tk.Label(
            header,
            text="Installation Complete!",
            font=("Segoe UI", 14, "bold"),
            bg="#10b981",
            fg="#ffffff",
        )
        lbl_header.pack(anchor="w", padx=20, pady=18)

        body = tk.Frame(self.root, padx=20, pady=30)
        body.pack(fill="both", expand=True)

        lbl_msg = tk.Label(
            body,
            text="Job Aggregator has been successfully installed on your computer.",
            font=("Segoe UI", 10),
            justify="left",
        )
        lbl_msg.pack(anchor="w", pady=(0, 20))

        cb_launch = tk.Checkbutton(
            body, text="Launch Job Aggregator now", variable=self.launch_now_var, font=("Segoe UI", 10)
        )
        cb_launch.pack(anchor="w")

        footer = tk.Frame(self.root, bg="#f8fafc", height=50)
        footer.pack(fill="x", side="bottom")

        btn_finish = tk.Button(
            footer,
            text="Finish",
            font=("Segoe UI", 9, "bold"),
            bg="#0f172a",
            fg="#ffffff",
            width=12,
            command=self._on_finish,
        )
        btn_finish.pack(side="right", padx=20, pady=10)

    def _on_finish(self):
        if self.launch_now_var.get() and hasattr(self, "installed_exe"):
            subprocess.Popen([self.installed_exe], cwd=os.path.dirname(self.installed_exe))
        self.root.quit()


def main():
    root = tk.Tk()
    app = SetupWizardGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
