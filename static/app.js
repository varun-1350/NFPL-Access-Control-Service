/**
 * NAGARKOT ACCESS CONTROL - FRONTEND CONTROLLER
 * Full Reactive Filters, Sorting & Search for:
 * - Shipment Queue & Tasks
 * - Employee Database Table (name, id, Role, Branch, Job queue, is_active)
 * - Jobs Dataset Table (ID, Client, assigned_to, state, Mode, direction, branch)
 * - Audit Changes Log (ALLOWED/DENIED, verification status, actor search)
 */

let currentUser = null;
let cachedUsers = [];
let allJobsCache = [];
let allEmployeesCache = [];
let allAuditCache = [];
let queueItemsCache = [];

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    fetchUsersList();
});

// Toast notification helper
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    const icon = type === "success" ? "✓" : (type === "error" ? "⚠️" : "ℹ️");
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Fetch all employees for login selector
async function fetchUsersList() {
    try {
        const res = await fetch("/api/users");
        cachedUsers = await res.json();
        const select = document.getElementById("login-user-select");
        select.innerHTML = "";

        cachedUsers.forEach(u => {
            const opt = document.createElement("option");
            opt.value = u.id;
            const branchText = u.role === "Admin" ? "all (Global)" : u.branch;
            const statusText = u.is_active ? "Active" : "On Leave";
            opt.textContent = `${u.id} - ${u.name} [Role: ${u.role} | Branch: ${branchText} | Status: ${statusText}]`;
            select.appendChild(opt);
        });
    } catch (err) {
        showToast("Failed to fetch employees from server.", "error");
    }
}

// Quick select user chip handler
function quickSelectUser(uid) {
    const select = document.getElementById("login-user-select");
    select.value = uid;
    handleLogin();
}

// Authenticate and transition to Dashboard
async function handleLogin() {
    const uid = document.getElementById("login-user-select").value;
    if (!uid) {
        showToast("Please select a User ID.", "error");
        return;
    }

    try {
        const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: uid })
        });

        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || "Authentication failed.", "error");
            return;
        }

        currentUser = data;
        showToast(`Authenticated as ${currentUser.name} (${currentUser.role})`, "success");

        // Switch to Dashboard
        document.getElementById("login-page").classList.remove("active-page");
        document.getElementById("dashboard-page").classList.add("active-page");

        updateBanner();
        renderRoleControls(currentUser.role);
        loadQueue();
    } catch (err) {
        showToast("Connection error: " + err, "error");
    }
}

// Logout handler
function handleLogout() {
    currentUser = null;
    document.getElementById("dashboard-page").classList.remove("active-page");
    document.getElementById("login-page").classList.add("active-page");
    fetchUsersList();
    showToast("Logged out successfully.", "info");
}

// Update Top App Banner
function updateBanner() {
    if (!currentUser) return;
    document.getElementById("banner-user-name").textContent = `${currentUser.name} (${currentUser.id})`;

    const roleBadge = document.getElementById("banner-user-role");
    roleBadge.textContent = currentUser.role;

    const roleColors = {
        "Admin": "rgba(239, 68, 68, 0.2)",
        "Job_assigner": "rgba(16, 185, 129, 0.2)",
        "auditor": "rgba(245, 158, 11, 0.2)",
        "staff": "rgba(56, 189, 248, 0.2)"
    };
    roleBadge.style.background = roleColors[currentUser.role] || "rgba(56, 189, 248, 0.2)";

    document.getElementById("banner-user-branch").textContent = currentUser.branch === "all" ? "all (Global)" : currentUser.branch;

    const statusBadge = document.getElementById("banner-user-status");
    const statusText = document.getElementById("banner-status-text");

    if (currentUser.is_active) {
        statusBadge.className = "status-indicator";
        statusText.textContent = "Active On Duty";
    } else {
        statusBadge.className = "status-indicator status-absent";
        statusText.textContent = "On Leave (Soft-Locks Dissolved)";
    }
}

