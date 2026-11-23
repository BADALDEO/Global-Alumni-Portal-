from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from core.files import serve_file
from tracker.models import ExternalApplication

from .forms import GoalForm, NetworkingForm, ResumeForm
from .models import NetworkingActivity, Resume, SearchGoal
from .services import (
    FOLLOWUP_STATUSES, application_streak, current_week_series, daily_series, dashboard_stats,
    followups_due, followups_upcoming, resume_stats, today_progress, week_start, weekly_report,
)

candidate_only = role_required("student", "alumni")

PLATFORM_CARDS = [
    ("linkedin", "bi-linkedin", "Connect with alumni and recruiters"),
    ("github", "bi-github", "Explore developers' projects and connect"),
    ("leetcode", "bi-code-slash", "Connect with the coding community"),
    ("college", "bi-bank", "Reach out to seniors and alumni"),
]


def _safe_next(request, default):
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return default


# ------------------------------------------------------------------ overview
@candidate_only
def overview(request):
    user = request.user
    progress = today_progress(user)
    stats = dashboard_stats(user)
    chart = {"daily": daily_series(user, 14), "week": current_week_series(user)}
    week_target = progress["goal"].weekly_application_target
    week_pct = min(100, round(stats["week"] * 100 / week_target)) if week_target else 0
    return render(request, "planner/dashboard.html", {
        "active": "overview",
        "week_pct": week_pct,
        "progress": progress,
        "stats": stats,
        "streak": application_streak(user, progress["app_target"]),
        "followups": followups_due(user)[:5],
        "recent_networking": NetworkingActivity.objects.filter(user=user)[:5],
        "resumes": resume_stats(user)[:4],
        "week_target": week_target,
        "chart": chart,
    })


# ------------------------------------------------------------------ resumes
@candidate_only
def resume_list(request):
    resumes = resume_stats(request.user)
    usage = (
        ExternalApplication.objects.filter(user=request.user)
        .select_related("resume_version")
        .order_by("-applied_date", "-created_at")[:25]
    )
    return render(request, "planner/resume_list.html", {"active": "resumes", "resumes": resumes, "usage": usage})


@candidate_only
def resume_create(request):
    form = ResumeForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        resume = form.save(commit=False)
        resume.user = request.user
        if not Resume.objects.filter(user=request.user).exists():
            resume.is_default = True
        resume.save()
        messages.success(request, "Resume version saved to your library.")
        return redirect("planner:resumes")
    return render(request, "planner/resume_form.html", {"active": "resumes", "form": form, "heading": "Add a resume version"})


