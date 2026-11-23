from django import forms

from accounts.models import User
from core.forms import BootstrapFormMixin
from jobs.models import Job
from tracker.models import ExternalApplication

from .models import ReferralRequest

MAX_RESUME_MB = 5


class ReferralRequestForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ReferralRequest
        fields = [
            "alumni", "job", "external_application",
            "company_name", "job_title", "job_link", "message", "resume",
        ]
        widgets = {"message": forms.Textarea(attrs={"rows": 6})}
        labels = {
            "alumni": "Ask which alumnus?",
            "job": "Job on this portal (optional)",
            "external_application": "From my tracked applications (optional)",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        alumni_field = self.fields["alumni"]
        alumni_field.queryset = User.objects.filter(role=User.Role.ALUMNI).order_by("first_name", "username")
        alumni_field.label_from_instance = lambda u: f"{u.display_name} - {u.company_name or 'Alumni'}"
        alumni_field.empty_label = "Select an alumnus"

        self.fields["job"].queryset = Job.objects.filter(is_active=True).order_by("-created_at")
        self.fields["job"].required = False
        self.fields["job"].empty_label = "None"

        self.fields["external_application"].queryset = (
            ExternalApplication.objects.filter(user=user) if user else ExternalApplication.objects.none()
        )
        self.fields["external_application"].required = False
        self.fields["external_application"].empty_label = "None"

        # filled from the linked job or application when left empty
        self.fields["company_name"].required = False
        self.fields["job_title"].required = False

        self.fields["job_link"].required = False
        self.fields["message"].widget.attrs["placeholder"] = (
            "Introduce yourself, mention your skills and explain why you are a good fit for this role."
        )
        self.fields["resume"].required = False
        self.fields["resume"].help_text = (
            "Optional. If you skip this, the resume saved with your tracked application is used."
        )

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if resume and hasattr(resume, "size") and resume.size > MAX_RESUME_MB * 1024 * 1024:
            raise forms.ValidationError(f"Resume must be smaller than {MAX_RESUME_MB} MB.")
        return resume

    def clean(self):
        cleaned = super().clean()
        job = cleaned.get("job")
        tracked = cleaned.get("external_application")

        for source in (tracked, job):
            if not source:
                continue
            if not cleaned.get("company_name"):
                cleaned["company_name"] = source.company_name
            if not cleaned.get("job_title"):
                cleaned["job_title"] = source.title if source is job else source.job_title
            if tracked is source and not cleaned.get("job_link") and source.job_link:
                cleaned["job_link"] = source.job_link

        if not cleaned.get("company_name"):
            self.add_error("company_name", "Enter the company or pick a job above.")
        if not cleaned.get("job_title"):
            self.add_error("job_title", "Enter the job title or pick a job above.")

        alumni = cleaned.get("alumni")
        if alumni and self.user and cleaned.get("company_name") and cleaned.get("job_title"):
            exists = ReferralRequest.objects.filter(
                student=self.user,
                alumni=alumni,
                status=ReferralRequest.Status.PENDING,
                company_name__iexact=cleaned["company_name"],
                job_title__iexact=cleaned["job_title"],
            ).exists()
            if exists:
                raise forms.ValidationError(
                    "You already have a pending request to this alumnus for the same role."
                )
        return cleaned


class ReferralResponseForm(forms.Form):
    decision = forms.ChoiceField(choices=[("accept", "Accept"), ("reject", "Decline")])
    reply = forms.CharField(required=False, max_length=1000)
