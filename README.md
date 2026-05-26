# LabVault - Web-based lab data collection system

LabVault is a Django web application for collecting, preserving, reviewing, and exporting laboratory data.

## Features

- User login
- Staff-only experiment creation
- Experiment-specific dynamic fields
- Repeated observation table per submission, with serial numbers
- Raw file upload per submission
- CSV export, one exported row per serial-numbered observation
- Admin interface
- Audit log model
- SQLite for local use; PostgreSQL-ready for deployment

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Admin:

```text
http://127.0.0.1:8000/admin/
```

## Workflow

1. Create a superuser.
2. Log in to `/admin/`.
3. Create an experiment.
4. Add `DataField` rows inline under the experiment, for example Length, Time, Voltage, Temperature.
5. Open the experiment page and click `Submit data`.
6. Enter repeated rows using the serial-numbered observation table.
7. Export data as CSV from the experiment page.

## Important database note

This package includes migration files. Therefore the normal command is enough:

```bash
python manage.py migrate
```

If you modify models later, run:

```bash
python manage.py makemigrations
python manage.py migrate
```

## CSV structure

The CSV export contains metadata plus one line per observation row:

```text
submission_id, created_at, submitted_by, sample_id, status, notes, serial_number, field_1, field_2, ...
```

## Backup

For local SQLite use, back up:

- `db.sqlite3`
- the `media/` folder

For PostgreSQL use, adapt `scripts/backup_postgres.sh` and schedule it with cron.

## Derived / calculated fields

Experiment fields can now be calculated automatically from other numeric fields.

In Django admin, add a `DataField` with:

- `field_type`: `Derived / calculated`
- `variable_name`: the name used by other formulas, e.g. `velocity`
- `calculation_formula`: the formula to compute the value, e.g. `distance / time`

Examples:

```text
velocity = distance / time
area = pi * radius**2
energy = m * g * h
angle_rad = theta * pi / 180
sine_value = sin(theta*pi/180)
r = sqrt(x**2 + y**2)
```

Supported operators/functions include `+`, `-`, `*`, `/`, `**`, `%`, parentheses, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sqrt`, `log`, `log10`, `exp`, `abs`, `round`, `min`, `max`, and constants `pi`, `e`, `tau`.

Use numeric input fields (`Integer` or `Decimal`) as formula variables. If one derived field depends on another derived field, set the dependency order first in the admin `order` column.
