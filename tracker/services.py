from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from .models import ExternalApplication

FOLLOW_UP_DAYS = 7  # default reminder after applying

# Portal application status -> tracker status
PORTAL_STATUS_MAP = {
    "applied": "applied",
    "shortlisted": "interview",
    "selected": "selected",
    "rejected": "rejected",
}


def status_summary(queryset):
    """Counts used by the tracker header, dashboard and analytics."""
    return queryset.aggregate(
        total=Count("id"),
        applied=Count("id", filter=Q(status="applied")),
        interview=Count("id", filter=Q(status="interview")),
        selected=Count("id", filter=Q(status="selected")),
        rejected=Count("id", filter=Q(status="rejected")),
        no_response=Count("id", filter=Q(status="no_response")),
        pending=Count("id", filter=Q(status__in=["applied", "no_response"])),
    )


def sync_portal_application(application):
    """Keep the student's tracker in step with an application made on this portal."""
    status = PORTAL_STATUS_MAP.get(application.status, "applied")
    applied_date = timezone.localtime(application.applied_at).date()
    entry, created = ExternalApplication.objects.get_or_create(
        portal_application=application,
        defaults={
            "user": application.student,
            "company_name": application.job.company_name,
            "job_title": application.job.title,
            "platform": ExternalApplication.Platform.PORTAL,
            "applied_date": applied_date,
            "follow_up_date": applied_date + timedelta(days=FOLLOW_UP_DAYS),
            "status": status,
            "resume": application.resume.name,
        },
    )
    if not created and entry.status != status:
        entry.status = status
        entry.save(update_fields=["status", "updated_at"])
    return entry
