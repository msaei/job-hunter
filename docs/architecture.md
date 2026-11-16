# Initial architecture decisions

## Agreed direction

Python and Django, starting with a personal tool. The owner reviews technology decisions; public-product architecture will be revisited later.

## Initial implementation choices

- Django 5.2 LTS: an established supported release compatible with the installed Python 3.14.
- Django templates and ordinary forms: keep the initial interface in one Python application.
- SQLite: local development without a database service. Revisit PostgreSQL when deployment or concurrency requires it.
- Django ORM and migrations: use Django's native data layer.

These implementation choices are reversible. No AI vendor, frontend framework, cloud host, or agent framework has been selected.

## Next increments

1. Verify the core tracker locally and refine its fields against real applications.
2. Attachments implemented locally: submitted résumé, cover letter, confirmation email, and screenshot; add authentication before deployment.
3. Import the master résumé from HTML into verified structured facts, retaining the original PDF as a visual reference.
4. Add a hosted-model tailoring experiment with structured proposals, supporting source facts, manual review, and HTML-to-PDF export.
5. Record prompt/model versions, latency, cost, and user edits. Evaluate factual accuracy and relevance using representative job descriptions.
6. Add sourced contact research and outreach drafts; then job discovery and matching.

Treat job descriptions and retrieved pages as untrusted input. Any later AI tools must use explicit permissions and must not send messages or submit applications without the owner's review.

Avoid adding orchestration services until a concrete workflow needs them. Keep model calls behind a small interface so a local model can later be evaluated against the same examples.
