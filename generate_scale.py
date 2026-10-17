"""Generates scale benchmark dataset (500 users, 200,000 jobs)."""
import random
import time
from engine import AccessEngine

def generate_scale(db_path="nfpl_scale.db"):
    print(f"Generating scale dataset at '{db_path}' (500 users, 200,000 jobs)...")
    t0 = time.time()
    engine = AccessEngine(db_path)
    con = engine.con

    with engine.tx():
        for tbl in ('jobs', 'grants', 'users'):
            con.execute(f"DELETE FROM {tbl}")

        users = [(f'usr_{i:03d}', f'User {i}', 'staff', None, None) for i in range(1, 501)]
        con.executemany("INSERT INTO users VALUES(?,?,?,?,?)", users)

        grants = [(f'usr_{i:03d}', 'Maker', '2026-01-01T00:00:00Z') for i in range(1, 501)]
        con.executemany("INSERT INTO grants(user_id, role, created_at) VALUES(?,?,?)", grants)

        jobs = []
        stages = ['Confirmed', 'Prepared', 'Checked', 'Filed']
        now = engine.now()
        for i in range(1, 200001):
            jobs.append((f"SCALE-{i:06d}", f"C-{(i%10)+1:03d}", f"B-{(i%5)+1:02d}", "import", "air", random.choice(stages), now, now))
            if len(jobs) >= 20000:
                con.executemany("INSERT INTO jobs(ref, client_id, branch_id, direction, mode, stage, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)", jobs)
                jobs = []
        if jobs:
            con.executemany("INSERT INTO jobs(ref, client_id, branch_id, direction, mode, stage, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)", jobs)

    print(f"Dataset generated in {time.time()-t0:.2f}s.")
    
    t_query = time.time()
    res = engine.queue("usr_001")
    print(f"Queue count returned {res['total']} jobs in {(time.time()-t_query)*1000:.2f} ms.")

if __name__ == "__main__":
    generate_scale()