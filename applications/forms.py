from django import forms
from pathlib import Path
from .models import Application, Attachment


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['company', 'role', 'job_url', 'location', 'description', 'status',
                  'applied_on', 'next_action', 'follow_up_on', 'notes']
        widgets = {
            'applied_on': forms.DateInput(attrs={'type': 'date'}),
            'follow_up_on': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 8}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['kind', 'file']
        help_texts = {'file': 'Up to 20 MB. PDF, HTML, DOCX, PNG, JPG, WEBP, EML, MSG, or TXT.'}

    def clean_file(self):
        file = self.cleaned_data['file']
        if file.size > 20 * 1024 * 1024:
            raise forms.ValidationError('Choose a file smaller than or equal to 20 MB.')
        if Path(file.name).suffix.lower() not in {
            '.pdf', '.html', '.htm', '.docx', '.png', '.jpg', '.jpeg', '.webp', '.eml', '.msg', '.txt',
        }:
            raise forms.ValidationError('This file type is not supported.')
        return file
