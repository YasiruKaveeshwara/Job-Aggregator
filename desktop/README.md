# Job Aggregator — Desktop Application & Setup Package

Native Windows desktop distribution for **Job Aggregator**. Embeds the FastAPI backend and static Next.js frontend into a PyWebview container with custom Windows Setup and Uninstall Wizards.

---

## Key Architecture & Features

- **PyWebview Native Container**: Launches FastAPI on a dynamic free local port and renders the UI in a native Windows webview window.
- **Console Terminal Suppression**: `console=False` in `build.spec` prevents unwanted black command prompt windows from popping up when opening the app.
- **Developer Mode Toggle**: Custom checkbox in installer GUI enables/disables DevTools inspector (F12) via a `debug_mode.flag` file.
- **Persistent Data Storage**: SQLite database automatically initialized at `%APPDATA%\JobAggregator\jobs.db` (`C:\Users\<Username>\AppData\Roaming\JobAggregator\jobs.db`).
- **Windows Security & Unblocking**: Includes automated PowerShell `Unblock-File` execution during setup to remove Zone.Identifier alternate data streams.
- **Standard Windows Installation & Uninstallation**:
  - Registered under Windows Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\JobAggregator`).
  - Appears in **Windows Settings > Apps** & **Control Panel**.
  - Custom Uninstall Wizard GUI (`uninstall.exe`) handles clean file removal, shortcut cleanup, optional database purging, and safe self-deletion via `%TEMP%`.

---

## App Lifecycle & Termination

Closing the main application window (clicking X or `Alt+F4`) gracefully terminates the PyWebview container, stops the Uvicorn server thread, releases socket bindings, and exits the process completely. No background services or system tray icons linger in Task Manager.

---

## Installation & Launch Options

### Option 1: Standard One-Click Installer (`JobAggregatorSetup.exe`)
Double-click `JobAggregatorSetup.exe` in `desktop/dist/`. The setup wizard presents a 3-step modern GUI:
1. Destination folder selection (automatically formats path to append `\JobAggregator`).
2. Option checkbuttons for Desktop shortcut, Start Menu shortcut, and Developer Mode.
3. Live real-time installation progress bar and log console.

### Option 2: Batch Launcher (`start.bat` / `install.bat`)
- **`start.bat`**: Direct 1-click launcher for portable/dev builds. Unblocks binary alternate data streams and launches `JobAggregator.exe`.
- **`install.bat`**: Unblocks binary files and launches `JobAggregatorSetup.exe`.

---

## Uninstallation

Uninstalling can be performed via two equivalent methods:
1. **Windows Settings**: Open **Settings → Apps → Installed apps → Job Aggregator** → click **Uninstall**.
2. **Direct Execution**: Run `uninstall.exe` inside the installed application directory (`%LOCALAPPDATA%\Programs\JobAggregator\uninstall.exe`).

The uninstall wizard presents a confirmation view, progress bar, log console, and an optional checkbox:
`[ ] Delete saved job database & settings (jobs.db, API keys)` (unchecked by default to preserve job history upon reinstall).

---

## 4-Step Build Sequence from Source

To compile the entire desktop distribution package from scratch, execute the following steps in order from the `desktop/` directory:

```powershell
cd desktop
pip install -r requirements.txt

# Step 1: Build the main application payload (onedir)
python -m PyInstaller -y build.spec
# -> Generates dist/JobAggregator/ (contains JobAggregator.exe & dependencies)

# Step 2: Build the standalone uninstaller wizard (onefile)
python -m PyInstaller -y uninstaller_build.spec
# -> Generates dist/uninstall.exe

# Step 3: Bundle uninstaller into the main app payload
copy dist\uninstall.exe dist\JobAggregator\uninstall.exe

# Step 4: Build the single setup wizard installer
python -m PyInstaller -y installer_build.spec
# -> Generates dist/JobAggregatorSetup.exe
```

---

## Artifact Locations Summary

| File / Folder | Location |
| :--- | :--- |
| **Setup Installer Executable** | `desktop/dist/JobAggregatorSetup.exe` |
| **Standalone App Directory** | `desktop/dist/JobAggregator/` |
| **Main Executable** | `desktop/dist/JobAggregator/JobAggregator.exe` |
| **Uninstaller Executable** | `desktop/dist/JobAggregator/uninstall.exe` |
| **Installed App Target** | `%LOCALAPPDATA%\Programs\JobAggregator\` |
| **Database File (`jobs.db`)** | `%APPDATA%\JobAggregator\jobs.db` |

---

## Integration with Sub-projects

- **[Backend Engine](../backend/README.md)**: Embedded FastAPI server running behind PyWebview.
- **[Frontend Web App](../frontend/README.md)**: Compiled static export (`frontend/out`) rendered inside PyWebview.
- **[Root Documentation](../README.md)**: Master repository architecture overview.
