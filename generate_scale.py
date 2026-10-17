import os
import random
import time
from engine import AccessEngine, BRANCHES, MODES, DIRECTIONS, STANDARD_STAGES, SCHEMA

DEFAULT_SCALE_DB = os.path.join("data", "nfpl_scale.db")
CLIENTS = [f"Client_{i:02d}" for i in range(1, 11)]

def generate_scale(db_path=DEFAULT_SCALE_DB):
    print(f"Generating scale dataset at '{db_path}' (500 users, 200,000 jobs)...")
    t0 = time.time()
    engine = AccessEngine(db_path)
    con = engine.con

    with engine.tx():
        for tbl in ('audit', 'job_events', 'jobs', 'employees', 'branches'):
            con.execute(f"DROP TABLE IF EXISTS {tbl}")
    con.executescript(SCHEMA)

    with engine.tx():
        # 1. Insert Branches
        branches_data = [(b, f"Branch {b.upper()}") for b in BRANCHES]
        con.executemany("INSERT INTO branches VALUES(?,?)", branches_data)

        # 2. Insert 500 Employees
        employees = []
        # Carol Admin
        employees.append(("Carol Admin", "admin1", "Admin", "all", "", 1))
        # 5 assigners (one per branch)
        for i, b in enumerate(BRANCHES, start=1):
            employees.append((f"Assigner {b.upper()}", f"assigner_{b}", "Job_assigner", b, "", 1))
        # 5 auditors
        for i, b in enumerate(BRANCHES, start=1):
            employees.append((f"Auditor {b.upper()}", f"auditor_{b}", "auditor", b, "", 1))
        # Remaining staff up to 500
        for i in range(12, 501):
            b = BRANCHES[i % len(BRANCHES)]
            is_active = 0 if i % 50 == 0 else 1
            employees.append((f"Staff User {i:03d}", f"usr_{i:03d}", "staff", b, "", is_active))

        con.executemany(
            "INSERT INTO employees(name, id, role, branch, job_queue, is_active) VALUES(?,?,?,?,?,?)",
            employees
        )

        # 3. Insert 200,000 Jobs in batches
        now = engine.now()
        batch = []
        batch_size = 10000

        for i in range(1, 200001):
            client = CLIENTS[i % len(CLIENTS)]
            branch = BRANCHES[i % len(BRANCHES)]
            mode = MODES[i % len(MODES)]
            direction = DIRECTIONS[i % len(DIRECTIONS)]
            state = STANDARD_STAGES[i % len(STANDARD_STAGES)]
            
            # Some jobs assigned to staff in the same branch
            staff_id = f"usr_{(i % 480) + 12:03d}" if i % 3 == 0 else None
            prep_by = staff_id if state in ('Prepared', 'Checked', 'Filed') else None

            batch.append((i, client, staff_id, state, mode, direction, branch, prep_by, now, now))

            if len(batch) >= batch_size:
                con.executemany(
                    "INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch, prepared_by, created_at, updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    batch
                )
                batch = []

        if batch:
            con.executemany(
                "INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch, prepared_by, created_at, updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                batch
            )

    print(f"Dataset generated in {time.time()-t0:.2f}s.")

    # Performance Benchmark: query queue for a staff member
    t_query = time.time()
    res = engine.queue("usr_015")
    duration_ms = (time.time() - t_query) * 1000
    print(f"Queue count for 'usr_015' returned {res['total']} actionable jobs in {duration_ms:.2f} ms.")

if __name__ == "__main__":
    generate_scale()