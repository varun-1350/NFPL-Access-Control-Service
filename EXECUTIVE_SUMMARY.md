# Nagarkot Access Control System (NFPL)
## Remade Technical Architecture & Database Specification

**Target Audience:** Evaluators, HR Leadership, Systems Engineering  
**Technology Stack:** Python 3.10+, SQLite 3 (WAL mode), Flask REST Backend, Modern HTML5/CSS3/ES6 Web App, CustomTkinter Desktop App  

---

### 1. Remade Database Schema

#### A. `employees` Table
| Column | Type | Constraints / Purpose |
|---|---|---|
| `name` | TEXT | Full name of the employee |
| `id` | TEXT | Primary Key (e.g. `admin1`, `u_job_assigner`, `u_auditor`, `u_staff_1`) |
| `role` | TEXT | `Admin`, `Job_assigner`, `auditor`, `staff` |
| `branch` | TEXT | `b1`, `b2`, `b3`, `b4`, `b5` (or `all` for Admin) |
| `job_queue` | TEXT | Comma-separated list of active assigned job IDs |
| `is_active` | INTEGER | `1` (Active on duty), `0` (On leave — soft locks dissolved) |

#### B. `jobs` Table
| Column | Type | Constraints / Purpose |
|---|---|---|
| `id` | INTEGER | Primary Key (Auto Increment) |
| `client` | TEXT | Client entity (`ACME Corp`, `Globex`, `Initech`, etc.) |
| `assigned_to` | TEXT | References `employees(id)` |
| `state` | TEXT | `Confirmed` $\to$ `Prepared` $\to$ `Checked` $\to$ `Filed` (or `Cancelled`, `Reopened` by Admin only) |
| `mode` | TEXT | `air`, `land`, `sea` |
| `direction` | TEXT | `import`, `export` |
| `branch` | TEXT | `b1`, `b2`, `b3`, `b4`, `b5` |
| `prepared_by`| TEXT | Identity of the staff who prepared the shipment (Maker-Checker SoD) |

---

### 2. Roles, Branches & Lifecycle Capabilities

- **Branches:** `b1`, `b2`, `b3`, `b4`, `b5`.
- **Modes:** `air`, `land`, `sea`.
- **Jobs Lifecycle:**
  $$\text{Confirmed} \xrightarrow[\text{staff/Admin}]{\text{prepare}} \text{Prepared} \xrightarrow[\text{staff/Admin}]{\text{check (SoD)}} \text{Checked} \xrightarrow[\text{staff/Admin}]{\text{file}} \text{Filed}$$
  - **Sensitive Operations (Admin Only):**
    - `Cancelled`: Can only be triggered by **Admin**.
    - `Reopened`: Can only be triggered by **Admin** from `Filed` or `Cancelled`.

| Role | Target Persona | Scope Enforcement | Core Capabilities |
|---|---|---|---|
| **`Admin`** | Carol Admin (`admin1`) | Global (`all`) | • Access full Jobs dataset<br>• Access complete Employee Database table<br>• **Exclusive ability to Cancel and Reopen jobs**<br>• Access system Audit Log<br>• **Exclusively manage staff access and role assignments** |
| **`staff`** | Branch Staff (`u_staff_1` ... `7`) | Branch Bound (`b1`..`b5`) | • Access and change assigned jobs queue (`prepare`, `check`, `file`) with Maker-Checker SoD<br>• Apply for absent leave (toggling `is_active=0`, auto-releasing soft locks)<br>• Filter queue by Assignment (All / Assigned / Unassigned)<br>• Read-only audit log access |
| **`Job_assigner`** | Alice Assigner (`u_job_assigner`) | Cross-Branch Allowed | • Access jobs dataset<br>• **Assign jobs to staff members across any branch** (b1 restriction removed) |
| **`auditor`** | Bob Auditor (`u_auditor`) | Primary Audit Stream | • **Main Dashboard displays Audit Stream directly** with real-time filters and sorting<br>• Interactive review actions: **Verify**, **Flag**, and **Reject** on each audit entry<br>• Secondary read-only access to Jobs Dataset (no execution actions) |

---

### 3. Interactive UI & Profile Capabilities

1. **Profile Section**:
   - Both Web and Desktop applications include a **"👤 My Profile"** feature displaying the logged-in employee's name, user ID, system role, branch clearance, active/on-leave duty status, and assigned job queue IDs.
   - Staff members can also conveniently apply for or end absent leave directly from their profile view.
2. **Assignment Filtering**:
   - Filter dropdowns across task queues and jobs datasets provide instant toggling between:
     - `All Jobs (Assigned & Unassigned)`
     - `Only Assigned Jobs`
     - `Only Unassigned Jobs`
3. **Auditor-First UI**:
   - Logging in as `auditor` automatically switches the primary dashboard from the task queue to the live **System Audit & Compliance Stream**.
   - Auditors can filter by security decision (`ALLOWED`/`DENIED`), review status (`Pending`, `Verified`, `Flagged`, `Rejected`), and search actor/operation/details.
   - Each audit entry features dedicated action buttons: **✓ Verify**, **🚩 Flag**, and **✕ Reject**.
   - Jobs are available as a secondary, strictly read-only dataset.

---

### 4. Execution & Testing

```bash
# 1. Run Web Application via launcher
run.bat

# 2. Run Desktop CustomTkinter Application
run_desktop.bat
# or manually: python seed_demo.py && python app.py

# 3. Run Automated Access Control Test Suite
python test_access.py
```
