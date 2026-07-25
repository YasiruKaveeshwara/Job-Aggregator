# Job Aggregator — Desktop Application File & Configuration Locations

Native Windows Desktop application for software engineering job aggregation in Sri Lanka.

---

## 1. Database File Location (`jobs.db`)

### For Desktop Application (`JobAggregatorSetup.exe` / `JobAggregator.exe`)
The SQLite database file `jobs.db` is automatically created and stored at:
```
%APPDATA%\JobAggregator\jobs.db
```
*(Full path: `C:\Users\<YourUsername>\AppData\Roaming\JobAggregator\jobs.db`)*

> 💡 **Migrating existing data**: If you have an existing `jobs.db` database from web development, copy and paste it into `C:\Users\<YourUsername>\AppData\Roaming\JobAggregator\jobs.db`.

### For Backend / Web Development Mode
Stored inside the backend folder:
```
backend/jobs.db
```

---

## 2. API Keys & Configuration (`.env` vs Settings UI)

### Desktop Application (Recommended: Settings UI)
**You do NOT need a `.env` file for the desktop app.**
1. Launch **Job Aggregator**.
2. Open the **Admin Portal** (`/admin`).
3. Under **Application Settings**, enter your **Gemini API Key** and click **Save**.
4. The key is securely saved to your local `%APPDATA%\JobAggregator\jobs.db` database.

*(Optional)* If you wish to use a `.env` file override, place your `.env` file alongside the executable:
- **Installed App**: `%LOCALAPPDATA%\Programs\JobAggregator\.env`
- **Portable App**: `desktop/dist/JobAggregator/.env`

### Web Development Mode
Placed inside the backend root folder:
```
backend/.env
```

---

## Installation & Launch

### Option A: Using `install.bat` (Recommended if Windows Smart App Control is enabled)
1. Double-click **[install.bat](file:///d:/My%20GitHub/Job-Aggregator/desktop/install.bat)** inside the `desktop/` folder.
2. It will automatically unblock the executable binaries and launch `JobAggregatorSetup.exe`.

### Option B: Manual Installation
1. Right-click **`JobAggregatorSetup.exe`** inside `desktop/dist/` -> **Properties**.
2. Check **Unblock** at the bottom of the General tab, then click **Apply** / **OK**.
3. Double-click **`JobAggregatorSetup.exe`** to install.

### Option C: Portable / Direct Launch (`start.bat`)
Double-click **[start.bat](file:///d:/My%20GitHub/Job-Aggregator/desktop/start.bat)** inside the `desktop/` folder to run the standalone app without installing.

