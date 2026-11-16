"""CSV transport for application records, independent of the web interface."""
import csv
import io
from datetime import datetime

from .forms import ApplicationForm
from .models import Application

FIELDS = list(ApplicationForm.Meta.fields)
HEADERS = ['id', *FIELDS, 'created_at', 'updated_at']
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 1000


def spreadsheet_cell(value):
    value = str(value) if value is not None else ''
    # Prevent spreadsheet formula execution; a leading apostrophe is reversible.
    if value.startswith("'") or value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
        return "'" + value
    return value


def import_cell(value):
    if value.startswith("'") and spreadsheet_cell(value[1:]) == value:
        return value[1:]
    return value


def parse_csv(content):
    if len(content) > MAX_BYTES:
        raise ValueError('CSV files must be 5 MB or smaller.')
    try:
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''), strict=True)
        headers = reader.fieldnames
        if not headers or len(set(headers)) != len(headers):
            raise ValueError('The CSV needs unique column headings.')
        if not {'company', 'role'}.issubset(headers):
            raise ValueError('The CSV must include company and role columns. Export a CSV for a template.')
        unknown = set(headers) - set(HEADERS)
        if unknown:
            raise ValueError('Unknown columns: ' + ', '.join(sorted(unknown)))
        rows = []
        for row in reader:
            if None in row or None in row.values():
                raise ValueError(f'Row {reader.line_num} has a different number of columns than the header.')
            if not any(row.values()):
                continue
            if len(rows) >= MAX_ROWS:
                raise ValueError(f'Import at most {MAX_ROWS} applications at a time.')
            rows.append({key: import_cell(value) for key, value in row.items()})
        if not rows:
            raise ValueError('The CSV contains no application rows.')
        return rows
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError('Use a valid UTF-8 CSV file with comma-separated columns.') from exc


def prepare_rows(rows, update_existing=False):
    """Validate the whole import before saving anything. Updates require explicit IDs."""
    results = []
    seen = set()
    for number, row in enumerate(rows, start=2):
        errors = []
        instance = None
        identifier = row.get('id', '').strip()
        if identifier:
            if not identifier.isdecimal() or len(identifier) > 18:
                errors.append('ID must be a positive integer, or blank for a new application.')
            else:
                instance = Application.objects.filter(pk=int(identifier)).first()
                if instance is None:
                    errors.append('ID not found. Clear the ID to create a new application.')
        key = ('id', int(identifier)) if identifier.isdecimal() and len(identifier) <= 18 else (
            'job', row.get('company', '').strip().casefold(), row.get('role', '').strip().casefold(),
            row.get('job_url', '').strip(),
        )
        if key in seen:
            errors.append('Duplicate application within this CSV.')
        seen.add(key)
        data = {field: getattr(instance, field) if instance else '' for field in FIELDS}
        data.update({field: row[field] for field in FIELDS if field in row})
        data['status'] = data['status'] or Application.Status.SAVED
        labels = {label.casefold(): value for value, label in Application.Status.choices}
        data['status'] = labels.get(str(data['status']).casefold(), data['status'])
        for field in ['applied_on', 'follow_up_on']:
            if data[field] and isinstance(data[field], str):
                try:
                    datetime.strptime(data[field], '%Y-%m-%d')
                except ValueError:
                    errors.append(f'{field} must use YYYY-MM-DD.')
        form = ApplicationForm(data, instance=instance)
        if not form.is_valid():
            errors.extend(f'{field}: {message}' for field, messages in form.errors.items() for message in messages)
        action = 'Update' if instance and update_existing else 'Skip' if instance else 'Create'
        if not instance and not errors:
            matches = Application.objects.filter(company__iexact=data['company'], role__iexact=data['role'])
            if data['job_url']:
                matches = matches | Application.objects.filter(job_url=data['job_url'])
            if matches.exists():
                action = 'Skip'
        results.append({'number': number, 'company': row['company'], 'role': row['role'],
                        'action': action, 'errors': errors, 'form': form})
    return results
