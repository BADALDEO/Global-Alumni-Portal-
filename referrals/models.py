from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


class ReferralRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_requests"
    )
    alumni = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_received"
    )
    # The role the referral is for. Link it to a portal job or a tracked application,
    # or just type the company and title.
    job = models.ForeignKey("jobs.Job", null=True, blank=True, on_delete=models.SET_NULL, related_name="referral_requests")
    external_application = models.ForeignKey(
        "tracker.ExternalApplication", null=True, blank=True, on_delete=models.SET_NULL, related_name="referral_requests"
    )
    company_name = models.CharField(max_length=150)
    job_title = models.CharField(max_length=200)
    job_link = models.URLField(blank=True)

    message = models.TextField()
    resume = models.FileField(
        upload_to="resumes/referrals/",
        blank=True,
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    alumni_reply = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} -> {self.alumni}: {self.job_title} @ {self.company_name}"

    def linked_application_status(self):
        """Status of the student's application for this role, if we can find it: (value, label) or None."""
        if self.external_application_id:
            app = self.external_application
            return app.status, app.get_status_display()
        if self.job_id:
            app = self.job.applications.filter(student_id=self.student_id).first()
            if app:
                return app.status, app.get_status_display()
        return None
