"""Nagarkot Access Control Engine - Remade Architecture.

Schema & Workflow Specification:
1. Roles: Admin, Job_assigner, auditor, staff.
2. Branches: b1, b2, b3, b4, b5.
3. Jobs states: Confirmed -> Prepared -> Checked -> Filed.
   Cancelled and Reopened can ONLY be performed by Admin.
4. Employee table: name, id, Role, Branch, Job_queue, is_active.
5. Jobs table: id, client, assigned_to, state, mode (air, land, sea), direction (import/export), branch.
"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

TS_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
BRANCHES = ('b1', 'b2', 'b3', 'b4', 'b5')
MODES = ('air', 'land', 'sea')
DIRECTIONS = ('import', 'export')
ROLES = ('Admin', 'Job_assigner', 'auditor', 'staff')
STANDARD_STAGES = ('Confirmed', 'Prepared', 'Checked', 'Filed')
ALL_STAGES = ('Confirmed', 'Prepared', 'Checked', 'Filed', 'Cancelled', 'Reopened')

SCHEMA = """
CREATE TABLE IF NOT EXISTS branches (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employees (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('Admin', 'Job_assigner', 'auditor', 'staff')),
    branch TEXT,
    job_queue TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client TEXT NOT NULL,
    assigned_to TEXT,
    state TEXT NOT NULL CHECK(state IN ('Confirmed', 'Prepared', 'Checked', 'Filed', 'Cancelled', 'Reopened')),
    mode TEXT NOT NULL CHECK(mode IN ('air', 'land', 'sea')),
    direction TEXT NOT NULL CHECK(direction IN ('import', 'export')),
    branch TEXT NOT NULL,
    prepared_by TEXT,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY(assigned_to) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    assigned_after TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    op TEXT NOT NULL,
    target TEXT NOT NULL,
    allowed INTEGER NOT NULL,
    detail TEXT NOT NULL,
    verified_by TEXT,
    verified_at TEXT,
    verification_notes TEXT,
    verification_status TEXT DEFAULT 'pending'
);
"""


def utcnow():
    return datetime.now(timezone.utc).strftime(TS_FORMAT)


class Denied(Exception):
    def __init__(self, decision):
        super().__init__(decision.summary())
        self.decision = decision


class Refused(Exception):
    def __init__(self, code, detail):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


class NotFound(Exception):
    pass


class Decision:
    def __init__(self, user, action, job_id):
        self.user, self.action, self.job_id = user, action, job_id
        self.checks = []

    def add(self, check, ok, detail):
        self.checks.append(dict(check=check, ok=bool(ok), detail=detail))
        return ok

    @property
    def allowed(self):
        return bool(self.checks) and all(c['ok'] for c in self.checks)

    @property
    def code(self):
        for c in self.checks:
            if not c['ok']:
                return c['check']
        return 'allowed'

    def summary(self):
        for c in self.checks:
            if not c['ok']:
                return f"denied ({c['check']}): {c['detail']}"
        return 'allowed'

    def explain(self):
        head = f"{'ALLOWED' if self.allowed else 'DENIED'}: {self.user} -> {self.action}" + \
               (f" on job #{self.job_id}" if self.job_id else "")
        return '\n'.join([head] + [f"  [{'ok' if c['ok'] else 'FAIL'}] {c['check']}: {c['detail']}" for c in self.checks])


class AccessEngine:
    def __init__(self, path=':memory:', clock=None):
        self.con = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.con.row_factory = sqlite3.Row
        self.con.execute('PRAGMA journal_mode=WAL')
        self.con.executescript(SCHEMA)
        try:
            self.con.execute("ALTER TABLE audit ADD COLUMN verification_status TEXT DEFAULT 'pending'")
        except sqlite3.OperationalError:
            pass
        self.clock = clock or utcnow
        self.lock = threading.RLock()

    def now(self):
        return self.clock()

    @contextmanager
    def tx(self):
        with self.lock:
            self.con.execute('BEGIN IMMEDIATE')
            try:
                yield
                self.con.execute('COMMIT')
            except BaseException:
                self.con.execute('ROLLBACK')
                raise

    def _employee(self, emp_id):
        r = self.con.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
        if not r:
            raise NotFound(f"employee '{emp_id}'")
        return dict(r)

    def _job(self, job_id):
        r = self.con.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not r:
            raise NotFound(f"job #{job_id}")
        return dict(r)

    def _sync_employee_queue(self, emp_id):
        """Update job_queue attribute of an employee with list of assigned jobs."""
        if not emp_id:
            return
        jobs = [str(r['id']) for r in self.con.execute("SELECT id FROM jobs WHERE assigned_to=? AND state NOT IN ('Filed', 'Cancelled')", (emp_id,)).fetchall()]
        q_str = ', '.join(jobs)
        self.con.execute("UPDATE employees SET job_queue=? WHERE id=?", (q_str, emp_id))

    def decide(self, actor_id, action, job, reason=None):
        d = Decision(actor_id, action, job.get('id') if job else None)
        try:
            actor = self._employee(actor_id)
        except NotFound:
            d.add('user_known', False, f"User '{actor_id}' does not exist")
            return d

        d.add('user_known', True, f"User '{actor_id}' exists")

        # 1. Presence check (except read-only audit/view)
        if action not in ('view', 'audit'):
            is_active = bool(actor['is_active'])
            d.add('user_active', is_active, 'Account is active on duty' if is_active else 'Account is on leave (inactive)')
            if not is_active:
                return d

        role = actor['role']
        job_state = job.get('state') if job else None
        job_branch = job.get('branch') if job else None

        # 2. Branch scope check (Admin has global scope 'all'; Job_assigner can assign across branches)
        if role != 'Admin' and action != 'audit' and not (role == 'Job_assigner' and action == 'assign'):
            matches_branch = (actor['branch'] == 'all' or actor['branch'] == job_branch)
            d.add('branch_scope', matches_branch, f"Branch match ({actor['branch']} == {job_branch})" if matches_branch else f"User branch {actor['branch']} cannot access job branch {job_branch}")
            if not matches_branch:
                return d

        # 3. Role & State Transition Rules
        if action == 'prepare':
            # staff or Admin can prepare from Confirmed or Reopened
            can_role = role in ('staff', 'Admin')
            d.add('role_permitted', can_role, f"Role '{role}' can prepare shipments" if can_role else f"Role '{role}' cannot prepare")
            can_state = job_state in ('Confirmed', 'Reopened')
            d.add('state_valid', can_state, f"Job in valid stage '{job_state}' for prepare" if can_state else f"Cannot prepare job in state '{job_state}'")

            # Soft lock check: if assigned to another staff who is active, locked!
            assigned = job.get('assigned_to')
            if assigned and assigned != actor_id:
                assignee = self._employee(assigned)
                if assignee['is_active']:
                    d.add('soft_lock', False, f"Soft-locked by active assignee {assigned}")
                    return d
                else:
                    d.add('soft_lock', True, f"Soft-lock dissolved (assignee {assigned} is on leave)")
            else:
                d.add('soft_lock', True, "Job is unassigned or assigned to you")

        elif action == 'check':
            # staff or Admin can check Prepared jobs
            can_role = role in ('staff', 'Admin')
            d.add('role_permitted', can_role, f"Role '{role}' can check shipments")
            can_state = job_state == 'Prepared'
            d.add('state_valid', can_state, f"Job in 'Prepared' stage" if can_state else f"Cannot check job in state '{job_state}'")

            # Maker-Checker SoD: Person who prepared cannot check!
            prepared_by = job.get('prepared_by')
            sod_ok = (prepared_by != actor_id)
            d.add('maker_checker', sod_ok, "Independent checker verification" if sod_ok else "Maker cannot check own work (Separation of Duties)")

        elif action == 'file':
            # staff or Admin can file Checked jobs
            can_role = role in ('staff', 'Admin')
            d.add('role_permitted', can_role, f"Role '{role}' can file shipments")
            can_state = job_state == 'Checked'
            d.add('state_valid', can_state, f"Job in 'Checked' stage" if can_state else f"Cannot file job in state '{job_state}'")

        elif action in ('cancel', 'reopen'):
            # ONLY ADMIN CAN CANCEL OR REOPEN!
            is_admin = (role == 'Admin')
            d.add('admin_only', is_admin, "Action restricted exclusively to Admin role" if not is_admin else "Admin authorized for sensitive lifecycle control")
            if action == 'cancel':
                valid = job_state in ('Confirmed', 'Prepared', 'Checked', 'Reopened')
                d.add('state_valid', valid, f"State '{job_state}' can be cancelled" if valid else f"Cannot cancel job in state '{job_state}'")
            elif action == 'reopen':
                valid = job_state in ('Filed', 'Cancelled')
                d.add('state_valid', valid, f"State '{job_state}' can be reopened" if valid else f"Cannot reopen job in state '{job_state}'")

        elif action == 'assign':
            # Job_assigner or Admin
            can_assign = role in ('Job_assigner', 'Admin')
            d.add('role_permitted', can_assign, f"Role '{role}' can assign jobs")
            valid = job_state in ('Confirmed', 'Prepared', 'Checked', 'Reopened')
            d.add('state_valid', valid, f"Job in state '{job_state}' is assignable")

        elif action == 'audit':
            # auditor, Admin, or staff (read-only)
            can_audit = role in ('auditor', 'Admin', 'staff')
            d.add('role_permitted', can_audit, f"Role '{role}' has audit access")

        return d

    def act(self, actor_id, job_id, action, reason=None, **kw):
        with self.tx():
            job = self._job(job_id)
            actor = self._employee(actor_id)
            d = self.decide(actor_id, action, job, reason)

            if not d.allowed:
                self.con.execute(
                    "INSERT INTO audit(ts, actor, op, target, allowed, detail) VALUES(?,?,?,?,0,?)",
                    (self.now(), actor_id, action, f"job:{job_id}", d.summary())
                )
                raise Denied(d)

            old_state = job['state']

            # Lifecycle Progression
            if action == 'prepare':
                self.con.execute(
                    "UPDATE jobs SET state='Prepared', prepared_by=?, updated_at=? WHERE id=?",
                    (actor_id, self.now(), job_id)
                )
                new_state = 'Prepared'
            elif action == 'check':
                self.con.execute(
                    "UPDATE jobs SET state='Checked', updated_at=? WHERE id=?",
                    (self.now(), job_id)
                )
                new_state = 'Checked'
            elif action == 'file':
                self.con.execute(
                    "UPDATE jobs SET state='Filed', assigned_to=NULL, updated_at=? WHERE id=?",
                    (self.now(), job_id)
                )
                new_state = 'Filed'
            elif action == 'cancel':
                self.con.execute(
                    "UPDATE jobs SET state='Cancelled', assigned_to=NULL, updated_at=? WHERE id=?",
                    (self.now(), job_id)
                )
                new_state = 'Cancelled'
            elif action == 'reopen':
                self.con.execute(
                    "UPDATE jobs SET state='Reopened', updated_at=? WHERE id=?",
                    (self.now(), job_id)
                )
                new_state = 'Reopened'
            elif action == 'assign':
                target_assignee = kw.get('assignee')
                target_emp = self._employee(target_assignee)

                old_assignee = job['assigned_to']
                self.con.execute(
                    "UPDATE jobs SET assigned_to=?, updated_at=? WHERE id=?",
                    (target_assignee, self.now(), job_id)
                )
                self._sync_employee_queue(target_assignee)
                if old_assignee:
                    self._sync_employee_queue(old_assignee)

                self.con.execute(
                    "INSERT INTO job_events(job_id, ts, actor, action, from_state, to_state, assigned_after, reason) VALUES(?,?,?,?,?,?,?,?)",
                    (job_id, self.now(), actor_id, 'assign', old_state, old_state, target_assignee, reason or "Assigned to staff")
                )
                self.con.execute(
                    "INSERT INTO audit(ts, actor, op, target, allowed, detail) VALUES(?,?,?,?,1,?)",
                    (self.now(), actor_id, 'assign', f"job:{job_id}", f"Assigned to {target_assignee} (branch {target_emp['branch']})")
                )
                return dict(job_id=job_id, assigned_to=target_assignee, state=old_state)

            # Record event & audit
            assigned_now = job['assigned_to'] if new_state not in ('Filed', 'Cancelled') else None
            self.con.execute(
                "INSERT INTO job_events(job_id, ts, actor, action, from_state, to_state, assigned_after, reason) VALUES(?,?,?,?,?,?,?,?)",
                (job_id, self.now(), actor_id, action, old_state, new_state, assigned_now, reason or f"Executed {action}")
            )
            self.con.execute(
                "INSERT INTO audit(ts, actor, op, target, allowed, detail) VALUES(?,?,?,?,1,?)",
                (self.now(), actor_id, action, f"job:{job_id}", f"Transition: {old_state} -> {new_state}")
            )
            if job['assigned_to']:
                self._sync_employee_queue(job['assigned_to'])

            return dict(job_id=job_id, state=new_state)

    def queue(self, actor_id, assignment='all'):
        """Derive actionable queue items for staff member with assignment filter ('all', 'assigned', 'unassigned')."""
        with self.lock:
            actor = self._employee(actor_id)
            if not actor['is_active']:
                return dict(items=[], total=0, counts=dict(prepare=0, check=0, file=0))

            branch = actor['branch']
            # Eligible jobs in actor's branch
            if branch == 'all':
                jobs = [dict(r) for r in self.con.execute("SELECT * FROM jobs WHERE state IN ('Confirmed', 'Prepared', 'Checked', 'Reopened') ORDER BY id DESC").fetchall()]
            else:
                jobs = [dict(r) for r in self.con.execute("SELECT * FROM jobs WHERE branch=? AND state IN ('Confirmed', 'Prepared', 'Checked', 'Reopened') ORDER BY id DESC", (branch,)).fetchall()]

            valid_items = []
            counts = dict(prepare=0, check=0, file=0)

            for j in jobs:
                st = j['state']
                act = 'prepare' if st in ('Confirmed', 'Reopened') else ('check' if st == 'Prepared' else 'file')
                d = self.decide(actor_id, act, j)
                if d.allowed:
                    item = dict(j)
                    item['action'] = act
                    if j['assigned_to'] == actor_id:
                        item['why_in_queue'] = 'Assigned directly to you'
                    elif j['assigned_to']:
                        item['why_in_queue'] = f"Covering for {j['assigned_to']} (On Leave - Soft-Lock Dissolved)"
                    else:
                        item['why_in_queue'] = 'Unassigned in branch queue'

                    valid_items.append(item)
                    counts[act] = counts.get(act, 0) + 1

            if assignment == 'assigned':
                valid_items = [j for j in valid_items if j.get('assigned_to')]
            elif assignment == 'unassigned':
                valid_items = [j for j in valid_items if not j.get('assigned_to')]

            return dict(items=valid_items, total=len(valid_items), counts=counts)

    def toggle_leave(self, emp_id):
        """Toggle is_active attribute for an employee (1 <-> 0)."""
        with self.tx():
            emp = self._employee(emp_id)
            new_active = 0 if emp['is_active'] == 1 else 1
            self.con.execute("UPDATE employees SET is_active=? WHERE id=?", (new_active, emp_id))
            note = "Returned to active duty" if new_active == 1 else "Went on absent leave (soft locks dissolved)"
            self.con.execute(
                "INSERT INTO audit(ts, actor, op, target, allowed, detail) VALUES(?,?,?,?,1,?)",
                (self.now(), emp_id, 'toggle_leave', f"employee:{emp_id}", note)
            )
            return dict(id=emp_id, is_active=new_active, message=note)

    def review_audit_entry(self, checker_id, audit_id, status='verified', notes=""):
        """Review an audit entry: 'verified', 'flagged', or 'rejected'."""
        with self.tx():
            emp = self._employee(checker_id)
            if emp['role'] not in ('auditor', 'Admin'):
                raise Refused('unauthorized', f"Role '{emp['role']}' cannot review audit log")
            if status not in ('verified', 'flagged', 'rejected'):
                raise Refused('invalid_status', f"Invalid review status '{status}'")

            row = self.con.execute("SELECT * FROM audit WHERE id=?", (audit_id,)).fetchone()
            if not row:
                raise NotFound(f"Audit entry #{audit_id}")

            self.con.execute(
                "UPDATE audit SET verified_by=?, verified_at=?, verification_notes=?, verification_status=? WHERE id=?",
                (checker_id, self.now(), notes, status, audit_id)
            )
            return dict(audit_id=audit_id, verified_by=checker_id, status=status, notes=notes)

    def verify_audit_entry(self, checker_id, audit_id, notes="Verified by auditor"):
        return self.review_audit_entry(checker_id, audit_id, status='verified', notes=notes)

    def update_employee_role(self, actor_id, emp_id, new_role, new_branch=None):
        with self.tx():
            actor = self._employee(actor_id)
            if actor['role'] != 'Admin':
                raise Refused('unauthorized', f"Only Admin can manage staff access (Role '{actor['role']}' denied)")
            if new_role not in ROLES:
                raise Refused('unknown_role', f"Role '{new_role}' does not exist")

            if new_branch:
                self.con.execute("UPDATE employees SET role=?, branch=? WHERE id=?", (new_role, new_branch, emp_id))
            else:
                self.con.execute("UPDATE employees SET role=? WHERE id=?", (new_role, emp_id))

            self.con.execute(
                "INSERT INTO audit(ts, actor, op, target, allowed, detail) VALUES(?,?,?,?,1,?)",
                (self.now(), actor_id, 'manage_access', f"employee:{emp_id}", f"Updated role to {new_role}")
            )
            return dict(employee_id=emp_id, role=new_role, branch=new_branch)