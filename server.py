"""Nagarkot Access Control System - Web Server.

Provides REST API with filtering, sorting, and search for:
- Jobs Dataset: filter by branch, state, mode, direction, client search; sort by id, client, state, mode.
- Employee Database: filter by branch, role, is_active, search by name/id; sort by name, id, role.
- Job Queue: filter by state, mode, search, sort.
- Audit Log: filter by allowed (ALLOWED/DENIED), verification status, actor search, sort by timestamp.
"""
import os
from flask import Flask, request, jsonify, send_from_directory
from engine import AccessEngine, Denied, Refused, NotFound

app = Flask(__name__, static_folder="static", static_url_path="")
DB_PATH = "nfpl_demo.db"

# Auto-seed database if missing (for zero-config cloud deployments)
if not os.path.exists(DB_PATH):
    from seed_demo import seed_demo
    seed_demo(DB_PATH)

engine = AccessEngine(DB_PATH)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/users", methods=["GET"])
def get_users():
    """Return all employees for login selection."""
    employees = [dict(r) for r in engine.con.execute("SELECT name, id, role, branch, job_queue, is_active FROM employees ORDER BY branch, id").fetchall()]
    return jsonify(employees)


@app.route("/api/login", methods=["POST"])
def login():
    """Authenticate employee ID and return employee record."""
    data = request.json or {}
    uid = data.get("user_id", "").strip()

    try:
        emp = engine._employee(uid)
    except NotFound:
        return jsonify({"error": f"Employee ID '{uid}' not found."}), 404

    return jsonify({
        "id": emp['id'],
        "name": emp['name'],
        "role": emp['role'],
        "branch": emp['branch'],
        "job_queue": emp['job_queue'],
        "is_active": bool(emp['is_active'])
    })


@app.route("/api/queue", methods=["GET"])
def get_queue():
    """Return actionable queue or jobs dataset for employee with optional filtering."""
    uid = request.args.get("user_id", "")
    role = request.args.get("role", "")
    branch = request.args.get("branch", "")
    state_filter = request.args.get("state", "All")
    mode_filter = request.args.get("mode", "All")
    assignment = request.args.get("assignment", "all")
    search = request.args.get("search", "").lower()
    sort_by = request.args.get("sort", "id_desc")

    # For Admin, Job_assigner, and auditor: return jobs dataset
    if role in ("Job_assigner", "Admin", "auditor"):
        query = "SELECT * FROM jobs WHERE 1=1"
        params = []
        if branch and branch != "all":
            query += " AND branch=?"
            params.append(branch)
        if state_filter and state_filter != "All":
            query += " AND state=?"
            params.append(state_filter)
        if mode_filter and mode_filter != "All":
            query += " AND mode=?"
            params.append(mode_filter)
        if assignment == "assigned":
            query += " AND assigned_to IS NOT NULL AND assigned_to != ''"
        elif assignment == "unassigned":
            query += " AND (assigned_to IS NULL OR assigned_to = '')"
        if search:
            query += " AND (LOWER(client) LIKE ? OR CAST(id AS TEXT) LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        # Sorting
        if sort_by == "id_asc":
            query += " ORDER BY id ASC"
        elif sort_by == "client_asc":
            query += " ORDER BY client ASC"
        elif sort_by == "state":
            query += " ORDER BY state ASC, id DESC"
        else:
            query += " ORDER BY id DESC"

        rows = [dict(r) for r in engine.con.execute(query, params).fetchall()]
        return jsonify({
            "mode": "jobs_dataset",
            "items": rows,
            "total": len(rows)
        })

    # For staff: return derived actionable queue with assignment filter
    q = engine.queue(uid, assignment=assignment)
    items = q['items']

    if state_filter and state_filter != "All":
        items = [j for j in items if j['state'] == state_filter]
    if mode_filter and mode_filter != "All":
        items = [j for j in items if j['mode'] == mode_filter]
    if search:
        items = [j for j in items if search in j['client'].lower() or search in str(j['id'])]

    if sort_by == "id_asc":
        items.sort(key=lambda x: x['id'])
    elif sort_by == "client_asc":
        items.sort(key=lambda x: x['client'].lower())
    elif sort_by == "state":
        items.sort(key=lambda x: (x['state'], -x['id']))
    else:
        items.sort(key=lambda x: -x['id'])

    return jsonify({
        "mode": "staff_queue",
        "items": items,
        "total": len(items),
        "counts": q['counts']
    })


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """Return jobs dataset with filters and sorting."""
    branch = request.args.get("branch", "all")
    state_filter = request.args.get("state", "All")
    mode_filter = request.args.get("mode", "All")
    dir_filter = request.args.get("direction", "All")
    assignment = request.args.get("assignment", "all")
    search = request.args.get("search", "").lower()
    sort_by = request.args.get("sort", "id_desc")

    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if branch and branch != "all":
        query += " AND branch=?"
        params.append(branch)
    if state_filter and state_filter != "All":
        query += " AND state=?"
        params.append(state_filter)
    if mode_filter and mode_filter != "All":
        query += " AND mode=?"
        params.append(mode_filter)
    if dir_filter and dir_filter != "All":
        query += " AND direction=?"
        params.append(dir_filter)
    if assignment == "assigned":
        query += " AND assigned_to IS NOT NULL AND assigned_to != ''"
    elif assignment == "unassigned":
        query += " AND (assigned_to IS NULL OR assigned_to = '')"
    if search:
        query += " AND (LOWER(client) LIKE ? OR CAST(id AS TEXT) LIKE ? OR LOWER(COALESCE(assigned_to, '')) LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if sort_by == "id_asc":
        query += " ORDER BY id ASC"
    elif sort_by == "client_asc":
        query += " ORDER BY client ASC"
    elif sort_by == "state":
        query += " ORDER BY state ASC, id DESC"
    elif sort_by == "branch":
        query += " ORDER BY branch ASC, id DESC"
    else:
        query += " ORDER BY id DESC"

    rows = [dict(r) for r in engine.con.execute(query, params).fetchall()]
    return jsonify(rows)


