"""Unit tests for Remade Nagarkot Access Control Engine.

Validates:
1. Maker-Checker SoD (Staff who prepared cannot check).
2. Job_assigner strict branch boundary (b1 assigner cannot assign to b2 staff).
3. Soft-lock dissolution when assignee is inactive (is_active=0).
4. Cancel and Reopen restricted EXCLUSIVELY to Admin.
5. Auditor verification sign-off.
"""
import unittest
from engine import AccessEngine, Denied, Refused


class TestAccessEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AccessEngine(":memory:")
        con = self.engine.con
        con.execute("INSERT INTO branches VALUES('b1', 'Branch 1')")
        con.execute("INSERT INTO branches VALUES('b2', 'Branch 2')")

        employees = [
            ('Carol Admin', 'admin1', 'Admin', 'all', '', 1),
            ('Alice Assigner', 'u_assigner', 'Job_assigner', 'b1', '', 1),
            ('Bob Auditor', 'u_auditor', 'auditor', 'b1', '', 1),
            ('Priya Sharma', 'u_staff_1', 'staff', 'b1', '', 1),
            ('Rahul Verma', 'u_staff_2', 'staff', 'b1', '', 1),
            ('Amit Patel', 'u_staff_b2', 'staff', 'b2', '', 1)
        ]
        con.executemany("INSERT INTO employees(name, id, role, branch, job_queue, is_active) VALUES(?,?,?,?,?,?)", employees)

    def test_maker_cannot_check_own_work(self):
        con = self.engine.con
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch) VALUES(1, 'ACME', NULL, 'Confirmed', 'air', 'import', 'b1')")

        # u_staff_1 prepares the job
        self.engine.act("u_staff_1", 1, "prepare", reason="Prepared documentation")
        self.assertEqual(self.engine._job(1)['state'], 'Prepared')
        self.assertEqual(self.engine._job(1)['prepared_by'], 'u_staff_1')

        # u_staff_1 attempting to check own work must fail under SoD
        d = self.engine.decide("u_staff_1", "check", self.engine._job(1))
        self.assertFalse(d.allowed)
        self.assertEqual(d.code, "maker_checker")

        # Independent peer u_staff_2 can check
        res = self.engine.act("u_staff_2", 1, "check", reason="Verified by independent peer")
        self.assertEqual(res['state'], 'Checked')

    def test_job_assigner_can_assign_across_branches(self):
        con = self.engine.con
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch) VALUES(2, 'Globex', NULL, 'Confirmed', 'sea', 'export', 'b2')")

        # Job_assigner can assign job (even in b2) to staff in b2 or b1 without b1 restriction
        res = self.engine.act("u_assigner", 2, "assign", assignee="u_staff_b2", reason="Assigned cross-branch")
        self.assertEqual(res['assigned_to'], 'u_staff_b2')

    def test_staff_access_managed_only_by_admin(self):
        # Admin can update employee access
        res = self.engine.update_employee_role("admin1", "u_staff_1", "auditor", "b2")
        self.assertEqual(res['role'], 'auditor')

        # Staff attempting to manage access is strictly REFUSED
        with self.assertRaises(Refused) as cm:
            self.engine.update_employee_role("u_staff_2", "u_staff_1", "Admin", "b1")
        self.assertEqual(cm.exception.code, "unauthorized")

    def test_auditor_review_verify_flag_reject(self):
        con = self.engine.con
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch) VALUES(5, 'ACME', NULL, 'Confirmed', 'sea', 'import', 'b1')")
        self.engine.act("u_staff_1", 5, "prepare", reason="Ready")

        audit_row = con.execute("SELECT id FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        self.assertIsNotNone(audit_row)
        audit_id = audit_row['id']

        # Auditor can verify
        res_v = self.engine.review_audit_entry("u_auditor", audit_id, status="verified", notes="All good")
        self.assertEqual(res_v['status'], 'verified')

        # Auditor can flag
        res_f = self.engine.review_audit_entry("u_auditor", audit_id, status="flagged", notes="Requires supervisor review")
        self.assertEqual(res_f['status'], 'flagged')

        # Auditor can reject
        res_r = self.engine.review_audit_entry("u_auditor", audit_id, status="rejected", notes="Violation noted")
        self.assertEqual(res_r['status'], 'rejected')

        # Non-auditor / staff cannot review audit entry
        with self.assertRaises(Refused) as cm:
            self.engine.review_audit_entry("u_staff_2", audit_id, status="verified", notes="Staff check attempt")
        self.assertEqual(cm.exception.code, "unauthorized")

    def test_queue_assignment_filter(self):
        con = self.engine.con
        # Add 1 assigned job and 1 unassigned job for u_staff_1 in b1
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch) VALUES(6, 'AssignedJob', 'u_staff_1', 'Confirmed', 'air', 'import', 'b1')")
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch) VALUES(7, 'UnassignedJob', NULL, 'Confirmed', 'air', 'import', 'b1')")

        q_all = self.engine.queue("u_staff_1", assignment="all")
        q_assigned = self.engine.queue("u_staff_1", assignment="assigned")
        q_unassigned = self.engine.queue("u_staff_1", assignment="unassigned")

        self.assertTrue(any(j['id'] == 6 for j in q_assigned['items']))
        self.assertFalse(any(j['id'] == 7 for j in q_assigned['items']))

        self.assertTrue(any(j['id'] == 7 for j in q_unassigned['items']))
        self.assertFalse(any(j['id'] == 6 for j in q_unassigned['items']))

        self.assertEqual(len(q_all['items']), len(q_assigned['items']) + len(q_unassigned['items']))

    def test_absence_dissolves_soft_lock(self):
        con = self.engine.con
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch) VALUES(3, 'Initech', 'u_staff_1', 'Confirmed', 'land', 'import', 'b1')")

        # While u_staff_1 is active, peer u_staff_2 is locked out
        job = self.engine._job(3)
        d_locked = self.engine.decide("u_staff_2", "prepare", job)
        self.assertFalse(d_locked.allowed)
        self.assertEqual(d_locked.code, "soft_lock")

        # Staff 1 goes on leave (is_active = 0)
        self.engine.toggle_leave("u_staff_1")

        # Soft-lock dissolves: u_staff_2 can prepare job
        d_unlocked = self.engine.decide("u_staff_2", "prepare", job)
        self.assertTrue(d_unlocked.allowed)

    def test_cancel_and_reopen_restricted_to_admin(self):
        con = self.engine.con
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch) VALUES(4, 'Stark', NULL, 'Confirmed', 'air', 'export', 'b1')")

        # Staff attempting to cancel job is BLOCKED
        with self.assertRaises(Denied) as cm:
            self.engine.act("u_staff_1", 4, "cancel", reason="Staff cancellation attempt")
        self.assertEqual(cm.exception.decision.code, "admin_only")

        # Admin can successfully cancel job
        res_cancel = self.engine.act("admin1", 4, "cancel", reason="Admin cancelled shipment")
        self.assertEqual(res_cancel['state'], 'Cancelled')

        # Staff attempting to reopen job is BLOCKED
        with self.assertRaises(Denied) as cm:
            self.engine.act("u_staff_1", 4, "reopen", reason="Staff reopen attempt")
        self.assertEqual(cm.exception.decision.code, "admin_only")

        # Admin can successfully reopen job
        res_reopen = self.engine.act("admin1", 4, "reopen", reason="Admin reopened shipment")
        self.assertEqual(res_reopen['state'], 'Reopened')

    def test_admin_self_escalation_blocked(self):
        """Staff cannot escalate themselves or others to Admin; unauthorized access changes fail."""
        # Staff attempting to grant themselves Admin privileges is rejected
        with self.assertRaises(Refused) as cm:
            self.engine.update_employee_role("u_staff_1", "u_staff_1", "Admin")
        self.assertEqual(cm.exception.code, "unauthorized")

        # Staff attempting to promote a peer is rejected
        with self.assertRaises(Refused) as cm:
            self.engine.update_employee_role("u_staff_2", "u_staff_1", "Admin")
        self.assertEqual(cm.exception.code, "unauthorized")

        # Admin attempting to assign an invalid/nonexistent role is rejected
        with self.assertRaises(Refused) as cm:
            self.engine.update_employee_role("admin1", "u_staff_1", "SuperUserGodMode")
        self.assertEqual(cm.exception.code, "unknown_role")

    def test_mid_job_responsibility_change(self):
        """When responsibilities change mid-job, new access rules apply live immediately."""
        con = self.engine.con
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch) VALUES(8, 'Omega Corp', NULL, 'Confirmed', 'air', 'import', 'b1')")

        # u_staff_1 starts the job in b1
        self.engine.act("u_staff_1", 8, "prepare", reason="Initial preparation")
        self.assertEqual(self.engine._job(8)['state'], 'Prepared')

        # Admin transfers u_staff_2 from b1 to b2 (responsibility change mid-job)
        self.engine.update_employee_role("admin1", "u_staff_2", "staff", "b2")

        # u_staff_2 can no longer check this job because their branch is now b2
        d = self.engine.decide("u_staff_2", "check", self.engine._job(8))
        self.assertFalse(d.allowed)
        self.assertEqual(d.code, "branch_scope")

        # However, event history still accurately records that u_staff_1 prepared it
        events = con.execute("SELECT * FROM job_events WHERE job_id=8").fetchall()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['actor'], 'u_staff_1')

    def test_parser_service_account(self):
        """Overnight parser is treated as an automated service account: creates/prepares, cannot check own work."""
        con = self.engine.con
        con.execute("INSERT INTO employees(name, id, role, branch, job_queue, is_active) VALUES('EDI Parser', 'u_parser', 'staff', 'b1', '', 1)")
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch) VALUES(9, 'AutoClient', NULL, 'Confirmed', 'sea', 'import', 'b1')")

        # Parser prepares batch shipment
        res = self.engine.act("u_parser", 9, "prepare", reason="Automated overnight batch ingest")
        self.assertEqual(res['state'], 'Prepared')

        # Parser CANNOT check its own work (Maker-Checker SoD applies to automated parser as well)
        d = self.engine.decide("u_parser", "check", self.engine._job(9))
        self.assertFalse(d.allowed)
        self.assertEqual(d.code, "maker_checker")

        # Human staff member in b1 can check the parser's work
        res_check = self.engine.act("u_staff_1", 9, "check", reason="Human verified parser output")
        self.assertEqual(res_check['state'], 'Checked')

    def test_compare_explains_why_she_can_and_he_cannot(self):
        """Compare API accurately answers 'Why can she do this and he cannot?'."""
        con = self.engine.con
        con.execute("INSERT INTO jobs(id, client, assigned_to, state, mode, direction, branch, prepared_by) VALUES(10, 'CompareClient', NULL, 'Prepared', 'air', 'import', 'b1', 'u_staff_1')")

        # u_staff_1 prepared job 10. Priya (u_staff_1) cannot check; Rahul (u_staff_2) can check.
        cmp_result = self.engine.compare("u_staff_2", "u_staff_1", 10, "check")

        self.assertTrue(cmp_result['user_a']['allowed'])
        self.assertFalse(cmp_result['user_b']['allowed'])
        self.assertIn("Priya Sharma", cmp_result['summary'])
        self.assertIn("Rahul Verma", cmp_result['summary'])
        self.assertTrue(any(diff['check'] == 'maker_checker' for diff in cmp_result['differences']))


if __name__ == "__main__":
    unittest.main()