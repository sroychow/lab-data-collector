from decimal import Decimal, InvalidOperation


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


def build_plot_data(plot_config, submission):
    """
    Build x-y data for one submitted lab entry.

    The admin defines PlotConfig once for the experiment.
    This function filters the plotted data to one submission only.
    """

    rows = (
        submission.rows
        .prefetch_related("values", "values__field")
        .order_by("serial_number", "id")
    )

    data = []

    for row in rows:
        values_by_field_id = {
            field_value.field_id: field_value.value
            for field_value in row.values.all()
        }

        x_raw = values_by_field_id.get(plot_config.x_field_id)
        y_raw = values_by_field_id.get(plot_config.y_field_id)

        x_value = _to_float(x_raw)
        y_value = _to_float(y_raw)

        if x_value is None or y_value is None:
            continue

        data.append({
            "serial_number": row.serial_number,
            "x": x_value,
            "y": y_value,
        })

    return data
