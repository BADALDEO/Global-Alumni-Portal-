from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class ExternalApplication(models.Model):
    """My Job Applications: a record of an application made on ANY platform."""

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        INTERVIEW = "interview", "Interview"
        SELECTED = "selected", "Selected"
        REJECTED = "rejected", "Rejected"
        NO_RESPONSE = "no_response", "No Response"

    class Platform(models.TextChoices):
        LINKEDIN = "linkedin", "LinkedIn"
        NAUKRI = "naukri", "Naukri"
        INDEED = "indeed", "Indeed"
        COMPANY_SITE = "company_site", "Company Website"
        INTERNSHALA = "internshala", "Internshala"
        GLASSDOOR = "glassdoor", "Glassdoor"
        WELLFOUND = "wellfound", "Wellfound"
        REFERRAL = "referral", "Referral / Direct"
        PORTAL = "portal", "Global Alumni Portal"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tracked_applications"
    )
    company_name = models.CharField(max_length=150)
    job_title = models.CharField(max_length=200)
    platform = models.CharField(max_length=20, choices=Platform.choices)
    applied_date = models.DateField(default=timezone.localdate)
    resume = models.FileField(
        upload_to="resumes/tracker/",
        blank=True,
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )
    resume_version = models.ForeignKey(
        "planner.Resume", null=True, blank=True, on_delete=models.SET_NULL, related_name="applications"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.APPLIED)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_done = models.BooleanField(default=False)
    job_link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    # Set automatically when the student applies to a job posted on this portal
    portal_application = models.OneToOneField(
        "jobs.Application",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="tracker_entry",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_date", "-created_at"]

    def __str__(self):
        return f"{self.job_title} @ {self.company_name} ({self.get_platform_display()})"

    @property
    def follow_up_state(self):
        """'', 'overdue', 'today' or 'upcoming' - used to colour the reminder."""
        if self.follow_up_done or not self.follow_up_date:
            return ""
        if self.status not in ("applied", "no_response", "interview"):
            return ""
        today = timezone.localdate()
        if self.follow_up_date < today:
            return "overdue"
        if self.follow_up_date == today:
            return "today"
        return "upcoming"
