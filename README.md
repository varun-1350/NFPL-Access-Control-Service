# Nagarkot Access Control Platform (NFPL)

A production-grade, high-performance Access Control & Shipment Lifecycle Management Platform engineered for customs brokerage operations at **Nagarkot Forwarders Pvt. Ltd. (NFPL)**.

Combines **Role-Based Access Control (RBAC)** and **Attribute-Based Access Control (ABAC)** implemented in Python, SQLite (WAL mode), Flask REST API, an enterprise B2B SaaS web dashboard (inspired by Stripe and Flexport), and a standalone CustomTkinter desktop application.

---

## 🚀 Quick Start Guide

### 🌐 1. Web Application (Recommended)
Double-click **`run.bat`** or execute in your terminal:
```bash
./run.bat
```
This automatically initializes the SQLite database (`seed_demo.py`), opens `http://localhost:5000` in your default browser, and starts the server.

### 🖥️ 2. Desktop GUI Application (CustomTkinter)
Double-click **`run_desktop.bat`** or run:
```bash
python seed_demo.py
python app.py
```

### 🧪 3. Automated Security & Access Test Suite
Verify all 11 security constraints, Maker-Checker SoD checks, and ABAC policies:
```bash
python test_access.py
```

### ⚡ 4. Scale Benchmark Generator (500 Users, 200,000 Jobs)
Stress test the engine's real-time queue derivation across massive data volumes:
```bash
python generate_scale.py
```
*Generates 500 users and 200,000 shipment jobs in ~1.5s, querying live queues in ~350ms.*

---

## 👥 Plain-Terms Personnel Access Matrix (20 Evaluated Personas)

As mandated by the NFPL operational specification, each employee's operational scope is defined in plain terms:

| # | Person | User ID | Plain-Terms Access Grant | Duty Status |
|---|---|---|---|---|
| 1 | **Carol Admin** | `admin1` | Role **Admin** for **all clients**, **all branches**, **all directions**, **all modes**. Full lifecycle authority (exclusive `cancel` & `reopen`), user access management, and forensic audit inspection. | Active |
| 2 | **David Systems Admin** | `admin2` | Role **Admin** for **all clients**, **all branches**, **all directions**, **all modes**. Dual administrative authority and break-glass supervisor. | Active |
| 3 | **Alice Assigner** | `u_job_assigner_b1` | Role **Job_assigner** for **all clients**, based in **branch b1 (Mumbai)**. Authorized to assign jobs across branches for all directions and transport modes. | Active |
| 4 | **Deepak Assigner** | `u_job_assigner_b2` | Role **Job_assigner** for **all clients**, based in **branch b2 (Delhi)**. Cross-branch assignment capability across all directions and modes. | Active |
| 5 | **Bob Auditor** | `u_auditor_1` | Role **auditor** for **all clients**, based in **branch b1 (Mumbai)**. Primary compliance stream access with **Verify**, **Flag**, and **Reject** review sign-offs. | Active |
| 6 | **Meera Auditor** | `u_auditor_2` | Role **auditor** for **all clients**, based in **branch b2 (Delhi)**. Senior compliance auditor with full audit ledger inspection. | Active |
| 7 | **Priya Sharma** | `u_staff_1` | Role **staff** for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. Maker of Job #1; subject to Maker-Checker SoD. | Active |
| 8 | **Rahul Verma** | `u_staff_2` | Role **staff** for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. Independent checker for Job #1. | Active |
| 9 | **Frank Absent** | `u_absent` | Role **staff** for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. **Currently on leave** (`is_active = 0`); soft-locks dissolved for peers. | On Leave |
| 10 | **Amit Patel** | `u_staff_3` | Role **staff** for **all clients**, **branch b2 (Delhi)**, **all directions**, **all modes**. | Active |
| 11 | **Sneha Rao** | `u_staff_4` | Role **staff** for **all clients**, **branch b2 (Delhi)**, **all directions**, **all modes**. | Active |
| 12 | **Vikram Nair** | `u_staff_5` | Role **staff** for **all clients**, **branch b3 (Bengaluru)**, **all directions**, **all modes**. | Active |
| 13 | **Ritu Menon** | `u_staff_6` | Role **staff** for **all clients**, **branch b3 (Bengaluru)**, **all directions**, **all modes**. | Active |
| 14 | **Ananya Das** | `u_staff_7` | Role **staff** for **all clients**, **branch b4 (Chennai)**, **all directions**, **all modes**. | Active |
| 15 | **Suresh Raman** | `u_staff_8` | Role **staff** for **all clients**, **branch b4 (Chennai)**, **all directions**, **all modes**. | Active |
| 16 | **Karan Singh** | `u_staff_9` | Role **staff** for **all clients**, **branch b5 (Kolkata)**, **all directions**, **all modes**. | Active |
| 17 | **Pooja Banerjee** | `u_staff_10` | Role **staff** for **all clients**, **branch b5 (Kolkata)**, **all directions**, **all modes**. | Active |
| 18 | **Manoj Sen** | `u_staff_11` | Role **staff** for **all clients**, **branch b5 (Kolkata)**, **all directions**, **all modes**. **Currently on leave** (`is_active = 0`). | On Leave |
| 19 | **Tarun Junior** | `u_staff_junior` | Role **staff** for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. Junior probationary operator. | Active |
| 20 | **Overnight EDI Parser** | `u_parser` | Role **staff** (Automated Service Account) for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. Ingests and prepares batch entries; blocked from checking own jobs. | Active (System) |