@app.route("/api/employees", methods=["GET"])
def get_employees():
    """Return Employee table with filters and sorting."""
    branch = request.args.get("branch", "All")
    role = request.args.get("role", "All")
    status = request.args.get("status", "All")
    search = request.args.get("search", "").lower()
    sort_by = request.args.get("sort", "name_asc")

    query = "SELECT name, id, role, branch, job_queue, is_active FROM employees WHERE 1=1"
    params = []

    if branch and branch != "All":
        query += " AND branch=?"
        params.append(branch)
    if role and role != "All":
        query += " AND role=?"
        params.append(role)
    if status and status != "All":
        is_active_val = 1 if status == "Active" else 0
        query += " AND is_active=?"
        params.append(is_active_val)
    if search:
        query += " AND (LOWER(name) LIKE ? OR LOWER(id) LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if sort_by == "name_desc":
        query += " ORDER BY name DESC"
    elif sort_by == "id_asc":
        query += " ORDER BY id ASC"
    elif sort_by == "role":
        query += " ORDER BY role ASC, name ASC"
    elif sort_by == "branch":
        query += " ORDER BY branch ASC, name ASC"
    else:
        query += " ORDER BY name ASC"

    rows = [dict(r) for r in engine.con.execute(query, params).fetchall()]
    return jsonify(rows)


@app.route("/api/branch-staff", methods=["GET"])
def get_branch_staff():
    """Return staff belonging to the specified branch or all staff if branch is all."""
    branch = request.args.get("branch", "all")
    if branch == "all":
        staff = [dict(r) for r in engine.con.execute("SELECT id, name, branch FROM employees WHERE role='staff'").fetchall()]
    else:
        staff = [dict(r) for r in engine.con.execute("SELECT id, name, branch FROM employees WHERE role='staff' AND branch=?", (branch,)).fetchall()]
    return jsonify(staff)