@candidate_only
def resume_edit(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    form = ResumeForm(request.POST or None, request.FILES or None, instance=resume)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Resume details updated.")
        return redirect("planner:resumes")
    return render(request, "planner/resume_form.html", {"active": "resumes", "form": form, "heading": "Edit resume version"})


@candidate_only
@require_POST
def resume_delete(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    resume.delete()
    messages.success(request, "Resume removed from your library. Past applications keep their saved copy.")
    return redirect("planner:resumes")


@candidate_only
@require_POST
def resume_default(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    resume.is_default = True
    resume.save()
    messages.success(request, f"{resume.label} is now your default resume.")
    return redirect("planner:resumes")


@candidate_only
def resume_file(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    return serve_file(resume.file)


# ------------------------------------------------------------------ networking
@candidate_only
def networking_list(request):
    user = request.user
    base = NetworkingActivity.objects.filter(user=user).select_related("alumni")
    monday = week_start(timezone.localdate())

    summary_rows = (
        base.values("platform")
        .annotate(total=Count("id"), week=Count("id", filter=Q(date__gte=monday)))
        .order_by("platform")
    )
    summary = {row["platform"]: row for row in summary_rows}
    cards = []
    for key, icon, hint in PLATFORM_CARDS:
        row = summary.get(key, {})
        cards.append({
            "key": key, "label": dict(NetworkingActivity.Platform.choices)[key], "icon": icon,
            "hint": hint, "total": row.get("total", 0), "week": row.get("week", 0),
        })

    platform = request.GET.get("platform", "")
    activity = request.GET.get("activity", "")
    q = request.GET.get("q", "").strip()
    items = base
    if platform in dict(NetworkingActivity.Platform.choices):
        items = items.filter(platform=platform)
    if activity in dict(NetworkingActivity.Activity.choices):
        items = items.filter(activity=activity)
    if q:
        items = items.filter(Q(contact_name__icontains=q) | Q(contact_role__icontains=q) | Q(notes__icontains=q))

    page_obj = Paginator(items, 15).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "planner/networking_list.html", {
        "active": "networking",
        "cards": cards,
        "page_obj": page_obj,
        "platform": platform,
        "activity": activity,
        "q": q,
        "platform_choices": NetworkingActivity.Platform.choices,
        "activity_choices": NetworkingActivity.Activity.choices,
        "querystring": params.urlencode(),
        "total": base.count(),
        "has_any": base.exists(),
        "progress": today_progress(user),
    })


@candidate_only
def networking_create(request):
    initial = {}
    alumni_id = request.GET.get("alumni", "")
    if alumni_id.isdigit():
        initial.update(alumni=alumni_id, is_alumni=True)
    platform = request.GET.get("platform", "")
    if platform in dict(NetworkingActivity.Platform.choices):
        initial["platform"] = platform
    form = NetworkingForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        activity = form.save(commit=False)
        activity.user = request.user
        activity.save()
        messages.success(request, "Networking activity logged.")
        return redirect("planner:networking")
    return render(request, "planner/networking_form.html", {"active": "networking", "form": form, "heading": "Log networking activity"})


@candidate_only
def networking_edit(request, pk):
    activity = get_object_or_404(NetworkingActivity, pk=pk, user=request.user)
    form = NetworkingForm(request.POST or None, instance=activity)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Activity updated.")
        return redirect("planner:networking")
    return render(request, "planner/networking_form.html", {"active": "networking", "form": form, "heading": "Edit networking activity"})


@candidate_only
@require_POST
def networking_delete(request, pk):
    get_object_or_404(NetworkingActivity, pk=pk, user=request.user).delete()
    messages.success(request, "Activity deleted.")
    return redirect("planner:networking")


# ------------------------------------------------------------------ follow-ups
@candidate_only
def followup_list(request):
    user = request.user
    recently_done = ExternalApplication.objects.filter(
        user=user, follow_up_done=True, status__in=FOLLOWUP_STATUSES
    ).order_by("-updated_at")[:8]
    return render(request, "planner/followups.html", {
        "active": "followups",
        "due": followups_due(user),
        "upcoming": followups_upcoming(user, 14),
        "recently_done": recently_done,
    })


@candidate_only
@require_POST
def followup_done(request, pk):
    app = get_object_or_404(ExternalApplication, pk=pk, user=request.user)
    app.follow_up_done = True
    app.save(update_fields=["follow_up_done", "updated_at"])
    messages.success(request, f"Follow-up for {app.company_name} marked as done.")
    return redirect(_safe_next(request, "planner:followups"))


@candidate_only
@require_POST
def followup_snooze(request, pk):
    app = get_object_or_404(ExternalApplication, pk=pk, user=request.user)
    app.follow_up_date = timezone.localdate() + timedelta(days=3)
    app.follow_up_done = False
    app.save(update_fields=["follow_up_date", "follow_up_done", "updated_at"])
    messages.info(request, f"Reminder for {app.company_name} moved to {app.follow_up_date:%d %b}.")
    return redirect(_safe_next(request, "planner:followups"))


# ------------------------------------------------------------------ weekly report & goals
@candidate_only
def weekly_report_view(request):
    user = request.user
    rows = weekly_report(user, weeks=8)
    progress = today_progress(user)
    stats = dashboard_stats(user)
    return render(request, "planner/report.html", {
        "active": "report",
        "rows": rows,
        "current": rows[0],
        "stats": stats,
        "progress": progress,
        "streak": application_streak(user, progress["app_target"]),
        "chart": {"daily": daily_series(user, 14), "week": current_week_series(user)},
    })


@candidate_only
def goals(request):
    goal = SearchGoal.for_user(request.user)
    form = GoalForm(request.POST or None, instance=goal)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Targets saved.")
        return redirect("planner:overview")
    return render(request, "planner/goals.html", {"active": "goals", "form": form, "goal": goal})