---

## 🏛️ Core Security Architecture & Policies

```
                    +------------------------------------+
                    |      Incoming Action Request       |
                    | (Actor ID, Action, Job ID, Reason) |
                    +-----------------+------------------+
                                      |
                                      v
                      +--------------------------------+
                      |   1. Active Duty Validation    | ---> Inactive/On Leave? DENIED
                      +---------------+----------------+      (Dissolves soft-locks)
                                      | Active
                                      v
                      +--------------------------------+
                      |   2. Physical Branch Scope     | ---> Out-of-Branch? DENIED
                      +---------------+----------------+      (Admin global; Assigner cross)
                                      | Passed
                                      v
                      +--------------------------------+
                      |  3. Role Permission Gate       | ---> Role Unauthorized? DENIED
                      +---------------+----------------+      (Admin exclusive for cancel/reopen)
                                      | Passed
                                      v
                      +--------------------------------+
                      |  4. Lifecycle State Check      | ---> Illegal State Jump? DENIED
                      +---------------+----------------+
                                      | Valid State
                                      v
                      +--------------------------------+
                      | 5. Maker-Checker SoD Gate      | ---> Same Actor as Prepared By? DENIED
                      +---------------+----------------+
                                      | Verified
                                      v
                      +--------------------------------+
                      |  6. Atomic Commit & Audit Log  | ---> Update Job State, record in
                      |     (jobs, events, audit)      |      immutable tamper-evident audit
                      +--------------------------------+
```

### 1. Four Specialized Operational Roles
- **`Admin`**: Global branch scope (`all`), staff user access management, forensic audit inspection, and **exclusive authority to `cancel` and `reopen` jobs**.
- **`Job_assigner`**: Cross-branch assignment authority, delegation of shipment jobs to branch staff members.
- **`auditor`**: Dedicated compliance interface with audit log query tools and sign-off actions (**Verify**, **Flag**, **Reject**).
- **`staff`**: Operational progression through `Confirmed` $\to$ `Prepared` $\to$ `Checked` $\to$ `Filed`, constrained by branch location and Maker-Checker SoD.

### 2. Maker-Checker Separation of Duties (SoD)
The employee recorded in `prepared_by` is cryptographically and logically prohibited from checking the same shipment (`prepared_by != actor_id`), even if they hold the highest clearances. An independent colleague must review and verify.

### 3. Dynamic Absence & Soft-Lock Dissolution
When a job is assigned to a staff member, peer colleagues are soft-locked from interfering. However, if the assignee applies for absent leave (`is_active = 0`), the soft-lock dissolves immediately so branch peers can take over without operational delay.

