from decimal import Decimal, InvalidOperation

from .models import ObservationRow


def _to_float(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(",", ".")

    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def build_plot_data(plot_config, submission=None):
    """
    Build x-y plot data for a PlotConfig.

    If submission is provided, only rows belonging to that submission are used.
    This is the desired behavior for per-lab-entry plots.

    If submission is None, rows from all submissions for that table are used.
    """

    rows = (
        ObservationRow.objects
        .filter(table=plot_config.table)
        .select_related("submission")
        .prefetch_related("values", "values__field")
        .order_by("serial_number", "id")
    )

    if submission is not None:
        rows = rows.filter(submission=submission)

    data = []

    for row in rows:
        values_by_field_id = {
            value.field_id: value.value
            for value in row.values.all()
        }

        x_raw = values_by_field_id.get(plot_config.x_field_id)
        y_raw = values_by_field_id.get(plot_config.y_field_id)

        x = _to_float(x_raw)
        y = _to_float(y_raw)

        if x is None or y is None:
            continue

        data.append({
            "serial_number": row.serial_number,
            "submission_id": row.submission_id,
            "x": x,
            "y": y,
        })

    return data