// Render Action Panel controls tailored strictly to the 4 roles
function renderRoleControls(role) {
    const container = document.getElementById("role-controls-container");
    container.innerHTML = "";

    document.getElementById("action-panel-role-scope").textContent = `Privilege Scope: ${role}`;

    // -------------------------------------------------------------
    // ROLE 1: Admin
    // Cases: Can access Jobs, Employee Database, Audit Log (+ cancel/reopen, manage access)
    // -------------------------------------------------------------
    if (role === "Admin") {
        container.innerHTML = `
            <div class="section-label text-rose">Admin Controls</div>
            <button class="btn btn-primary btn-block" onclick="openJobsModal()">
                <span>📦 Access Jobs Dataset</span>
            </button>
            <button class="btn btn-primary btn-block" onclick="openEmployeesModal()">
                <span>👥 Employee Database</span>
            </button>
            <button class="btn btn-danger btn-block" onclick="openAdminLifecycleModal()">
                <span>⚙️ Cancel / Reopen Jobs (Admin Only)</span>
            </button>
            <button class="btn btn-success btn-block" onclick="openAuditModal()">
                <span>🛡️ View System Audit Log</span>
            </button>
            <button class="btn btn-primary btn-block" onclick="openAccessModal()">
                <span>🔑 Manage Staff Access</span>
            </button>
        `;
    }
    // -------------------------------------------------------------
    // ROLE 2: staff
    // Cases: Can access & change jobs queue assigned to them (by branch),
    //        apply for absent leave, audit log (read-only)
    // -------------------------------------------------------------
    else if (role === "staff") {
        const leaveBtnText = currentUser.is_active ? "🏖️ Apply for Absent Leave" : "🟢 Return to Duty (End Leave)";
        const leaveBtnClass = currentUser.is_active ? "btn-warning" : "btn-success";

        container.innerHTML = `
            <div class="section-label text-sky">Staff Controls (Branch ${currentUser.branch})</div>
            <button class="btn btn-success btn-block" onclick="advanceNextJob()">
                <span>⏩ Advance Next Assigned Job</span>
            </button>
            <button class="btn ${leaveBtnClass} btn-block" onclick="toggleLeave()">
                <span>${leaveBtnText}</span>
            </button>
            <button class="btn btn-secondary btn-block" onclick="openAuditModal()">
                <span>📜 Audit Log (Read-Only)</span>
            </button>
        `;
    }
    // -------------------------------------------------------------
    // ROLE 3: Job_assigner
    // Cases: Can assign jobs to staff, access jobs dataset (cross-branch permitted)
    // -------------------------------------------------------------
    else if (role === "Job_assigner") {
        container.innerHTML = `
            <div class="section-label text-emerald">Branch Task Assigner (${currentUser.branch})</div>
            <button class="btn btn-primary btn-block" onclick="openJobsModal()">
                <span>📦 Access Jobs Dataset</span>
            </button>
            <button class="btn btn-success btn-block" onclick="openAssignModal()">
                <span>🎯 Assign Job (Cross-Branch Permitted)</span>
            </button>
        `;
    }
    // -------------------------------------------------------------
    // ROLE 4: auditor
    // Cases: Access audit stream as primary UI, verify/flag/reject audits; jobs dataset read-only
    // -------------------------------------------------------------
    else if (role === "auditor") {
        container.innerHTML = `
            <div class="section-label text-amber">Forensic Auditor Controls</div>
            <button class="btn btn-primary btn-block" onclick="openJobsModal(true)">
                <span>📦 View Jobs Dataset (Read-Only)</span>
            </button>
            <button class="btn btn-warning btn-block" onclick="loadQueue()">
                <span>🔄 Refresh Audit Stream</span>
            </button>
            <button class="btn btn-secondary btn-block" onclick="openAuditModal()">
                <span>🔍 Advanced Audit Query Tool</span>
            </button>
        `;
    }
}

// Load Task Queue & Shipment Box (or Auditor Compliance Stream)
async function loadQueue() {
    if (!currentUser) return;
    const container = document.getElementById("tasks-container");
    container.innerHTML = '<div class="loading-spinner">Loading workitems...</div>';

    // AUDITOR MODE: Audit stream is the primary UI!
    if (currentUser.role === "auditor") {
        document.getElementById("standard-filter-toolbar").style.display = "none";
        document.getElementById("auditor-stream-toolbar").style.display = "flex";
        document.getElementById("queue-main-title").textContent = "📜 System Audit Log & Compliance Stream";
        document.getElementById("queue-subtitle").textContent = "Real-time forensic verification, anomaly flagging, and violation tracking";

        try {
            const res = await fetch("/api/audit");
            allAuditCache = await res.json();

            const tot = allAuditCache.length;
            const pending = allAuditCache.filter(a => (!a.verification_status || a.verification_status === "pending") && !a.verified_by).length;
            const verified = allAuditCache.filter(a => a.verification_status === "verified" || a.verified_by).length;
            const flagged = allAuditCache.filter(a => a.verification_status === "flagged" || a.verification_status === "rejected").length;

            document.getElementById("metric-total").textContent = tot;
            document.getElementById("metric-prepare").textContent = pending;
            document.getElementById("metric-check").textContent = verified;
            document.getElementById("metric-file").textContent = flagged;

            // Change metric labels for auditor
            document.querySelectorAll(".metric-name")[0].textContent = "Total Audits";
            document.querySelectorAll(".metric-name")[1].textContent = "Pending Review";
            document.querySelectorAll(".metric-name")[2].textContent = "Verified";
            document.querySelectorAll(".metric-name")[3].textContent = "Flagged / Rejected";

            filterAuditorStream();
        } catch (err) {
            container.innerHTML = `<div style="color: var(--rose); padding: 1rem;">Failed to load audit stream: ${err}</div>`;
        }
        return;
    }

    // NON-AUDITOR MODE: Standard task queue
    document.getElementById("standard-filter-toolbar").style.display = "flex";
    document.getElementById("auditor-stream-toolbar").style.display = "none";
    document.getElementById("queue-main-title").textContent = "Shipment Tasks & Branch Queue";

    // Restore metric labels
    document.querySelectorAll(".metric-name")[0].textContent = "Actionable Tasks";
    document.querySelectorAll(".metric-name")[1].textContent = "Prepare Stage";
    document.querySelectorAll(".metric-name")[2].textContent = "Check Stage";
    document.querySelectorAll(".metric-name")[3].textContent = "File Stage";

    try {
        const res = await fetch(`/api/queue?user_id=${currentUser.id}&branch=${currentUser.branch}&role=${currentUser.role}`);
        const data = await res.json();
        queueItemsCache = data.items || [];

        // Update top metrics
        if (data.mode === "staff_queue") {
            document.getElementById("metric-total").textContent = data.total;
            document.getElementById("metric-prepare").textContent = data.counts.prepare;
            document.getElementById("metric-check").textContent = data.counts.check;
            document.getElementById("metric-file").textContent = data.counts.file;
            document.getElementById("queue-subtitle").textContent = `Assigned items waiting in branch queue [${currentUser.branch}]`;
        } else {
            document.getElementById("metric-total").textContent = data.total;
            document.getElementById("metric-prepare").textContent = queueItemsCache.filter(i => i.state === "Confirmed").length;
            document.getElementById("metric-check").textContent = queueItemsCache.filter(i => i.state === "Prepared").length;
            document.getElementById("metric-file").textContent = queueItemsCache.filter(i => i.state === "Checked").length;
            document.getElementById("queue-subtitle").textContent = `Shipment ledger view for role [${currentUser.role}] in branch [${currentUser.branch}]`;
        }

        filterQueue();
    } catch (err) {
        container.innerHTML = `<div style="color: var(--rose); padding: 1rem;">Failed to load queue: ${err}</div>`;
    }
}

