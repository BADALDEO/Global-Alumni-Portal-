from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from core.files import serve_file
from jobs.models import Job
from tracker.models import ExternalApplication

from .forms import ReferralRequestForm, ReferralResponseForm
from .models import ReferralRequest
from .notifications import notify_new_request, notify_response

student_only = role_required("student")
alumni_only = role_required("alumni")
student_or_alumni = role_required("student", "alumni")


def _digits(value):
    return value if value and value.isdigit() else None


@student_or_alumni
def referral_list(request):
    user = request.user
    if user.is_alumni:
        base = ReferralRequest.objects.filter(alumni=user).select_related("student", "job", "external_application")
    else:
        base = ReferralRequest.objects.filter(student=user).select_related("alumni", "job", "external_application")

    counts = base.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        accepted=Count("id", filter=Q(status="accepted")),
        rejected=Count("id", filter=Q(status="rejected")),
    )

    status = request.GET.get("status", "")
    referrals = base
    if status in dict(ReferralRequest.Status.choices):
        referrals = referrals.filter(status=status)

    page_obj = Paginator(referrals, 10).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "referrals/referral_list.html", {
        "page_obj": page_obj,
        "counts": counts,
        "status": status,
        "status_choices": ReferralRequest.Status.choices,
        "querystring": params.urlencode(),
    })


@student_only
def alumni_directory(request):
    alumni = (
        User.objects.filter(role=User.Role.ALUMNI)
        .annotate(referrals_given=Count("referral_received", filter=Q(referral_received__status="accepted")))
        .order_by("company_name", "first_name")
    )
    mentors_only = request.GET.get("mentor") == "1"
    if mentors_only:
        alumni = alumni.filter(open_to_mentorship=True)
    q = request.GET.get("q", "").strip()
    if q:
        alumni = alumni.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)
            | Q(company_name__icontains=q) | Q(designation__icontains=q)
        )
    page_obj = Paginator(alumni, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "referrals/alumni_directory.html", {
        "page_obj": page_obj,
        "q": q,
        "mentors_only": mentors_only,
        "querystring": params.urlencode(),
    })


@student_only
def referral_request(request):
    initial = {}
    prefill_company = ""

    alumni_id = _digits(request.GET.get("alumni"))
    if alumni_id:
        initial["alumni"] = alumni_id

    job_id = _digits(request.GET.get("job"))
    if job_id:
        job = Job.objects.filter(pk=job_id).first()
        if job:
            initial.update(job=job.pk, company_name=job.company_name, job_title=job.title)
            prefill_company = job.company_name

    app_id = _digits(request.GET.get("application"))
    if app_id:
        tracked = ExternalApplication.objects.filter(pk=app_id, user=request.user).first()
        if tracked:
            initial.update(
                external_application=tracked.pk, company_name=tracked.company_name,
                job_title=tracked.job_title, job_link=tracked.job_link,
            )
            prefill_company = tracked.company_name

    form = ReferralRequestForm(
        request.POST or None, request.FILES or None, user=request.user, initial=initial
    )
    if request.method == "POST" and form.is_valid():
        referral = form.save(commit=False)
        referral.student = request.user
        tracked = referral.external_application
        if not referral.resume and tracked and tracked.resume:
            referral.resume = tracked.resume.name
        referral.save()
        notify_new_request(referral)
        messages.success(request, f"Referral request sent to {referral.alumni.display_name}.")
        return redirect("referrals:detail", pk=referral.pk)

    company = prefill_company or (form["company_name"].value() or "")
    suggestions = []
    if company:
        suggestions = list(
            User.objects.filter(role=User.Role.ALUMNI, company_name__icontains=company)[:5]
        )

    return render(request, "referrals/referral_form.html", {"form": form, "suggestions": suggestions})


@student_or_alumni
def referral_detail(request, pk):
    referral = get_object_or_404(
        ReferralRequest.objects.select_related("student", "alumni", "job", "external_application"), pk=pk
    )
    user = request.user
    if user.id not in (referral.student_id, referral.alumni_id):
        raise PermissionDenied
    return render(request, "referrals/referral_detail.html", {
        "r": referral,
        "is_alumni_side": user.id == referral.alumni_id,
        "app_status": referral.linked_application_status(),
    })


@alumni_only
@require_POST
def referral_respond(request, pk):
    referral = get_object_or_404(ReferralRequest, pk=pk, alumni=request.user)
    if referral.status != ReferralRequest.Status.PENDING:
        messages.info(request, "You have already responded to this request.")
        return redirect("referrals:detail", pk=pk)

    form = ReferralResponseForm(request.POST)
    if form.is_valid():
        accepted = form.cleaned_data["decision"] == "accept"
        referral.status = ReferralRequest.Status.ACCEPTED if accepted else ReferralRequest.Status.REJECTED
        referral.alumni_reply = form.cleaned_data["reply"].strip()
        referral.responded_at = timezone.now()
        referral.save(update_fields=["status", "alumni_reply", "responded_at"])
        notify_response(referral)
        messages.success(request, "Referral request accepted." if accepted else "Referral request declined.")
    else:
        messages.error(request, "Could not save your response. Please try again.")
    return redirect("referrals:detail", pk=pk)


@student_only
@require_POST
def referral_withdraw(request, pk):
    referral = get_object_or_404(ReferralRequest, pk=pk, student=request.user)
    if referral.status == ReferralRequest.Status.PENDING:
        referral.status = ReferralRequest.Status.WITHDRAWN
        referral.responded_at = timezone.now()
        referral.save(update_fields=["status", "responded_at"])
        messages.success(request, "Request withdrawn.")
    return redirect("referrals:detail", pk=pk)


@student_or_alumni
def referral_resume(request, pk):
    referral = get_object_or_404(ReferralRequest, pk=pk)
    if request.user.id not in (referral.student_id, referral.alumni_id):
        raise PermissionDenied
    return serve_file(referral.resume)