@app.route("/api/act", methods=["POST"])
def execute_action():
    """Execute lifecycle action: prepare, check, file, cancel, reopen."""
    data = request.json or {}
    actor = data.get("actor")
    job_id = int(data.get("job_id"))
    action = data.get("action")
    reason = data.get("reason", f"Executed {action} via interface")

    try:
        res = engine.act(actor, job_id, action, reason=reason)
        return jsonify({"success": True, "state": res.get("state")})
    except Denied as d:
        return jsonify({
            "success": False,
            "error": "DENIED",
            "summary": d.decision.summary(),
            "explanation": d.decision.explain(),
            "code": d.decision.code
        }), 403
    except Refused as r:
        return jsonify({"success": False, "error": "REFUSED", "detail": r.detail, "code": r.code}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/compare", methods=["GET", "POST"])
def compare_access():
    """Compare why Person A can perform an action and Person B cannot."""
    if request.method == "POST":
        data = request.json or {}
        user_a = data.get("user_a")
        user_b = data.get("user_b")
        job_id = int(data.get("job_id", 1))
        action = data.get("action", "check")
    else:
        user_a = request.args.get("user_a")
        user_b = request.args.get("user_b")
        job_id = int(request.args.get("job_id", 1))
        action = request.args.get("action", "check")

    if not user_a or not user_b:
        return jsonify({"error": "Both 'user_a' and 'user_b' parameters are required."}), 400

    try:
        res = engine.compare(user_a, user_b, job_id, action)
        return jsonify(res)
    except NotFound as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/assign", methods=["POST"])
def assign_job():
    """Assign job strictly to branch staff."""
    data = request.json or {}
    actor = data.get("actor")
    job_id = int(data.get("job_id"))
    assignee = data.get("assignee")
    reason = data.get("reason", "Assigned via interface")

    try:
        res = engine.act(actor, job_id, "assign", assignee=assignee, reason=reason)
        return jsonify({"success": True, "assigned_to": res.get("assigned_to")})
    except Refused as r:
        return jsonify({"success": False, "error": "REFUSED", "detail": r.detail, "code": r.code}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/toggle-leave", methods=["POST"])
def toggle_leave():
    """Toggle is_active attribute for an employee (absent leave)."""
    data = request.json or {}
    uid = data.get("user_id")

    try:
        res = engine.toggle_leave(uid)
        return jsonify({
            "is_active": bool(res['is_active']),
            "message": res['message']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/audit", methods=["GET"])
def get_audit_log():
    """Return audit changes log with filtering."""
    decision = request.args.get("decision", "All")
    verification = request.args.get("verification", "All")
    search = request.args.get("search", "").lower()
    sort_by = request.args.get("sort", "newest")

    query = "SELECT * FROM audit WHERE 1=1"
    params = []

    if decision == "ALLOWED":
        query += " AND allowed=1"
    elif decision == "DENIED":
        query += " AND allowed=0"

    if verification == "Verified":
        query += " AND verification_status = 'verified'"
    elif verification == "Flagged":
        query += " AND verification_status = 'flagged'"
    elif verification == "Rejected":
        query += " AND verification_status = 'rejected'"
    elif verification == "Pending":
        query += " AND (verification_status = 'pending' OR verification_status IS NULL OR verified_by IS NULL)"

    if search:
        query += " AND (LOWER(actor) LIKE ? OR LOWER(op) LIKE ? OR LOWER(target) LIKE ? OR LOWER(detail) LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

    if sort_by == "oldest":
        query += " ORDER BY id ASC"
    else:
        query += " ORDER BY id DESC"

    rows = [dict(r) for r in engine.con.execute(query, params).fetchall()]
    return jsonify(rows)


@app.route("/api/audit/verify", methods=["POST"])
@app.route("/api/audit/review", methods=["POST"])
def verify_audit():
    """Verify, flag, or reject an audit entry (auditor/Admin)."""
    data = request.json or {}
    checker_id = data.get("checker_id") or data.get("actor")
    audit_id = int(data.get("audit_id"))
    status = data.get("status", "verified")
    notes = data.get("notes", f"Reviewed as {status}")

    try:
        res = engine.review_audit_entry(checker_id, audit_id, status=status, notes=notes)
        return jsonify({"success": True, "result": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/update-role", methods=["POST"])
def update_role():
    """Update employee role and branch (Strictly Admin only)."""
    data = request.json or {}
    actor = data.get("actor")
    emp_id = data.get("emp_id")
    role = data.get("role")
    branch = data.get("branch")

    try:
        res = engine.update_employee_role(actor, emp_id, role, branch)
        return jsonify({"success": True, "result": res})
    except Refused as r:
        return jsonify({"success": False, "error": r.detail, "code": r.code}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n=======================================================")
    print(f" Nagarkot Access Control Web App running on port {port}")
    print(f" http://localhost:{port}")
    print("=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