// Filter and Sort Queue Items in Real-Time
function filterQueue() {
    const container = document.getElementById("tasks-container");
    const search = (document.getElementById("queue-search-input").value || "").toLowerCase().trim();
    const stateFilter = document.getElementById("queue-state-filter").value;
    const modeFilter = document.getElementById("queue-mode-filter").value;
    const assignFilter = document.getElementById("queue-assignment-filter").value;
    const sortBy = document.getElementById("queue-sort-select").value;

    let filtered = [...queueItemsCache];

    if (search) {
        filtered = filtered.filter(j => (j.client && j.client.toLowerCase().includes(search)) || String(j.id).includes(search));
    }
    if (stateFilter !== "All") {
        filtered = filtered.filter(j => j.state === stateFilter);
    }
    if (modeFilter !== "All") {
        filtered = filtered.filter(j => j.mode === modeFilter);
    }
    if (assignFilter === "assigned") {
        filtered = filtered.filter(j => j.assigned_to && j.assigned_to.trim() !== "");
    } else if (assignFilter === "unassigned") {
        filtered = filtered.filter(j => !j.assigned_to || j.assigned_to.trim() === "");
    }

    // Sort
    if (sortBy === "id_asc") {
        filtered.sort((a, b) => a.id - b.id);
    } else if (sortBy === "client_asc") {
        filtered.sort((a, b) => (a.client || "").localeCompare(b.client || ""));
    } else if (sortBy === "state") {
        filtered.sort((a, b) => (a.state || "").localeCompare(b.state || ""));
    } else {
        filtered.sort((a, b) => b.id - a.id);
    }

    container.innerHTML = "";

    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔍</div>
                <p style="font-weight: 600;">No shipment tasks match the selected filters.</p>
                <button class="btn btn-secondary btn-sm" style="margin-top: 0.75rem;" onclick="resetQueueFilters()">Reset Filters</button>
            </div>
        `;
        return;
    }

    filtered.forEach(j => {
        const card = document.createElement("div");
        card.className = "task-card";

        const stageClass = `badge-stage-${j.state.toLowerCase()}`;
        const whyText = j.why_in_queue || (j.assigned_to ? `Assigned to ${j.assigned_to}` : "Unassigned in branch");
        const routingClass = whyText.includes("directly to you") ? "routing-assigned" : (whyText.includes("Covering") ? "routing-dissolved" : "routing-unassigned");

        let actionBtnHtml = "";
        if (currentUser.role === "staff" && j.action) {
            const actName = j.action.charAt(0).toUpperCase() + j.action.slice(1);
            const btnColor = j.action === "prepare" ? "btn-primary" : (j.action === "check" ? "btn-warning" : "btn-success");
            actionBtnHtml = `<button class="btn ${btnColor} btn-sm" onclick="executeTaskAction('${j.action}', ${j.id})">Execute: ${actName}</button>`;
        } else if (currentUser.role === "Job_assigner" && (j.state === "Confirmed" || j.state === "Prepared" || j.state === "Reopened")) {
            actionBtnHtml = `<button class="btn btn-success btn-sm" onclick="openAssignModal(${j.id})">Assign to Staff</button>`;
        }

        card.innerHTML = `
            <div class="task-top">
                <div class="task-title-group">
                    <span class="badge-stage ${stageClass}">${j.state}</span>
                    <span class="task-id">Job #${j.id}</span>
                    <span style="font-size: 0.85rem; color: var(--text-secondary); font-weight: 600;">[Client: ${j.client}]</span>
                </div>
                <span class="task-owner-badge">Assigned to: ${j.assigned_to || 'Unassigned'}</span>
            </div>
            <div class="task-meta-row">
                <span>Branch: <strong>${j.branch}</strong></span>
                <span>Mode: <strong style="text-transform: uppercase;">${j.mode}</strong></span>
                <span>Direction: <strong style="text-transform: capitalize;">${j.direction}</strong></span>
                <span>Prepared By: <strong>${j.prepared_by || 'None'}</strong></span>
            </div>
            <div class="task-bottom">
                <span class="routing-reason ${routingClass}">📌 ${whyText}</span>
                ${actionBtnHtml}
            </div>
        `;
        container.appendChild(card);
    });
}

function resetQueueFilters() {
    document.getElementById("queue-search-input").value = "";
    document.getElementById("queue-state-filter").value = "All";
    document.getElementById("queue-mode-filter").value = "All";
    document.getElementById("queue-sort-select").value = "id_desc";
    filterQueue();
}

// Execute Stage Action via live ABAC engine
async function executeTaskAction(action, jobId) {
    try {
        const res = await fetch("/api/act", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                actor: currentUser.id,
                job_id: jobId,
                action: action,
                reason: `Web execution of ${action}`
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Job #${jobId} state updated to: ${data.state}`, "success");
            loadQueue();
        } else {
            showDenialModal(data.summary || data.error, data.explanation || data.detail);
        }
    } catch (err) {
        showToast("Error executing action: " + err, "error");
    }
}

// Advance next assigned job in staff queue
async function advanceNextJob() {
    const res = await fetch(`/api/queue?user_id=${currentUser.id}&branch=${currentUser.branch}&role=staff`);
    const data = await res.json();
    if (data.items && data.items.length > 0) {
        const first = data.items[0];
        executeTaskAction(first.action, first.id);
    } else {
        showToast("No pending jobs waiting in your assigned scope.", "info");
    }
}

// Toggle Leave Status (Demonstrates Soft-Lock Dissolution)
async function toggleLeave() {
    try {
        const res = await fetch("/api/toggle-leave", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: currentUser.id })
        });

        const data = await res.json();
        currentUser.is_active = data.is_active;
        updateBanner();
        renderRoleControls(currentUser.role);
        loadQueue();
        showToast(data.message, currentUser.is_active ? "success" : "info");
    } catch (err) {
        showToast("Failed to toggle leave: " + err, "error");
    }
}

