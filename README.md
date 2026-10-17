# Nagarkot Access Control Platform (NFPL)

A simplified, robust Role-Based and Attribute-Based Access Control (RBAC/ABAC) system for logistics shipment workflows, built with Python, SQLite, Flask, and modern frontend Web & CustomTkinter Desktop interfaces.

---

## 🚀 Quick Start

### 🌐 Web Application (Recommended)
Double-click **`run.bat`** (or execute in PowerShell/CMD). It seeds the SQLite database, launches your default web browser at `http://localhost:5000`, and starts the Flask server:
```bash
run.bat
```

### 🖥️ Desktop GUI Application (CustomTkinter)
Double-click **`run_desktop.bat`** or run:
```bash
run_desktop.bat
# or manually:
python seed_demo.py
python app.py
```

### 🧪 Automated Access Control Test Suite
```bash
python test_access.py
```

---

## 🏛️ Architecture & Rules

### 1. The 4 Roles
- **Admin**:
  - Full access to view and manage Employee Database.
  - Access to full Jobs dataset across all branches (`b1`..`b5`).
  - Read & inspect system Audit Logs.
  - **Exclusive Authority**: Only `Admin` can perform sensitive lifecycle operations: **`cancel`** and **`reopen`**.
- **Job_assigner**:
  - Assigns jobs to staff members.
  - Can access the jobs dataset.
  - **Strict Branch Restriction**: Can **only** assign jobs to employees of the **respective branch**. Cross-branch delegation is strictly denied.
- **staff**:
  - Accesses and operates on job queues assigned to their branch.
  - Progresses jobs through standard lifecycle states: `Confirmed` → `Prepared` → `Checked` → `Filed`.
  - **Maker-Checker SoD**: The person who prepared a job can never check the same job.
  - **Absent Leave**: Can apply for absent leave (`is_active = 0`), which automatically releases any soft locks / assigned jobs.
  - Audit log read-only access.
  - Can manage staff role/branch assignments if authorized.
- **auditor**:
  - Has access to inspect and search all audit log records.
  - Performs formal compliance verification and sign-off on audit entries.

### 2. Schema & Attributes
- **`employees` Table**:
  - `name`: Full employee name
  - `id`: Unique user identifier (e.g., `admin1`, `u_job_assigner`, `u_staff_1`)
  - `role`: Role (`Admin`, `Job_assigner`, `auditor`, `staff`)
  - `branch`: Branch (`b1`, `b2`, `b3`, `b4`, `b5`, or `all` for Admin)
  - `job_queue`: Comma-separated list of assigned job IDs
  - `is_active`: Binary active flag (`1` = active on duty, `0` = on absent leave)

- **`jobs` Table**:
  - `id`: Integer primary key
  - `client`: Client company name
  - `assigned_to`: Foreign key / user ID of assigned staff member
  - `state`: Current workflow state (`Confirmed`, `Prepared`, `Checked`, `Filed`, `Cancelled`, `Reopened`)
  - `mode`: Transportation mode (`air`, `land`, `sea`)
  - `direction`: Logistics direction (`import`, `export`)
  - `branch`: Assigned branch (`b1`, `b2`, `b3`, `b4`, `b5`)
  - `prepared_by`: Staff member who prepared the job (enforces Maker-Checker SoD)

---

## 🔍 Real-Time Search, Filter & Sort Capabilities

Both the **Web Application** and **Desktop CustomTkinter GUI** feature interactive filter and sort toolbars across all views:

1. **Task / Job Queue**:
   - Filter by **Workflow State** (`Confirmed`, `Prepared`, `Checked`, `Filed`, etc.).
   - Filter by **Mode** (`air`, `land`, `sea`).
   - Live Search by **Client Name** or **Job ID**.
   - Sort by: *ID (Newest)*, *ID (Oldest)*, *Client (A-Z)*, *State*.

2. **Employee Database Table**:
   - Filter by **Role** (`Admin`, `Job_assigner`, `auditor`, `staff`).
   - Filter by **Branch** (`b1`..`b5`).
   - Filter by **Duty Status** (`Active`, `On Leave`).
   - Live Search by **Employee Name** or **ID**.
   - Sort by: *Name (A-Z)*, *ID*, *Branch*.

3. **Jobs Master Dataset**:
   - Filter by **Branch** (`b1`..`b5`).
   - Filter by **State** (`Confirmed`, `Prepared`, `Checked`, `Filed`, `Cancelled`, `Reopened`).
   - Filter by **Mode** (`air`, `land`, `sea`).
   - Filter by **Direction** (`import`, `export`).
   - Live Search across Client, ID, and Assigned Staff.
   - Sort by: *ID (Newest)*, *ID (Oldest)*, *Client (A-Z)*, *State*, *Branch*.

4. **Audit Changes Log**:
   - Filter by **Decision Status** (`ALLOWED`, `DENIED`).
   - Filter by **Auditor Verification** (`Verified`, `Pending`).
   - Live Search by Actor ID, Operation, or Detail Reason.
   - Sort by: *Newest First*, *Oldest First*.

