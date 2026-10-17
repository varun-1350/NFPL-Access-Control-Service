# 5-Minute Technical & Evaluator Walkthrough Guide

Use this script during your live 5-minute assessment demonstration:

---

### ⏱️ 0:00–0:45 — The Situation & Problem
> *"NFPL is a customs brokerage with 120 staff across 5 physical branches (`b1` Mumbai to `b5` Kolkata). Each shipment is a job moving through Confirmed → Prepared → Checked → Filed.*
>
> *Recently, an unauthorized person altered a filed shipment because there was no unified authorization engine or clear audit trail. Management required an access system that is strict where it matters, easy to run day-to-day, and enforces four core principles: branch operational segregation, strict Maker-Checker Separation of Duties (SoD), automated soft-lock dissolution on employee absence, and executive lockdown for sensitive cancellations or reopens."*

---

### ⏱️ 0:45–1:45 — Live Architecture & Actionable Queue
1. Log in as **Priya Sharma (`u_staff_1`)** (Branch `b1` Mumbai).
2. Show the **Shipment Tasks & Branch Queue**:
   > *"Notice how Priya's queue only presents actionable shipments in Branch `b1` where she is eligible to perform the immediate next step. Our queue calculation isn't a dumb database filter—it runs the exact same `decide()` engine pipeline, verifying presence, branch clearance, stage validity, and Maker-Checker SoD."*
3. Show Priya clicking **Prepare** on an unassigned job. Notice how `prepared_by` records `u_staff_1`.

---

### ⏱️ 1:45–3:00 — Core Demo: "Why Can She Do This and He Can't?"
1. Click **`⚖️ Compare Access`** in the top navigation bar.
2. Select:
   - **Person A**: `Rahul Verma (u_staff_2)`
   - **Person B**: `Priya Sharma (u_staff_1)`
   - **Action**: `check`
   - **Job ID**: `1` (Prepared by Priya in Branch `b1`)
3. Click **Compare**:
   > *"Here is the live answer to the assessment's central question: 'Why can Rahul check this job and Priya cannot?' Both work in branch `b1`. Both are active on duty. But Priya was the Maker who prepared Job #1. The engine's Maker-Checker SoD gate strictly blocks Priya to prevent self-approval fraud, while Rahul—an independent peer—is fully authorized."*
4. Quick second comparison:
   - Change **Person A** to `Carol Admin (admin1)` vs **Person B** to `Priya Sharma (u_staff_1)` for action **`cancel`**.
   - Show how only `Admin` is authorized for sensitive lifecycle overrides (`admin_only` rule).

---

### ⏱️ 3:00–3:45 — Absence & Soft-Lock Dissolution
1. Switch to **👤 My Profile** as Priya. Click **🏖️ Apply for Absent Leave**.
2. Notice status switches to `On Leave` (`is_active = 0`).
3. Log in as **Rahul Verma (`u_staff_2`)**:
   > *"Any jobs previously soft-locked to Priya have their soft-locks automatically dissolved. Her branch peers immediately see the jobs marked 'Covering for colleague on leave', ensuring shipments never stall at customs due to staff absence."*

---

### ⏱️ 3:45–4:30 — Compliance Auditor Dashboard & Sign-Off
1. Log in as **Bob Auditor (`u_auditor_1`)**.
2. Notice the UI automatically renders the **System Audit & Compliance Stream**:
   > *"Every decision—both allowed operations and denied policy violations—is permanently logged with actor, timestamp, and rule diagnostics. The compliance auditor has live interactive actions to **Verify (✓)**, **Flag (🚩)**, or **Reject (✕)** any entry with auditable compliance notes."*

---

### ⏱️ 4:30–5:00 — Scale Benchmark & Closing Trade-offs
1. Mention the automated test suite and scale benchmark:
   > *"We validate this with 11 automated unit tests covering SoD, absence, cross-branch assignment, admin escalation blocks, mid-lifecycle transfer, and the overnight parser. Furthermore, `generate_scale.py` proves that with 500 users and 200,000 jobs, our indexed queue responds in under 350 milliseconds.*
   >
   > *Our key design trade-off was live atomic database evaluation over stale permission caching—guaranteeing that role changes and leaves take effect with zero latency."*