// =========================================================================
// MODAL CONTROLLERS & DATA POPULATION WITH FILTERS & SORTING
// =========================================================================

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove("active");
}

function showDenialModal(summary, explanation) {
    document.getElementById("denial-summary").textContent = summary;
    document.getElementById("denial-explanation").textContent = explanation;
    document.getElementById("modal-denial").classList.add("active");
}

// Modal 1: Audit Log Modal (with Filters & Auditor Sign-off bar)
async function openAuditModal() {
    const modal = document.getElementById("modal-audit");
    const auditorBar = document.getElementById("auditor-verify-bar");
    const isAuditorOrAdmin = currentUser.role === "auditor" || currentUser.role === "Admin";

    auditorBar.style.display = isAuditorOrAdmin ? "flex" : "none";
    document.getElementById("audit-modal-subtitle").textContent = isAuditorOrAdmin ?
        "Auditor Sign-off Enabled: Verify and check compliance entries" :
        "Read-Only Audit Ledger Access";

    modal.classList.add("active");
    loadAuditEntries();
}

async function loadAuditEntries() {
    const list = document.getElementById("audit-log-list");
    list.innerHTML = '<div class="loading-spinner">Loading audit records...</div>';

    try {
        const res = await fetch("/api/audit");
        allAuditCache = await res.json();
        filterAuditLogs();
    } catch (err) {
        list.innerHTML = `<div style="color: var(--rose);">Failed to load audit records: ${err}</div>`;
    }
}

function filterAuditLogs() {
    const list = document.getElementById("audit-log-list");
    const search = (document.getElementById("audit-search-input").value || "").toLowerCase().trim();
    const decisionFilter = document.getElementById("audit-decision-filter").value;
    const verifyFilter = document.getElementById("audit-verify-filter").value;
    const sortBy = document.getElementById("audit-sort-select").value;

    let filtered = [...allAuditCache];

    if (search) {
        filtered = filtered.filter(a =>
            (a.actor && a.actor.toLowerCase().includes(search)) ||
            (a.op && a.op.toLowerCase().includes(search)) ||
            (a.target && a.target.toLowerCase().includes(search)) ||
            (a.detail && a.detail.toLowerCase().includes(search))
        );
    }
    if (decisionFilter === "ALLOWED") {
        filtered = filtered.filter(a => a.allowed === 1);
    } else if (decisionFilter === "DENIED") {
        filtered = filtered.filter(a => a.allowed === 0);
    }

    if (verifyFilter === "Verified") {
        filtered = filtered.filter(a => a.verified_by);
    } else if (verifyFilter === "Pending") {
        filtered = filtered.filter(a => !a.verified_by);
    }

    if (sortBy === "oldest") {
        filtered.sort((a, b) => a.id - b.id);
    } else {
        filtered.sort((a, b) => b.id - a.id);
    }

    document.getElementById("audit-count-badge").textContent = `Showing ${filtered.length} of ${allAuditCache.length} audit entries`;
    list.innerHTML = "";

    if (filtered.length === 0) {
        list.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 2rem;">No audit records match the current filters.</div>';
        return;
    }

    filtered.forEach(a => {
        const card = document.createElement("div");
        card.className = "audit-card";
        const tagColor = a.allowed ? "text-emerald" : "text-rose";
        const tagText = a.allowed ? "ALLOWED" : "DENIED";

        const verifiedHtml = a.verified_by ?
            `<span class="audit-verified-badge">✓ Checked by ${a.verified_by} (${a.verification_notes})</span>` :
            `<span class="audit-pending-badge">Pending Auditor Check</span>`;

        card.innerHTML = `
            <div class="audit-card-top">
                <div>
                    <strong class="${tagColor}">[${tagText}]</strong>
                    <span>Entry #${a.id} | ${a.ts}</span>
                </div>
                ${verifiedHtml}
            </div>
            <div class="audit-detail-text">
                <strong>Actor:</strong> ${a.actor} | <strong>Op:</strong> ${a.op} | <strong>Target:</strong> ${a.target} | <strong>Detail:</strong> ${a.detail}
            </div>
        `;
        list.appendChild(card);
    });
}

async function submitAuditVerification() {
    const auditId = document.getElementById("verify-audit-id").value.trim();
    const notes = document.getElementById("verify-audit-notes").value.trim() || "Compliance audit verified";

    if (!auditId) {
        showToast("Please enter an Audit Entry ID to check.", "error");
        return;
    }

    try {
        const res = await fetch("/api/audit/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                checker_id: currentUser.id,
                audit_id: auditId,
                notes: notes
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Audit Entry #${auditId} verified and signed off.`, "success");
            document.getElementById("verify-audit-id").value = "";
            document.getElementById("verify-audit-notes").value = "";
            loadAuditEntries();
        } else {
            showToast("Failed to verify audit entry: " + data.error, "error");
        }
    } catch (err) {
        showToast("Error verifying audit: " + err, "error");
    }
}

// Modal 2: Employee Database Table (name, id, Role, Branch, Job queue, is_active)
async function openEmployeesModal() {
    const modal = document.getElementById("modal-employees");
    modal.classList.add("active");
    loadEmployeesTable();
}

async function loadEmployeesTable() {
    const tbody = document.getElementById("employee-table-body");
    tbody.innerHTML = '<tr><td colspan="6" class="loading-spinner">Loading employees...</td></tr>';

    try {
        const res = await fetch("/api/employees");
        allEmployeesCache = await res.json();
        filterEmployeeTable();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" style="color: var(--rose);">Failed to load employee directory: ${err}</td></tr>`;
    }
}

