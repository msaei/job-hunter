# Job Hunter

A personal job application workspace built with Python, Django templates, and SQLite.

## Local setup

Requires Python 3.10–3.14 and internet access to install dependencies.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver
```

Open http://127.0.0.1:8000. To use the optional Django admin, run `python manage.py createsuperuser` and visit `/admin/`.

Supports creating, editing, searching, and filtering applications, saving job descriptions, recording application and follow-up dates, and attaching application documents. AI tailoring, inbox integration, and contact research are planned.

## Attachments

Open an application and use **Add an attachment**. Choose a category (résumé, cover letter, application screenshot, confirmation email, or other) and a file. Each upload is kept separately, even when filenames match, so submitted versions are preserved.

Supported formats: PDF, HTML/HTM, DOCX, PNG, JPG/JPEG, WEBP, EML, MSG, and TXT; maximum 20 MB per file. Save confirmation emails as EML/MSG, PDF, or text before uploading. Files are downloaded rather than rendered in the browser, including HTML.

Files live in the ignored `media/` directory; metadata lives in SQLite. Back up **both** `media/` and `db.sqlite3` to preserve attachments. Removal requires checking a confirmation box and permanently deletes the attachment and its file. Downloads use application routes rather than a public media directory; the local app still has no login.

This is a local, single-user development app. Application pages do not require login. Bind the development server to localhost; authentication and production settings are required before hosting it.

## CSV import and export

The applications page provides **Export all applications (CSV)** and **Import CSV**. Export includes every application, regardless of filters, with IDs, application fields, and timestamps. CSV does not contain attachments; keep backing up `media/` separately. Excel and ZIP exports are planned.

Use an export as the import template. CSV files must be UTF-8, comma-separated, at most 5 MB and 1,000 application rows. `company` and `role` are required headers; dates use `YYYY-MM-DD`. Status accepts saved, preparing, applied, interviewing, offer, rejected, withdrawn, or their display labels. Unknown or duplicate headers and invalid rows are rejected before any changes are saved.

Upload to preview actions, then confirm to save. IDs refer to this database: known IDs are skipped by default, or updated when **Update existing applications using CSV IDs** is selected. Missing columns preserve existing values; blank cells clear them. Timestamps are exported for reference and ignored on import. To import into another database, clear the ID column first.

Rows without IDs create applications unless company and role, or a nonempty job URL, match an existing record; those matches are skipped. If two distinct openings share company and role, add them manually. Duplicate rows within a CSV must be resolved before importing. Imports never delete records or alter attachments.

Potential spreadsheet formulas and leading apostrophes are escaped with an apostrophe on export, then unescaped on re-import. Importing external CSVs uses the same convention. Exported descriptions and notes preserve commas, Unicode, quotes, and line breaks.

## Validation

```sh
python manage.py check
python manage.py test
```

Attachment tests use temporary file storage and cover upload validation, version preservation, downloads, application association, and confirmed removal.

See [architecture decisions](docs/architecture.md) for the intended direction.
