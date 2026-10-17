"""Seed script generating demo database with remade architecture.

Schema:
1. Roles: Admin, Job_assigner, auditor, staff
2. Branches: b1, b2, b3, b4, b5
3. Employee table: name, id, Role, Branch, Job_queue, is_active
4. Jobs table: id, client, assigned_to, state, mode (air, land, sea), direction (import/export), branch
"""
from engine import AccessEngine

BRANCHES = [
    ('b1', 'Branch 1 - Mumbai'),
    ('b2', 'Branch 2 - Delhi'),
    ('b3', 'Branch 3 - Bengaluru'),
    ('b4', 'Branch 4 - Chennai'),
    ('b5', 'Branch 5 - Kolkata')
]

CLIENTS = ['ACME Corp', 'Globex International', 'Initech Logistics', 'Umbrella Corp', 'Stark Freight']


def seed_demo(db_path="nfpl_demo.db"):
    engine = AccessEngine(db_path)
    con = engine.con

    from engine import SCHEMA
    with engine.tx():
        for tbl in ('audit', 'job_events', 'jobs', 'employees', 'branches'):
            con.execute(f"DROP TABLE IF EXISTS {tbl}")
    con.executescript(SCHEMA)

    with engine.tx():
        # 1. Insert Branches: b1, b2, b3, b4, b5
        con.executemany("INSERT INTO branches VALUES(?,?)", BRANCHES)

        # 2. Insert Employees: name, id, Role, Branch, Job_queue, is_active
        employees = [
            ('Carol Admin', 'admin1', 'Admin', 'all', '', 1),
            ('Alice Assigner', 'u_job_assigner', 'Job_assigner', 'b1', '', 1),
            ('Bob Auditor', 'u_auditor', 'auditor', 'b1', '', 1),
            ('Priya Sharma', 'u_staff_1', 'staff', 'b1', '', 1),
            ('Rahul Verma', 'u_staff_2', 'staff', 'b1', '', 1),
            ('Amit Patel', 'u_staff_3', 'staff', 'b2', '', 1),
            ('Sneha Rao', 'u_staff_4', 'staff', 'b2', '', 1),
            ('Vikram Nair', 'u_staff_5', 'staff', 'b3', '', 1),
            ('Ananya Das', 'u_staff_6', 'staff', 'b4', '', 1),
            ('Karan Singh', 'u_staff_7', 'staff', 'b5', '', 1),
            ('Frank Absent', 'u_absent', 'staff', 'b1', '', 0) # Absent (on leave, is_active=0)
        ]
        con.executemany("INSERT INTO employees(name, id, role, branch, job_queue, is_active) VALUES(?,?,?,?,?,?)", employees)

        # 3. Seed Specific Test Scenario Jobs
        # Job #1: Prepared by u_staff_1 in b1. Demonstrates Maker-Checker: u_staff_1 CANNOT check it, u_staff_2 CAN check it.
        con.execute(
            "INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch, prepared_by, created_at, updated_at) "
            "VALUES(1, 'ACME Corp', NULL, 'Prepared', 'air', 'import', 'b1', 'u_staff_1', ?, ?)",
            (engine.now(), engine.now())
        )
        con.execute(
            "INSERT INTO job_events(job_id, ts, actor, action, from_state, to_state, assigned_after, reason) "
            "VALUES(1, ?, 'u_staff_1', 'prepare', 'Confirmed', 'Prepared', NULL, 'Prepared by Priya')",
            (engine.now(),)
        )

        # Job #2: Assigned to u_absent (Frank, is_active=0) in b1. Demonstrates soft-lock dissolution: peers in b1 see it unlocked.
        con.execute(
            "INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch, prepared_by, created_at, updated_at) "
            "VALUES(2, 'Globex International', 'u_absent', 'Confirmed', 'sea', 'export', 'b1', NULL, ?, ?)",
            (engine.now(), engine.now())
        )

        # Job #3: Confirmed unassigned job in b1 for Job_assigner to assign.
        con.execute(
            "INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch, prepared_by, created_at, updated_at) "
            "VALUES(3, 'Initech Logistics', NULL, 'Confirmed', 'land', 'import', 'b1', NULL, ?, ?)",
            (engine.now(), engine.now())
        )

        # Job #4: Filed job to test Reopen (Admin only).
        con.execute(
            "INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch, prepared_by, created_at, updated_at) "
            "VALUES(4, 'Stark Freight', NULL, 'Filed', 'air', 'export', 'b2', 'u_staff_3', ?, ?)",
            (engine.now(), engine.now())
        )

        # 4. Generate ~100 additional jobs distributed across b1-b5, modes (air, land, sea), directions (import, export)
        modes = ('air', 'land', 'sea')
        directions = ('import', 'export')
        branches = ('b1', 'b2', 'b3', 'b4', 'b5')

        for i in range(5, 105):
            client = CLIENTS[i % len(CLIENTS)]
            mode = modes[i % len(modes)]
            direction = directions[i % len(directions)]
            branch = branches[i % len(branches)]
            state = 'Confirmed' if i % 3 != 0 else ('Prepared' if i % 5 != 0 else 'Checked')
            prep = 'u_staff_1' if state in ('Prepared', 'Checked') and branch == 'b1' else None
            assigned = 'u_staff_2' if i % 7 == 0 and branch == 'b1' else ('u_staff_3' if i % 7 == 1 and branch == 'b2' else None)

            con.execute(
                "INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch, prepared_by, created_at, updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (i, client, assigned, state, mode, direction, branch, prep, engine.now(), engine.now())
            )

        # 5. Initial Audit Entries demonstrating verification, flagging, rejection, and pending states
        con.execute(
            "INSERT INTO audit(ts, actor, op, target, allowed, detail, verified_by, verified_at, verification_notes, verification_status) "
            "VALUES(?, 'admin1', 'system_init', 'employees,jobs', 1, 'Database initialized with roles Admin, Job_assigner, auditor, staff and branches b1-b5', 'u_auditor', ?, 'Initial audit baseline confirmed', 'verified')",
            (engine.now(), engine.now())
        )
        con.execute(
            "INSERT INTO audit(ts, actor, op, target, allowed, detail, verified_by, verified_at, verification_notes, verification_status) "
            "VALUES(?, 'u_job_assigner', 'assign', 'job:2', 1, 'Assigned to u_absent in branch b1', NULL, NULL, NULL, 'pending')",
            (engine.now(),)
        )
        con.execute(
            "INSERT INTO audit(ts, actor, op, target, allowed, detail, verified_by, verified_at, verification_notes, verification_status) "
            "VALUES(?, 'u_staff_1', 'cancel', 'job:4', 0, 'denied (admin_only): Action restricted exclusively to Admin role', NULL, NULL, NULL, 'pending')",
            (engine.now(),)
        )
        con.execute(
            "INSERT INTO audit(ts, actor, op, target, allowed, detail, verified_by, verified_at, verification_notes, verification_status) "
            "VALUES(?, 'admin1', 'reopen', 'job:104', 1, 'Admin reopened closed shipment for client inquiry', 'u_auditor', ?, 'High-risk override flagged for board review', 'flagged')",
            (engine.now(), engine.now())
        )

    # Sync initial employee queues
    with engine.tx():
        for emp in ('admin1', 'u_job_assigner', 'u_auditor', 'u_staff_1', 'u_staff_2', 'u_staff_3', 'u_staff_4', 'u_absent'):
            engine._sync_employee_queue(emp)

    print(f"Successfully seeded '{db_path}' with remade schema:")
    print(" - Branches: b1, b2, b3, b4, b5")
    print(" - Roles: Admin, Job_assigner, auditor, staff")
    print(" - Modes: air, land, sea")
    print(" - 11 Employees and 104 Jobs initialized.")


if __name__ == "__main__":
    seed_demo()
