requireLogin();

const params = new URLSearchParams(window.location.search);
const slug = params.get("slug");

const titleBox = document.getElementById("experimentTitle");
const metaBox = document.getElementById("experimentMeta");
const objectiveBox = document.getElementById("experimentObjective");
const tablesBox = document.getElementById("tablesBox");
const resultsBox = document.getElementById("resultsBox");
const plotsBox = document.getElementById("plotsBox");
const errorBox = document.getElementById("errorBox");
const submitLink = document.getElementById("submitLink");
const submissionLink = document.getElementById("submissionLink");
const experimentSubmissionsBox = document.getElementById("experimentSubmissionsBox");

document.getElementById("logoutButton").addEventListener("click", logout);

if (!slug) {
    errorBox.textContent = "No experiment slug provided.";
} else {
    submitLink.href = `submit.html?slug=${encodeURIComponent(slug)}`;
    submissionLink.href = `submission.html?experiment=${encodeURIComponent(slug)}`;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function fieldRow(field) {
    const required = field.required ? "Yes" : "No";
    const formula = field.calculation_formula ? `<code>${escapeHtml(field.calculation_formula)}</code>` : "—";

    return `
        <tr>
            <td>${escapeHtml(field.name)}</td>
            <td><code>${escapeHtml(field.variable_name)}</code></td>
            <td>${escapeHtml(field.field_type)}</td>
            <td>${escapeHtml(field.unit || "—")}</td>
            <td>${required}</td>
            <td>${formula}</td>
        </tr>
    `;
}

async function loadExperimentSubmissions() {
    if (!slug) return;

    try {
        const submissions = await apiFetch(`/submissions/?experiment=${encodeURIComponent(slug)}`);

        if (!submissions.length) {
            experimentSubmissionsBox.innerHTML = "<p>No submitted entries yet.</p>";
            return;
        }

        experimentSubmissionsBox.innerHTML = `
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Entry</th>
                            <th>Sample / Run ID</th>
                            <th>Submitted by</th>
                            <th>Created</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${submissions.map((submission) => `
                            <tr>
                                <td>#${submission.id}</td>
                                <td>${escapeHtml(submission.sample_id || "—")}</td>
                                <td>${escapeHtml(submission.submitted_by_username || "—")}</td>
                                <td>${new Date(submission.created_at).toLocaleString()}</td>
                                <td>
                                    <a class="btn btn-secondary"
                                       href="submission.html?id=${encodeURIComponent(submission.id)}">
                                       Open data
                                    </a>
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        `;
    } catch (error) {
        experimentSubmissionsBox.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
    }
}

async function loadSchema() {
    try {
        const schema = await apiFetch(`/experiments/${encodeURIComponent(slug)}/schema/`);

        titleBox.textContent = schema.title;
        metaBox.textContent = [
            schema.course_or_project || "No course/project",
            `Protocol ${schema.protocol_version}`,
            schema.status
        ].join(" · ");
        objectiveBox.textContent = schema.objective || "No objective added.";

        if (!schema.tables.length) {
            tablesBox.innerHTML = "<p>No tables configured.</p>";
        } else {
            tablesBox.innerHTML = schema.tables.map((table) => `
                <section class="card">
                    <h2>${escapeHtml(table.name)}</h2>
                    <p class="muted">Variable name: <code>${escapeHtml(table.variable_name)}</code></p>
                    ${table.description ? `<p>${escapeHtml(table.description)}</p>` : ""}
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Field</th>
                                    <th>Variable</th>
                                    <th>Type</th>
                                    <th>Unit</th>
                                    <th>Required</th>
                                    <th>Formula</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${table.fields.map(fieldRow).join("")}
                            </tbody>
                        </table>
                    </div>
                </section>
            `).join("");
        }

        if (!schema.result_fields.length) {
            resultsBox.innerHTML = "<p>No final result fields configured.</p>";
        } else {
            resultsBox.innerHTML = `
                <section class="card">
                    <h2>Final result fields</h2>
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr><th>Result</th><th>Variable</th><th>Formula</th><th>Unit</th></tr>
                            </thead>
                            <tbody>
                                ${schema.result_fields.map((result) => `
                                    <tr>
                                        <td>${escapeHtml(result.name)}</td>
                                        <td><code>${escapeHtml(result.variable_name)}</code></td>
                                        <td><code>${escapeHtml(result.calculation_formula)}</code></td>
                                        <td>${escapeHtml(result.unit || "—")}</td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                </section>
            `;
        }

        if (!schema.plot_configs.length) {
            plotsBox.innerHTML = "<p>No plots configured.</p>";
        } else {
            plotsBox.innerHTML = `
                <section class="card">
                    <h2>Configured plots</h2>
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr><th>Plot</th><th>Table</th><th>X field</th><th>Y field</th><th>Chart</th><th>Fit</th></tr>
                            </thead>
                            <tbody>
                                ${schema.plot_configs.map((plot) => `
                                    <tr>
                                        <td>${escapeHtml(plot.title)}</td>
                                        <td>${escapeHtml(plot.table_name)}</td>
                                        <td>${escapeHtml(plot.x_field_name)}</td>
                                        <td>${escapeHtml(plot.y_field_name)}</td>
                                        <td>${escapeHtml(plot.chart_type)}</td>
                                        <td>${escapeHtml(plot.fit_type || "none")}</td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                </section>
            `;
        }
    } catch (error) {
        errorBox.textContent = error.message;
    }
}

loadSchema();
loadExperimentSubmissions();
