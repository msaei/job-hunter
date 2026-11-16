import tempfile
import csv
import io
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Application, Attachment


class AttachmentTests(TestCase):
    def setUp(self):
        temporary_media = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_media.cleanup)
        settings = override_settings(MEDIA_ROOT=temporary_media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.application = Application.objects.create(company='Example', role='Engineer')
        self.upload_url = reverse('applications:upload_attachment', args=[self.application.pk])

    def upload(self, name='resume.pdf', content=b'%PDF-1.4 example'):
        return self.client.post(self.upload_url, {
            'kind': Attachment.Kind.RESUME,
            'file': SimpleUploadedFile(name, content),
        })

    def test_upload_list_and_download_preserve_exact_bytes(self):
        response = self.upload()
        self.assertRedirects(response, self.application.get_absolute_url())
        attachment = Attachment.objects.get()
        self.assertEqual(attachment.application, self.application)
        self.assertEqual(attachment.original_name, 'resume.pdf')
        self.assertNotEqual(Path(attachment.file.name).name, 'resume.pdf')
        self.assertContains(self.client.get(self.application.get_absolute_url()), 'resume.pdf')
        response = self.client.get(reverse('applications:download_attachment', args=[self.application.pk, attachment.pk]))
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 example')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        response.close()

    def test_invalid_uploads_do_not_save_files(self):
        for name, content in [('script.exe', b'bad'), ('large.pdf', b'x' * (20 * 1024 * 1024 + 1))]:
            with self.subTest(name=name):
                self.assertEqual(self.upload(name, content).status_code, 400)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_same_filename_keeps_both_versions(self):
        self.upload()
        self.upload(content=b'another version')
        names = list(Attachment.objects.values_list('file', flat=True))
        self.assertEqual(len(set(names)), 2)

    def test_attachment_cannot_be_accessed_through_another_application(self):
        self.upload()
        attachment = Attachment.objects.get()
        other = Application.objects.create(company='Other', role='Engineer')
        for action in ['download_attachment', 'remove_attachment']:
            url = reverse(f'applications:{action}', args=[other.pk, attachment.pk])
            response = self.client.post(url, {'confirm': 'on'}) if action == 'remove_attachment' else self.client.get(url)
            self.assertEqual(response.status_code, 404)
        self.assertEqual(Attachment.objects.count(), 1)

    def test_removal_requires_post_and_confirmation_and_deletes_file(self):
        self.upload()
        attachment = Attachment.objects.get()
        path = Path(attachment.file.path)
        url = reverse('applications:remove_attachment', args=[self.application.pk, attachment.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertTrue(path.exists())
        self.assertEqual(Attachment.objects.count(), 1)
        self.assertRedirects(self.client.post(url, {'confirm': 'on'}), self.application.get_absolute_url())
        self.assertFalse(path.exists())
        self.assertFalse(Attachment.objects.exists())


class CSVTests(TestCase):
    def setUp(self):
        self.application = Application.objects.create(
            company='Café, Inc.', role='AI Engineer', description='First line\nSecond, "quoted" line',
            notes='=HYPERLINK("https://example.com")', applied_on='2026-11-14', status='applied',
        )
        self.url = reverse('applications:import_csv')

    def preview(self, text, update=False):
        return self.client.post(self.url, {
            'file': SimpleUploadedFile('applications.csv', text.encode('utf-8')),
            **({'update_existing': 'on'} if update else {}),
        })

    def confirm(self):
        return self.client.post(self.url, {'action': 'confirm'})

    def test_export_all_rows_unicode_multiline_and_formula_protection(self):
        response = self.client.get(reverse('applications:export_csv'), {'q': 'no match'})
        self.assertIn('attachment;', response['Content-Disposition'])
        records = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['company'], self.application.company)
        self.assertEqual(records[0]['description'], self.application.description)
        self.assertEqual(records[0]['notes'], "'" + self.application.notes)
        self.assertEqual(records[0]['applied_on'], '2026-11-14')

    def test_round_trip_updates_only_when_selected(self):
        exported = self.client.get(reverse('applications:export_csv')).content.decode('utf-8-sig')
        self.application.company = 'Changed'
        self.application.save()
        self.assertContains(self.preview(exported), 'Skip')
        self.confirm()
        self.application.refresh_from_db()
        self.assertEqual(self.application.company, 'Changed')
        self.assertContains(self.preview(exported, update=True), 'Update')
        self.confirm()
        self.application.refresh_from_db()
        self.assertEqual(self.application.company, 'Café, Inc.')
        self.assertEqual(self.application.notes, '=HYPERLINK("https://example.com")')
        self.assertEqual(Application.objects.count(), 1)

    def test_preview_required_then_create_and_repeat_skips(self):
        text = 'company,role,status,applied_on\nNew Company,Developer,Applied,2026-11-14\n'
        self.preview(text)
        self.assertEqual(Application.objects.count(), 1)
        self.confirm()
        self.assertEqual(Application.objects.get(company='New Company').status, 'applied')
        self.preview(text)
        self.confirm()
        self.assertEqual(Application.objects.count(), 2)
        self.assertContains(self.confirm(), 'preview expired')

    def test_invalid_rows_prevent_entire_import(self):
        response = self.preview('company,role,applied_on\nValid,Engineer,2026-11-14\nInvalid,Engineer,tomorrow\n')
        self.assertContains(response, 'YYYY-MM-DD')
        self.assertNotIn('csv_import', self.client.session)
        self.confirm()
        self.assertEqual(Application.objects.count(), 1)

    def test_bad_csv_and_unknown_ids_rejected(self):
        for text in [
            'company,company,role\na,b,c', 'company\nExample',
            'company,role\na,b,c', 'company,role,unknown\na,b,c',
            'id,company,role\n999999,Example,Engineer',
            'company,role\nSame,Engineer\nSame,Engineer',
        ]:
            with self.subTest(text=text):
                self.preview(text)
                self.assertNotIn('csv_import', self.client.session)

    def test_missing_columns_preserved_and_present_blank_cells_cleared(self):
        self.preview(f'id,company,role,notes\n{self.application.pk},Updated,Engineer,\n', update=True)
        self.confirm()
        self.application.refresh_from_db()
        self.assertEqual(self.application.notes, '')
        self.assertEqual(self.application.description, 'First line\nSecond, "quoted" line')
        self.assertEqual(self.application.status, 'applied')

    def test_confirm_revalidates_deleted_records(self):
        self.preview(f'id,company,role\n{self.application.pk},Updated,Engineer', update=True)
        self.application.delete()
        self.assertContains(self.confirm(), 'ID not found')
        self.assertFalse(Application.objects.exists())

    def test_limits_and_csrf(self):
        from .csv_io import parse_csv
        from django.test import Client
        for content in [b'x' * (5 * 1024 * 1024 + 1), b'company,role\n' + b'Example,Engineer\n' * 1001]:
            with self.assertRaises(ValueError):
                parse_csv(content)
        self.assertEqual(Client(enforce_csrf_checks=True).post(self.url, {'action': 'confirm'}).status_code, 403)
