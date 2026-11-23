from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from core.files import serve_file

from .forms import ExternalApplicationForm, QuickStatusForm
from .models import ExternalApplication
from .services import status_summary

candidate_only = role_required("student", "alumni")


@candidate_only
def application_list(request):
    all_apps = ExternalApplication.objects.filter(user=request.user).select_related("resume_version")
    summary = status_summary(all_apps)

    apps = all_apps
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    platform = request.GET.get("platform", "")

    if q:
        apps = apps.filter(Q(company_name__icontains=q) | Q(job_title__icontains=q))
    if status in dict(ExternalApplication.Status.choices):
        apps = apps.filter(status=status)
    if platform in dict(ExternalApplication.Platform.choices):
        apps = apps.filter(platform=platform)

    page_obj = Paginator(apps, 10).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "tracker/application_list.html", {
        "page_obj": page_obj,
        "summary": summary,
        "has_any": summary["total"] > 0,
        "q": q,
        "status": status,
        "platform": platform,
        "status_choices": ExternalApplication.Status.choices,
        "platform_choices": ExternalApplication.Platform.choices,
        "querystring": params.urlencode(),
    })


@candidate_only
def application_create(request):
    form = ExternalApplicationForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        app = form.save(commit=False)
        app.user = request.user
        app.save()
        messages.success(request, "Application saved to your tracker.")
        return redirect("tracker:list")
    return render(request, "tracker/application_form.html", {"form": form, "heading": "Add Application"})


@candidate_only
def application_edit(request, pk):
    app = get_object_or_404(ExternalApplication, pk=pk, user=request.user)
    form = ExternalApplicationForm(request.POST or None, request.FILES or None, instance=app, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Application updated.")
        return redirect("tracker:list")
    return render(request, "tracker/application_form.html", {"form": form, "heading": "Edit Application", "app": app})


@candidate_only
def application_delete(request, pk):
    app = get_object_or_404(ExternalApplication, pk=pk, user=request.user)
    if request.method == "POST":
        app.delete()
        messages.success(request, "Application removed.")
        return redirect("tracker:list")
    return render(request, "tracker/application_confirm_delete.html", {"app": app})


@candidate_only
@require_POST
def quick_status(request, pk):
    app = get_object_or_404(ExternalApplication, pk=pk, user=request.user)
    form = QuickStatusForm(request.POST)
    if form.is_valid():
        app.status = form.cleaned_data["status"]
        app.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Status updated to {app.get_status_display()}.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("tracker:list")


@candidate_only
def application_resume(request, pk):
    app = get_object_or_404(ExternalApplication, pk=pk)
    if app.user_id != request.user.id:
        raise PermissionDenied
    return serve_file(app.resume)
