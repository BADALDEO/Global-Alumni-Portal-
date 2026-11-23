from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Job(models.Model):
    class JobType(models.TextChoices):
        JOB = "job", "Full-time Job"
        INTERNSHIP = "internship", "Internship"

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posted_jobs"
    )
    title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=150)
    job_type = models.CharField(max_length=12, choices=JobType.choices, default=JobType.JOB)
    location = models.CharField(max_length=120, blank=True, help_text="e.g. Bengaluru, Remote")
    description = models.TextField()
    skills_required = models.CharField(max_length=300, blank=True, help_text="Comma separated")
    salary_or_stipend = models.CharField(max_length=100, blank=True)
    apply_deadline = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.company_name}"

    def get_absolute_url(self):
        return reverse("jobs:detail", args=[self.pk])

    @property
    def is_open(self):
        if not self.is_active:
            return False
        if self.apply_deadline and self.apply_deadline < timezone.localdate():
            return False
        return True

    @property
    def skills_list(self):
        return [s.strip() for s in self.skills_required.split(",") if s.strip()]


class Application(models.Model):
    """A student applying to a job posted on this portal."""

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        SHORTLISTED = "shortlisted", "Shortlisted"
        SELECTED = "selected", "Selected"
        REJECTED = "rejected", "Rejected"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portal_applications"
    )
    resume = models.FileField(
        upload_to="resumes/portal/",
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )
    cover_note = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("job", "student")
        ordering = ["-applied_at"]

    def __str__(self):
        return f"{self.student} -> {self.job}"
