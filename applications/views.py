from django.db.models import Q
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.http import FileResponse, Http404, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods, require_GET
from django.utils import timezone
import csv
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import ApplicationForm, AttachmentForm, AppliedDateFilterForm
from .models import Application, Attachment
from .csv_io import HEADERS, MAX_BYTES, parse_csv, prepare_rows, spreadsheet_cell


class ApplicationList(ListView):
    model = Application
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        self.date_filter = AppliedDateFilterForm(self.request.GET)
        if not self.date_filter.is_valid():
            return queryset.none()
        start = self.date_filter.cleaned_data.get('applied_from')
        end = self.date_filter.cleaned_data.get('applied_through')
        if start:
            queryset = queryset.filter(applied_on__gte=start)
        if end:
            queryset = queryset.filter(applied_on__lte=end)
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(company__icontains=query) | Q(role__icontains=query))
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        params = self.request.GET.copy()
        params.pop('page', None)
        return super().get_context_data(
            **kwargs, statuses=Application.Status.choices,
            date_filter=self.date_filter, filter_query=params.urlencode(),
        )


class ApplicationDetail(DetailView):
    model = Application

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, attachment_form=AttachmentForm())


class ApplicationCreate(CreateView):
    model = Application
    form_class = ApplicationForm


class ApplicationUpdate(UpdateView):
    model = Application
    form_class = ApplicationForm


@require_POST
def upload_attachment(request, pk):
    application = get_object_or_404(Application, pk=pk)
    form = AttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.application = application
        attachment.original_name = form.cleaned_data['file'].name
        attachment.save()
        return redirect(application)
    return render(request, 'applications/application_detail.html', {
        'object': application, 'attachment_form': form,
    }, status=400)


def download_attachment(request, pk, attachment_pk):
    attachment = get_object_or_404(Attachment, pk=attachment_pk, application_id=pk)
    try:
        file = attachment.file.open('rb')
    except FileNotFoundError:
        raise Http404('This file is no longer available.')
    response = FileResponse(file, as_attachment=True, filename=attachment.original_name,
                            content_type='application/octet-stream')
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@require_POST
def remove_attachment(request, pk, attachment_pk):
    attachment = get_object_or_404(Attachment, pk=attachment_pk, application_id=pk)
    if request.POST.get('confirm') != 'on':
        return redirect('applications:detail', pk=pk)
    attachment.file.delete(save=False)
    attachment.delete()
    return redirect('applications:detail', pk=pk)


@require_GET
def export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="applications-{timezone.localdate()}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(HEADERS)
    for application in Application.objects.order_by('pk').iterator():
        writer.writerow([spreadsheet_cell(getattr(application, field)) for field in HEADERS])
    return response


@require_http_methods(['GET', 'POST'])
def import_csv(request):
    context = {}
    if request.method == 'POST':
        if request.POST.get('action') == 'confirm':
            pending = request.session.get('csv_import')
            if not pending:
                context['error'] = 'Your preview expired. Upload the CSV again.'
            else:
                with transaction.atomic():
                    results = prepare_rows(pending['rows'], pending['update'])
                    if any(result['errors'] for result in results):
                        context.update(results=results, error='The data changed. Fix these errors and upload again.')
                    else:
                        counts = {'Create': 0, 'Update': 0, 'Skip': 0}
                        for result in results:
                            counts[result['action']] += 1
                            if result['action'] != 'Skip':
                                result['form'].save()
                        del request.session['csv_import']
                        messages.success(request, f"Imported: {counts['Create']} created, {counts['Update']} updated, {counts['Skip']} skipped.")
                        return redirect('applications:list')
        else:
            request.session.pop('csv_import', None)
            upload = request.FILES.get('file')
            try:
                if upload is None:
                    raise ValueError('Choose a CSV file.')
                rows = parse_csv(upload.read(MAX_BYTES + 1))
                update = request.POST.get('update_existing') == 'on'
                results = prepare_rows(rows, update)
                valid = not any(result['errors'] for result in results)
                context.update(results=results, can_confirm=valid, update_existing=update)
                if valid:
                    request.session['csv_import'] = {'rows': rows, 'update': update}
                else:
                    context['error'] = 'Nothing has been imported. Fix the errors below and upload again.'
            except ValueError as exc:
                context['error'] = str(exc)
    return render(request, 'applications/import_csv.html', context)
