requireLogin();

const params = new URLSearchParams(window.location.search);
const slug = params.get("slug");

const pageTitle = document.getElementById("pageTitle");
const errorBox = document.getElementById("errorBox");
const formTables = document.getElementById("formTables");
const form = document.getElementById("submissionForm");

let schema = null;

document.getElementById("logoutButton").addEventListener("click", logout);

if (!slug) {
    errorBox.textContent = "No experiment slug provided.";
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function inputTypeFor(field) {
    if (field.field_type === "integer" || field.field_type === "decimal") return "text";
    if (field.field_type === "date") return "date";
    if (field.field_type === "boolean") return "checkbox";
    return "text";
}

function buildInput(table, field, rowNumber) {
    if (field.field_type === "derived") {
        return `<input disabled placeholder="Calculated on server">`;
    }

    const name = `table_${table.id}_row_${rowNumber}_field_${field.id}`;
    const required = field.required ? "required" : "";
    const type = inputTypeFor(field);

    if (type === "checkbox") {
        return `<input type="checkbox" name="${name}" value="true">`;
    }

    return `
        <input
            type="${type}"
            name="${name}"
            ${required}
            placeholder="${escapeHtml(field.unit || "")}"
            inputmode="${field.field_type === "decimal" ? "decimal" : ""}">
    `;
}

function renderForm(schemaData) {
    pageTitle.textContent = `Submit data: ${schemaData.title}`;

    formTables.innerHTML = schemaData.tables.map((table) => {
        const rows = [1, 2, 3, 4, 5];

        return `
            <section class="card" data-table-id="${table.id}">
                <h2>${escapeHtml(table.name)}</h2>
                <p class="muted">Variable name: <code>${escapeHtml(table.variable_name)}</code></p>

                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Serial No.</th>
                                ${table.fields.map((field) => `
                                    <th>
                                        ${escapeHtml(field.name)}
                                        ${field.unit ? `(${escapeHtml(field.unit)})` : ""}
                                        ${field.field_type === "derived" ? "<br><small>calculated</small>" : ""}
                                    </th>
                                `).join("")}
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.map((rowNumber) => `
                                <tr data-row-number="${rowNumber}">
                                    <td>${rowNumber}</td>
                                    ${table.fields.map((field) => `
                                        <td>${buildInput(table, field, rowNumber)}</td>
                                    `).join("")}
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>
            </section>
        `;
    }).join("");
}

async function loadSchema() {
    try {
        schema = await apiFetch(`/experiments/${encodeURIComponent(slug)}/schema/`);
        renderForm(schema);
    } catch (error) {
        errorBox.textContent = error.message;
    }
}

function getFieldValue(tableId, rowNumber, fieldId, fieldType) {
    const name = `table_${tableId}_row_${rowNumber}_field_${fieldId}`;
    const input = form.querySelector(`[name="${name}"]`);

    if (!input) return "";

    if (fieldType === "boolean") {
        return input.checked ? "true" : "false";
    }

    return input.value;
}

function buildPayload() {
    const observationRows = [];

    schema.tables.forEach((table) => {
        [1, 2, 3, 4, 5].forEach((rowNumber) => {
            const values = {};
            let hasAnyValue = false;

            table.fields.forEach((field) => {
                if (field.field_type === "derived") return;

                const value = getFieldValue(table.id, rowNumber, field.id, field.field_type);
                values[field.id] = value;

                if (String(value).trim() !== "") {
                    hasAnyValue = true;
                }
            });

            if (hasAnyValue) {
                observationRows.push({
                    table: table.id,
                    serial_number: rowNumber,
                    values: values
                });
            }
        });
    });

    return {
        sample_id: document.getElementById("sampleId").value,
        notes: document.getElementById("notes").value,
        observation_rows: observationRows
    };
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.textContent = "";

    try {
        const payload = buildPayload();

        if (!payload.observation_rows.length) {
            errorBox.textContent = "Please enter at least one observation row.";
            return;
        }

        const result = await apiFetch(`/experiments/${encodeURIComponent(slug)}/submissions/`, {
            method: "POST",
            body: JSON.stringify(payload)
        });

        window.location.href = `submission.html?id=${encodeURIComponent(result.id)}`;
    } catch (error) {
        errorBox.textContent = error.message;
    }
});

loadSchema();
