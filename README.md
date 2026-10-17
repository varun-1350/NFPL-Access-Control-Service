# Nagarkot Access Control Platform (NFPL)

A high-performance, robust Access Control Service designed for customs brokerage shipment lifecycles at **Nagarkot Forwarders Pvt. Ltd. (NFPL)**. Built with Python, SQLite (WAL mode), Flask REST API, Modern HTML5/CSS3/ES6 Web Application, and a CustomTkinter Desktop GUI.

---

## 🚀 Quick Start

### 🌐 1. Web Application (Recommended)
Double-click **`run.bat`** (or execute in terminal). It initializes the SQLite database, launches `http://localhost:5000` in your default browser, and starts the server:
```bash
run.bat
```

### 🖥️ 2. Desktop GUI Application (CustomTkinter)
Double-click **`run_desktop.bat`** or execute:
```bash
run_desktop.bat
# or manually:
python seed_demo.py
python app.py
```

### 🧪 3. Automated Test Suite (All 11 Edge Cases)
```bash
python test_access.py
```

### ⚡ 4. Scale Benchmark Generator (500 Users, 200,000 Jobs)
```bash
python generate_scale.py
```
*Generates 500 users and 200,000 jobs in ~1.5s, querying queues across 200,000 jobs in ~350ms.*

---

## 👥 Plain-Terms Personnel Access Matrix (20 Deliberate Personas)

As mandated by the NFPL technical specification, here is each person's operational access expressed in plain terms:

| # | Person | User ID | Plain-Terms Access Grant | Duty Status |
|---|---|---|---|---|
| 1 | **Carol Admin** | `admin1` | Has role **Admin** for **all clients**, **all branches**, **all directions**, **all modes**. Full lifecycle authority (exclusive `cancel` & `reopen`), user access management, and audit inspection. | Active |
| 2 | **David Systems Admin** | `admin2` | Has role **Admin** for **all clients**, **all branches**, **all directions**, **all modes**. Dual administrative authority and break-glass supervisor. | Active |
| 3 | **Alice Assigner** | `u_job_assigner_b1` | Has role **Job_assigner** for **all clients**, based in **branch b1**, cross-branch assignment capability across **all directions** and **all modes**. | Active |
| 4 | **Deepak Assigner** | `u_job_assigner_b2` | Has role **Job_assigner** for **all clients**, based in **branch b2**, cross-branch assignment capability across **all directions** and **all modes**. | Active |
| 5 | **Bob Auditor** | `u_auditor_1` | Has role **auditor** for **all clients**, based in **branch b1**, all directions, all modes. Primary compliance stream access with **Verify**, **Flag**, and **Reject** authority. | Active |
| 6 | **Meera Auditor** | `u_auditor_2` | Has role **auditor** for **all clients**, based in **branch b2**, all directions, all modes. Secondary senior compliance auditor. | Active |
| 7 | **Priya Sharma** | `u_staff_1` | Has role **staff** for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. Maker of Job #1; subject to Maker-Checker SoD. | Active |
| 8 | **Rahul Verma** | `u_staff_2` | Has role **staff** for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. Independent checker for Job #1. | Active |
| 9 | **Frank Absent** | `u_absent` | Has role **staff** for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. **Currently on leave** (`is_active = 0`); soft-locks dissolved for peers. | On Leave |
| 10 | **Amit Patel** | `u_staff_3` | Has role **staff** for **all clients**, **branch b2 (Delhi)**, **all directions**, **all modes**. | Active |
| 11 | **Sneha Rao** | `u_staff_4` | Has role **staff** for **all clients**, **branch b2 (Delhi)**, **all directions**, **all modes**. | Active |
| 12 | **Vikram Nair** | `u_staff_5` | Has role **staff** for **all clients**, **branch b3 (Bengaluru)**, **all directions**, **all modes**. | Active |
| 13 | **Ritu Menon** | `u_staff_6` | Has role **staff** for **all clients**, **branch b3 (Bengaluru)**, **all directions**, **all modes**. | Active |
| 14 | **Ananya Das** | `u_staff_7` | Has role **staff** for **all clients**, **branch b4 (Chennai)**, **all directions**, **all modes**. | Active |
| 15 | **Suresh Raman** | `u_staff_8` | Has role **staff** for **all clients**, **branch b4 (Chennai)**, **all directions**, **all modes**. | Active |
| 16 | **Karan Singh** | `u_staff_9` | Has role **staff** for **all clients**, **branch b5 (Kolkata)**, **all directions**, **all modes**. | Active |
| 17 | **Pooja Banerjee** | `u_staff_10` | Has role **staff** for **all clients**, **branch b5 (Kolkata)**, **all directions**, **all modes**. | Active |
| 18 | **Manoj Sen** | `u_staff_11` | Has role **staff** for **all clients**, **branch b5 (Kolkata)**, **all directions**, **all modes**. **Currently on leave** (`is_active = 0`). | On Leave |
| 19 | **Tarun Junior** | `u_staff_junior` | Has role **staff** for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. Junior probationary operator. | Active |
| 20 | **Overnight EDI Parser** | `u_parser` | Has role **staff** (Automated Service Account) for **all clients**, **branch b1 (Mumbai)**, **all directions**, **all modes**. Ingests and prepares overnight batch entries; blocked from checking own jobs. | Active (System) |

