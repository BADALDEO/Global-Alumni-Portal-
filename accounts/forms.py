from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from core.forms import BootstrapFormMixin

from .models import User


def _validate_year(value):
    if value is None:
        return value
    current = timezone.localdate().year
    if value < 1950 or value > current + 8:
        raise forms.ValidationError(f"Enter a year between 1950 and {current + 8}.")
    return value


class SignupForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=User.Role.choices, widget=forms.RadioSelect, initial=User.Role.STUDENT)

    class Meta:
        model = User
        fields = (
            "username", "first_name", "last_name", "email",
            "role", "company_name", "graduation_year",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["company_name"].label = "Current company"
        self.fields["graduation_year"].label = "Graduation year"
        self.fields["password1"].help_text = "At least 8 characters. Avoid common passwords."
        self.fields["password2"].help_text = ""
        self.fields["password2"].label = "Confirm password"
        self.fields["email"].widget.attrs["autocomplete"] = "email"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_graduation_year(self):
        return _validate_year(self.cleaned_data.get("graduation_year"))

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        if role in (User.Role.ALUMNI, User.Role.COMPANY) and not cleaned.get("company_name"):
            self.add_error("company_name", "Company name is required for alumni and company accounts.")
        return cleaned


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email", "designation", "company_name",
            "graduation_year", "linkedin_url", "github_url", "leetcode_url",
            "open_to_mentorship", "bio",
        ]
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance
        self.fields["email"].required = True
        if user.is_student:
            del self.fields["designation"]
            del self.fields["company_name"]
            del self.fields["open_to_mentorship"]
            self.fields["graduation_year"].label = "Expected graduation year"
        elif user.is_company:
            for name in ("designation", "graduation_year", "github_url", "leetcode_url", "open_to_mentorship"):
                del self.fields[name]
            self.fields["company_name"].label = "Company name"
        else:
            self.fields["company_name"].label = "Current company"
            self.fields["graduation_year"].label = "Graduation year"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is used by another account.")
        return email

    def clean_graduation_year(self):
        return _validate_year(self.cleaned_data.get("graduation_year"))


class CompleteProfileForm(BootstrapFormMixin, forms.ModelForm):
    """Shown once after the first Google sign-in."""

    role = forms.ChoiceField(choices=User.Role.choices, widget=forms.RadioSelect, initial=User.Role.STUDENT)

    class Meta:
        model = User
        fields = ["role", "company_name", "graduation_year"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company_name"].label = "Current company"
        self.fields["graduation_year"].label = "Graduation year"

    def clean_graduation_year(self):
        return _validate_year(self.cleaned_data.get("graduation_year"))

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        if role in (User.Role.ALUMNI, User.Role.COMPANY) and not cleaned.get("company_name"):
            self.add_error("company_name", "Company name is required for alumni and company accounts.")
        return cleaned
