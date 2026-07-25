"""
Job Aggregator Uninstall Wizard.

Builds into uninstall.exe (see uninstaller_build.spec). A copy of this exe
ships inside the installed application folder, and installer_gui.py registers
it as the "Uninstall" entry for Job Aggregator in Windows Settings > Apps, so
both entry points (Settings > Apps, or double-clicking uninstall.exe directly)
launch this same wizard.
"""

import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

# High-DPI Awareness for crisp rendering on modern Windows displays
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\JobAggregator"


def get_install_dir() -> str:
    """This uninstaller always lives inside the folder it's meant to remove."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


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


def get_start_menu_folder() -> str:
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Job Aggregator")


def get_appdata_dir() -> str:
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(appdata, "JobAggregator")


def remove_path(path: str) -> bool:
    """Remove a file or a whole folder tree, if it exists. Never raises."""
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            return True
        if os.path.isfile(path):
            os.remove(path)
            return True
    except Exception:
        pass
    return False


def remove_registry_entry() -> None:
    """Deletes the registry key that makes Job Aggregator show up in
    Windows Settings > Apps."""
    try:
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH)
    except Exception:
        pass


def schedule_self_delete(install_dir: str) -> None:
    bat_path = os.path.join(
        os.environ.get("TEMP", os.path.expanduser("~")), "job_aggregator_cleanup.bat"
    )
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(
            "@echo off\n"
            "timeout /t 2 /nobreak >nul\n"
            f'rmdir /s /q "{install_dir}" >nul 2>&1\n'
            'del "%~f0" >nul 2>&1\n'
        )

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags |= subprocess.CREATE_NO_WINDOW
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags |= subprocess.DETACHED_PROCESS

    subprocess.Popen(["cmd", "/c", bat_path], creationflags=creationflags, close_fds=True)


class UninstallWizardGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Job Aggregator Uninstall Wizard")
        self.root.geometry("600x470")
        self.root.resizable(False, False)
        self.root.configure(bg="#f8fafc")

        # TTK Style configuration
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "Red.Horizontal.TProgressbar",
            troughcolor="#e2e8f0",
            background="#ef4444",
            bordercolor="#e2e8f0",
            lightcolor="#ef4444",
            darkcolor="#ef4444",
        )

        self.install_dir = get_install_dir()
        self.delete_user_data_var = tk.BooleanVar(value=False)
        self.ui_queue = queue.Queue()

        self._build_confirm_view()
        self.root.after(100, self._process_ui_queue)

    def _build_confirm_view(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        header = tk.Frame(self.root, bg="#991b1b", height=80)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        top_header = tk.Frame(header, bg="#991b1b")
        top_header.pack(fill="x", padx=24, pady=(14, 0))

        lbl_header = tk.Label(
            top_header,
            text="Uninstall Job Aggregator",
            font=("Segoe UI", 15, "bold"),
            bg="#991b1b",
            fg="#ffffff",
        )
        lbl_header.pack(side="left")

        badge = tk.Label(
            top_header,
            text="● CONFIRMATION",
            font=("Segoe UI", 8, "bold"),
            bg="#7f1d1d",
            fg="#fca5a5",
            padx=8,
            pady=2,
        )
        badge.pack(side="right")

        lbl_sub = tk.Label(
            header,
            text=self.install_dir,
            font=("Segoe UI", 9),
            bg="#991b1b",
            fg="#fecaca",
        )
        lbl_sub.pack(anchor="w", padx=24, pady=(2, 0))

        body = tk.Frame(self.root, bg="#f8fafc", padx=24, pady=20)
        body.pack(fill="both", expand=True)

        card_info = tk.LabelFrame(
            body,
            text=" Components to Remove ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            padx=16,
            pady=14,
            bd=1,
            relief="solid",
        )
        card_info.pack(fill="x", pady=(0, 16))

        for line in (
            "• Program files & backend dependencies",
            "• Desktop & Start Menu application shortcuts",
            "• Windows Control Panel & Settings Apps registration",
        ):
            tk.Label(
                card_info,
                text=line,
                font=("Segoe UI", 9),
                fg="#334155",
                bg="#ffffff",
            ).pack(anchor="w", pady=2)

        card_data = tk.LabelFrame(
            body,
            text=" User Data Option ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            padx=16,
            pady=14,
            bd=1,
            relief="solid",
        )
        card_data.pack(fill="x")

        cb_data = tk.Checkbutton(
            card_data,
            text="Delete saved job database & settings (jobs.db, API keys)",
            variable=self.delete_user_data_var,
            font=("Segoe UI", 9, "bold"),
            fg="#dc2626",
            bg="#ffffff",
            activebackground="#ffffff",
        )
        cb_data.pack(anchor="w")

        tk.Label(
            card_data,
            text="Keep unchecked if you plan to reinstall and retain your saved job history.",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#ffffff",
        ).pack(anchor="w", padx=(20, 0), pady=(2, 0))

        footer = tk.Frame(self.root, bg="#ffffff", height=60, bd=1, relief="solid")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        btn_uninstall = tk.Button(
            footer,
            text="Uninstall Now",
            font=("Segoe UI", 10, "bold"),
            bg="#dc2626",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            bd=0,
            width=14,
            height=2,
            cursor="hand2",
            command=self._start_uninstall_thread,
        )
        btn_uninstall.pack(side="right", padx=24, pady=12)

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

    def _start_uninstall_thread(self):
        if not messagebox.askyesno(
            "Confirm Uninstall",
            "Are you sure you want to uninstall Job Aggregator? This cannot be undone.",
        ):
            return
        self._build_progress_view()
        threading.Thread(target=self._do_uninstall, daemon=True).start()

    def _build_progress_view(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        header = tk.Frame(self.root, bg="#991b1b", height=75)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        top_header = tk.Frame(header, bg="#991b1b")
        top_header.pack(fill="x", padx=24, pady=(12, 0))

        lbl_header = tk.Label(
            top_header,
            text="Uninstalling Job Aggregator...",
            font=("Segoe UI", 14, "bold"),
            bg="#991b1b",
            fg="#ffffff",
        )
        lbl_header.pack(side="left")

        badge = tk.Label(
            top_header,
            text="● REMOVING ASSETS",
            font=("Segoe UI", 8, "bold"),
            bg="#7f1d1d",
            fg="#fca5a5",
            padx=8,
            pady=2,
        )
        badge.pack(side="right")

        self.lbl_status = tk.Label(
            header,
            text="Starting uninstallation process...",
            font=("Segoe UI", 9),
            bg="#991b1b",
            fg="#fecaca",
        )
        self.lbl_status.pack(anchor="w", padx=24, pady=(2, 0))

        body = tk.Frame(self.root, bg="#f8fafc", padx=24, pady=18)
        body.pack(fill="both", expand=True)

        self.progress_bar = ttk.Progressbar(
            body, orient="horizontal", mode="determinate", style="Red.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=(0, 12))

        lbl_log = tk.Label(body, text="Uninstall Log Output:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#0f172a")
        lbl_log.pack(anchor="w", pady=(0, 4))

        self.log_box = ScrolledText(
            body, height=11, font=("Consolas", 8), bg="#090d16", fg="#f87171", bd=1, relief="solid"
        )
        self.log_box.pack(fill="both", expand=True)

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
                self._build_finish_view()
            elif kind == "error":
                messagebox.showerror("Uninstall Error", item[1])

        self.root.after(100, self._process_ui_queue)

    def _do_uninstall(self):
        try:
            self._log("[START] Removing Desktop and Start Menu shortcuts...", "Removing shortcuts...")
            self._set_progress(10)
            remove_path(os.path.join(get_desktop_path(), "Job Aggregator.lnk"))
            remove_path(get_start_menu_folder())
            self._set_progress(35)

            self._log("[REGISTRY] Removing entry from Windows Settings > Apps...", "Cleaning registry entries...")
            remove_registry_entry()
            self._set_progress(60)

            if self.delete_user_data_var.get():
                self._log("[DATA] Removing saved job database and settings...", "Deleting user data...")
                remove_path(get_appdata_dir())
            else:
                self._log("[DATA] Preserved saved job database and settings.", None)
            self._set_progress(80)

            self._log("[CLEANUP] Scheduling background cleanup of application folder...", "Finalizing cleanup...")
            schedule_self_delete(self.install_dir)
            self._set_progress(100)

            self._log("[COMPLETE] Uninstallation finished successfully!", "Uninstall Complete!")
            self.ui_queue.put(("finish", None))

        except Exception as exc:
            self.ui_queue.put(("error", str(exc)))

    def _build_finish_view(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        header = tk.Frame(self.root, bg="#10b981", height=75)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        top_header = tk.Frame(header, bg="#10b981")
        top_header.pack(fill="x", padx=24, pady=(12, 0))

        lbl_header = tk.Label(
            top_header,
            text="Uninstall Complete",
            font=("Segoe UI", 14, "bold"),
            bg="#10b981",
            fg="#ffffff",
        )
        lbl_header.pack(side="left")

        badge = tk.Label(
            top_header,
            text="● REMOVED SUCCESSFULLY",
            font=("Segoe UI", 8, "bold"),
            bg="#047857",
            fg="#ffffff",
            padx=8,
            pady=2,
        )
        badge.pack(side="right")

        lbl_sub = tk.Label(
            header,
            text="Job Aggregator has been uninstalled from your system.",
            font=("Segoe UI", 9),
            bg="#10b981",
            fg="#ecfdf5",
        )
        lbl_sub.pack(anchor="w", padx=24, pady=(2, 0))

        body = tk.Frame(self.root, bg="#f8fafc", padx=24, pady=25)
        body.pack(fill="both", expand=True)

        card_msg = tk.LabelFrame(
            body,
            text=" Status Summary ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            padx=16,
            pady=14,
            bd=1,
            relief="solid",
        )
        card_msg.pack(fill="x")

        tk.Label(
            card_msg,
            text=(
                "Job Aggregator has been removed from Windows Settings > Apps and shortcuts deleted.\n\n"
                "The application folder will finish being removed automatically in a few seconds."
            ),
            font=("Segoe UI", 9),
            justify="left",
            wraplength=480,
            fg="#334155",
            bg="#ffffff",
        ).pack(anchor="w")

        footer = tk.Frame(self.root, bg="#ffffff", height=60, bd=1, relief="solid")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        btn_close = tk.Button(
            footer,
            text="Close",
            font=("Segoe UI", 10, "bold"),
            bg="#0f172a",
            fg="#ffffff",
            activebackground="#1e293b",
            activeforeground="#ffffff",
            bd=0,
            width=14,
            height=2,
            cursor="hand2",
            command=self.root.destroy,
        )
        btn_close.pack(side="right", padx=24, pady=12)


def main():
    root = tk.Tk()
    UninstallWizardGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
