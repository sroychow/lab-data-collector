requireLogin();

const params = new URLSearchParams(window.location.search);
const submissionId = params.get("submission");
const plotId = params.get("plot");

const plotTitle = document.getElementById("plotTitle");
const plotMeta = document.getElementById("plotMeta");
const errorBox = document.getElementById("errorBox");
const fitBox = document.getElementById("fitBox");
const backLink = document.getElementById("backLink");

document.getElementById("logoutButton").addEventListener("click", logout);

if (submissionId) {
    backLink.href = `submission.html?id=${encodeURIComponent(submissionId)}`;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function renderFit(fitResult) {
    if (!fitResult) {
        fitBox.innerHTML = "";
        return;
    }

    if (fitResult.error) {
        fitBox.innerHTML = `
            <section class="card">
                <h2>Curve fitting result</h2>
                <p>${escapeHtml(fitResult.error)}</p>
            </section>
        `;
        return;
    }

    fitBox.innerHTML = `
        <section class="card">
            <h2>Curve fitting result</h2>
            <div class="table-wrap">
                <table>
                    <tbody>
                        <tr><th>Fit model</th><td>y = m x + c</td></tr>
                        <tr><th>Slope, m</th><td>${Number(fitResult.slope).toPrecision(8)}</td></tr>
                        <tr><th>Intercept, c</th><td>${Number(fitResult.intercept).toPrecision(8)}</td></tr>
                        <tr><th>R</th><td>${fitResult.r === null ? "—" : Number(fitResult.r).toPrecision(6)}</td></tr>
                        <tr><th>R²</th><td>${fitResult.r_squared === null ? "—" : Number(fitResult.r_squared).toPrecision(6)}</td></tr>
                        <tr><th>Points used</th><td>${fitResult.n}</td></tr>
                    </tbody>
                </table>
            </div>
            <p>
                <strong>Fitted equation:</strong>
                y = ${Number(fitResult.slope).toPrecision(6)} x
                ${fitResult.intercept >= 0 ? "+" : ""}
                ${Number(fitResult.intercept).toPrecision(6)}
            </p>
        </section>
    `;
}

function renderChart(data) {
    const chartData = data.chart_data || [];
    const fitLine = data.fit_line || [];
    const plot = data.plot;

    plotTitle.textContent = plot.title;
    plotMeta.textContent = `${data.experiment} · Points: ${data.point_count}`;

    if (!chartData.length) {
        errorBox.textContent = "No numeric points available for this plot.";
        return;
    }

    const ctx = document.getElementById("labPlot");

    if (plot.chart_type === "bar") {
        new Chart(ctx, {
            type: "bar",
            data: {
                labels: chartData.map(p => p.serial_number),
                datasets: [{
                    label: plot.title,
                    data: chartData.map(p => p.y)
                }]
            },
            options: {
                responsive: true,
                scales: {
                    x: { title: { display: true, text: "Serial number" } },
                    y: { title: { display: true, text: plot.y_axis_label || plot.y_field_name } }
                }
            }
        });
        return;
    }

    const datasets = [{
        label: plot.title,
        data: chartData.map(p => ({x: p.x, y: p.y})),
        showLine: plot.chart_type === "line",
        tension: 0.15
    }];

    if (fitLine.length === 2) {
        datasets.push({
            label: "Linear fit",
            data: fitLine.map(p => ({x: p.x, y: p.y})),
            type: "line",
            showLine: true,
            pointRadius: 0,
            borderDash: [6, 4],
            tension: 0
        });
    }

    new Chart(ctx, {
        type: "scatter",
        data: { datasets },
        options: {
            responsive: true,
            parsing: false,
            scales: {
                x: {
                    type: "linear",
                    title: { display: true, text: plot.x_axis_label || plot.x_field_name }
                },
                y: {
                    title: { display: true, text: plot.y_axis_label || plot.y_field_name }
                }
            }
        }
    });

    renderFit(data.fit_result);
}

async function loadPlot() {
    if (!submissionId || !plotId) {
        errorBox.textContent = "Missing submission or plot id.";
        return;
    }

    try {
        const data = await apiFetch(`/submissions/${encodeURIComponent(submissionId)}/plots/${encodeURIComponent(plotId)}/`);
        renderChart(data);
    } catch (error) {
        errorBox.textContent = error.message;
    }
}

loadPlot();
