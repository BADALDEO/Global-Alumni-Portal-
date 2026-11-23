from django import forms
from django.utils import timezone

from accounts.models import User
from core.forms import BootstrapFormMixin

from .models import NetworkingActivity, Resume, SearchGoal

MAX_RESUME_MB = 5


class ResumeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Resume
        fields = ["title", "version", "target_role", "file", "notes", "is_default"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
        labels = {"file": "Resume file", "is_default": "Use as my default resume"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs["placeholder"] = "Backend developer resume"
        self.fields["version"].widget.attrs["placeholder"] = "v2"
        self.fields["target_role"].widget.attrs["placeholder"] = "Python / Django developer"
        self.fields["notes"].widget.attrs["placeholder"] = "Added my FoodShare project, shortened the summary..."
        self.fields["file"].help_text = "PDF, DOC or DOCX, max 5 MB."

    def clean_file(self):
        upload = self.cleaned_data.get("file")
        if upload and hasattr(upload, "size") and upload.size > MAX_RESUME_MB * 1024 * 1024:
            raise forms.ValidationError(f"Resume must be smaller than {MAX_RESUME_MB} MB.")
        return upload


class GoalForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SearchGoal
        fields = ["daily_application_target", "daily_networking_target", "active_days_per_week"]
        labels = {
            "daily_application_target": "Job applications per day",
            "daily_networking_target": "Networking actions per day",
            "active_days_per_week": "Active days per week",
        }
        widgets = {
            "daily_application_target": forms.NumberInput(attrs={"min": 1, "max": 30}),
            "daily_networking_target": forms.NumberInput(attrs={"min": 0, "max": 30}),
            "active_days_per_week": forms.NumberInput(attrs={"min": 1, "max": 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["daily_application_target"].help_text = "Most students aim for 5 to 7 relevant applications a day."
        self.fields["active_days_per_week"].help_text = "Weekly target = daily target x active days."


class NetworkingForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = NetworkingActivity
        fields = [
            "platform", "activity", "contact_name", "contact_role", "profile_url",
            "alumni", "is_alumni", "date", "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {"alumni": "Link an alumnus from this portal (optional)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["alumni"]
        field.queryset = User.objects.filter(role=User.Role.ALUMNI).order_by("first_name", "username")
        field.label_from_instance = lambda u: f"{u.display_name} - {u.company_name or 'Alumni'}"
        field.empty_label = "Not from the portal"
        field.required = False
        self.fields["contact_name"].required = False
        self.fields["contact_name"].widget.attrs["placeholder"] = "Person's name"
        self.fields["notes"].widget.attrs["placeholder"] = "What did you talk about? Next step?"

    def clean_date(self):
        value = self.cleaned_data["date"]
        if value > timezone.localdate():
            raise forms.ValidationError("The date cannot be in the future.")
        return value

    def clean(self):
        cleaned = super().clean()
        alumni = cleaned.get("alumni")
        platform = cleaned.get("platform")
        if alumni:
            cleaned["is_alumni"] = True
            if not cleaned.get("contact_name"):
                cleaned["contact_name"] = alumni.display_name
            if not cleaned.get("contact_role"):
                role = " at ".join(x for x in (alumni.designation, alumni.company_name) if x)
                cleaned["contact_role"] = role
            if not cleaned.get("profile_url"):
                link = {
                    "linkedin": alumni.linkedin_url,
                    "github": alumni.github_url,
                    "leetcode": alumni.leetcode_url,
                }.get(platform, "")
                cleaned["profile_url"] = link
        if not cleaned.get("contact_name"):
            self.add_error("contact_name", "Enter the person's name or link an alumnus.")
        return cleaned
