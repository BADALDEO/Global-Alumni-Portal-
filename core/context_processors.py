from django.utils import timezone


def nav(request):
    """Tells the sidebar which section is active and feeds its notification badges."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    match = getattr(request, "resolver_match", None)
    namespace = match.namespace if match else ""
    name = match.url_name if match else ""

    section = ""
    if namespace == "jobs":
        if name in ("my_posted", "applicants"):
            section = "posted"
        elif name == "my_applications":
            section = "portal_apps"
        else:
            section = "jobs"
    elif namespace == "tracker":
        section = "tracker"
    elif namespace == "referrals":
        section = "directory" if name == "directory" else "referrals"
    elif namespace == "analytics":
        section = "analytics"
    elif namespace == "planner":
        if name.startswith("resume"):
            section = "plan_resumes"
        elif name.startswith("networking"):
            section = "plan_networking"
        elif name.startswith("followup"):
            section = "plan_followups"
        else:
            section = "plan"
    elif name == "dashboard":
        section = "dashboard"
    elif name == "profile":
        section = "profile"

    context = {"nav_section": section}

    role = getattr(user, "role", "")
    if role == "alumni":
        received = getattr(user, "referral_received", None)
        if received is not None:
            context["pending_referrals"] = received.filter(status="pending").count()

    if role in ("student", "alumni"):
        tracked = getattr(user, "tracked_applications", None)
        if tracked is not None:
            context["due_followups"] = tracked.filter(
                follow_up_done=False,
                follow_up_date__isnull=False,
                follow_up_date__lte=timezone.localdate(),
                status__in=("applied", "no_response", "interview"),
            ).count()
    return context


def features(request):
    from django.conf import settings

    return {"google_login_enabled": getattr(settings, "GOOGLE_LOGIN_ENABLED", False)}
