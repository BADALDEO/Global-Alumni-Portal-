from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from referrals.models import ReferralRequest
from tracker.models import ExternalApplication
from tracker.services import status_summary

STATUS_COLORS = {
    "applied": "#94a3b8",
    "interview": "#0ea5e9",
    "selected": "#10b981",
    "rejected": "#ef4444",
    "no_response": "#f59e0b",
}


def _pct(part, whole):
    return round(part * 100 / whole) if whole else 0


def _last_months(count=6):
    today = timezone.localdate()
    year, month = today.year, today.month
    months = []
    for back in range(count - 1, -1, -1):
        m, y = month - back, year
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))
    return months


def career_stats(user):
    qs = ExternalApplication.objects.filter(user=user)
    totals = status_summary(qs)
    total = totals["total"]

    # --- platform-wise
    labels = dict(ExternalApplication.Platform.choices)
    platform_rows = (
        qs.values("platform")
        .annotate(
            count=Count("id"),
            interviews=Count("id", filter=Q(status="interview")),
            selected=Count("id", filter=Q(status="selected")),
            rejected=Count("id", filter=Q(status="rejected")),
            pending=Count("id", filter=Q(status__in=["applied", "no_response"])),
        )
        .order_by("-count")
    )
    platforms = []
    for row in platform_rows:
        reached = row["interviews"] + row["selected"]
        platforms.append({
            "key": row["platform"],
            "label": labels.get(row["platform"], row["platform"]),
            "count": row["count"],
            "interviews": row["interviews"],
            "selected": row["selected"],
            "rejected": row["rejected"],
            "pending": row["pending"],
            "share": _pct(row["count"], total),
            "interview_rate": _pct(reached, row["count"]),
        })

    # --- monthly trend (last 6 months)
    rows = (
        qs.annotate(month=TruncMonth("applied_date"))
        .values("month")
        .annotate(c=Count("id"))
        .order_by("month")
    )
    counts = {(r["month"].year, r["month"].month): r["c"] for r in rows if r["month"]}
    months = _last_months(6)
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly = {
        "labels": [f"{month_names[m - 1]} {str(y)[2:]}" for y, m in months],
        "data": [counts.get(key, 0) for key in months],
    }

    # --- charts payload
    status_labels = dict(ExternalApplication.Status.choices)
    status_keys = ["applied", "interview", "selected", "rejected", "no_response"]
    chart = {
        "status": {
            "labels": [status_labels[k] for k in status_keys],
            "data": [totals[k] for k in status_keys],
            "colors": [STATUS_COLORS[k] for k in status_keys],
        },
        "platform": {
            "labels": [p["label"] for p in platforms],
            "data": [p["count"] for p in platforms],
        },
        "monthly": monthly,
    }

    # --- rates
    reached_interview = totals["interview"] + totals["selected"]
    responded = reached_interview + totals["rejected"]
    rates = {
        "interview": _pct(reached_interview, total),
        "response": _pct(responded, total),
        "success": _pct(totals["selected"], total),
    }

    # --- plain-language insights
    insights = []
    if total:
        insights.append(
            f"You have applied to {total} job{'s' if total != 1 else ''} across "
            f"{len(platforms)} platform{'s' if len(platforms) != 1 else ''}."
        )
        top = platforms[0]
        insights.append(f"Most of your applications ({top['count']}) came from {top['label']} ({top['share']}%).")
        contenders = [p for p in platforms if p["count"] >= 2 and p["interview_rate"] > 0]
        if contenders:
            best = max(contenders, key=lambda p: (p["interview_rate"], p["count"]))
            insights.append(
                f"{best['label']} is converting best: {best['interview_rate']}% of your applications there "
                "reached the interview stage."
            )
        if totals["no_response"]:
            insights.append(
                f"{totals['no_response']} application{'s have' if totals['no_response'] != 1 else ' has'} had no "
                "response. A follow-up email or an alumni referral can help."
            )
        if totals["selected"]:
            insights.append(f"Congratulations! You have been selected in {totals['selected']} application"
                            f"{'s' if totals['selected'] != 1 else ''}.")

    # --- referrals (as student: requests made, as alumni: requests received)
    if user.is_alumni:
        ref_qs = ReferralRequest.objects.filter(alumni=user)
    else:
        ref_qs = ReferralRequest.objects.filter(student=user)
    referrals = ref_qs.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        accepted=Count("id", filter=Q(status="accepted")),
        rejected=Count("id", filter=Q(status="rejected")),
    )

    return {
        "totals": totals,
        "rates": rates,
        "platforms": platforms,
        "chart": chart,
        "insights": insights,
        "referrals": referrals,
    }
