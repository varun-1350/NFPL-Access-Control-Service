# NFPL Access Control Service: Design Notes

## 1. Overview

The service answers a practical question: may this person perform this action on this shipment right now? It combines role-based access control (RBAC) with attribute-based access control (ABAC). RBAC says which actions a role contains. ABAC limits that role to a job's client, branch, import/export direction, and transport mode.

The project keeps the existing structure. `core.py` owns policy and persistence, `app.py` is a Tkinter demonstration, `seed_demo.py` loads a deliberate sample, and `generate_scaled_data.py` builds a larger benchmark dataset. SQLite is enough for a local assessment and supports indexes for common queue and history lookups.

## 2. Data model and decision path

- **Users** have a kind (`staff`, `client`, or `system`), an optional client binding, and optional deactivation time.
- **Roles** are versioned bundles of permissions. Versioning preserves the role definition that was in effect at an earlier time.
- **Grants** assign a role to a user with optional client, branch, direction, mode, and validity dates. Null scope means “any”. Revocation is recorded rather than deleting the grant.
- **Jobs** contain immutable business dimensions, current stage, owner, and the identity that prepared the current cycle.
- **Job events** record actions and stage changes. **Audit rows** record successful and denied administrative/security operations. **Requests** represent sensitive changes requiring another person to decide.
- **Absences** temporarily prevent action and release an otherwise eligible owner's soft lock.

For a decision, the service checks that the action and user are known, the account is active, the user is not absent for a work action, the job is at an allowed stage, a live grant supplies the required permission for the job's scope, and extra controls such as maker-checker, owner assignment, a reason, or a second approver pass. Unknown or failed checks deny the action. Explanations include the failed check and its reason.

## 3. Key trade-offs

**Read access differs from action access.** A person needs `job.view` to see a job. A client user receives only an external view role bound to their own client; internal fields and staff history are withheld. Staff action permissions are checked separately.

**Scope is explicit and composable.** One person can hold Maker for all jobs and Checker for only two clients by holding two grants. Another can hold Checker only for one client, one branch, and imports. This is easier to reason about than hard-coded user exceptions.

**Live checks over permission caching.** The service builds the current context from SQLite for each decision. Revocation therefore affects the next decision, at the cost of extra database reads. The 200,000-job benchmark checks whether the indexed queue path is adequate for the assessment. A larger deployment could cache carefully, but would need reliable invalidation.

**Separation of duties.** The person recorded as preparing the current cycle cannot check it. A qualified checker who prepared the job is denied even if they hold the Checker role. Re-preparation starts a new cycle and updates `prepared_by`.

**Absence and ownership.** A normal owner soft-locks the next action to themselves when eligible. If the owner is absent, inactive, or no longer eligible, another qualified user may cover the job. Reassignment is checked against the next required action.

**Sensitive state changes use two people.** Cancelling a filed shipment or reopening a filed/cancelled shipment is requested with a written reason. A different authorized approver decides. A break-glass override can send a job backward for rework, but cannot advance it directly to Checked or Filed.

**History is append-oriented.** Job events and grants are retained instead of overwritten/deleted. This supports investigation and point-in-time reconstruction. The reconstruction is an assessment-level approximation of historical authority, not a tamper-proof compliance archive; production would need immutable storage and stronger event integrity guarantees.

## 4. Answers to the assessment questions

1. **Should everyone see everything?** No. `job.view` is required. Staff may see internal fields only with an internal view grant. External client users see summaries for their own client. Viewing a job does not grant permission to modify it.
2. **Maker everywhere, Checker for a few clients?** Give the person a global Maker grant and separate client-scoped Checker grants. For a Checker restricted to one client, branch, and imports, set all three fields on that grant; other dimensions remain unrestricted only if null.
3. **Maker also qualifies as Checker?** The maker-checker rule overrides the qualification for that job cycle. Another person must check it.
4. **Responsible person absent?** Their work action is blocked while absent. The owner soft-lock is released to another eligible user, and assignment can be updated.
5. **Responsibilities change mid-job?** New decisions use current grants, so newly revoked authority stops working immediately. The job remains in its stage; a new eligible colleague can take it over. The audit trail keeps the old assignments and events.
6. **Cancel filed/reopen closed?** A user with the appropriate request permission submits a reason. A different person with sensitive-approval permission approves or rejects it. The request becomes stale if the job has moved to an incompatible stage.
7. **Client employee follows shipments?** A client-kind user gets an external, read-only role scoped to their own client. They cannot use staff workflow actions or read internal history.
8. **Admin fixes a stuck job? Self-escalation?** Break-glass authority can move a job backward for rework with a reason. It cannot bypass the real check/file stages. Granting oneself access is rejected; privileged grants require a second approver. Admin activity is audited.
9. **Overnight parser?** It is a distinct `system` user with a narrow ParserRole for create and permitted early-stage edits. It is not a human admin and cannot approve or complete workflow stages.
10. **Why can she but not he?** `why()` evaluates both users against the same job and action, then compares the checks and gives explanations, including scope, stage, absence, and maker-checker differences.
11. **Who could have changed a job on a date?** `who_could_have()` reconstructs the job state and access context at relevant points in the date window, then lists potential actions and recorded actual events. Potential authority is not proof that a person made the change.
12. **New role next quarter?** Add a versioned role definition using the existing permission vocabulary, then grant it to users. The role's permissions must be known to the engine; introducing an entirely new action still requires code changes and tests. Role changes are audited.
13. **Queue count matches action rights?** Queue generation uses the same permission, scope, stage, absence, owner, and maker-checker rules as the decision engine. It filters candidates in SQL before checking owner exceptions, rather than showing every job a role name might suggest.
14. **System unsure?** Fail closed: deny and explain that a check could not be established. Security should not depend on optimistic guesses.

## 5. Further production questions

- Who authenticates users and protects the API? This assessment GUI uses a selected demo identity, not real authentication.
- Should the event log be cryptographically chained or exported to write-once storage?
- What are the required retention periods for shipment data, denied attempts, and access grants?
- What is the operational SLA for queue refresh and grant revocation?
- Should client users see exact shipment fields or a separately defined client-safe projection?

These are deliberate boundaries of the local assessment rather than claims that SQLite and a desktop GUI alone are production-ready.
