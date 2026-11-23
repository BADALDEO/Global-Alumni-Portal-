from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from core.files import serve_file
from tracker.services import sync_portal_application

from .forms import ApplicationForm, ApplicationStatusForm, JobForm
from .models import Application, Job


@login_required
def job_list(request):
    today = timezone.localdate()
    jobs = Job.objects.filter(is_active=True).filter(
        Q(apply_deadline__isnull=True) | Q(apply_deadline__gte=today)
    ).select_related("posted_by")

    q = request.GET.get("q", "").strip()
    job_type = request.GET.get("type", "")
    location = request.GET.get("location", "").strip()

    if q:
        jobs = jobs.filter(
            Q(title__icontains=q)
            | Q(company_name__icontains=q)
            | Q(skills_required__icontains=q)
            | Q(description__icontains=q)
        )
    if job_type in dict(Job.JobType.choices):
        jobs = jobs.filter(job_type=job_type)
    if location:
        jobs = jobs.filter(location__icontains=location)

    total = jobs.count()
    page_obj = Paginator(jobs, 9).get_page(request.GET.get("page"))

    applied_ids = set()
    if request.user.is_student:
        applied_ids = set(
            Application.objects.filter(student=request.user, job__in=list(page_obj))
            .values_list("job_id", flat=True)
        )

    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "jobs/job_list.html", {
        "page_obj": page_obj,
        "total": total,
        "applied_ids": applied_ids,
        "q": q,
        "job_type": job_type,
        "location": location,
        "job_types": Job.JobType.choices,
        "querystring": params.urlencode(),
    })


@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related("posted_by"), pk=pk)
    is_owner = job.posted_by_id == request.user.id
    if not job.is_active and not is_owner:
        raise Http404("This job is no longer available.")
    already_applied = (
        request.user.is_student
        and Application.objects.filter(job=job, student=request.user).exists()
    )
    return render(request, "jobs/job_detail.html", {
        "job": job,
        "is_owner": is_owner,
        "already_applied": already_applied,
        "can_apply": request.user.is_student and job.is_open and not already_applied,
    })


@role_required("alumni", "company")
def job_create(request):
    form = JobForm(request.POST or None, initial={"company_name": request.user.company_name})
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.posted_by = request.user
        job.save()
        messages.success(request, "Job posted successfully.")
        return redirect(job)
    return render(request, "jobs/job_form.html", {"form": form, "heading": "Post a Job or Internship"})


@role_required("alumni", "company")
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk, posted_by=request.user)
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Job updated.")
        return redirect(job)
    return render(request, "jobs/job_form.html", {"form": form, "heading": "Edit Job", "job": job})


@role_required("alumni", "company")
def job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk, posted_by=request.user)
    if request.method == "POST":
        job.delete()
        messages.success(request, "Job deleted.")
        return redirect("jobs:my_posted")
    return render(request, "jobs/job_confirm_delete.html", {"job": job})


@role_required("alumni", "company")
def my_posted_jobs(request):
    jobs = Job.objects.filter(posted_by=request.user).annotate(applicant_count=Count("applications"))
    return render(request, "jobs/my_posted_jobs.html", {"jobs": jobs})


@role_required("student")
def apply(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not job.is_open:
        messages.error(request, "Applications for this job are closed.")
        return redirect(job)
    if Application.objects.filter(job=job, student=request.user).exists():
        messages.info(request, "You have already applied to this job.")
        return redirect(job)

    form = ApplicationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        application = form.save(commit=False)
        application.job = job
        application.student = request.user
        application.save()
        sync_portal_application(application)  # also lands in My Job Applications
        messages.success(request, "Application submitted! It has been added to your tracker too.")
        return redirect("jobs:my_applications")
    return render(request, "jobs/apply.html", {"form": form, "job": job})


@role_required("student")
def my_portal_applications(request):
    applications = Application.objects.filter(student=request.user).select_related("job")
    return render(request, "jobs/my_portal_applications.html", {"applications": applications})


@role_required("alumni", "company")
def applicants(request, pk):
    job = get_object_or_404(Job, pk=pk, posted_by=request.user)
    apps = job.applications.select_related("student")
    return render(request, "jobs/applicants.html", {
        "job": job,
        "applications": apps,
        "status_choices": Application.Status.choices,
    })


@role_required("alumni", "company")
@require_POST
def update_application_status(request, pk):
    application = get_object_or_404(
        Application.objects.select_related("job"), pk=pk, job__posted_by=request.user
    )
    form = ApplicationStatusForm(request.POST)
    if form.is_valid():
        application.status = form.cleaned_data["status"]
        application.save(update_fields=["status"])
        sync_portal_application(application)
        messages.success(request, f"{application.student.display_name} marked as {application.get_status_display()}.")
    return redirect("jobs:applicants", pk=application.job_id)


@login_required
def application_resume(request, pk):
    application = get_object_or_404(Application.objects.select_related("job"), pk=pk)
    if request.user.id not in (application.student_id, application.job.posted_by_id):
        raise PermissionDenied
    return serve_file(application.resume)