function filterEmployeeTable() {
    const tbody = document.getElementById("employee-table-body");
    const search = (document.getElementById("emp-search-input").value || "").toLowerCase().trim();
    const roleFilter = document.getElementById("emp-role-filter").value;
    const branchFilter = document.getElementById("emp-branch-filter").value;
    const statusFilter = document.getElementById("emp-status-filter").value;
    const sortBy = document.getElementById("emp-sort-select").value;

    let filtered = [...allEmployeesCache];

    if (search) {
        filtered = filtered.filter(u =>
            (u.name && u.name.toLowerCase().includes(search)) ||
            (u.id && u.id.toLowerCase().includes(search))
        );
    }
    if (roleFilter !== "All") {
        filtered = filtered.filter(u => u.role === roleFilter);
    }
    if (branchFilter !== "All") {
        filtered = filtered.filter(u => u.branch === branchFilter);
    }
    if (statusFilter === "Active") {
        filtered = filtered.filter(u => u.is_active === 1);
    } else if (statusFilter === "On Leave") {
        filtered = filtered.filter(u => u.is_active === 0);
    }

    if (sortBy === "name_desc") {
        filtered.sort((a, b) => b.name.localeCompare(a.name));
    } else if (sortBy === "id_asc") {
        filtered.sort((a, b) => a.id.localeCompare(b.id));
    } else if (sortBy === "role") {
        filtered.sort((a, b) => a.role.localeCompare(b.role) || a.name.localeCompare(b.name));
    } else if (sortBy === "branch") {
        filtered.sort((a, b) => a.branch.localeCompare(b.branch) || a.name.localeCompare(b.name));
    } else {
        filtered.sort((a, b) => a.name.localeCompare(b.name));
    }

    document.getElementById("emp-count-badge").textContent = `Showing ${filtered.length} of ${allEmployeesCache.length} employees`;
    tbody.innerHTML = "";

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No employees match the filters.</td></tr>';
        return;
    }

    filtered.forEach(u => {
        const tr = document.createElement("tr");
        const statusHtml = u.is_active ?
            '<span class="text-emerald font-semibold">🟢 Active</span>' :
            '<span class="text-purple font-semibold">🟣 On Leave</span>';

        tr.innerHTML = `
            <td><strong>${u.name}</strong></td>
            <td><code>${u.id}</code></td>
            <td><span class="meta-badge badge-role">${u.role}</span></td>
            <td><span class="meta-badge badge-branch">${u.branch}</span></td>
            <td>${u.job_queue || '<span style="color: var(--text-muted);">Empty</span>'}</td>
            <td>${statusHtml}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Modal 3: Jobs Dataset Table (ID, Client, assigned_to, state, Mode, direction, branch)
async function openJobsModal() {
    const modal = document.getElementById("modal-jobs");
    modal.classList.add("active");
    loadJobsTable();
}

async function loadJobsTable() {
    const tbody = document.getElementById("jobs-table-body");
    tbody.innerHTML = '<tr><td colspan="7" class="loading-spinner">Loading jobs dataset...</td></tr>';

    try {
        const res = await fetch(`/api/jobs?branch=all`);
        allJobsCache = await res.json();

        // If not Admin, default branch filter to their branch
        if (currentUser.branch !== "all") {
            document.getElementById("jobs-branch-filter").value = currentUser.branch;
        }

        filterJobsTable();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="color: var(--rose);">Failed to load jobs: ${err}</td></tr>`;
    }
}

