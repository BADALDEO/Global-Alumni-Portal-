from datetime import timedelta

from django import forms

from core.forms import BootstrapFormMixin

from planner.models import Resume

from .models import ExternalApplication
from .services import FOLLOW_UP_DAYS

MAX_RESUME_MB = 5


class ExternalApplicationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ExternalApplication
        fields = [
            "company_name", "job_title", "platform", "applied_date",
            "status", "job_link", "resume_version", "resume", "follow_up_date", "notes",
        ]
        labels = {"resume_version": "Resume version used", "resume": "Or upload a file"}
        widgets = {
            "applied_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resume_version"].queryset = (
            Resume.objects.filter(user=user) if user else Resume.objects.none()
        )
        self.fields["resume_version"].required = False
        self.fields["resume_version"].empty_label = "Choose from my resume library"
        self.fields["follow_up_date"].required = False
        self.fields["follow_up_date"].help_text = (
            f"Optional. If left blank, a reminder is set {FOLLOW_UP_DAYS} days after you apply."
        )
        self.fields["job_link"].help_text = "Optional. Paste the posting URL so you can find it later."
        self.fields["resume"].help_text = "PDF, DOC or DOCX, max 5 MB. Save the version you applied with."
        self.fields["notes"].widget.attrs["placeholder"] = "Recruiter name, interview dates, salary talk..."

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if resume and hasattr(resume, "size") and resume.size > MAX_RESUME_MB * 1024 * 1024:
            raise forms.ValidationError(f"Resume must be smaller than {MAX_RESUME_MB} MB.")
        return resume

    def save(self, commit=True):
        app = super().save(commit=False)

        # attach the file of the chosen library version unless a new file was uploaded
        version = self.cleaned_data.get("resume_version")
        uploaded_new = "resume" in self.changed_data
        if version and not uploaded_new and (not app.resume or "resume_version" in self.changed_data):
            app.resume = version.file.name

        # reminders: new date resets the "done" flag; blank date gets a sensible default
        if "follow_up_date" in self.changed_data:
            app.follow_up_done = False
        if not app.follow_up_date and app.status in ("applied", "no_response"):
            app.follow_up_date = app.applied_date + timedelta(days=FOLLOW_UP_DAYS)

        if commit:
            app.save()
        return app


class QuickStatusForm(forms.Form):
    status = forms.ChoiceField(choices=ExternalApplication.Status.choices)
