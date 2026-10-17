"""Nagarkot Access Control Desktop Application.

Features:
- Simplified Login: Only asks for User ID and Password.
- Four Core Roles: Admin, Job_assigner, auditor, staff.
- Branches: b1, b2, b3, b4, b5.
- Jobs states: Confirmed -> Prepared -> Checked -> Filed (Cancelled and Reopened by Admin only).
- Employee table: name, id, Role, Branch, Job queue, is_active.
- Jobs table: ID, Client, assigned_to, state, Mode (air, land, sea), direction (import/export), branch.
- Interactive Filters, Search, and Sorting across:
  * Task Queue
  * Jobs Dataset
  * Employee Database Directory
  * Audit Changes Log
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from engine import AccessEngine, Denied, Refused

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class NagarkotApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Nagarkot Access Control Service - NFPL")
        self.geometry("1220x800")
        self.minsize(1080, 720)

        # Initialize Decision Engine
        try:
            self.engine = AccessEngine("nfpl_demo.db")
        except Exception as e:
            messagebox.showerror("Database Error", f"Unable to open 'nfpl_demo.db': {e}\nPlease run 'python seed_demo.py' first.")
            self.destroy()
            return

        # Session State
        self.logged_in_user = None
        self.logged_in_user_name = None
        self.logged_in_role = None
        self.logged_in_branch = None

        # Cache for live queue filtering
        self.queue_cache = []

        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self._show_login_page()

    # =========================================================================
    # PAGE 1: LOGIN PAGE (User ID & Password only)
    # =========================================================================
    def _show_login_page(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        login_card = ctk.CTkFrame(self.container, corner_radius=16, fg_color=("gray90", "#1E293B"), width=480, height=520)
        login_card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            login_card,
            text="NAGARKOT ACCESS CONTROL",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#38BDF8"
        ).pack(pady=(35, 6))

        ctk.CTkLabel(
            login_card,
            text="Enterprise Logistics Security Gateway (b1 - b5)",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(pady=(0, 25))

        # 1. User ID Selector / Dropdown
        ctk.CTkLabel(login_card, text="User ID:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=45, pady=(5, 3))

        employees = [dict(r) for r in self.engine.con.execute("SELECT name, id, role, branch, job_queue, is_active FROM employees").fetchall()]
        self.employee_records = {e['id']: e for e in employees}

        user_list = [f"{e['id']} - {e['name']} [{e['role']} | Branch: {e['branch']}]" for e in employees]

        self.user_cb = ctk.CTkOptionMenu(
            login_card,
            values=user_list,
            width=390,
            height=38
        )
        self.user_cb.pack(padx=45, pady=(0, 16))

        # 2. Password Entry
        ctk.CTkLabel(login_card, text="Password:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=45, pady=(5, 3))
        self.password_entry = ctk.CTkEntry(
            login_card,
            placeholder_text="Enter password (Optional for demo)",
            show="*",
            width=390,
            height=38
        )
        self.password_entry.pack(padx=45, pady=(0, 8))

        ctk.CTkLabel(
            login_card,
            text="ℹ️ Test App Mode: Password verification is bypassed for rapid evaluation.",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        ).pack(padx=45, pady=(0, 24), anchor="w")

        # Submit Login Button
        submit_btn = ctk.CTkButton(
            login_card,
            text="Log In",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            width=390,
            fg_color="#0284C7",
            hover_color="#0369A1",
            command=self._handle_login
        )
        submit_btn.pack(padx=45, pady=(0, 30))

        if user_list:
            self.user_cb.set(user_list[0])

    def _handle_login(self):
        val = self.user_cb.get()
        uid = val.split(" - ")[0].strip() if val else ""
        emp = self.employee_records.get(uid)
        if not emp:
            messagebox.showerror("Error", f"Employee '{uid}' not found.")
            return

        self.logged_in_user = emp['id']
        self.logged_in_user_name = emp['name']
        self.logged_in_role = emp['role']
        self.logged_in_branch = emp['branch']

        self._show_dashboard_page()

    # =========================================================================
    # PAGE 2: DASHBOARD PAGE
    # =========================================================================
    def _show_dashboard_page(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        emp = self.engine._employee(self.logged_in_user)
        is_active = bool(emp['is_active'])

        # Top Banner Bar
        top_bar = ctk.CTkFrame(self.container, corner_radius=12, fg_color=("#E2E8F0", "#0F172A"))
        top_bar.pack(fill="x", padx=16, pady=12)

        info_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        info_frame.pack(side="left", padx=16, pady=10)

        ctk.CTkLabel(
            info_frame,
            text=f"👤 {self.logged_in_user_name} ({self.logged_in_user})",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38BDF8"
        ).pack(side="left", padx=(0, 15))

        role_colors = {
            "Admin": "#EF4444",
            "Job_assigner": "#059669",
            "auditor": "#F59E0B",
            "staff": "#3B82F6"
        }
        r_color = role_colors.get(self.logged_in_role, "#38BDF8")
        ctk.CTkLabel(
            info_frame,
            text=f"Role: {self.logged_in_role}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=r_color
        ).pack(side="left", padx=(0, 15))

        branch_text = "all (Global)" if self.logged_in_branch == "all" else self.logged_in_branch
        ctk.CTkLabel(
            info_frame,
            text=f"Branch: {branch_text}",
            font=ctk.CTkFont(size=13),
            text_color="#10B981"
        ).pack(side="left", padx=(0, 15))

        status_text = "● ACTIVE ON DUTY" if is_active else "● ON LEAVE (Soft-Locks Dissolved)"
        status_color = "#22C55E" if is_active else "#A855F7"
        ctk.CTkLabel(
            info_frame,
            text=status_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=status_color
        ).pack(side="left")

        # Top Action Buttons
        btn_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=16, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="👤 My Profile",
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            command=self._show_profile_modal
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="📜 Audit Changes Log",
            fg_color="#D97706",
            hover_color="#B45309",
            height=32,
            command=self._show_audit_modal
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="🚪 Log Out",
            fg_color="#DC2626",
            hover_color="#991B1B",
            height=32,
            width=90,
            command=self._show_login_page
        ).pack(side="left")

        # Main Workspace Container
        main_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Left Column: Task Box & Queue OR Auditor Compliance Stream (65% width)
        left_card = ctk.CTkFrame(main_frame, corner_radius=12, fg_color=("#F1F5F9", "#1E293B"))
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 12))

        q_header = ctk.CTkFrame(left_card, fg_color="transparent")
        q_header.pack(fill="x", padx=16, pady=(12, 4))

        is_auditor = (self.logged_in_role == "auditor")
        title_text = "📜 System Audit Log & Compliance Stream" if is_auditor else "Shipment Task Queue & Branch Jobs"
        ctk.CTkLabel(
            q_header,
            text=title_text,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#E2E8F0"
        ).pack(side="left")

        ctk.CTkButton(
            q_header,
            text="🔄 Refresh",
            width=80,
            height=28,
            fg_color="#334155",
            hover_color="#475569",
            command=self._load_task_queue
        ).pack(side="right")

        self.metrics_label = ctk.CTkLabel(left_card, text="Loading metrics...", font=ctk.CTkFont(size=12), text_color="#94A3B8")
        self.metrics_label.pack(anchor="w", padx=16, pady=(0, 8))

        # Filter & Sort Toolbar for Left Card
        filter_bar = ctk.CTkFrame(left_card, fg_color=("#E2E8F0", "#0F172A"), corner_radius=8)
        filter_bar.pack(fill="x", padx=16, pady=(0, 8))

        self.queue_search_var = tk.StringVar()
        self.queue_search_var.trace_add("write", lambda *args: self._filter_and_render_queue())

        if is_auditor:
            queue_search = ctk.CTkEntry(filter_bar, textvariable=self.queue_search_var, placeholder_text="🔍 Search Actor, Op, Target...", width=180, height=28)
            queue_search.pack(side="left", padx=8, pady=6)

            self.audit_dec_cb = ctk.CTkOptionMenu(
                filter_bar,
                values=["All Decisions", "ALLOWED", "DENIED"],
                width=120,
                height=28,
                command=lambda v: self._filter_and_render_queue()
            )
            self.audit_dec_cb.pack(side="left", padx=(0, 6), pady=6)

            self.audit_status_cb = ctk.CTkOptionMenu(
                filter_bar,
                values=["All Status", "Pending", "Verified", "Flagged", "Rejected"],
                width=120,
                height=28,
                command=lambda v: self._filter_and_render_queue()
            )
            self.audit_status_cb.pack(side="left", padx=(0, 6), pady=6)

            self.queue_sort_cb = ctk.CTkOptionMenu(
                filter_bar,
                values=["Newest First", "Oldest First"],
                width=120,
                height=28,
                command=lambda v: self._filter_and_render_queue()
            )
            self.queue_sort_cb.pack(side="left", padx=(0, 8), pady=6)
        else:
            queue_search = ctk.CTkEntry(filter_bar, textvariable=self.queue_search_var, placeholder_text="🔍 Search Client or ID...", width=150, height=28)
            queue_search.pack(side="left", padx=8, pady=6)

            self.queue_state_cb = ctk.CTkOptionMenu(
                filter_bar,
                values=["All States", "Confirmed", "Prepared", "Checked", "Filed", "Cancelled", "Reopened"],
                width=110,
                height=28,
                command=lambda v: self._filter_and_render_queue()
            )
            self.queue_state_cb.pack(side="left", padx=(0, 6), pady=6)

            self.queue_mode_cb = ctk.CTkOptionMenu(
                filter_bar,
                values=["All Modes", "air", "land", "sea"],
                width=95,
                height=28,
                command=lambda v: self._filter_and_render_queue()
            )
            self.queue_mode_cb.pack(side="left", padx=(0, 6), pady=6)

            self.queue_assign_cb = ctk.CTkOptionMenu(
                filter_bar,
                values=["All Jobs", "Only Assigned", "Only Unassigned"],
                width=120,
                height=28,
                command=lambda v: self._filter_and_render_queue()
            )
            self.queue_assign_cb.pack(side="left", padx=(0, 6), pady=6)

            self.queue_sort_cb = ctk.CTkOptionMenu(
                filter_bar,
                values=["ID (Newest)", "ID (Oldest)", "Client (A-Z)", "State"],
                width=110,
                height=28,
                command=lambda v: self._filter_and_render_queue()
            )
            self.queue_sort_cb.pack(side="left", padx=(0, 8), pady=6)

        self.task_scroll = ctk.CTkScrollableFrame(left_card, fg_color="transparent")
        self.task_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Right Column: Role Action Panel (35% width)
        right_card = ctk.CTkFrame(main_frame, corner_radius=12, fg_color=("#F1F5F9", "#1E293B"), width=340)
        right_card.pack(side="right", fill="y", padx=0)
        right_card.pack_propagate(False)

        ctk.CTkLabel(
            right_card,
            text="Role Action Panel",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#E2E8F0"
        ).pack(anchor="w", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            right_card,
            text=f"Privilege Scope: {self.logged_in_role}",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=16, pady=(0, 14))

        self._render_case_controls(right_card)
        self._load_task_queue()

    # =========================================================================
    # ROLE CONTROLS DISPATCH
    # =========================================================================
    def _render_case_controls(self, parent):
        r = self.logged_in_role

        if r == "Admin":
            ctk.CTkLabel(parent, text="ADMIN ACTIONS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#EF4444").pack(anchor="w", padx=16, pady=(8, 4))

            ctk.CTkButton(parent, text="📦 Access Jobs Dataset Table", fg_color="#2563EB", height=38, command=self._view_all_jobs).pack(fill="x", padx=16, pady=5)
            ctk.CTkButton(parent, text="👥 Employee Database Table", fg_color="#2563EB", height=38, command=self._view_emp_db).pack(fill="x", padx=16, pady=5)
            ctk.CTkButton(parent, text="⚙️ Cancel / Reopen Jobs (Admin Only)", fg_color="#DC2626", height=38, command=self._admin_lifecycle_modal).pack(fill="x", padx=16, pady=5)
            ctk.CTkButton(parent, text="🛡️ View System Audit Log", fg_color="#0D9488", height=38, command=self._show_audit_modal).pack(fill="x", padx=16, pady=5)
            ctk.CTkButton(parent, text="🔑 Manage Staff Access", fg_color="#2563EB", height=38, command=self._manage_access).pack(fill="x", padx=16, pady=5)

        elif r == "staff":
            ctk.CTkLabel(parent, text="STAFF ACTIONS (BRANCH BOUND)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=16, pady=(8, 4))

            ctk.CTkButton(parent, text="⏩ Advance Next Assigned Job", fg_color="#059669", height=38, command=self._advance_next_job).pack(fill="x", padx=16, pady=5)

            emp = self.engine._employee(self.logged_in_user)
            leave_text = "🟢 Return to Duty (End Leave)" if not emp['is_active'] else "🏖️ Apply for Absent Leave"
            leave_color = "#10B981" if not emp['is_active'] else "#7C3AED"
            ctk.CTkButton(parent, text=leave_text, fg_color=leave_color, height=38, command=self._toggle_leave).pack(fill="x", padx=16, pady=5)

            ctk.CTkButton(parent, text="📜 Audit Log (Read-Only)", fg_color="#64748B", height=38, command=self._show_audit_modal).pack(fill="x", padx=16, pady=5)
            # Staff access management removed: Strictly managed by Admin!

        elif r == "Job_assigner":
            ctk.CTkLabel(parent, text="JOB ASSIGNER ACTIONS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#059669").pack(anchor="w", padx=16, pady=(8, 4))

            ctk.CTkButton(parent, text="📦 Access Jobs Dataset Table", fg_color="#2563EB", height=38, command=self._view_all_jobs).pack(fill="x", padx=16, pady=5)
            ctk.CTkButton(parent, text="🎯 Assign Job (Cross-Branch Permitted)", fg_color="#059669", height=38, command=self._assign_job_modal).pack(fill="x", padx=16, pady=5)

        elif r == "auditor":
            ctk.CTkLabel(parent, text="AUDITOR ACTIONS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#F59E0B").pack(anchor="w", padx=16, pady=(8, 4))

            ctk.CTkButton(parent, text="📦 View Jobs Dataset (Read-Only)", fg_color="#2563EB", height=38, command=lambda: self._view_all_jobs(read_only=True)).pack(fill="x", padx=16, pady=5)
            ctk.CTkButton(parent, text="🔄 Refresh Audit Stream", fg_color="#D97706", height=38, command=self._load_task_queue).pack(fill="x", padx=16, pady=5)

    # =========================================================================
    # TASK QUEUE RENDERING & REACTIVE FILTERING
    # =========================================================================
    def _load_task_queue(self):
        uid = self.logged_in_user
        role = self.logged_in_role
        branch = self.logged_in_branch

        if role == "auditor":
            self.audit_cache = [dict(r) for r in self.engine.con.execute("SELECT * FROM audit ORDER BY id DESC").fetchall()]
            tot = len(self.audit_cache)
            p = len([a for a in self.audit_cache if (a.get('verification_status') == 'pending' or not a.get('verification_status')) and not a.get('verified_by')])
            v = len([a for a in self.audit_cache if a.get('verification_status') == 'verified' or a.get('verified_by')])
            f = len([a for a in self.audit_cache if a.get('verification_status') in ('flagged', 'rejected')])
            self.metrics_label.configure(text=f"Compliance Stream | Total: {tot} | Pending Review: {p} | Verified: {v} | Flagged/Rejected: {f}")
        elif role in ("Job_assigner", "Admin"):
            if branch and branch != "all":
                self.queue_cache = [dict(r) for r in self.engine.con.execute("SELECT * FROM jobs WHERE branch=? ORDER BY id DESC", (branch,)).fetchall()]
            else:
                self.queue_cache = [dict(r) for r in self.engine.con.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()]
            self.metrics_label.configure(text=f"Jobs Dataset Scope: {branch} (Total: {len(self.queue_cache)})")
        else:
            q = self.engine.queue(uid)
            self.queue_cache = q['items']
            self.metrics_label.configure(text=f"Assigned Branch Queue [{branch}] | Actionable: {q['total']} (Prepare: {q['counts']['prepare']}, Check: {q['counts']['check']}, File: {q['counts']['file']})")

        self._filter_and_render_queue()

    def _auditor_action(self, aid, new_status):
        notes = f"Compliance {new_status} by {self.logged_in_user}"
        try:
            self.engine.review_audit_entry(self.logged_in_user, aid, status=new_status, notes=notes)
            messagebox.showinfo("Audit Review", f"Audit Entry #{aid} marked as '{new_status}'.")
            self._load_task_queue()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _filter_and_render_queue(self):
        for widget in self.task_scroll.winfo_children():
            widget.destroy()

        search = self.queue_search_var.get().strip().lower()

        # AUDITOR PRIMARY VIEW: RENDER AUDIT LOG STREAM
        if self.logged_in_role == "auditor":
            d_filt = self.audit_dec_cb.get()
            s_filt = self.audit_status_cb.get()
            sort_by = self.queue_sort_cb.get()

            filtered = list(self.audit_cache)

            if search:
                filtered = [a for a in filtered if search in a['actor'].lower() or search in a['op'].lower() or search in a['target'].lower() or search in a['detail'].lower()]
            if d_filt == "ALLOWED":
                filtered = [a for a in filtered if a['allowed'] == 1]
            elif d_filt == "DENIED":
                filtered = [a for a in filtered if a['allowed'] == 0]

            if s_filt == "Pending":
                filtered = [a for a in filtered if (a.get('verification_status') == 'pending' or not a.get('verification_status')) and not a.get('verified_by')]
            elif s_filt == "Verified":
                filtered = [a for a in filtered if a.get('verification_status') == 'verified' or a.get('verified_by')]
            elif s_filt == "Flagged":
                filtered = [a for a in filtered if a.get('verification_status') == 'flagged']
            elif s_filt == "Rejected":
                filtered = [a for a in filtered if a.get('verification_status') == 'rejected']

            if sort_by == "Oldest First":
                filtered.sort(key=lambda x: x['id'])
            else:
                filtered.sort(key=lambda x: -x['id'])

            if not filtered:
                empty_frame = ctk.CTkFrame(self.task_scroll, fg_color="transparent")
                empty_frame.pack(fill="both", expand=True, pady=40)
                ctk.CTkLabel(empty_frame, text="🔍 No audit entries match the selected filters.", font=ctk.CTkFont(size=14, weight="bold"), text_color="#94A3B8").pack()
                return

            for a in filtered:
                card = ctk.CTkFrame(self.task_scroll, corner_radius=10, fg_color=("#E2E8F0", "#1E293B"))
                card.pack(fill="x", pady=5, padx=4)

                top_row = ctk.CTkFrame(card, fg_color="transparent")
                top_row.pack(fill="x", padx=12, pady=(8, 2))

                status_tag = "ALLOWED" if a['allowed'] else "DENIED"
                tag_color = "#10B981" if a['allowed'] else "#EF4444"
                ctk.CTkLabel(top_row, text=f" [{status_tag}] ", fg_color=tag_color, font=ctk.CTkFont(size=11, weight="bold"), corner_radius=4, text_color="#FFFFFF").pack(side="left")

                v_status = (a.get('verification_status') or ('verified' if a.get('verified_by') else 'pending')).upper()
                v_color = "#10B981" if v_status == "VERIFIED" else ("#F59E0B" if v_status == "FLAGGED" else ("#EF4444" if v_status == "REJECTED" else "#94A3B8"))
                ctk.CTkLabel(top_row, text=f" {v_status} ", fg_color=v_color, font=ctk.CTkFont(size=10, weight="bold"), corner_radius=4, text_color="#FFFFFF").pack(side="left", padx=(6, 0))

                ctk.CTkLabel(top_row, text=f"  Entry #{a['id']} | [{a['ts']}]", font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(side="left")

                # Action Buttons on right of top row
                btn_row = ctk.CTkFrame(top_row, fg_color="transparent")
                btn_row.pack(side="right")
                ctk.CTkButton(btn_row, text="✓ Verify", width=65, height=24, fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=11, weight="bold"), command=lambda aid=a['id']: self._auditor_action(aid, 'verified')).pack(side="left", padx=2)
                ctk.CTkButton(btn_row, text="🚩 Flag", width=60, height=24, fg_color="#F59E0B", hover_color="#D97706", font=ctk.CTkFont(size=11, weight="bold"), command=lambda aid=a['id']: self._auditor_action(aid, 'flagged')).pack(side="left", padx=2)
                ctk.CTkButton(btn_row, text="✕ Reject", width=65, height=24, fg_color="#EF4444", hover_color="#DC2626", font=ctk.CTkFont(size=11, weight="bold"), command=lambda aid=a['id']: self._auditor_action(aid, 'rejected')).pack(side="left", padx=2)

                bot_row = ctk.CTkFrame(card, fg_color="transparent")
                bot_row.pack(fill="x", padx=12, pady=(2, 8))
                detail_text = f"Actor: {a['actor']} | Op: {a['op']} | Target: {a['target']} | Detail: {a['detail']}"
                if a.get('verified_by'):
                    detail_text += f" | Sign-off: {a['verified_by']} ({a.get('verification_notes') or ''})"
                ctk.CTkLabel(bot_row, text=detail_text, font=ctk.CTkFont(size=12), text_color="#E2E8F0").pack(anchor="w")
            return

        # STANDARD VIEW: RENDER SHIPMENT TASKS QUEUE
        state_filter = self.queue_state_cb.get()
        mode_filter = self.queue_mode_cb.get()
        assign_filter = self.queue_assign_cb.get()
        sort_by = self.queue_sort_cb.get()

        filtered = list(self.queue_cache)

        if search:
            filtered = [j for j in filtered if search in j['client'].lower() or search in str(j['id'])]
        if state_filter != "All States":
            filtered = [j for j in filtered if j['state'] == state_filter]
        if mode_filter != "All Modes":
            filtered = [j for j in filtered if j['mode'] == mode_filter]
        if assign_filter == "Only Assigned":
            filtered = [j for j in filtered if j.get('assigned_to')]
        elif assign_filter == "Only Unassigned":
            filtered = [j for j in filtered if not j.get('assigned_to')]

        if sort_by == "ID (Oldest)":
            filtered.sort(key=lambda x: x['id'])
        elif sort_by == "Client (A-Z)":
            filtered.sort(key=lambda x: x['client'].lower())
        elif sort_by == "State":
            filtered.sort(key=lambda x: (x['state'], -x['id']))
        else:
            filtered.sort(key=lambda x: -x['id'])

        if not filtered:
            empty_frame = ctk.CTkFrame(self.task_scroll, fg_color="transparent")
            empty_frame.pack(fill="both", expand=True, pady=40)
            ctk.CTkLabel(empty_frame, text="🔍 No shipment tasks match the selected filters.", font=ctk.CTkFont(size=14, weight="bold"), text_color="#94A3B8").pack()
            return

        for j in filtered:
            card = ctk.CTkFrame(self.task_scroll, corner_radius=10, fg_color=("#E2E8F0", "#334155"))
            card.pack(fill="x", pady=5, padx=4)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=12, pady=(8, 2))

            stage_colors = {"Confirmed": "#3B82F6", "Prepared": "#F59E0B", "Checked": "#10B981", "Filed": "#64748B", "Cancelled": "#EF4444", "Reopened": "#A855F7"}
            ctk.CTkLabel(top_row, text=f" {j['state']} ", fg_color=stage_colors.get(j['state'], "#3B82F6"), corner_radius=4, font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFFFFF").pack(side="left")
            ctk.CTkLabel(top_row, text=f"  Job #{j['id']} - {j['client']}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#F8FAFC").pack(side="left")

            owner_str = f"Assigned: {j['assigned_to'] or 'Unassigned'}"
            ctk.CTkLabel(top_row, text=owner_str, font=ctk.CTkFont(size=11), text_color="#CBD5E1").pack(side="right")

            bot_row = ctk.CTkFrame(card, fg_color="transparent")
            bot_row.pack(fill="x", padx=12, pady=(2, 8))

            details = f"Branch: {j['branch']}  |  Mode: {j['mode'].upper()}  |  Direction: {j['direction'].capitalize()}  |  Prep: {j.get('prepared_by') or 'None'}"
            ctk.CTkLabel(bot_row, text=details, font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(side="left")

            if self.logged_in_role == "staff" and 'action' in j:
                act = j['action']
                tag_color = "#3B82F6" if act == "prepare" else ("#F59E0B" if act == "check" else "#10B981")
                ctk.CTkButton(bot_row, text=f"Execute: {act.capitalize()}", height=24, width=110, fg_color=tag_color, command=lambda a=act, jid=j['id']: self._execute_task_action(a, jid)).pack(side="right")
            elif self.logged_in_role == "Job_assigner" and j['state'] in ('Confirmed', 'Prepared', 'Reopened'):
                ctk.CTkButton(bot_row, text="Assign to Staff", height=24, width=110, fg_color="#059669", command=lambda jid=j['id']: self._assign_job_modal(jid)).pack(side="right")

    def _execute_task_action(self, action, job_id):
        reason = f"Desktop execution of {action}"
        try:
            res = self.engine.act(self.logged_in_user, job_id, action, reason=reason)
            messagebox.showinfo("Queue Updated", f"Job #{job_id} advanced successfully!\nNew State: {res.get('state')}")
            self._load_task_queue()
        except Denied as d:
            messagebox.showerror(
                "Access Denied (Security Policy Violation)",
                f"Policy Engine Blocked Action '{action}' on Job #{job_id}:\n\n{d.decision.summary()}\n\nEvaluation Details:\n{d.decision.explain()}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to execute action: {e}")

    def _advance_next_job(self):
        q = self.engine.queue(self.logged_in_user)
        if q['items']:
            self._execute_task_action(q['items'][0]['action'], q['items'][0]['id'])
        else:
            messagebox.showinfo("Queue Empty", "No tasks currently waiting in your branch queue.")

    def _toggle_leave(self):
        res = self.engine.toggle_leave(self.logged_in_user)
        messagebox.showinfo("Leave Status", res['message'])
        self._show_dashboard_page()

    # =========================================================================
    # ROLE MODALS WITH FILTERS & SORTING
    # =========================================================================
    def _view_emp_db(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Employee Database Table")
        modal.geometry("920x600")
        modal.grab_set()

        ctk.CTkLabel(modal, text="👥 Employee Database Table", font=ctk.CTkFont(size=18, weight="bold"), text_color="#38BDF8").pack(pady=(16, 2))
        ctk.CTkLabel(modal, text="Attributes: name, id, Role, Branch, Job queue, is_active", font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 10))

        # Filter bar
        filter_bar = ctk.CTkFrame(modal, fg_color=("#E2E8F0", "#1E293B"), corner_radius=8)
        filter_bar.pack(fill="x", padx=20, pady=(0, 10))

        search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(filter_bar, textvariable=search_var, placeholder_text="🔍 Search Name or ID...", width=160, height=28)
        search_entry.pack(side="left", padx=8, pady=6)

        role_cb = ctk.CTkOptionMenu(filter_bar, values=["All Roles", "Admin", "Job_assigner", "auditor", "staff"], width=110, height=28)
        role_cb.pack(side="left", padx=(0, 6), pady=6)

        branch_cb = ctk.CTkOptionMenu(filter_bar, values=["All Branches", "all", "b1", "b2", "b3", "b4", "b5"], width=110, height=28)
        branch_cb.pack(side="left", padx=(0, 6), pady=6)

        status_cb = ctk.CTkOptionMenu(filter_bar, values=["All Status", "Active", "On Leave"], width=110, height=28)
        status_cb.pack(side="left", padx=(0, 6), pady=6)

        sort_cb = ctk.CTkOptionMenu(filter_bar, values=["Name (A-Z)", "Name (Z-A)", "ID (A-Z)", "Role", "Branch"], width=120, height=28)
        sort_cb.pack(side="left", padx=(0, 8), pady=6)

        scroll = ctk.CTkScrollableFrame(modal, width=860, height=420)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        count_label = ctk.CTkLabel(modal, text="Showing employees...", font=ctk.CTkFont(size=12), text_color="#94A3B8")
        count_label.pack(anchor="w", padx=20, pady=(0, 10))

        all_employees = [dict(r) for r in self.engine.con.execute("SELECT name, id, role, branch, job_queue, is_active FROM employees").fetchall()]

        def render_employees():
            for widget in scroll.winfo_children():
                widget.destroy()

            s_text = search_var.get().strip().lower()
            r_filt = role_cb.get()
            b_filt = branch_cb.get()
            st_filt = status_cb.get()
            sort_val = sort_cb.get()

            filtered = list(all_employees)

            if s_text:
                filtered = [e for e in filtered if s_text in e['name'].lower() or s_text in e['id'].lower()]
            if r_filt != "All Roles":
                filtered = [e for e in filtered if e['role'] == r_filt]
            if b_filt != "All Branches":
                filtered = [e for e in filtered if e['branch'] == b_filt]
            if st_filt == "Active":
                filtered = [e for e in filtered if e['is_active'] == 1]
            elif st_filt == "On Leave":
                filtered = [e for e in filtered if e['is_active'] == 0]

            if sort_val == "Name (Z-A)":
                filtered.sort(key=lambda x: x['name'], reverse=True)
            elif sort_val == "ID (A-Z)":
                filtered.sort(key=lambda x: x['id'])
            elif sort_val == "Role":
                filtered.sort(key=lambda x: (x['role'], x['name']))
            elif sort_val == "Branch":
                filtered.sort(key=lambda x: (x['branch'], x['name']))
            else:
                filtered.sort(key=lambda x: x['name'])

            count_label.configure(text=f"Showing {len(filtered)} of {len(all_employees)} employees")

            for e in filtered:
                card = ctk.CTkFrame(scroll, fg_color=("#E2E8F0", "#1E293B"), corner_radius=8)
                card.pack(fill="x", pady=4, padx=4)

                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=8)

                status = "🟢 Active" if e['is_active'] else "🟣 On Leave"
                txt = f"{e['name']} ({e['id']})  |  Role: {e['role']}  |  Branch: {e['branch']}  |  Status: {status}"
                ctk.CTkLabel(row, text=txt, font=ctk.CTkFont(size=13, weight="bold"), text_color="#F8FAFC").pack(anchor="w")

                q_txt = f"Job Queue: {e['job_queue'] or 'Empty'}"
                ctk.CTkLabel(row, text=q_txt, font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(anchor="w", pady=(2, 0))

        search_var.trace_add("write", lambda *args: render_employees())
        role_cb.configure(command=lambda v: render_employees())
        branch_cb.configure(command=lambda v: render_employees())
        status_cb.configure(command=lambda v: render_employees())
        sort_cb.configure(command=lambda v: render_employees())

        render_employees()

    def _view_all_jobs(self, read_only=False):
        modal = ctk.CTkToplevel(self)
        title_tag = " (Read-Only Inspection)" if read_only else ""
        modal.title(f"Jobs Dataset Table{title_tag}")
        modal.geometry("980x640")
        modal.grab_set()

        ctk.CTkLabel(modal, text=f"📦 Jobs Dataset Table{title_tag}", font=ctk.CTkFont(size=18, weight="bold"), text_color="#38BDF8").pack(pady=(16, 2))
        ctk.CTkLabel(modal, text="Attributes: ID, Client, assigned_to, state, Mode (air, land, sea), direction (import/export), branch", font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 10))

        filter_bar = ctk.CTkFrame(modal, fg_color=("#E2E8F0", "#1E293B"), corner_radius=8)
        filter_bar.pack(fill="x", padx=20, pady=(0, 8))

        search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(filter_bar, textvariable=search_var, placeholder_text="🔍 Search Client or ID...", width=150, height=28)
        search_entry.pack(side="left", padx=8, pady=6)

        branch_cb = ctk.CTkOptionMenu(filter_bar, values=["All Branches", "b1", "b2", "b3", "b4", "b5"], width=105, height=28)
        branch_cb.pack(side="left", padx=(0, 6), pady=6)

        state_cb = ctk.CTkOptionMenu(filter_bar, values=["All States", "Confirmed", "Prepared", "Checked", "Filed", "Cancelled", "Reopened"], width=105, height=28)
        state_cb.pack(side="left", padx=(0, 6), pady=6)

        mode_cb = ctk.CTkOptionMenu(filter_bar, values=["All Modes", "air", "land", "sea"], width=95, height=28)
        mode_cb.pack(side="left", padx=(0, 6), pady=6)

        dir_cb = ctk.CTkOptionMenu(filter_bar, values=["All Directions", "import", "export"], width=105, height=28)
        dir_cb.pack(side="left", padx=(0, 6), pady=6)

        assign_cb = ctk.CTkOptionMenu(filter_bar, values=["All Assignment", "Only Assigned", "Only Unassigned"], width=120, height=28)
        assign_cb.pack(side="left", padx=(0, 6), pady=6)

        sort_cb = ctk.CTkOptionMenu(filter_bar, values=["ID (Newest)", "ID (Oldest)", "Client (A-Z)", "State", "Branch"], width=110, height=28)
        sort_cb.pack(side="left", padx=(0, 8), pady=6)

        scroll = ctk.CTkScrollableFrame(modal, width=900, height=440)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        count_label = ctk.CTkLabel(modal, text="Showing jobs...", font=ctk.CTkFont(size=12), text_color="#94A3B8")
        count_label.pack(anchor="w", padx=20, pady=(0, 8))

        all_jobs = [dict(r) for r in self.engine.con.execute("SELECT * FROM jobs").fetchall()]

        def render_jobs():
            for widget in scroll.winfo_children():
                widget.destroy()

            s_text = search_var.get().strip().lower()
            b_filt = branch_cb.get()
            st_filt = state_cb.get()
            m_filt = mode_cb.get()
            d_filt = dir_cb.get()
            sort_val = sort_cb.get()

            filtered = list(all_jobs)

            if s_text:
                filtered = [j for j in filtered if s_text in j['client'].lower() or s_text in str(j['id']) or (j['assigned_to'] and s_text in j['assigned_to'].lower())]
            if b_filt != "All Branches":
                filtered = [j for j in filtered if j['branch'] == b_filt]
            if st_filt != "All States":
                filtered = [j for j in filtered if j['state'] == st_filt]
            if m_filt != "All Modes":
                filtered = [j for j in filtered if j['mode'] == m_filt]
            if d_filt != "All Directions":
                filtered = [j for j in filtered if j['direction'] == d_filt]

            if sort_val == "ID (Oldest)":
                filtered.sort(key=lambda x: x['id'])
            elif sort_val == "Client (A-Z)":
                filtered.sort(key=lambda x: x['client'].lower())
            elif sort_val == "State":
                filtered.sort(key=lambda x: (x['state'], -x['id']))
            elif sort_val == "Branch":
                filtered.sort(key=lambda x: (x['branch'], -x['id']))
            else:
                filtered.sort(key=lambda x: -x['id'])

            count_label.configure(text=f"Showing {len(filtered)} of {len(all_jobs)} shipment jobs")

            for j in filtered:
                card = ctk.CTkFrame(scroll, fg_color=("#E2E8F0", "#1E293B"), corner_radius=8)
                card.pack(fill="x", pady=4, padx=4)

                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=8)

                txt = f"Job #{j['id']}  |  Client: {j['client']}  |  State: {j['state']}  |  Mode: {j['mode'].upper()}  |  Dir: {j['direction']}  |  Branch: {j['branch']}"
                ctk.CTkLabel(row, text=txt, font=ctk.CTkFont(size=12, weight="bold"), text_color="#F8FAFC").pack(side="left")

                assigned = f"Assigned to: {j['assigned_to'] or 'Unassigned'}"
                ctk.CTkLabel(row, text=assigned, font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(side="right")

            a_filt = assign_cb.get()
            if a_filt == "Only Assigned":
                filtered = [j for j in filtered if j.get('assigned_to')]
            elif a_filt == "Only Unassigned":
                filtered = [j for j in filtered if not j.get('assigned_to')]

        search_var.trace_add("write", lambda *args: render_jobs())
        branch_cb.configure(command=lambda v: render_jobs())
        state_cb.configure(command=lambda v: render_jobs())
        mode_cb.configure(command=lambda v: render_jobs())
        dir_cb.configure(command=lambda v: render_jobs())
        assign_cb.configure(command=lambda v: render_jobs())
        sort_cb.configure(command=lambda v: render_jobs())

        render_jobs()

    def _admin_lifecycle_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Cancel / Reopen Jobs (Admin Only)")
        modal.geometry("540x380")
        modal.grab_set()

        ctk.CTkLabel(modal, text="⚙️ Admin Lifecycle Operations", font=ctk.CTkFont(size=18, weight="bold"), text_color="#EF4444").pack(pady=(16, 4))
        ctk.CTkLabel(modal, text="Sensitive Operations Restricted Exclusively to Admin", font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 16))

        action_cb = ctk.CTkOptionMenu(modal, values=["cancel", "reopen"], width=420)
        action_cb.pack(pady=8)

        jobs = self.engine.con.execute("SELECT id, client, state FROM jobs ORDER BY id DESC LIMIT 30").fetchall()
        job_choices = [f"Job #{j['id']} ({j['client']}) - Current State: {j['state']}" for j in jobs]
        job_cb = ctk.CTkOptionMenu(modal, values=job_choices, width=420)
        job_cb.pack(pady=8)

        reason_entry = ctk.CTkEntry(modal, placeholder_text="Enter mandatory justification reason", width=420)
        reason_entry.pack(pady=12)

        def do_execute():
            action = action_cb.get()
            job_id = int(job_cb.get().split("Job #")[1].split(" ")[0])
            reason = reason_entry.get().strip() or f"Admin {action}"
            try:
                res = self.engine.act(self.logged_in_user, job_id, action, reason=reason)
                messagebox.showinfo("Success", f"Job #{job_id} updated to '{res['state']}' by Admin.")
                modal.destroy()
                self._load_task_queue()
            except Denied as d:
                messagebox.showerror("Denied", d.decision.summary())
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

        ctk.CTkButton(modal, text="Execute Action", fg_color="#DC2626", hover_color="#991B1B", height=38, command=do_execute).pack(pady=12)

    def _assign_job_modal(self, preselected_job_id=None):
        modal = ctk.CTkToplevel(self)
        modal.title("Assign Job (Cross-Branch Permitted)")
        modal.geometry("560x420")
        modal.grab_set()

        ctk.CTkLabel(modal, text="🎯 Assign Shipment Job", font=ctk.CTkFont(size=18, weight="bold"), text_color="#38BDF8").pack(pady=(16, 4))
        ctk.CTkLabel(modal, text="Assign job to any available staff member (Cross-Branch Allowed)", font=ctk.CTkFont(size=12), text_color="#10B981").pack(pady=(0, 16))

        jobs = self.engine.con.execute("SELECT id, client, branch, state FROM jobs WHERE state IN ('Confirmed', 'Prepared', 'Reopened') ORDER BY branch, id").fetchall()
        if not jobs:
            ctk.CTkLabel(modal, text="No assignable jobs currently in the system.").pack(pady=20)
            return

        job_choices = [f"[Branch {j['branch']}] Job #{j['id']} ({j['client']}) - {j['state']}" for j in jobs]
        job_cb = ctk.CTkOptionMenu(modal, values=job_choices, width=460)
        job_cb.pack(padx=40, pady=(6, 12))

        staff_members = self.engine.con.execute("SELECT id, name, branch FROM employees WHERE role='staff' ORDER BY branch, name").fetchall()
        staff_choices = [f"{s['id']} - {s['name']} (Branch {s['branch']})" for s in staff_members]
        staff_cb = ctk.CTkOptionMenu(modal, values=staff_choices, width=460)
        staff_cb.pack(padx=40, pady=(6, 24))

        def do_assign():
            job_id = int(job_cb.get().split("Job #")[1].split(" ")[0])
            assignee = staff_cb.get().split(" - ")[0]
            try:
                res = self.engine.act(self.logged_in_user, job_id, "assign", assignee=assignee)
                messagebox.showinfo("Job Assigned", f"Job #{job_id} successfully assigned to {res['assigned_to']}.")
                modal.destroy()
                self._load_task_queue()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ctk.CTkButton(modal, text="Confirm Assignment", fg_color="#059669", height=38, command=do_assign).pack(padx=40, fill="x")

    def _manage_access(self):
        if self.logged_in_role != "Admin":
            messagebox.showerror("Access Denied", "Staff access management is restricted exclusively to Admin.")
            return

        modal = ctk.CTkToplevel(self)
        modal.title("Manage Staff Access (Admin Only)")
        modal.geometry("540x360")
        modal.grab_set()

        ctk.CTkLabel(modal, text="🔑 Manage Staff Access", font=ctk.CTkFont(size=18, weight="bold"), text_color="#38BDF8").pack(pady=(16, 4))
        ctk.CTkLabel(modal, text="Restricted Exclusively to Admin", font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 10))

        staff_rows = self.engine.con.execute("SELECT id, name, role, branch FROM employees").fetchall()
        staff_choices = [f"{s['id']} - {s['name']} ({s['role']} | {s['branch']})" for s in staff_rows]
        emp_cb = ctk.CTkOptionMenu(modal, values=staff_choices, width=420)
        emp_cb.pack(pady=10)

        role_cb = ctk.CTkOptionMenu(modal, values=["staff", "Job_assigner", "auditor"], width=420)
        role_cb.pack(pady=10)

        branch_cb = ctk.CTkOptionMenu(modal, values=["b1", "b2", "b3", "b4", "b5"], width=420)
        branch_cb.pack(pady=10)

        def do_update():
            emp_id = emp_cb.get().split(" - ")[0]
            role = role_cb.get()
            branch = branch_cb.get()
            try:
                self.engine.update_employee_role(self.logged_in_user, emp_id, role, branch)
                messagebox.showinfo("Access Updated", f"Employee {emp_id} updated to Role '{role}' in branch '{branch}'.")
                modal.destroy()
                self._load_task_queue()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

        ctk.CTkButton(modal, text="Update Access", fg_color="#2563EB", height=38, command=do_update).pack(pady=14)

    def _show_profile_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("My Profile - Security Context")
        modal.geometry("520x460")
        modal.grab_set()

        emp = self.engine._employee(self.logged_in_user)
        is_active = bool(emp['is_active'])

        ctk.CTkLabel(modal, text="👤 Employee Profile", font=ctk.CTkFont(size=20, weight="bold"), text_color="#38BDF8").pack(pady=(20, 4))
        ctk.CTkLabel(modal, text="Security Clearance & Access Context", font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 16))

        card = ctk.CTkFrame(modal, fg_color=("#E2E8F0", "#1E293B"), corner_radius=10)
        card.pack(fill="x", padx=24, pady=8)

        rows = [
            ("Full Name:", emp['name']),
            ("User ID:", emp['id']),
            ("System Role:", emp['role']),
            ("Assigned Branch:", "all (Global)" if emp['branch'] == "all" else emp['branch']),
            ("Duty Status:", "Active on Duty" if is_active else "On Absent Leave (Soft-Locks Dissolved)"),
            ("Assigned Job Queue:", emp['job_queue'] if emp['job_queue'] else "None (Queue Empty)")
        ]

        for label, val in rows:
            r_frame = ctk.CTkFrame(card, fg_color="transparent")
            r_frame.pack(fill="x", padx=16, pady=5)
            ctk.CTkLabel(r_frame, text=label, font=ctk.CTkFont(size=12, weight="bold"), text_color="#94A3B8", width=140, anchor="w").pack(side="left")
            val_color = "#22C55E" if "Active" in val else ("#A855F7" if "Leave" in val else "#F8FAFC")
            ctk.CTkLabel(r_frame, text=val, font=ctk.CTkFont(size=12), text_color=val_color, anchor="w").pack(side="left")

        if emp['role'] == "staff":
            leave_text = "🟢 Return to Active Duty" if not is_active else "🏖️ Apply for Absent Leave"
            leave_color = "#10B981" if not is_active else "#7C3AED"
            def toggle_and_refresh():
                self._toggle_leave()
                modal.destroy()
            ctk.CTkButton(modal, text=leave_text, fg_color=leave_color, height=36, command=toggle_and_refresh).pack(pady=16, padx=24, fill="x")

        ctk.CTkButton(modal, text="Close Profile", fg_color="#334155", hover_color="#475569", height=32, command=modal.destroy).pack(pady=(8, 16))

    def _show_audit_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("System Audit Changes Log")
        modal.geometry("960x640")
        modal.grab_set()

        ctk.CTkLabel(modal, text="📜 System Audit Changes Log", font=ctk.CTkFont(size=18, weight="bold"), text_color="#38BDF8").pack(pady=(16, 2))

        is_auditor = self.logged_in_role in ("auditor", "Admin")

        if is_auditor:
            bar = ctk.CTkFrame(modal, fg_color=("#E2E8F0", "#1E293B"), corner_radius=8)
            bar.pack(fill="x", padx=20, pady=(0, 8))

            ctk.CTkLabel(bar, text="Auditor Sign-off:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#F59E0B").pack(side="left", padx=12, pady=6)
            id_entry = ctk.CTkEntry(bar, width=60, placeholder_text="ID")
            id_entry.pack(side="left", padx=(0, 8))
            notes_entry = ctk.CTkEntry(bar, width=220, placeholder_text="Verification remarks")
            notes_entry.pack(side="left", padx=(0, 8))

            def do_verify():
                aid = id_entry.get().strip()
                if not aid.isdigit():
                    messagebox.showerror("Error", "Enter numeric ID")
                    return
                try:
                    self.engine.verify_audit_entry(self.logged_in_user, int(aid), notes_entry.get().strip())
                    messagebox.showinfo("Verified", f"Audit entry #{aid} verified.")
                    modal.destroy()
                    self._show_audit_modal()
                except Exception as ex:
                    messagebox.showerror("Error", str(ex))

            ctk.CTkButton(bar, text="Check & Verify", fg_color="#D97706", width=120, height=28, command=do_verify).pack(side="left")

        # Audit Filters Toolbar
        filter_bar = ctk.CTkFrame(modal, fg_color=("#E2E8F0", "#1E293B"), corner_radius=8)
        filter_bar.pack(fill="x", padx=20, pady=(0, 8))

        search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(filter_bar, textvariable=search_var, placeholder_text="🔍 Search Actor, Operation...", width=200, height=28)
        search_entry.pack(side="left", padx=8, pady=6)

        decision_cb = ctk.CTkOptionMenu(filter_bar, values=["All Decisions", "ALLOWED", "DENIED"], width=130, height=28)
        decision_cb.pack(side="left", padx=(0, 6), pady=6)

        verify_cb = ctk.CTkOptionMenu(filter_bar, values=["All Status", "Pending", "Verified", "Flagged", "Rejected"], width=130, height=28)
        verify_cb.pack(side="left", padx=(0, 6), pady=6)

        sort_cb = ctk.CTkOptionMenu(filter_bar, values=["Newest First", "Oldest First"], width=120, height=28)
        sort_cb.pack(side="left", padx=(0, 8), pady=6)

        scroll = ctk.CTkScrollableFrame(modal, width=900, height=440)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        count_label = ctk.CTkLabel(modal, text="Showing audit entries...", font=ctk.CTkFont(size=12), text_color="#94A3B8")
        count_label.pack(anchor="w", padx=20, pady=(0, 8))

        all_audits = [dict(r) for r in self.engine.con.execute("SELECT * FROM audit ORDER BY id DESC").fetchall()]

        def render_audits():
            for widget in scroll.winfo_children():
                widget.destroy()

            s_text = search_var.get().strip().lower()
            d_filt = decision_cb.get()
            v_filt = verify_cb.get()
            sort_val = sort_cb.get()

            filtered = list(all_audits)

            if s_text:
                filtered = [a for a in filtered if s_text in a['actor'].lower() or s_text in a['op'].lower() or s_text in a['detail'].lower() or s_text in a['target'].lower()]
            if d_filt == "ALLOWED":
                filtered = [a for a in filtered if a['allowed'] == 1]
            elif d_filt == "DENIED":
                filtered = [a for a in filtered if a['allowed'] == 0]

            if v_filt == "Pending":
                filtered = [a for a in filtered if (a.get('verification_status') == 'pending' or not a.get('verification_status')) and not a.get('verified_by')]
            elif v_filt == "Verified":
                filtered = [a for a in filtered if a.get('verification_status') == 'verified' or a.get('verified_by')]
            elif v_filt == "Flagged":
                filtered = [a for a in filtered if a.get('verification_status') == 'flagged']
            elif v_filt == "Rejected":
                filtered = [a for a in filtered if a.get('verification_status') == 'rejected']

            if sort_val == "Oldest First":
                filtered.sort(key=lambda x: x['id'])
            else:
                filtered.sort(key=lambda x: -x['id'])

            count_label.configure(text=f"Showing {len(filtered)} of {len(all_audits)} audit entries")

            for a in filtered:
                card = ctk.CTkFrame(scroll, fg_color=("#E2E8F0", "#1E293B"), corner_radius=8)
                card.pack(fill="x", pady=4, padx=4)

                top = ctk.CTkFrame(card, fg_color="transparent")
                top.pack(fill="x", padx=12, pady=(6, 2))

                status_tag = "ALLOWED" if a['allowed'] else "DENIED"
                tag_color = "#10B981" if a['allowed'] else "#EF4444"
                ctk.CTkLabel(top, text=f" [{status_tag}] ", fg_color=tag_color, font=ctk.CTkFont(size=11, weight="bold"), corner_radius=4, text_color="#FFFFFF").pack(side="left")

                v_status = (a.get('verification_status') or ('verified' if a.get('verified_by') else 'pending')).upper()
                v_color = "#10B981" if v_status == "VERIFIED" else ("#F59E0B" if v_status == "FLAGGED" else ("#EF4444" if v_status == "REJECTED" else "#94A3B8"))
                ctk.CTkLabel(top, text=f" {v_status} ", fg_color=v_color, font=ctk.CTkFont(size=10, weight="bold"), corner_radius=4, text_color="#FFFFFF").pack(side="left", padx=(6, 0))

                ctk.CTkLabel(top, text=f"  Entry #{a['id']} | [{a['ts']}]", font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(side="left")

                if is_auditor:
                    btn_row = ctk.CTkFrame(top, fg_color="transparent")
                    btn_row.pack(side="right")
                    ctk.CTkButton(btn_row, text="✓ Verify", width=65, height=22, fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(size=10, weight="bold"), command=lambda aid=a['id']: self._auditor_action(aid, 'verified')).pack(side="left", padx=2)
                    ctk.CTkButton(btn_row, text="🚩 Flag", width=55, height=22, fg_color="#F59E0B", hover_color="#D97706", font=ctk.CTkFont(size=10, weight="bold"), command=lambda aid=a['id']: self._auditor_action(aid, 'flagged')).pack(side="left", padx=2)
                    ctk.CTkButton(btn_row, text="✕ Reject", width=60, height=22, fg_color="#EF4444", hover_color="#DC2626", font=ctk.CTkFont(size=10, weight="bold"), command=lambda aid=a['id']: self._auditor_action(aid, 'rejected')).pack(side="left", padx=2)
                else:
                    if a['verified_by']:
                        ctk.CTkLabel(top, text=f"✓ Checked by {a['verified_by']} ({a['verification_notes']})", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38BDF8").pack(side="right")
                    else:
                        ctk.CTkLabel(top, text="Pending Auditor Check", font=ctk.CTkFont(size=11), text_color="#F59E0B").pack(side="right")

                bot = ctk.CTkFrame(card, fg_color="transparent")
                bot.pack(fill="x", padx=12, pady=(2, 6))
                ctk.CTkLabel(bot, text=f"Actor: {a['actor']} | Op: {a['op']} | Target: {a['target']} | Detail: {a['detail']}", font=ctk.CTkFont(size=12), text_color="#E2E8F0").pack(anchor="w")

        search_var.trace_add("write", lambda *args: render_audits())
        decision_cb.configure(command=lambda v: render_audits())
        verify_cb.configure(command=lambda v: render_audits())
        sort_cb.configure(command=lambda v: render_audits())

        render_audits()


if __name__ == "__main__":
    app = NagarkotApp()
    app.mainloop()