function filterJobsTable() {
    const tbody = document.getElementById("jobs-table-body");
    const search = (document.getElementById("jobs-search-input").value || "").toLowerCase().trim();
    const branchFilter = document.getElementById("jobs-branch-filter").value;
    const stateFilter = document.getElementById("jobs-state-filter").value;
    const modeFilter = document.getElementById("jobs-mode-filter").value;
    const dirFilter = document.getElementById("jobs-dir-filter").value;
    const sortBy = document.getElementById("jobs-sort-select").value;

    let filtered = [...allJobsCache];

    if (search) {
        filtered = filtered.filter(j =>
            (j.client && j.client.toLowerCase().includes(search)) ||
            String(j.id).includes(search) ||
            (j.assigned_to && j.assigned_to.toLowerCase().includes(search))
        );
    }
    if (branchFilter !== "all") {
        filtered = filtered.filter(j => j.branch === branchFilter);
    }
    if (stateFilter !== "All") {
        filtered = filtered.filter(j => j.state === stateFilter);
    }
    if (modeFilter !== "All") {
        filtered = filtered.filter(j => j.mode === modeFilter);
    }
    if (dirFilter !== "All") {
        filtered = filtered.filter(j => j.direction === dirFilter);
    }

    // Sort
    if (sortBy === "id_asc") {
        filtered.sort((a, b) => a.id - b.id);
    } else if (sortBy === "client_asc") {
        filtered.sort((a, b) => (a.client || "").localeCompare(b.client || ""));
    } else if (sortBy === "state") {
        filtered.sort((a, b) => (a.state || "").localeCompare(b.state || "") || b.id - a.id);
    } else if (sortBy === "branch") {
        filtered.sort((a, b) => (a.branch || "").localeCompare(b.branch || "") || b.id - a.id);
    } else {
        filtered.sort((a, b) => b.id - a.id);
    }

    document.getElementById("jobs-count-badge").textContent = `Showing ${filtered.length} of ${allJobsCache.length} jobs`;
    tbody.innerHTML = "";

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No jobs match the selected filters.</td></tr>';
        return;
    }

    filtered.forEach(j => {
        const tr = document.createElement("tr");
        const stageClass = `badge-stage-${j.state.toLowerCase()}`;
        tr.innerHTML = `
            <td><strong>#${j.id}</strong></td>
            <td><strong>${j.client}</strong></td>
            <td>${j.assigned_to ? `<code>${j.assigned_to}</code>` : '<span style="color: var(--text-muted);">Unassigned</span>'}</td>
            <td><span class="badge-stage ${stageClass}">${j.state}</span></td>
            <td><strong style="text-transform: uppercase;">${j.mode}</strong></td>
            <td><span style="text-transform: capitalize;">${j.direction}</span></td>
            <td><span class="meta-badge badge-branch">${j.branch}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// Modal 3: Jobs Dataset Table (with Assignment Filter and Read-Only Flag)
let isJobsModalReadOnly = false;

async function openJobsModal(readOnly = false) {
    isJobsModalReadOnly = Boolean(readOnly);
    const modal = document.getElementById("modal-jobs");
    const title = document.querySelector("#modal-jobs .modal-title");
    title.textContent = isJobsModalReadOnly ? "📦 Jobs Dataset (Read-Only Inspection)" : "📦 Jobs Dataset Table";

    modal.classList.add("active");
    loadJobsTable();
}

function filterJobsTable() {
    const tbody = document.getElementById("jobs-table-body");
    const search = (document.getElementById("jobs-search-input").value || "").toLowerCase().trim();
    const branchFilter = document.getElementById("jobs-branch-filter").value;
    const stateFilter = document.getElementById("jobs-state-filter").value;
    const modeFilter = document.getElementById("jobs-mode-filter").value;
    const dirFilter = document.getElementById("jobs-dir-filter").value;
    const assignFilter = document.getElementById("jobs-assign-filter").value;
    const sortBy = document.getElementById("jobs-sort-select").value;

    let filtered = [...allJobsCache];

    if (search) {
        filtered = filtered.filter(j =>
            (j.client && j.client.toLowerCase().includes(search)) ||
            String(j.id).includes(search) ||
            (j.assigned_to && j.assigned_to.toLowerCase().includes(search))
        );
    }
    if (branchFilter !== "All") {
        filtered = filtered.filter(j => j.branch === branchFilter);
    }
    if (stateFilter !== "All") {
        filtered = filtered.filter(j => j.state === stateFilter);
    }
    if (modeFilter !== "All") {
        filtered = filtered.filter(j => j.mode === modeFilter);
    }
    if (dirFilter !== "All") {
        filtered = filtered.filter(j => j.direction === dirFilter);
    }
    if (assignFilter === "assigned") {
        filtered = filtered.filter(j => j.assigned_to && j.assigned_to.trim() !== "");
    } else if (assignFilter === "unassigned") {
        filtered = filtered.filter(j => !j.assigned_to || j.assigned_to.trim() === "");
    }

    // Sort
    if (sortBy === "id_asc") {
        filtered.sort((a, b) => a.id - b.id);
    } else if (sortBy === "client_asc") {
        filtered.sort((a, b) => (a.client || "").localeCompare(b.client || ""));
    } else if (sortBy === "state") {
        filtered.sort((a, b) => (a.state || "").localeCompare(b.state || "") || b.id - a.id);
    } else if (sortBy === "branch") {
        filtered.sort((a, b) => (a.branch || "").localeCompare(b.branch || "") || b.id - a.id);
    } else {
        filtered.sort((a, b) => b.id - a.id);
    }

    document.getElementById("jobs-count-badge").textContent = `Showing ${filtered.length} of ${allJobsCache.length} jobs`;
    tbody.innerHTML = "";

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No jobs match the selected filters.</td></tr>';
        return;
    }

    filtered.forEach(j => {
        const tr = document.createElement("tr");
        const stageClass = `badge-stage-${j.state.toLowerCase()}`;
        tr.innerHTML = `
            <td><strong>#${j.id}</strong></td>
            <td><strong>${j.client}</strong></td>
            <td>${j.assigned_to ? `<code>${j.assigned_to}</code>` : '<span style="color: var(--text-muted);">Unassigned</span>'}</td>
            <td><span class="badge-stage ${stageClass}">${j.state}</span></td>
            <td><strong style="text-transform: uppercase;">${j.mode}</strong></td>
            <td><span style="text-transform: capitalize;">${j.direction}</span></td>
            <td><span class="meta-badge badge-branch">${j.branch}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// Modal 4: Assign Job to Staff (Cross-Branch Permitted for Job Assigner)
async function openAssignModal(preselectedJobId = null) {
    const modal = document.getElementById("modal-assign");
    document.getElementById("assign-modal-subtitle").textContent = "Cross-Branch Assignment Enabled: Assign any job to any staff";
    document.getElementById("assign-staff-label").textContent = "Select Assignee (Staff Member)";

    const jobSelect = document.getElementById("assign-job-select");
    jobSelect.innerHTML = "<option>Loading jobs...</option>";
    const staffSelect = document.getElementById("assign-staff-select");
    staffSelect.innerHTML = "<option>Loading staff...</option>";

    modal.classList.add("active");

    try {
        const [jobsRes, staffRes] = await Promise.all([
            fetch("/api/jobs?branch=all"),
            fetch("/api/branch-staff?branch=all")
        ]);

        const jobs = await jobsRes.json();
        const staff = await staffRes.json();

        jobSelect.innerHTML = "";
        const assignableJobs = jobs.filter(j => j.state === "Confirmed" || j.state === "Prepared" || j.state === "Reopened");

        if (assignableJobs.length === 0) {
            jobSelect.innerHTML = "<option value=''>No assignable jobs currently available</option>";
        } else {
            assignableJobs.forEach(j => {
                const opt = document.createElement("option");
                opt.value = j.id;
                opt.textContent = `[Branch ${j.branch}] Job #${j.id} - ${j.state} (${j.client} | ${j.mode})`;
                if (preselectedJobId && j.id === preselectedJobId) opt.selected = true;
                jobSelect.appendChild(opt);
            });
        }

        staffSelect.innerHTML = "";
        if (staff.length === 0) {
            staffSelect.innerHTML = "<option value=''>No staff registered</option>";
        } else {
            staff.forEach(s => {
                const opt = document.createElement("option");
                opt.value = s.id;
                opt.textContent = `${s.id} - ${s.name} (Branch ${s.branch})`;
                staffSelect.appendChild(opt);
            });
        }
    } catch (err) {
        showToast("Error loading assignment data: " + err, "error");
    }
}

async function submitJobAssignment() {
    const jobId = document.getElementById("assign-job-select").value;
    const assignee = document.getElementById("assign-staff-select").value;

    if (!jobId || !assignee) {
        showToast("Please select both a job and an assignee.", "error");
        return;
    }

    try {
        const res = await fetch("/api/assign", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                actor: currentUser.id,
                job_id: jobId,
                assignee: assignee,
                reason: "Assigned via interface"
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Job #${jobId} successfully assigned to ${data.assigned_to}!`, "success");
            closeModal("modal-assign");
            loadQueue();
        } else {
            showToast(`Assignment Blocked: ${data.detail || data.error}`, "error");
        }
    } catch (err) {
        showToast("Error processing assignment: " + err, "error");
    }
}

// Modal 5: Admin Sensitive Lifecycle Control (Cancel & Reopen Jobs)
async function openAdminLifecycleModal() {
    const modal = document.getElementById("modal-admin-lifecycle");
    modal.classList.add("active");
    updateLifecycleJobsList();
}

async function updateLifecycleJobsList() {
    const action = document.getElementById("lifecycle-action-select").value;
    const jobSelect = document.getElementById("lifecycle-job-select");
    jobSelect.innerHTML = "<option>Loading eligible jobs...</option>";

    try {
        const res = await fetch("/api/jobs?branch=all");
        const jobs = await res.json();
        jobSelect.innerHTML = "";

        let eligible = [];
        if (action === "cancel") {
            eligible = jobs.filter(j => ['Confirmed', 'Prepared', 'Checked', 'Reopened'].includes(j.state));
        } else if (action === "reopen") {
            eligible = jobs.filter(j => ['Filed', 'Cancelled'].includes(j.state));
        }

        if (eligible.length === 0) {
            jobSelect.innerHTML = `<option value="">No jobs eligible to ${action}</option>`;
        } else {
            eligible.forEach(j => {
                const opt = document.createElement("option");
                opt.value = j.id;
                opt.textContent = `Job #${j.id} [${j.client}] - Current State: ${j.state} (${j.branch})`;
                jobSelect.appendChild(opt);
            });
        }
    } catch (err) {
        showToast("Error loading jobs: " + err, "error");
    }
}

async function submitAdminLifecycleAction() {
    const action = document.getElementById("lifecycle-action-select").value;
    const jobId = document.getElementById("lifecycle-job-select").value;
    const reason = document.getElementById("lifecycle-reason").value.trim() || `Admin executed ${action}`;

    if (!jobId) {
        showToast("Please select a job.", "error");
        return;
    }

    try {
        const res = await fetch("/api/act", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                actor: currentUser.id,
                job_id: jobId,
                action: action,
                reason: reason
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Job #${jobId} state updated to '${data.state}' by Admin.`, "success");
            closeModal("modal-admin-lifecycle");
            loadQueue();
        } else {
            showToast(`Action Denied: ${data.summary || data.error}`, "error");
        }
    } catch (err) {
        showToast("Error executing admin action: " + err, "error");
    }
}

// Modal 6: Staff Access Management Portal (Strictly Admin Only)
async function openAccessModal() {
    if (!currentUser || currentUser.role !== "Admin") {
        showToast("Access Denied: Staff access is only managed by admin.", "error");
        return;
    }

    const modal = document.getElementById("modal-access");
    modal.classList.add("active");

    const empSelect = document.getElementById("access-emp-select");
    empSelect.innerHTML = "";

    cachedUsers.forEach(u => {
        const opt = document.createElement("option");
        opt.value = u.id;
        opt.textContent = `${u.id} - ${u.name} (Current: ${u.role}, Branch: ${u.branch})`;
        empSelect.appendChild(opt);
    });
}

// AUDITOR STREAM HANDLERS (Verify / Flag / Reject)
function filterAuditorStream() {
    const container = document.getElementById("tasks-container");
    const search = (document.getElementById("auditor-stream-search").value || "").toLowerCase().trim();
    const decFilter = document.getElementById("auditor-stream-decision").value;
    const statusFilter = document.getElementById("auditor-stream-status").value;
    const sortBy = document.getElementById("auditor-stream-sort").value;

    let filtered = [...allAuditCache];

    if (search) {
        filtered = filtered.filter(a =>
            a.actor.toLowerCase().includes(search) ||
            a.op.toLowerCase().includes(search) ||
            a.target.toLowerCase().includes(search) ||
            a.detail.toLowerCase().includes(search)
        );
    }

    if (decFilter === "ALLOWED") {
        filtered = filtered.filter(a => a.allowed === 1);
    } else if (decFilter === "DENIED") {
        filtered = filtered.filter(a => a.allowed === 0);
    }

    if (statusFilter === "Pending") {
        filtered = filtered.filter(a => (!a.verification_status || a.verification_status === "pending") && !a.verified_by);
    } else if (statusFilter === "Verified") {
        filtered = filtered.filter(a => a.verification_status === "verified" || a.verified_by);
    } else if (statusFilter === "Flagged") {
        filtered = filtered.filter(a => a.verification_status === "flagged");
    } else if (statusFilter === "Rejected") {
        filtered = filtered.filter(a => a.verification_status === "rejected");
    }

    if (sortBy === "oldest") {
        filtered.sort((a, b) => a.id - b.id);
    } else {
        filtered.sort((a, b) => b.id - a.id);
    }

    container.innerHTML = "";

    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔍</div>
                <p style="font-weight: 600;">No audit entries match the current filters.</p>
            </div>
        `;
        return;
    }

    filtered.forEach(a => {
        const card = document.createElement("div");
        card.className = "task-card";

        const tagText = a.allowed ? "ALLOWED" : "DENIED";
        const tagClass = a.allowed ? "tag-allowed" : "tag-denied";
        const vStatus = (a.verification_status || (a.verified_by ? "verified" : "pending")).toLowerCase();

        card.innerHTML = `
            <div class="task-top">
                <div class="task-title-group">
                    <span class="${tagClass}">[${tagText}]</span>
                    <span class="audit-status-badge status-${vStatus}">Status: ${vStatus.toUpperCase()}</span>
                    <h3 class="task-title">Entry #${a.id}</h3>
                    <span class="task-client">${a.ts}</span>
                </div>
                <div class="audit-action-btn-group">
                    <button class="btn btn-success btn-sm" onclick="reviewAuditItem(${a.id}, 'verified')">✓ Verify</button>
                    <button class="btn btn-warning btn-sm" onclick="reviewAuditItem(${a.id}, 'flagged')">🚩 Flag</button>
                    <button class="btn btn-danger btn-sm" onclick="reviewAuditItem(${a.id}, 'rejected')">✕ Reject</button>
                </div>
            </div>
            <div class="task-meta">
                <div class="meta-pill"><strong>Actor:</strong>&nbsp;<code>${a.actor}</code></div>
                <div class="meta-pill"><strong>Op:</strong>&nbsp;<code>${a.op}</code></div>
                <div class="meta-pill"><strong>Target:</strong>&nbsp;<code>${a.target}</code></div>
            </div>
            <div class="task-footer" style="margin-top: 0.5rem; font-size: 0.85rem; color: #E2E8F0;">
                <span><strong>Detail:</strong> ${a.detail}</span>
                ${a.verified_by ? `<span style="color: var(--sky); font-weight: 600;">[Reviewed by ${a.verified_by}: ${a.verification_notes || ''}]</span>` : ''}
            </div>
        `;
        container.appendChild(card);
    });
}

async function reviewAuditItem(auditId, status) {
    const defaultNotes = status === "verified" ? "Audit verified & certified" : (status === "flagged" ? "Flagged for supervisor review" : "Violation rejected by auditor");
    const notes = prompt(`Enter remarks for ${status.toUpperCase()} on Audit #${auditId}:`, defaultNotes);
    if (notes === null) return;

    try {
        const res = await fetch("/api/audit/review", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                checker_id: currentUser.id,
                audit_id: auditId,
                status: status,
                notes: notes
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Audit Entry #${auditId} successfully marked as '${status}'!`, "success");
            loadQueue();
        } else {
            showToast("Failed to review audit entry: " + data.error, "error");
        }
    } catch (err) {
        showToast("Error reviewing audit entry: " + err, "error");
    }
}

// PROFILE SECTION MODAL
async function openProfileModal() {
    if (!currentUser) return;
    const modal = document.getElementById("modal-profile");

    // Fetch fresh employee record
    try {
        const res = await fetch("/api/users");
        const users = await res.json();
        const me = users.find(u => u.id === currentUser.id) || currentUser;

        document.getElementById("prof-name").textContent = me.name;
        document.getElementById("prof-id").textContent = `ID: ${me.id}`;
        document.getElementById("prof-role").textContent = me.role;
        document.getElementById("prof-branch").textContent = me.branch === "all" ? "all (Global)" : me.branch;

        const statusEl = document.getElementById("prof-status");
        if (me.is_active) {
            statusEl.className = "status-indicator";
            statusEl.textContent = "Active On Duty";
        } else {
            statusEl.className = "status-indicator status-absent";
            statusEl.textContent = "On Absent Leave";
        }

        const queueList = document.getElementById("prof-queue-list");
        queueList.innerHTML = "";
        const queueItems = (me.job_queue || "").split(",").map(s => s.trim()).filter(Boolean);

        document.getElementById("prof-queue-count").textContent = `${queueItems.length} jobs`;

        if (queueItems.length === 0) {
            queueList.innerHTML = '<span class="chip-empty">No active jobs assigned</span>';
        } else {
            queueItems.forEach(jid => {
                const chip = document.createElement("span");
                chip.className = "chip-job";
                chip.textContent = `Job #${jid}`;
                queueList.appendChild(chip);
            });
        }

        const staffActions = document.getElementById("prof-staff-actions");
        const leaveBtn = document.getElementById("prof-leave-btn");
        if (me.role === "staff") {
            staffActions.style.display = "block";
            leaveBtn.innerHTML = me.is_active ? "<span>🏖️ Apply for Absent Leave</span>" : "<span>🟢 Return to Duty (End Leave)</span>";
            leaveBtn.className = me.is_active ? "btn btn-warning btn-block" : "btn btn-success btn-block";
        } else {
            staffActions.style.display = "none";
        }

        modal.classList.add("active");
    } catch (err) {
        showToast("Failed to load profile data: " + err, "error");
    }
}

async function toggleLeaveFromProfile() {
    await toggleLeave();
    openProfileModal();
}

async function submitRoleUpdate() {
    const empId = document.getElementById("access-emp-select").value;
    const role = document.getElementById("access-role-select").value;
    const branch = document.getElementById("access-branch-select").value;

    try {
        const res = await fetch("/api/update-role", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                actor: currentUser.id,
                emp_id: empId,
                role: role,
                branch: branch
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Updated ${empId} to Role '${role}' in branch '${branch}'`, "success");
            closeModal("modal-access");
            fetchUsersList();
        } else {
            showToast(`Update Failed: ${data.error}`, "error");
        }
    } catch (err) {
        showToast("Error updating access: " + err, "error");
    }
}
