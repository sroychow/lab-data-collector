import json
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from labdata.models import Experiment, PlotConfig, Submission

SITE_BASE = "/lab-data-collector"


def esc(value):
    value = "" if value is None else str(value)
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


def fmt_dt(value):
    if not value:
        return ""
    return timezone.localtime(value).strftime("%d %b %Y, %I:%M %p")


def page(title, body):
    generated_at = timezone.localtime().strftime("%d %b %Y, %I:%M %p")
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{esc(title)} | LabVault Snapshot</title>
  <link rel="stylesheet" href="{SITE_BASE}/assets/css/styles.css">
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <a class="brand" href="{SITE_BASE}/">LabVault Snapshot</a>
      <nav class="actions">
        <a class="btn btn-secondary" href="{SITE_BASE}/">Experiments</a>
        <a class="btn btn-secondary" href="{SITE_BASE}/submissions/">Submissions</a>
        <a class="btn btn-secondary" href="{SITE_BASE}/data/experiments.json">JSON</a>
      </nav>
    </div>
  </header>
  <main class="container">
    <section class="notice">
      Read-only public snapshot generated on {esc(generated_at)}.
      Live updates are maintained on the local Django server.
    </section>
    {body}
  </main>
  <script src="{SITE_BASE}/assets/js/site.js"></script>
