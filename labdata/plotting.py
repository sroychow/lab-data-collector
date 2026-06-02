from decimal import Decimal, InvalidOperation
from math import sqrt

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


def build_plot_data(plot_config, submission):
    rows = (
        ObservationRow.objects
        .filter(submission=submission, table=plot_config.table)
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


def linear_fit(plot_data):
    '''
    Ordinary least-squares straight-line fit: y = m*x + c.

    Returns:
        fit_result: dict with slope, intercept, r, r_squared, n
        fit_line: two points spanning min(x) to max(x), suitable for Chart.js
    '''

    points = [
        (float(point["x"]), float(point["y"]))
        for point in plot_data
        if point.get("x") is not None and point.get("y") is not None
    ]

    n = len(points)
    if n < 2:
        return None, []

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_yy = sum((y - mean_y) ** 2 for y in ys)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in points)

    if ss_xx == 0:
        return {
            "error": "Cannot fit a straight line because all x values are identical.",
            "n": n,
        }, []

    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x

    if ss_xx > 0 and ss_yy > 0:
        r = ss_xy / sqrt(ss_xx * ss_yy)
        r_squared = r ** 2
    else:
        r = None
        r_squared = None

    x_min = min(xs)
    x_max = max(xs)

    fit_line = [
        {"x": x_min, "y": slope * x_min + intercept},
        {"x": x_max, "y": slope * x_max + intercept},
    ]

    fit_result = {
        "fit_type": "linear",
        "equation": "y = m x + c",
        "slope": slope,
        "intercept": intercept,
        "r": r,
        "r_squared": r_squared,
        "n": n,
    }

    return fit_result, fit_line


def build_fit(plot_config, plot_data):
    if getattr(plot_config, "fit_type", "none") == "linear":
        return linear_fit(plot_data)

    return None, []
