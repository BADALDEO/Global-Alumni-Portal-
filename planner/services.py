from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from referrals.models import ReferralRequest
from tracker.models import ExternalApplication
from tracker.services import status_summary

from .models import NetworkingActivity, SearchGoal

FOLLOWUP_STATUSES = ("applied", "no_response", "interview")
OUTREACH_ACTIVITIES = ("connect", "connected", "message", "meeting")


def week_start(day):
    return day - timedelta(days=day.weekday())  # Monday


def _pct(part, whole):
    if not whole:
        return 0
    return min(100, round(part * 100 / whole))


def _day_counts(queryset, field, start, end):
    rows = (
        queryset.filter(**{f"{field}__range": (start, end)})
        .values(field)
        .annotate(c=Count("id"))
        .order_by(field)
    )
    return {row[field]: row["c"] for row in rows}


def followups_due(user, today=None):
    today = today or timezone.localdate()
    return ExternalApplication.objects.filter(
        user=user, follow_up_done=False, follow_up_date__isnull=False,
        follow_up_date__lte=today, status__in=FOLLOWUP_STATUSES,
    ).order_by("follow_up_date")


def followups_upcoming(user, days=14, today=None):
    today = today or timezone.localdate()
    return ExternalApplication.objects.filter(
        user=user, follow_up_done=False, follow_up_date__gt=today,
        follow_up_date__lte=today + timedelta(days=days), status__in=FOLLOWUP_STATUSES,
    ).order_by("follow_up_date")


def today_progress(user):
    today = timezone.localdate()
    goal = SearchGoal.for_user(user)
    apps = ExternalApplication.objects.filter(user=user, applied_date=today).count()
    network = NetworkingActivity.objects.filter(user=user, date=today).count()
    app_target = goal.daily_application_target
    net_target = goal.daily_networking_target
    return {
        "goal": goal,
        "apps": apps,
        "app_target": app_target,
        "app_pct": _pct(apps, app_target),
        "app_remaining": max(0, app_target - apps),
        "app_done": apps >= app_target,
        "network": network,
        "net_target": net_target,
        "net_enabled": net_target > 0,
        "net_pct": _pct(network, net_target),
        "net_remaining": max(0, net_target - network),
        "net_done": net_target > 0 and network >= net_target,
    }


def application_streak(user, target):
    """Days in a row the application target was met, counting back from today (or yesterday)."""
    today = timezone.localdate()
    start = today - timedelta(days=120)
    counts = _day_counts(ExternalApplication.objects.filter(user=user), "applied_date", start, today)
    day = today
    if counts.get(day, 0) < target:
        day -= timedelta(days=1)
    streak = 0
    while day >= start and counts.get(day, 0) >= target:
        streak += 1
        day -= timedelta(days=1)
    return streak


def daily_series(user, days=14):
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    goal = SearchGoal.for_user(user)
    apps = _day_counts(ExternalApplication.objects.filter(user=user), "applied_date", start, today)
    network = _day_counts(NetworkingActivity.objects.filter(user=user), "date", start, today)
    dates = [start + timedelta(days=i) for i in range(days)]
    return {
        "labels": [d.strftime("%d %b") for d in dates],
        "applications": [apps.get(d, 0) for d in dates],
        "networking": [network.get(d, 0) for d in dates],
        "target": goal.daily_application_target,
    }


def current_week_series(user):
    today = timezone.localdate()
    monday = week_start(today)
    goal = SearchGoal.for_user(user)
    apps = _day_counts(ExternalApplication.objects.filter(user=user), "applied_date", monday, today)
    dates = [monday + timedelta(days=i) for i in range(7)]
    return {
        "labels": [d.strftime("%a %d") for d in dates],
        "applications": [apps.get(d, 0) if d <= today else 0 for d in dates],
        "target": goal.daily_application_target,
    }


def weekly_report(user, weeks=8):
    today = timezone.localdate()
    goal = SearchGoal.for_user(user)
    this_monday = week_start(today)
    rows = []
    for i in range(weeks):
        start = this_monday - timedelta(days=7 * i)
        end = start + timedelta(days=6)
        week_apps = ExternalApplication.objects.filter(user=user, applied_date__range=(start, end))
        stats = week_apps.aggregate(
            total=Count("id"),
            interviews=Count("id", filter=Q(status="interview")),
            selected=Count("id", filter=Q(status="selected")),
            rejected=Count("id", filter=Q(status="rejected")),
        )
        network = NetworkingActivity.objects.filter(user=user, date__range=(start, end)).count()
        target = goal.weekly_application_target
        rows.append({
            "start": start,
            "end": end,
            "current": i == 0,
            "applications": stats["total"],
            "interviews": stats["interviews"],
            "selected": stats["selected"],
            "rejected": stats["rejected"],
            "networking": network,
            "target": target,
            "pct": _pct(stats["total"], target),
            "net_target": goal.weekly_networking_target,
        })
    return rows


def dashboard_stats(user):
    today = timezone.localdate()
    monday = week_start(today)
    tracked = ExternalApplication.objects.filter(user=user)
    totals = status_summary(tracked)

    contacts = (
        NetworkingActivity.objects.filter(user=user, is_alumni=True, activity__in=OUTREACH_ACTIVITIES)
        .values("contact_name").distinct().count()
    )
    return {
        "total_applied": totals["total"],
        "today": tracked.filter(applied_date=today).count(),
        "week": tracked.filter(applied_date__range=(monday, today)).count(),
        "alumni_connections": contacts,
        "referral_requests": ReferralRequest.objects.filter(student=user).count(),
        "interviews": totals["interview"],
        "selected": totals["selected"],
        "rejected": totals["rejected"],
        "pending": totals["pending"],
        "followups_due": followups_due(user, today).count(),
        "followups_upcoming": followups_upcoming(user, 14, today).count(),
        "networking_total": NetworkingActivity.objects.filter(user=user).count(),
    }


def resume_stats(user):
    from .models import Resume

    return Resume.objects.filter(user=user).annotate(
        app_count=Count("applications"),
        interview_count=Count("applications", filter=Q(applications__status="interview")),
        selected_count=Count("applications", filter=Q(applications__status="selected")),
        rejected_count=Count("applications", filter=Q(applications__status="rejected")),
    )