</body>
</html>'''


def row_values(row):
    return list(row.values.select_related("field").order_by("field__order", "field__id"))


def submission_to_json(submission):
    rows = []
    for row in submission.rows.select_related("table").order_by("table__order", "serial_number", "id"):
        rows.append({
            "table": row.table.name,
            "serial_number": row.serial_number,
            "values": [
                {
                    "field": val.field.name,
                    "variable": val.field.variable_name,
                    "unit": val.field.unit,
                    "value": val.value,
                }
                for val in row_values(row)
            ],
        })

    results = []
    for result in submission.result_values.select_related("result_field").order_by("result_field__order", "result_field__id"):
        results.append({
            "name": result.result_field.name,
            "variable": result.result_field.variable_name,
            "unit": result.result_field.unit,
            "formula": result.result_field.calculation_formula,
            "value": result.value,
        })

    return {
        "id": submission.id,
        "experiment": submission.experiment.title,
        "experiment_slug": submission.experiment.slug,
        "sample_id": submission.sample_id,
        "notes": submission.notes,
        "status": submission.status,
        "submitted_by": getattr(submission.submitted_by, "username", ""),
        "created_at": submission.created_at.isoformat() if submission.created_at else "",
        "updated_at": submission.updated_at.isoformat() if submission.updated_at else "",
        "rows": rows,
        "results": results,
    }


def render_experiment(experiment, submissions):
    submission_rows = []
    for s in submissions:
        submission_rows.append(f'''
        <tr>
          <td>#{s.id}</td>
          <td>{esc(s.sample_id or "—")}</td>
          <td>{esc(getattr(s.submitted_by, "username", "—"))}</td>
          <td>{esc(fmt_dt(s.created_at))}</td>
          <td><a class="btn btn-secondary" href="{SITE_BASE}/submissions/{s.id}/">Open data</a></td>
        </tr>''')

    if submission_rows:
        submissions_html = f'''
        <section class="card">
          <h2>Submitted entries</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Entry</th><th>Sample / Run ID</th><th>Submitted by</th><th>Created</th><th></th></tr>
              </thead>
              <tbody>{"".join(submission_rows)}</tbody>
            </table>
          </div>
        </section>'''
    else:
        submissions_html = '''
        <section class="card">
          <h2>Submitted entries</h2>
          <p>No submitted entries in this snapshot.</p>
        </section>'''

    table_sections = []
    for table in experiment.tables.prefetch_related("fields").order_by("order", "id"):
        field_rows = []
        for field in table.fields.all().order_by("order", "id"):
            field_rows.append(f'''
            <tr>
              <td>{esc(field.name)}</td>
              <td><code>{esc(field.variable_name)}</code></td>
              <td>{esc(field.field_type)}</td>
              <td>{esc(field.unit or "—")}</td>
              <td>{esc("Yes" if field.required else "No")}</td>
              <td><code>{esc(field.calculation_formula or "—")}</code></td>
            </tr>''')
        table_sections.append(f'''
        <section class="card">
          <h2>{esc(table.name)}</h2>
          <p class="muted">Variable name: <code>{esc(table.variable_name)}</code></p>
          <p>{esc(table.description or "")}</p>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Field</th><th>Variable</th><th>Type</th><th>Unit</th><th>Required</th><th>Formula</th></tr></thead>
              <tbody>{"".join(field_rows)}</tbody>
            </table>
          </div>
        </section>''')

    plot_rows = []
    for plot in PlotConfig.objects.filter(table__experiment=experiment, is_active=True).select_related("table", "x_field", "y_field").order_by("order", "id"):
        plot_rows.append(f'''
        <tr>
          <td>{esc(plot.title)}</td>
          <td>{esc(plot.table.name)}</td>
          <td>{esc(plot.x_field.name)}</td>
          <td>{esc(plot.y_field.name)}</td>
          <td>{esc(plot.chart_type)}</td>
          <td>{esc(getattr(plot, "fit_type", "none"))}</td>
        </tr>''')

    plots_html = ""
    if plot_rows:
        plots_html = f'''
        <section class="card">
          <h2>Configured plots</h2>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Plot</th><th>Table</th><th>X field</th><th>Y field</th><th>Chart</th><th>Fit</th></tr></thead>
              <tbody>{"".join(plot_rows)}</tbody>
            </table>
          </div>
        </section>'''

    body = f'''
    <section class="card hero">
      <h1>{esc(experiment.title)}</h1>
      <p class="muted">{esc(experiment.course_or_project or "No course/project")} · Protocol {esc(experiment.protocol_version)} · {esc(experiment.status)}</p>
      <p>{esc(experiment.objective or "")}</p>
    </section>
    {submissions_html}
    {"".join(table_sections)}
    {plots_html}
    '''
    return page(experiment.title, body)


def render_submission(submission):
    grouped = {}
    for row in submission.rows.select_related("table").order_by("table__order", "serial_number", "id"):
        grouped.setdefault(row.table.name, []).append(row)

    sections = []
    for table_name, rows in grouped.items():
        values0 = row_values(rows[0]) if rows else []
        headers = "".join(
            f"<th>{esc(v.field.name)} {esc('(' + v.field.unit + ')' if v.field.unit else '')}</th>"
            for v in values0
        )
        body_rows = []
        for row in rows:
            values = row_values(row)
            cells = "".join(f"<td>{esc(v.value)}</td>" for v in values)
            body_rows.append(f"<tr><td>{row.serial_number}</td>{cells}</tr>")
        sections.append(f'''
        <section class="card">
          <h2>{esc(table_name)}</h2>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Serial No.</th>{headers}</tr></thead>
              <tbody>{"".join(body_rows)}</tbody>
            </table>
          </div>
        </section>''')

    result_rows = []
    for rv in submission.result_values.select_related("result_field").order_by("result_field__order", "result_field__id"):
        unit = f"({rv.result_field.unit})" if rv.result_field.unit else ""
        result_rows.append(f'''
        <tr>
          <td>{esc(rv.result_field.name)} {esc(unit)}</td>
          <td><code>{esc(rv.result_field.calculation_formula)}</code></td>
          <td>{esc(rv.value)}</td>
        </tr>''')

    results_html = ""
    if result_rows:
        results_html = f'''
        <section class="card">
          <h2>Final results</h2>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Quantity</th><th>Formula</th><th>Value</th></tr></thead>
              <tbody>{"".join(result_rows)}</tbody>
            </table>
          </div>
        </section>'''

    body = f'''
    <section class="card hero">
      <h1>{esc(submission.experiment.title)}</h1>
      <p class="muted">Entry #{submission.id} · Sample: {esc(submission.sample_id or "—")} · Submitted by {esc(getattr(submission.submitted_by, "username", "—"))} · {esc(fmt_dt(submission.created_at))}</p>
      <p>{esc(submission.notes or "")}</p>
      <p><a class="btn btn-secondary" href="{SITE_BASE}/experiments/{esc(submission.experiment.slug)}/">Back to experiment</a></p>
    </section>
    {"".join(sections)}
    {results_html}
    '''
    return page(f"Submission {submission.id}", body)


class Command(BaseCommand):
    help = "Export read-only static LabVault snapshot to docs/ for GitHub Pages."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="docs")
        parser.add_argument("--include-drafts", action="store_true")

    def handle(self, *args, **options):
        out = Path(settings.BASE_DIR) / options["output"]
        assets = Path(settings.BASE_DIR) / "readonly_site" / "assets"

        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

        if assets.exists():
            shutil.copytree(assets, out / "assets", dirs_exist_ok=True)

        experiments_qs = Experiment.objects.all().order_by("title")
        if not options["include_drafts"]:
            experiments_qs = experiments_qs.filter(status="active")
        experiments = list(experiments_qs)

        submissions = list(
            Submission.objects.filter(experiment__in=experiments)
            .select_related("experiment", "submitted_by")
            .prefetch_related("rows__table", "rows__values__field", "result_values__result_field")
            .order_by("-created_at")
        )

        (out / "data").mkdir(parents=True)
        exp_payload = []
        for e in experiments:
            count = sum(1 for s in submissions if s.experiment_id == e.id)
            exp_payload.append({
                "id": e.id,
                "title": e.title,
                "slug": e.slug,
                "course_or_project": e.course_or_project,
                "objective": e.objective,
                "protocol_version": e.protocol_version,
                "status": e.status,
                "submission_count": count,
            })

        (out / "data" / "experiments.json").write_text(json.dumps(exp_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / "data" / "submissions.json").write_text(json.dumps([submission_to_json(s) for s in submissions], indent=2, ensure_ascii=False), encoding="utf-8")

        cards = []
        for e in experiments:
            count = sum(1 for s in submissions if s.experiment_id == e.id)
            cards.append(f'''
            <article class="card">
              <h2>{esc(e.title)}</h2>
              <p class="muted">{esc(e.course_or_project or "No course/project")} · Protocol {esc(e.protocol_version)} · {esc(e.status)}</p>
              <p>{esc(e.objective or "")}</p>
              <p class="muted">Submissions in snapshot: {count}</p>
              <a class="btn" href="{SITE_BASE}/experiments/{esc(e.slug)}/">Open experiment</a>
            </article>''')

        index_body = f'''
        <section class="card hero">
          <h1>LabVault Read-only Snapshot</h1>
          <p>This public page is generated from the local Django database. It is read-only and does not accept logins or submissions.</p>
        </section>
        <section class="grid">{"".join(cards) if cards else "<p>No active experiments found.</p>"}</section>
        '''
        (out / "index.html").write_text(page("Home", index_body), encoding="utf-8")

        (out / "experiments").mkdir(parents=True)
        for e in experiments:
            e_dir = out / "experiments" / e.slug
            e_dir.mkdir(parents=True)
            e_subs = [s for s in submissions if s.experiment_id == e.id]
            (e_dir / "index.html").write_text(render_experiment(e, e_subs), encoding="utf-8")

        (out / "submissions").mkdir(parents=True)
        sub_rows = []
        for s in submissions:
            sub_rows.append(f'''
            <tr>
              <td>#{s.id}</td>
              <td>{esc(s.experiment.title)}</td>
              <td>{esc(s.sample_id or "—")}</td>
              <td>{esc(getattr(s.submitted_by, "username", "—"))}</td>
              <td>{esc(fmt_dt(s.created_at))}</td>
              <td><a class="btn btn-secondary" href="{SITE_BASE}/submissions/{s.id}/">Open data</a></td>
            </tr>''')
        sub_index = f'''
        <section class="card hero">
          <h1>Submissions</h1>
          <p class="muted">Read-only submissions included in this snapshot.</p>
        </section>
        <section class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Entry</th><th>Experiment</th><th>Sample / Run ID</th><th>Submitted by</th><th>Created</th><th></th></tr></thead>
              <tbody>{"".join(sub_rows)}</tbody>
            </table>
          </div>
        </section>
        '''
        (out / "submissions" / "index.html").write_text(page("Submissions", sub_index), encoding="utf-8")

        for s in submissions:
            s_dir = out / "submissions" / str(s.id)
            s_dir.mkdir(parents=True)
            (s_dir / "index.html").write_text(render_submission(s), encoding="utf-8")

        (out / ".nojekyll").write_text("", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Exported static snapshot to {out}"))
        self.stdout.write(self.style.SUCCESS(f"Experiments: {len(experiments)}"))
        self.stdout.write(self.style.SUCCESS(f"Submissions: {len(submissions)}"))
