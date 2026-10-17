# 5-minute HR / interviewer walkthrough

## 0:00–0:40 — Explain the problem

“Each shipment is a job. Different employees can prepare, check, and file it. We cannot grant access only by job title because the same person may work as a Maker for every client but as a Checker for just two clients. So we assign roles through scoped grants.”

## 0:40–1:30 — Explain the decision engine

“When someone attempts an action, `Service.decide()` checks the action, user status, absence, job stage, permission and scope. It also checks special rules like maker-checker and job ownership. The result is not just true or false: it includes the checks and a human-readable explanation. If the engine cannot prove access is allowed, it denies the action.”

## 1:30–2:20 — Show the queue

“Jobs waiting for me is not just a list of jobs owned by the person. It finds jobs where the user is allowed to perform the next step. It considers scope, stage, absence, assignment and maker-checker, so the queue follows the same rules as an action decision.”

## 2:20–3:20 — Show why Alice can and Bob cannot

In the app's comparison tab:

1. Select `u_maker_all` and `u_checker_narrow`.
2. Choose action `check`.
3. Enter a job ID for a `Prepared` ACME job. A seeded job can be found with this SQL if needed: `SELECT id, client_id, branch_id, direction, mode, stage, prepared_by FROM jobs WHERE client_id='C-ACME' AND stage='Prepared' LIMIT 10;`
4. Click Compare.

Explain: “Alice is Maker across all scopes and Checker only for ACME and Globex. Bob is Checker for ACME only. Both may have Checker permission for this ACME job, but the engine separately checks whether the person who prepared it is trying to check their own work. Scope and separation of duties are different checks.”

If the chosen job was prepared by Alice, her maker-checker check should fail. Use the actual job's `prepared_by` value when explaining the result; don't rely on names alone.

## 3:20–4:20 — Show audit

Select an internal admin user in the top bar, open Job history and audit, enter a job ID and date window, then build the report. Explain the difference between “had potential authority” and “actually performed a recorded action.” Permission history can identify possible actors; job events identify recorded changes.

## 4:20–5:00 — Close with the trade-off

“The service evaluates grants live, so revocation takes effect on the next request. It favors safety over convenience: unknown actions and uncertain decisions are denied. SQLite is sufficient for this local demonstration, and the scale script generates 500 users and 200,000 jobs to test queue performance. A production system would add authentication, an API, migrations, monitoring, backups, and tamper-resistant audit storage.”
