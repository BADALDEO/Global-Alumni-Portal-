from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from planner.services import today_progress
from tracker.services import status_summary

from .forms import CompleteProfileForm, ProfileForm, SignupForm


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to Global Alumni Portal, {user.first_name}!")
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def dashboard(request):
    user = request.user
    context = {}

    if user.is_student or user.is_alumni:
        tracked = user.tracked_applications.all()
        context["summary"] = status_summary(tracked)
        context["recent_apps"] = tracked[:5]
        context["progress"] = today_progress(user)

    if user.is_student:
        context["my_referrals"] = user.referral_requests.select_related("alumni")[:4]
        context["referral_counts"] = user.referral_requests.aggregate(total=Count("id"))
        context["portal_applications"] = user.portal_applications.count()

    if user.is_alumni:
        context["incoming_referrals"] = (
            user.referral_received.filter(status="pending").select_related("student")[:4]
        )

    if user.can_post_jobs:
        from jobs.models import Application

        posted = user.posted_jobs.all()
        context["jobs_posted"] = posted.count()
        applicants = Application.objects.filter(job__posted_by=user)
        context["total_applicants"] = applicants.count()
        context["recent_applicants"] = applicants.select_related("job", "student")[:5]

    return render(request, "accounts/dashboard.html", context)


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def complete_profile(request):
    user = request.user
    if user.profile_completed:
        return redirect("dashboard")
    form = CompleteProfileForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.profile_completed = True
        user.save()
        messages.success(request, f"You're all set, {user.first_name or user.username}!")
        return redirect("dashboard")
    return render(request, "accounts/complete_profile.html", {"form": form, "hide_shell": True})
