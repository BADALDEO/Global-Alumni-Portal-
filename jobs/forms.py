from django import forms

from core.forms import BootstrapFormMixin

from .models import Application, Job

MAX_RESUME_MB = 5


class JobForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "title", "company_name", "job_type", "location", "description",
            "skills_required", "salary_or_stipend", "apply_deadline", "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 7}),
            "apply_deadline": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        labels = {"is_active": "Accepting applications", "salary_or_stipend": "Salary / stipend"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skills_required"].widget.attrs["placeholder"] = "Python, Django, SQL"
        self.fields["salary_or_stipend"].widget.attrs["placeholder"] = "e.g. 6-8 LPA or 15,000/month"


class ApplicationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Application
        fields = ["resume", "cover_note"]
        widgets = {"cover_note": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resume"].help_text = "PDF, DOC or DOCX, max 5 MB."
        self.fields["cover_note"].label = "Cover note (optional)"
        self.fields["cover_note"].widget.attrs["placeholder"] = "Tell them why you are a great fit..."

    def clean_resume(self):
        resume = self.cleaned_data["resume"]
        if resume.size > MAX_RESUME_MB * 1024 * 1024:
            raise forms.ValidationError(f"Resume must be smaller than {MAX_RESUME_MB} MB.")
        return resume


class ApplicationStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Application.Status.choices)
