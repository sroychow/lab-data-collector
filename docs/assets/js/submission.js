requireLogin();

const params = new URLSearchParams(window.location.search);
const submissionId = params.get("id");

const pageTitle = document.getElementById("pageTitle");
const metaBox = document.getElementById("metaBox");
const errorBox = document.getElementById("errorBox");
const contentBox = document.getElementById("contentBox");

document.getElementById("logoutButton").addEventListener("click", logout);

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function groupRowsByTable(rows) {
    const grouped = new Map();

    rows.forEach((row) => {
        if (!grouped.has(row.table_id)) {
            grouped.set(row.table_id, {
                table_name: row.table_name,
                rows: []
            });
        }
        grouped.get(row.table_id).rows.push(row);
    });

    return Array.from(grouped.values());
}

function renderSubmission(submission) {
    pageTitle.textContent = `${submission.experiment_title}`;
    metaBox.textContent = [
        `Entry #${submission.id}`,
        submission.sample_id ? `Sample: ${submission.sample_id}` : "No sample id",
        `Submitted by ${submission.submitted_by_username || "—"}`,
        new Date(submission.created_at).toLocaleString()
    ].join(" · ");

    const groupedTables = groupRowsByTable(submission.rows);

    const tableHtml = groupedTables.map((group) => {
        const fields = group.rows[0]?.values || [];

        return `
            <section class="card">
                <h2>${escapeHtml(group.table_name)}</h2>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Serial No.</th>
                                ${fields.map((value) => `
                                    <th>${escapeHtml(value.field_name)} ${value.unit ? `(${escapeHtml(value.unit)})` : ""}</th>
                                `).join("")}
                            </tr>
                        </thead>
                        <tbody>
                            ${group.rows.map((row) => `
                                <tr>
                                    <td>${row.serial_number}</td>
                                    ${row.values.map((value) => `
                                        <td>${escapeHtml(value.value)}</td>
                                    `).join("")}
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>
            </section>
        `;
    }).join("");

    const resultsHtml = submission.result_values.length ? `
        <section class="card">
            <h2>Final results</h2>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Quantity</th>
                            <th>Formula</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${submission.result_values.map((result) => `
                            <tr>
                                <td>${escapeHtml(result.name)} ${result.unit ? `(${escapeHtml(result.unit)})` : ""}</td>
                                <td><code>${escapeHtml(result.formula)}</code></td>
                                <td>${escapeHtml(result.value)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        </section>
    ` : "";

    const plotsHtml = submission.plot_configs.length ? `
        <section class="card">
            <h2>Plots for this entry</h2>
            <div class="actions">
                ${submission.plot_configs.map((plot) => `
                    <a class="btn btn-secondary"
                       href="plot.html?submission=${encodeURIComponent(submission.id)}&plot=${encodeURIComponent(plot.id)}">
                        ${escapeHtml(plot.title)}
                    </a>
                `).join("")}
            </div>
        </section>
    ` : "";

    contentBox.innerHTML = plotsHtml + tableHtml + resultsHtml;
}

async function loadSubmissionList() {
    pageTitle.textContent = "Submissions";
    metaBox.textContent = "Recent submissions visible to your account.";
    contentBox.innerHTML = "<p>Loading submissions...</p>";

    const submissions = await apiFetch("/submissions/");

    if (!submissions.length) {
        contentBox.innerHTML = "<p>No submissions found.</p>";
        return;
    }

    contentBox.innerHTML = submissions.map((submission) => `
        <article class="card">
            <h2>${escapeHtml(submission.experiment_title)}</h2>
            <p class="muted">
                Entry #${submission.id}
                · ${submission.sample_id ? `Sample: ${escapeHtml(submission.sample_id)}` : "No sample id"}
                · ${new Date(submission.created_at).toLocaleString()}
            </p>
            <a class="btn" href="submission.html?id=${encodeURIComponent(submission.id)}">Open submission</a>
        </article>
    `).join("");
}

async function load() {
    try {
        if (submissionId) {
            const submission = await apiFetch(`/submissions/${encodeURIComponent(submissionId)}/`);
            renderSubmission(submission);
        } else {
            await loadSubmissionList();
        }
    } catch (error) {
        errorBox.textContent = error.message;
        contentBox.innerHTML = "";
    }
}

load();
