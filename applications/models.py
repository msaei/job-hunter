from django.db import models
from django.urls import reverse
from pathlib import Path
from uuid import uuid4


def attachment_path(instance, filename):
    return f'applications/{instance.application_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


class Application(models.Model):
    class Status(models.TextChoices):
        SAVED = 'saved', 'Saved'
        PREPARING = 'preparing', 'Preparing'
        APPLIED = 'applied', 'Applied'
        INTERVIEWING = 'interviewing', 'Interviewing'
        OFFER = 'offer', 'Offer'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    company = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    job_url = models.URLField(max_length=2000, blank=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SAVED)
    applied_on = models.DateField(null=True, blank=True)
    next_action = models.CharField(max_length=300, blank=True)
    follow_up_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.role} at {self.company}'

    def get_absolute_url(self):
        return reverse('applications:detail', args=[self.pk])


class Attachment(models.Model):
    class Kind(models.TextChoices):
        RESUME = 'resume', 'Résumé'
        COVER_LETTER = 'cover_letter', 'Cover letter'
        SCREENSHOT = 'screenshot', 'Application screenshot'
        CONFIRMATION = 'confirmation', 'Confirmation email'
        OTHER = 'other', 'Other'

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='attachments')
    kind = models.CharField(max_length=20, choices=Kind.choices)
    file = models.FileField(upload_to=attachment_path, max_length=300)
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at', '-pk']