### 4. ⚖️ Decision Comparison Engine ("Why can she and he can't?")
Provides a dedicated API endpoint (`/api/compare`) and diagnostic breakdown comparing any two employees against any job and action. It evaluates Active Duty, Branch Scope, Role Clearance, State Validity, Maker-Checker SoD, and Soft-Locks to explain exactly why one person is allowed and another is denied.

---

## 🎨 Enterprise SaaS Web Dashboard (V2)

The frontend features a clean, production-ready enterprise B2B SaaS interface inspired by platforms like Stripe Dashboard and Flexport:

- **Deep Slate Token System**: Grounded in high-contrast neutral slate (`#0F172A`, `#334155`, `#E2E8F0`, `#F8FAFC`) with no clashing rainbow block buttons.
- **User Context Dropdown**: Avatar trigger in the top right displaying initials, user name, role, branch, and live duty status badge, with a popover for profile inspection and leave application.
- **KPI Summary Grid**: Tight, responsive 4-card metric summary showing actionable shipment counts across lifecycle stages.
- **Unified 36px Form Controls**: Harmonized search input and filter dropdowns with universal `appearance: none` stripping native OS square controls.
- **Subtle Job Feed**: Dot-accented status badges (`status-confirmed`, `status-prepared`, `status-checked`, `status-filed`), monospace job IDs, and dot-separated metadata.
- **Role Action Panel**: Clean structured quick-action navigation cards with icons, labels, descriptions, and directional indicators.

---

## 🧪 Automated Test Suite (`test_access.py`)

The test suite validates 11 critical operational security scenarios:
1. `test_maker_cannot_check_own_work`: Enforces Maker-Checker SoD.
2. `test_job_assigner_can_assign_across_branches`: Cross-branch assignment delegation.
3. `test_staff_access_managed_only_by_admin`: Staff role/branch updates restricted to Admin.
4. `test_auditor_review_verify_flag_reject`: Auditor sign-off workflow.
5. `test_queue_assignment_filter`: Accurate queue filtering (all / assigned / unassigned).
6. `test_absence_dissolves_soft_lock`: Peer takeover when assignee is on leave.
7. `test_cancel_and_reopen_restricted_to_admin`: Sensitive lifecycle lockdown.
8. `test_admin_self_escalation_blocked`: Unauthorized privilege escalation strictly blocked.
9. `test_mid_job_responsibility_change`: Instant live re-evaluation upon branch transfer or role change.
10. `test_parser_service_account`: Automated parser batch creation and SoD enforcement.
11. `test_compare_explains_why_she_can_and_he_cannot`: Comparison engine differential breakdown.

To run:
```bash
python test_access.py
```

---

## 📁 Project Structure

```
nfpl_access_control_simplified/
├── data/
│   ├── nfpl_demo.db           # Seeded SQLite Database (Tracked in Git)
│   └── nfpl_scale.db          # 200k Records Scale Benchmark Database (Tracked in Git)
├── app.py                     # Standalone Desktop GUI Application (CustomTkinter)
├── engine.py                  # Core Security Decision Engine & SQLite Schema (ABAC/RBAC)
├── server.py                  # Flask REST API Web Server & Controller
├── seed_demo.py               # Database Seeder (20 Employees, 104 Shipment Jobs)
├── generate_scale.py          # Scale Benchmark Generator (500 Users, 200,000 Jobs)
├── test_access.py             # Automated Test Suite (11 Core & Edge Test Cases)
├── run.bat                    # One-Click Web App Launcher (Default Browser + Server)
├── run_desktop.bat            # One-Click Desktop GUI Launcher
├── DESIGN.md                  # Comprehensive Technical Design Document & 14 Questions
├── EXECUTIVE_SUMMARY.md       # High-Level Architecture & Lifecycle Summary
├── README.md                  # Project Overview & Quick Start Documentation
└── static/
    ├── index.html             # Enterprise B2B SaaS Dashboard UI
    ├── style.css              # Custom Design System (Slate Palette, Anti-Bleed Rules)
    └── app.js                 # Reactive Frontend Controller & Modal Manager
```