---

## 🏛️ Core Architectural Highlights

1. **Four Specialized System Roles**:
   - **`Admin`**: Global branch scope (`all`), staff user access management, audit inspection, and **exclusive authority to `cancel` and `reopen` jobs**.
   - **`Job_assigner`**: Cross-branch coordination, job allocation to branch staff members.
   - **`auditor`**: Compliance dashboard with audit search, filter, and interactive sign-off (**Verify**, **Flag**, **Reject**).
   - **`staff`**: Operational progression through `Confirmed` $\to$ `Prepared` $\to$ `Checked` $\to$ `Filed` with Maker-Checker Separation of Duties.

2. **Maker-Checker Separation of Duties (SoD)**:
   - The staff member who executed the `prepare` step (`prepared_by`) is strictly prohibited from executing the `check` step on the same shipment, even if they hold valid branch permissions. An independent colleague must review and check the shipment.

3. **Absence & Soft-Lock Dissolution**:
   - Staff can toggle absent leave (`is_active = 0`) directly from their profile. While active, an assigned job is soft-locked to the assignee; once absent, the soft-lock dissolves immediately so branch peers can take over without operational delay.

4. **⚖️ Decision Comparison Engine ("Why can she and he can't?")**:
   - Features a dedicated API endpoint (`/api/compare`) and interactive UI modal.
   - Evaluates any two employees against any job and action, breaking down every security check (Active Duty, Branch Scope, Role Permission, Lifecycle State, Maker-Checker SoD, Soft-Lock) and outputting an intuitive comparison verdict.

---

## 🧪 Automated Test Suite Coverage

The test suite in [`test_access.py`](file:///d:/my%20projects/NAGARKOT/nfpl_access_control_simplified/test_access.py) validates all 11 core and edge cases:
1. `test_maker_cannot_check_own_work`: Enforces Maker-Checker SoD.
2. `test_job_assigner_can_assign_across_branches`: Cross-branch assignment.
3. `test_staff_access_managed_only_by_admin`: Staff access modifications restricted to Admin.
4. `test_auditor_review_verify_flag_reject`: Auditor sign-off workflow.
5. `test_queue_assignment_filter`: Accurate queue filtering (all / assigned / unassigned).
6. `test_absence_dissolves_soft_lock`: Peer takeover when assignee is on leave.
7. `test_cancel_and_reopen_restricted_to_admin`: Sensitive lifecycle lockdown.
8. `test_admin_self_escalation_blocked`: Unauthorized privilege escalation strictly refused.
9. `test_mid_job_responsibility_change`: Instant live re-evaluation upon branch transfer or role change.
10. `test_parser_service_account`: Overnight automated parser batch handling and SoD enforcement.
11. `test_compare_explains_why_she_can_and_he_cannot`: Decision comparison engine differential breakdown.
